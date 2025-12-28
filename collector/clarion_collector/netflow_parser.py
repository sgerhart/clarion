"""
NetFlow packet parser for v5, v9, and IPFIX.
"""

import struct
import ipaddress
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NetFlowRecord:
    """Internal NetFlow record representation."""
    
    def __init__(self):
        self.src_ip: Optional[str] = None
        self.dst_ip: Optional[str] = None
        self.src_port: Optional[int] = None
        self.dst_port: Optional[int] = None
        self.protocol: Optional[int] = None
        self.bytes: Optional[int] = None
        self.packets: Optional[int] = None
        self.flow_start: Optional[int] = None  # Unix timestamp
        self.flow_end: Optional[int] = None
        self.src_sgt: Optional[int] = None
        self.dst_sgt: Optional[int] = None
        self.src_mac: Optional[str] = None
        self.dst_mac: Optional[str] = None
        self.vlan_id: Optional[int] = None
        self.switch_id: Optional[str] = None
        
    def to_dict(self) -> Dict:
        """Convert to dictionary for API submission."""
        return {
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port or 0,
            "dst_port": self.dst_port or 0,
            "protocol": self.protocol or 0,
            "bytes": self.bytes or 0,
            "packets": self.packets or 0,
            "flow_start": self.flow_start or int(datetime.now().timestamp()),
            "flow_end": self.flow_end or int(datetime.now().timestamp()),
            "switch_id": self.switch_id,
            "src_sgt": self.src_sgt,
            "dst_sgt": self.dst_sgt,
            "src_mac": self.src_mac,
            "dst_mac": self.dst_mac,
            "vlan_id": self.vlan_id,
        }


