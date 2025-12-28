"""
NetFlow v9 Template Parsing and Management

Implements template-based parsing for NetFlow v9 according to RFC 3954.
"""

import struct
import ipaddress
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

from .netflow_parser import NetFlowRecord

logger = logging.getLogger(__name__)


# NetFlow v9 Field Types (RFC 3954)
# Common field types we care about
NF9_FIELD_TYPES = {
    1: ('IN_BYTES', 8),           # Unsigned 64-bit
    2: ('IN_PKTS', 4),            # Unsigned 32-bit
    3: ('FLOWS', 4),              # Unsigned 32-bit
    4: ('PROTOCOL', 1),           # Unsigned 8-bit
    5: ('SRC_TOS', 1),            # Unsigned 8-bit
    6: ('TCP_FLAGS', 1),          # Unsigned 8-bit
    7: ('L4_SRC_PORT', 2),        # Unsigned 16-bit
    8: ('IPV4_SRC_ADDR', 4),      # IPv4 address
    9: ('SRC_MASK', 1),           # Unsigned 8-bit
    10: ('INPUT_SNMP', 4),        # Unsigned 32-bit
    11: ('L4_DST_PORT', 2),       # Unsigned 16-bit
    12: ('IPV4_DST_ADDR', 4),     # IPv4 address
    13: ('DST_MASK', 1),          # Unsigned 8-bit
    14: ('OUTPUT_SNMP', 4),       # Unsigned 32-bit
    15: ('IPV4_NEXT_HOP', 4),     # IPv4 address
    16: ('SRC_AS', 2),            # Unsigned 16-bit
    17: ('DST_AS', 2),            # Unsigned 16-bit
    21: ('LAST_SWITCHED', 4),      # Unsigned 32-bit (milliseconds)
    22: ('FIRST_SWITCHED', 4),     # Unsigned 32-bit (milliseconds)
    27: ('IPV6_SRC_ADDR', 16),    # IPv6 address
    28: ('IPV6_DST_ADDR', 16),    # IPv6 address
    56: ('SRC_MAC', 6),           # MAC address (6 bytes)
    57: ('DST_MAC', 6),           # MAC address (6 bytes)
    58: ('SRC_VLAN', 2),          # Unsigned 16-bit
    59: ('DST_VLAN', 2),          # Unsigned 16-bit
    85: ('TOTAL_BYTES_EXP', 8),   # Unsigned 64-bit
    86: ('TOTAL_PKTS_EXP', 8),    # Unsigned 64-bit
}

# Enterprise-specific field types (Cisco)
# These are in the range 32768-65535, with enterprise ID in high 16 bits
CISCO_ENTERPRISE_ID = 9  # Cisco Systems
# Common Cisco enterprise fields (simplified - actual mapping is more complex)
CISCO_FIELDS = {
    # SGT fields are typically in enterprise-specific templates
    # We'll detect them by field length and position in template
}


class NetFlowV9Template:
    """Represents a NetFlow v9 template."""
    
    def __init__(self, template_id: int, field_count: int, fields: List[Tuple[int, int]]):
        """
        Initialize template.
        
        Args:
            template_id: Template ID
            field_count: Number of fields
            fields: List of (field_type, field_length) tuples
        """
        self.template_id = template_id
        self.field_count = field_count
        self.fields = fields  # List of (field_type, field_length)
        self.created_at = time.time()
        self.last_used = time.time()
        # Calculate total record size
        self.record_size = sum(length for _, length in fields)
    
    def is_expired(self, max_age: int = 1800) -> bool:
        """Check if template is expired (default 30 minutes)."""
        return (time.time() - self.last_used) > max_age
    
    def update_usage(self):
        """Update last used timestamp."""
        self.last_used = time.time()


