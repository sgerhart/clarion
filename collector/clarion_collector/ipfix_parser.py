"""
IPFIX Template Parsing and Management

Implements template-based parsing for IPFIX according to RFC 5101, RFC 5102.
"""

import struct
import ipaddress
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

from .netflow_parser import NetFlowRecord

logger = logging.getLogger(__name__)


# IPFIX Information Elements (IE) - Standard IEs from RFC 5102
# Common IEs we care about
IPFIX_IES = {
    7: ('sourceTransportPort', 2),        # Unsigned 16-bit
    8: ('sourceIPv4Address', 4),         # IPv4 address
    11: ('destinationTransportPort', 2),  # Unsigned 16-bit
    12: ('destinationIPv4Address', 4),    # IPv4 address
    4: ('protocolIdentifier', 1),          # Unsigned 8-bit
    85: ('octetDeltaCount', 8),           # Unsigned 64-bit
    86: ('packetDeltaCount', 8),           # Unsigned 64-bit
    152: ('flowStartMilliseconds', 8),     # Date and time (milliseconds)
    153: ('flowEndMilliseconds', 8),       # Date and time (milliseconds)
    56: ('sourceMacAddress', 6),          # MAC address
    57: ('destinationMacAddress', 6),     # MAC address
    58: ('vlanId', 2),                    # Unsigned 16-bit
    15: ('ipNextHopIPv4Address', 4),      # IPv4 address
    # TrustSec SGT fields (CRITICAL)
    411: ('sourceSecurityGroupTag', 2),   # Unsigned 16-bit (Cisco enterprise IE)
    412: ('destinationSecurityGroupTag', 2), # Unsigned 16-bit (Cisco enterprise IE)
}

# Enterprise IDs
CISCO_ENTERPRISE_ID = 9  # Cisco Systems
# Enterprise-specific IEs are in format: (enterprise_id << 16) | ie_id


class IPFIXTemplate:
    """Represents an IPFIX template."""
    
    def __init__(self, template_id: int, field_count: int, fields: List[Tuple[int, int, Optional[int]]]):
        """
        Initialize template.
        
        Args:
            template_id: Template ID
            field_count: Number of fields
            fields: List of (ie_id, field_length, enterprise_id) tuples
                   enterprise_id is None for standard IEs
        """
        self.template_id = template_id
        self.field_count = field_count
        self.fields = fields  # List of (ie_id, field_length, enterprise_id)
        self.created_at = time.time()
        self.last_used = time.time()
        # Calculate total record size (with padding)
        self.record_size = sum(length for _, length, _ in fields)
        # Add padding to 4-byte boundary
        if self.record_size % 4 != 0:
            self.record_size += 4 - (self.record_size % 4)
    
    def is_expired(self, max_age: int = 1800) -> bool:
        """Check if template is expired (default 30 minutes)."""
        return (time.time() - self.last_used) > max_age
    
    def update_usage(self):
        """Update last used timestamp."""
        self.last_used = time.time()


class IPFIXTemplateManager:
    """Manages IPFIX templates per observation domain."""
    
    def __init__(self, template_expiry: int = 1800):
        """
        Initialize template manager.
        
        Args:
            template_expiry: Template expiry time in seconds (default: 30 minutes)
        """
        self.templates: Dict[Tuple[int, int, int], IPFIXTemplate] = {}  # (source_id, obs_domain_id, template_id) -> template
        self.template_expiry = template_expiry
    
    def add_template(self, source_id: int, obs_domain_id: int, template_id: int, field_count: int, fields: List[Tuple[int, int, Optional[int]]]):
        """Add or update a template."""
        key = (source_id, obs_domain_id, template_id)
        template = IPFIXTemplate(template_id, field_count, fields)
        self.templates[key] = template
        logger.debug(f"Added IPFIX template {template_id} from source {source_id}, domain {obs_domain_id} with {field_count} fields")
    
    def get_template(self, source_id: int, obs_domain_id: int, template_id: int) -> Optional[IPFIXTemplate]:
        """Get a template, checking for expiry."""
        key = (source_id, obs_domain_id, template_id)
        template = self.templates.get(key)
        
        if template:
            if template.is_expired(self.template_expiry):
                logger.warning(f"IPFIX template {template_id} from source {source_id} expired, removing")
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
            logger.debug(f"Cleaned up {len(expired)} expired IPFIX templates")


