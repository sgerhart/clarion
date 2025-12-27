"""
Tests for NetFlow v5 parser.
"""

import pytest
import struct
import ipaddress
from clarion_collector.netflow_parser import NetFlowV5Parser, NetFlowRecord


def test_netflow_v5_header_parsing():
    """Test NetFlow v5 header parsing."""
    # Create a minimal valid NetFlow v5 header
    header = struct.pack("!HHIIIIII",
        5,      # version
        1,      # count
        1000,   # sys_uptime
        1234567890,  # unix_secs
        1234567890123,  # unix_nsecs
        1,      # flow_sequence
        0,      # engine_type
        0,      # engine_id
    )
    
    # Add a minimal record (48 bytes)
    # src_addr(4), dst_addr(4), nexthop(4), input(4), output(4),
    # dPkts(4), dOctets(4), first(4), last(4), srcport(2), dstport(2),
    # pad1(1), tcp_flags(1), prot(1), tos(1), src_as(2), dst_as(2),
    # src_mask(1), dst_mask(1), pad2(2)
    src_ip = int(ipaddress.IPv4Address("10.0.0.1"))
    dst_ip = int(ipaddress.IPv4Address("10.0.0.2"))
    
    record = struct.pack("!IIIIIIIIIIHHBBBBHHBBH",
        src_ip,      # src_addr
        dst_ip,      # dst_addr
        0,           # nexthop
        0,           # input
        0,           # output
        10,          # dPkts
        1500,        # dOctets
        1000,        # first
        2000,        # last
        12345,       # srcport
        80,          # dstport
        0,           # pad1
        0,           # tcp_flags
        6,           # prot (TCP)
        0,           # tos
        0,           # src_as
        0,           # dst_as
        24,          # src_mask
        24,          # dst_mask
        0,           # pad2
    )
    
    packet = header + record
    
    records = NetFlowV5Parser.parse(packet, "192.168.1.1")
    
    assert len(records) == 1
    assert records[0].src_ip == "10.0.0.1"
    assert records[0].dst_ip == "10.0.0.2"
    assert records[0].src_port == 12345
    assert records[0].dst_port == 80
    assert records[0].protocol == 6
    assert records[0].packets == 10
    assert records[0].bytes == 1500
    assert records[0].switch_id == "192.168.1.1"


def test_netflow_v5_invalid_version():
    """Test that invalid version is rejected."""
    header = struct.pack("!HHIIIIII",
        9,      # Wrong version
        1,
        1000,
        1234567890,
        0,
        1,
        0,
        0,
    )
    
    records = NetFlowV5Parser.parse(header, "192.168.1.1")
    assert len(records) == 0


def test_netflow_v5_empty_packet():
    """Test that empty packet is handled."""
    records = NetFlowV5Parser.parse(b"", "192.168.1.1")
    assert len(records) == 0