class NetFlowV9TemplateManager:
    """Manages NetFlow v9 templates per source."""
    
    def __init__(self, template_expiry: int = 1800):
        """
        Initialize template manager.
        
        Args:
            template_expiry: Template expiry time in seconds (default: 30 minutes)
        """
        self.templates: Dict[Tuple[int, int], NetFlowV9Template] = {}  # (source_id, template_id) -> template
        self.template_expiry = template_expiry
    
    def add_template(self, source_id: int, template_id: int, field_count: int, fields: List[Tuple[int, int]]):
        """Add or update a template."""
        key = (source_id, template_id)
        template = NetFlowV9Template(template_id, field_count, fields)
        self.templates[key] = template
        logger.debug(f"Added template {template_id} from source {source_id} with {field_count} fields")
    
    def get_template(self, source_id: int, template_id: int) -> Optional[NetFlowV9Template]:
        """Get a template, checking for expiry."""
        key = (source_id, template_id)
        template = self.templates.get(key)
        
        if template:
            if template.is_expired(self.template_expiry):
                logger.warning(f"Template {template_id} from source {source_id} expired, removing")
                del self.templates[key]
                return None
            template.update_usage()
        
        return template
    
    def cleanup_expired(self):
        """Remove expired templates."""
        expired = [
            key for key, template in self.templates.items()
            if template.is_expired(self.template_expiry)
        ]
        for key in expired:
            del self.templates[key]
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired templates")