class IPFIXParser:
    """Parser for IPFIX (IETF standard)."""
    
    HEADER_FORMAT = "!HHIIII"
    HEADER_SIZE = 20
    
    # Set header format
    SET_HEADER_FORMAT = "!HH"
    SET_HEADER_SIZE = 4
    
    def __init__(self, template_manager: Optional[IPFIXTemplateManager] = None):
        """
        Initialize parser.
        
        Args:
            template_manager: Optional shared template manager
        """
        self.template_manager = template_manager or IPFIXTemplateManager()
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
        Parse IPFIX packet (template-based).
        
        Args:
            data: Raw UDP packet data
            source_ip: Source IP of the packet
            
        Returns:
            List of NetFlowRecord objects
        """
        if len(data) < IPFIXParser.HEADER_SIZE:
            logger.warning(f"IPFIX packet too small: {len(data)} bytes")
            return []
        
        try:
            # Parse header
            header = struct.unpack(IPFIXParser.HEADER_FORMAT, data[:IPFIXParser.HEADER_SIZE])
            version = header[0]
            length = header[1]
            export_time = header[2]
            sequence = header[3]
            observation_domain_id = header[4]
            
            if version != 10:  # IPFIX is version 10
                logger.warning(f"Expected IPFIX (v10), got version {version}")
                return []
            
            if length > len(data):
                logger.warning(f"IPFIX packet length {length} exceeds data length {len(data)}")
                length = len(data)
            
            # Get source_id for this IP
            source_id_key = self._get_source_id(source_ip)
            
            records = []
            offset = IPFIXParser.HEADER_SIZE
            
            # Parse sets until we reach the end
            while offset + IPFIXParser.SET_HEADER_SIZE <= length:
                # Parse set header
                set_header = struct.unpack(
                    IPFIXParser.SET_HEADER_FORMAT,
                    data[offset:offset + IPFIXParser.SET_HEADER_SIZE]
                )
                set_id = set_header[0]
                set_length = set_header[1]
                
                if set_length < IPFIXParser.SET_HEADER_SIZE:
                    logger.warning(f"Invalid set length: {set_length}")
                    break
                
                if offset + set_length > length:
                    logger.warning(f"Set extends beyond packet: {set_length} bytes")
                    break
                
                set_data = data[offset + IPFIXParser.SET_HEADER_SIZE:offset + set_length]
                
                # Set ID 2 = template set
                # Set ID 3 = options template set
                # Set ID 256-65535 = data set (uses template)
                if set_id == 2:
                    # Template set
                    self._parse_template_set(set_data, source_id_key, observation_domain_id)
                elif set_id == 3:
                    # Options template set (skip for now)
                    logger.debug("Options template set (not yet implemented)")
                elif set_id >= 256:
                    # Data set - use template
                    template_id = set_id
                    template = self.template_manager.get_template(source_id_key, observation_domain_id, template_id)
                    if template:
                        parsed = self._parse_data_set(
                            set_data,
                            template,
                            export_time,
                            source_ip
                        )
                        records.extend(parsed)
                    else:
                        logger.warning(f"No IPFIX template found for template_id {template_id} from {source_ip}")
                
                offset += set_length
                
                # Align to 4-byte boundary
                if offset % 4 != 0:
                    offset += 4 - (offset % 4)
            
            # Cleanup expired templates periodically
            if len(records) > 0:
                self.template_manager.cleanup_expired()
            
            if records:
                logger.debug(f"Parsed {len(records)} IPFIX records from {source_ip}")
            
            return records
            
        except Exception as e:
            logger.error(f"Error parsing IPFIX packet: {e}", exc_info=True)
            return []
    
    def _parse_template_set(self, data: bytes, source_id: int, obs_domain_id: int):
        """Parse a template set."""
        offset = 0
        
        while offset + 4 <= len(data):  # Minimum template header is 4 bytes
            # Template header: template_id (2), field_count (2)
            template_header = struct.unpack("!HH", data[offset:offset + 4])
            template_id = template_header[0]
            field_count = template_header[1]
            
            offset += 4
            
            if offset + (field_count * 4) > len(data):
                logger.warning(f"Template {template_id} extends beyond set")
                break
            
            # Parse fields: ie_id (2), field_length (2)
            # For enterprise IEs: ie_id (2), field_length (2), enterprise_id (4)
            fields = []
            for _ in range(field_count):
                if offset + 4 > len(data):
                    break
                
                field_info = struct.unpack("!HH", data[offset:offset + 4])
                ie_id = field_info[0]
                field_length = field_info[1]
                offset += 4
                
                # Check if this is an enterprise IE (ie_id >= 32768)
                enterprise_id = None
                if ie_id >= 32768:
                    # Enterprise IE - next 4 bytes are enterprise ID
                    if offset + 4 <= len(data):
                        enterprise_id = struct.unpack("!I", data[offset:offset + 4])[0]
                        offset += 4
                
                fields.append((ie_id, field_length, enterprise_id))
            
            # Add template
            self.template_manager.add_template(source_id, obs_domain_id, template_id, field_count, fields)
    
    def _parse_data_set(
        self,
        data: bytes,
        template: IPFIXTemplate,
        export_time: int,
        source_ip: str
    ) -> List[NetFlowRecord]:
        """Parse a data set using a template."""
        records = []
        offset = 0
        
        # Parse records until we run out of data
        while offset + template.record_size <= len(data):
            record_data = data[offset:offset + template.record_size]
            
            # Parse fields according to template
            field_values = {}
            field_offset = 0
            
            for ie_id, field_length, enterprise_id in template.fields:
                if field_offset + field_length > len(record_data):
                    logger.warning(f"Field extends beyond record data")
                    break
                
                field_data = record_data[field_offset:field_offset + field_length]
                
                # Parse based on field type
                value = self._parse_field(ie_id, field_length, field_data, enterprise_id)
                if value is not None:
                    # Store with enterprise context if applicable
                    key = (ie_id, enterprise_id) if enterprise_id else ie_id
                    field_values[key] = value
                
                field_offset += field_length
                # Align to 4-byte boundary if needed
                if field_offset % 4 != 0:
                    field_offset += 4 - (field_offset % 4)
            
            # Convert to NetFlowRecord
            record = self._field_values_to_record(field_values, export_time, source_ip)
            if record:
                records.append(record)
            
            offset += template.record_size
            # Align to 4-byte boundary
            if offset % 4 != 0:
                offset += 4 - (offset % 4)
        
        return records
    
    def _parse_field(self, ie_id: int, field_length: int, data: bytes, enterprise_id: Optional[int] = None):
        """Parse a field value based on IE ID and length."""
        try:
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
                # IPv6 address (skip for now)
                return None
            else:
                # Variable length or unknown
                return data.hex() if len(data) <= 16 else None
        except Exception as e:
            logger.debug(f"Error parsing IE {ie_id}: {e}")
            return None
    
    def _field_values_to_record(
        self,
        field_values: Dict,
        export_time: int,
        source_ip: str
    ) -> Optional[NetFlowRecord]:
        """Convert field values to NetFlowRecord."""
        record = NetFlowRecord()
        record.switch_id = source_ip
        
        # Map IPFIX IEs to record
        # sourceIPv4Address (8)
        if 8 in field_values:
            try:
                record.src_ip = str(ipaddress.IPv4Address(field_values[8]))
            except:
                pass
        
        # destinationIPv4Address (12)
        if 12 in field_values:
            try:
                record.dst_ip = str(ipaddress.IPv4Address(field_values[12]))
            except:
                pass
        
        # sourceTransportPort (7)
        if 7 in field_values:
            record.src_port = field_values[7]
        
        # destinationTransportPort (11)
        if 11 in field_values:
            record.dst_port = field_values[11]
        
        # protocolIdentifier (4)
        if 4 in field_values:
            record.protocol = field_values[4]
        
        # octetDeltaCount (85)
        if 85 in field_values:
            record.bytes = field_values[85]
        
        # packetDeltaCount (86)
        if 86 in field_values:
            record.packets = field_values[86]
        
        # flowStartMilliseconds (152) - 8 bytes timestamp
        if 152 in field_values:
            # Convert milliseconds since epoch to seconds
            record.flow_start = field_values[152] // 1000
        
        # flowEndMilliseconds (153) - 8 bytes timestamp
        if 153 in field_values:
            record.flow_end = field_values[153] // 1000
        
        # sourceMacAddress (56)
        if 56 in field_values:
            record.src_mac = field_values[56]
        
        # destinationMacAddress (57)
        if 57 in field_values:
            record.dst_mac = field_values[57]
        
        # vlanId (58)
        if 58 in field_values:
            record.vlan_id = field_values[58]
        
        # sourceSecurityGroupTag (411) - CRITICAL for TrustSec
        if 411 in field_values:
            record.src_sgt = field_values[411]
        elif (411, CISCO_ENTERPRISE_ID) in field_values:
            record.src_sgt = field_values[(411, CISCO_ENTERPRISE_ID)]
        
        # destinationSecurityGroupTag (412) - CRITICAL for TrustSec
        if 412 in field_values:
            record.dst_sgt = field_values[412]
        elif (412, CISCO_ENTERPRISE_ID) in field_values:
            record.dst_sgt = field_values[(412, CISCO_ENTERPRISE_ID)]
        
        # Validate we have minimum required fields
        if not record.src_ip or not record.dst_ip:
            return None
        
        return record