class NetFlowV5Parser:
    """Parser for NetFlow v5 (fixed format)."""
    
    # NetFlow v5 header format
    HEADER_FORMAT = "!HHIIIIII"
    HEADER_SIZE = 24
    
    # NetFlow v5 record format (fixed 48 bytes)
    # According to RFC 3954, NetFlow v5 record is 48 bytes
    # Format: src_addr(4), dst_addr(4), nexthop(4), input(4), output(4),
    #         dPkts(4), dOctets(4), first(4), last(4), srcport(2), dstport(2),
    #         pad1(1), tcp_flags(1), prot(1), tos(1), src_as(2), dst_as(2),
    #         src_mask(1), dst_mask(1), pad2(2)
    # Using explicit byte-by-byte parsing for accuracy
    RECORD_SIZE = 48
    
    @staticmethod
    def parse(data: bytes, source_ip: str) -> List[NetFlowRecord]:
        """
        Parse NetFlow v5 packet.
        
        Args:
            data: Raw UDP packet data
            source_ip: Source IP of the packet (used as switch_id)
            
        Returns:
            List of NetFlowRecord objects
        """
        if len(data) < NetFlowV5Parser.HEADER_SIZE:
            logger.warning(f"NetFlow v5 packet too small: {len(data)} bytes")
            return []
        
        try:
            # Parse header
            header = struct.unpack(
                NetFlowV5Parser.HEADER_FORMAT,
                data[:NetFlowV5Parser.HEADER_SIZE]
            )
            
            version = header[0]
            if version != 5:
                logger.warning(f"Expected NetFlow v5, got version {version}")
                return []
            
            count = header[1]  # Number of flows in this packet
            sys_uptime = header[2]
            unix_secs = header[3]
            unix_nsecs = header[4]
            flow_sequence = header[5]
            engine_type = header[6]
            engine_id = header[7]
            
            # Base timestamp
            base_timestamp = unix_secs
            
            records = []
            offset = NetFlowV5Parser.HEADER_SIZE
            
            for _ in range(count):
                if offset + NetFlowV5Parser.RECORD_SIZE > len(data):
                    logger.warning(f"Incomplete record at offset {offset}")
                    break
                
                # Parse flow record (48 bytes)
                record_data = data[offset:offset + NetFlowV5Parser.RECORD_SIZE]
                
                # NetFlow v5 record: first 36 bytes are 9 unsigned ints
                # Then 2 shorts, 4 bytes, 2 shorts, 2 bytes, 1 short (12 bytes total)
                # Total: 48 bytes
                int_fields = struct.unpack("!9I", record_data[0:36])
                src_addr = int_fields[0]
                dst_addr = int_fields[1]
                nexthop = int_fields[2]
                input_intf = int_fields[3]
                output_intf = int_fields[4]
                dPkts = int_fields[5]
                dOctets = int_fields[6]
                first = int_fields[7]
                last = int_fields[8]
                
                # Remaining 12 bytes: HHBBBBHHBBH
                short_fields = struct.unpack("!HHBBBBHHBBH", record_data[36:48])
                srcport = short_fields[0]
                dstport = short_fields[1]
                pad1 = short_fields[2]
                tcp_flags = short_fields[3]
                prot = short_fields[4]
                tos = short_fields[5]
                src_as = short_fields[6]
                dst_as = short_fields[7]
                src_mask = short_fields[8]
                dst_mask = short_fields[9]
                # pad2 = short_fields[10]  # Not used
                
                # Convert IP addresses
                try:
                    src_ip = str(ipaddress.IPv4Address(src_addr))
                    dst_ip = str(ipaddress.IPv4Address(dst_addr))
                except Exception as e:
                    logger.warning(f"Invalid IP address in record: {e}")
                    offset += NetFlowV5Parser.RECORD_SIZE
                    continue
                
                # Create record
                record = NetFlowRecord()
                record.src_ip = src_ip
                record.dst_ip = dst_ip
                record.src_port = srcport
                record.dst_port = dstport
                record.protocol = prot
                record.bytes = dOctets
                record.packets = dPkts
                record.flow_start = base_timestamp - sys_uptime + (first // 1000)
                record.flow_end = base_timestamp - sys_uptime + (last // 1000)
                record.switch_id = source_ip
                
                records.append(record)
                offset += NetFlowV5Parser.RECORD_SIZE
            
            logger.debug(f"Parsed {len(records)} NetFlow v5 records from {source_ip}")
            return records
            
        except Exception as e:
            logger.error(f"Error parsing NetFlow v5 packet: {e}", exc_info=True)
            return []


# NetFlow v9 parser moved to netflow_v9.py for better organization
# Import the full implementation
from .netflow_v9 import NetFlowV9Parser, NetFlowV9TemplateManager

# For backward compatibility, keep the class name here
# But use the full implementation from netflow_v9 module


# IPFIX parser moved to ipfix_parser.py for better organization
# Import the full implementation
from .ipfix_parser import IPFIXParser, IPFIXTemplateManager

# For backward compatibility, keep the class name here
# But use the full implementation from ipfix_parser module


# Global template managers (shared across packets from same source)
_v9_template_manager = NetFlowV9TemplateManager()
_ipfix_template_manager = IPFIXTemplateManager()


def parse_netflow_packet(
    data: bytes,
    source_ip: str,
    version: Optional[int] = None
) -> List[NetFlowRecord]:
    """
    Parse a NetFlow packet (auto-detect version or use specified).
    
    Args:
        data: Raw UDP packet data
        source_ip: Source IP address of the packet
        version: Optional version hint (5, 9, or 10 for IPFIX)
        
    Returns:
        List of NetFlowRecord objects
    """
    if len(data) < 2:
        return []
    
    # Detect version if not specified
    if version is None:
        version = struct.unpack("!H", data[:2])[0]
    
    if version == 5:
        return NetFlowV5Parser.parse(data, source_ip)
    elif version == 9:
        parser = NetFlowV9Parser(template_manager=_v9_template_manager)
        return parser.parse(data, source_ip)
    elif version == 10:  # IPFIX
        parser = IPFIXParser(template_manager=_ipfix_template_manager)
        return parser.parse(data, source_ip)
    else:
        logger.warning(f"Unsupported NetFlow version: {version}")
        return []