class NetFlowV9Parser:
    """Parser for NetFlow v9 (template-based)."""
    
    HEADER_FORMAT = "!HHIIII"
    HEADER_SIZE = 20
    
    # Flow set header format
    FLOWSET_HEADER_FORMAT = "!HH"
    FLOWSET_HEADER_SIZE = 4
    
    def __init__(self, template_manager: Optional[NetFlowV9TemplateManager] = None):
        """
        Initialize parser.
        
        Args:
            template_manager: Optional shared template manager (for multi-source parsing)
        """
        self.template_manager = template_manager or NetFlowV9TemplateManager()
        # Track source IP to source_id mapping (simplified - use hash of IP)
        self.source_id_map: Dict[str, int] = {}
        self._next_source_id = 1
    
    def _get_source_id(self, source_ip: str) -> int:
        """Get or create source_id for a source IP."""
        if source_ip not in self.source_id_map:
            self.source_id_map[source_ip] = self._next_source_id
            self._next_source_id += 1
        return self.source_id_map[source_ip]
    
    def parse(self, data: bytes, source_ip: str) -> List[NetFlowRecord]:
        """
        Parse NetFlow v9 packet (template-based).
        
        Args:
            data: Raw UDP packet data
            source_ip: Source IP of the packet
            
        Returns:
            List of NetFlowRecord objects
        """
        if len(data) < NetFlowV9Parser.HEADER_SIZE:
            logger.warning(f"NetFlow v9 packet too small: {len(data)} bytes")
            return []
        
        try:
            # Parse header
            header = struct.unpack(NetFlowV9Parser.HEADER_FORMAT, data[:NetFlowV9Parser.HEADER_SIZE])
            version = header[0]
            count = header[1]  # Number of flow sets
            sys_uptime = header[2]
            unix_secs = header[3]
            sequence = header[4]
            source_id = header[5]
            
            if version != 9:
                logger.warning(f"Expected NetFlow v9, got version {version}")
                return []
            
            # Base timestamp
            base_timestamp = unix_secs
            
            # Get source_id for this IP
            source_id_key = self._get_source_id(source_ip)
            
            records = []
            offset = NetFlowV9Parser.HEADER_SIZE
            
            # Parse flow sets
            for _ in range(count):
                if offset + NetFlowV9Parser.FLOWSET_HEADER_SIZE > len(data):
                    break
                
                # Parse flow set header
                flowset_header = struct.unpack(
                    NetFlowV9Parser.FLOWSET_HEADER_FORMAT,
                    data[offset:offset + NetFlowV9Parser.FLOWSET_HEADER_SIZE]
                )
                flowset_id = flowset_header[0]
                flowset_length = flowset_header[1]
                
                if offset + flowset_length > len(data):
                    logger.warning(f"Flow set extends beyond packet: {flowset_length} bytes")
                    break
                
                flowset_data = data[offset + NetFlowV9Parser.FLOWSET_HEADER_SIZE:offset + flowset_length]
                
                # Flow set ID 0 = template flow set
                # Flow set ID 1 = options template flow set
                # Flow set ID 256-65535 = data flow set (uses template)
                if flowset_id == 0:
                    # Template flow set
                    self._parse_template_flowset(flowset_data, source_id_key)
                elif flowset_id == 1:
                    # Options template flow set (skip for now)
                    logger.debug("Options template flow set (not yet implemented)")
                elif flowset_id >= 256:
                    # Data flow set - use template
                    template_id = flowset_id
                    template = self.template_manager.get_template(source_id_key, template_id)
                    if template:
                        parsed = self._parse_data_flowset(
                            flowset_data,
                            template,
                            base_timestamp,
                            sys_uptime,
                            source_ip
                        )
                        records.extend(parsed)
                    else:
                        logger.warning(f"No template found for template_id {template_id} from {source_ip}")
                
                offset += flowset_length
                
                # Align to 4-byte boundary
                if offset % 4 != 0:
                    offset += 4 - (offset % 4)
            
            # Cleanup expired templates periodically
            if len(records) > 0:
                self.template_manager.cleanup_expired()
            
            if records:
                logger.debug(f"Parsed {len(records)} NetFlow v9 records from {source_ip}")
            
            return records
            
        except Exception as e:
            logger.error(f"Error parsing NetFlow v9 packet: {e}", exc_info=True)
            return []
    
    def _parse_template_flowset(self, data: bytes, source_id: int):
        """Parse a template flow set."""
        offset = 0
        
        while offset + 4 <= len(data):  # Minimum template header is 4 bytes
            # Template header: template_id (2), field_count (2)
            template_header = struct.unpack("!HH", data[offset:offset + 4])
            template_id = template_header[0]
            field_count = template_header[1]
            
            offset += 4
            
            if offset + (field_count * 4) > len(data):
                logger.warning(f"Template {template_id} extends beyond flow set")
                break
            
            # Parse fields: field_type (2), field_length (2)
            fields = []
            for _ in range(field_count):
                field_info = struct.unpack("!HH", data[offset:offset + 4])
                field_type = field_info[0]
                field_length = field_info[1]
                fields.append((field_type, field_length))
                offset += 4
            
            # Add template
            self.template_manager.add_template(source_id, template_id, field_count, fields)
    
    def _parse_data_flowset(
        self,
        data: bytes,
        template: NetFlowV9Template,
        base_timestamp: int,
        sys_uptime: int,
        source_ip: str
    ) -> List[NetFlowRecord]:
        """Parse a data flow set using a template."""
        records = []
        offset = 0
        
        # Parse records until we run out of data
        while offset + template.record_size <= len(data):
            record_data = data[offset:offset + template.record_size]
            
            # Parse fields according to template
            field_values = {}
            field_offset = 0
            
            for field_type, field_length in template.fields:
                if field_offset + field_length > len(record_data):
                    logger.warning(f"Field extends beyond record data")
                    break
                
                field_data = record_data[field_offset:field_offset + field_length]
                
                # Parse based on field type
                value = self._parse_field(field_type, field_length, field_data)
                if value is not None:
                    field_values[field_type] = value
                
                field_offset += field_length
                # Align to 4-byte boundary if needed
                if field_offset % 4 != 0:
                    field_offset += 4 - (field_offset % 4)
            
            # Convert to NetFlowRecord
            record = self._field_values_to_record(field_values, base_timestamp, sys_uptime, source_ip)
            if record:
                records.append(record)
            
            offset += template.record_size
            # Align to 4-byte boundary
            if offset % 4 != 0:
                offset += 4 - (offset % 4)
        
        return records
    
    def _parse_field(self, field_type: int, field_length: int, data: bytes):
        """Parse a field value based on type and length."""
        try:
            if field_type in NF9_FIELD_TYPES:
                expected_length = NF9_FIELD_TYPES[field_type][1]
                if field_length != expected_length:
                    logger.debug(f"Field type {field_type} length mismatch: expected {expected_length}, got {field_length}")
            
            # Parse based on length
            if field_length == 1:
                return struct.unpack("!B", data)[0]
            elif field_length == 2:
                return struct.unpack("!H", data)[0]
            elif field_length == 4:
                return struct.unpack("!I", data)[0]
            elif field_length == 8:
                return struct.unpack("!Q", data)[0]
            elif field_length == 6:
                # MAC address
                return ':'.join(f'{b:02x}' for b in data)
            elif field_length == 16:
                # IPv6 address (skip for now, we only support IPv4)
                return None
            else:
                # Variable length or unknown
                return data.hex() if len(data) <= 16 else None
        except Exception as e:
            logger.debug(f"Error parsing field type {field_type}: {e}")
            return None
    
    def _field_values_to_record(
        self,
        field_values: Dict[int, any],
        base_timestamp: int,
        sys_uptime: int,
        source_ip: str
    ) -> Optional[NetFlowRecord]:
        """Convert field values to NetFlowRecord."""
        record = NetFlowRecord()
        record.switch_id = source_ip
        
        # Map NetFlow v9 fields to record
        # IPV4_SRC_ADDR (8)
        if 8 in field_values:
            try:
                record.src_ip = str(ipaddress.IPv4Address(field_values[8]))
            except:
                pass
        
        # IPV4_DST_ADDR (12)
        if 12 in field_values:
            try:
                record.dst_ip = str(ipaddress.IPv4Address(field_values[12]))
            except:
                pass
        
        # L4_SRC_PORT (7)
        if 7 in field_values:
            record.src_port = field_values[7]
        
        # L4_DST_PORT (11)
        if 11 in field_values:
            record.dst_port = field_values[11]
        
        # PROTOCOL (4)
        if 4 in field_values:
            record.protocol = field_values[4]
        
        # IN_BYTES (1) or TOTAL_BYTES_EXP (85)
        if 85 in field_values:
            record.bytes = field_values[85]
        elif 1 in field_values:
            record.bytes = field_values[1]
        
        # IN_PKTS (2) or TOTAL_PKTS_EXP (86)
        if 86 in field_values:
            record.packets = field_values[86]
        elif 2 in field_values:
            record.packets = field_values[2]
        
        # FIRST_SWITCHED (22)
        if 22 in field_values:
            record.flow_start = base_timestamp - sys_uptime + (field_values[22] // 1000)
        
        # LAST_SWITCHED (21)
        if 21 in field_values:
            record.flow_end = base_timestamp - sys_uptime + (field_values[21] // 1000)
        
        # SRC_MAC (56)
        if 56 in field_values:
            record.src_mac = field_values[56]
        
        # DST_MAC (57)
        if 57 in field_values:
            record.dst_mac = field_values[57]
        
        # SRC_VLAN (58) or DST_VLAN (59)
        if 58 in field_values:
            record.vlan_id = field_values[58]
        elif 59 in field_values:
            record.vlan_id = field_values[59]
        
        # SGT fields - Cisco enterprise fields
        # NetFlow v9 doesn't have standard SGT fields, but Cisco uses enterprise-specific fields
        # Common patterns:
        # - Field type in range 32768-65535 indicates enterprise field
        # - Cisco SGT fields are typically at specific positions in enterprise templates
        # For now, we check for common enterprise field types that might contain SGT
        # Note: Exact field IDs vary by Cisco device/version, so this is a best-effort approach
        
        # Check for enterprise fields that might be SGT
        # Common Cisco enterprise field patterns for SGT (these are device-specific)
        # We'll look for 2-byte fields that could be SGT values (0-65535 range)
        for field_type, value in field_values.items():
            if isinstance(value, int) and 0 <= value <= 65535:
                # If it's an enterprise field (>= 32768) and value looks like SGT
                # This is heuristic - actual SGT field IDs vary by device
                if field_type >= 32768 and value > 0 and value < 65535:
                    # Try to detect if this might be SGT based on position/context
                    # For now, we'll use a simple heuristic: if we don't have SGT yet and value is reasonable
                    if record.src_sgt is None and 100 <= value <= 65000:  # Typical SGT range
                        record.src_sgt = value
                    elif record.dst_sgt is None and 100 <= value <= 65000:
                        record.dst_sgt = value
        
        # Validate we have minimum required fields
        if not record.src_ip or not record.dst_ip:
            return None
        
        return record

