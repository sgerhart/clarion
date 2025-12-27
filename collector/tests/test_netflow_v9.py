"""
Tests for NetFlow v9 parser.
"""

import pytest
import struct
from clarion_collector.netflow_v9 import NetFlowV9Parser, NetFlowV9TemplateManager


def test_netflow_v9_template_parsing():
    """Test NetFlow v9 template parsing."""
    # Create a NetFlow v9 packet with template
    header = struct.pack("!HHIIII",
        9,      # version
        1,      # count (flow sets)
        1000,   # sys_uptime
        1234567890,  # unix_secs
        1,      # sequence
        0,      # source_id
    )
    
    # Template flow set (ID 0)
    # Template header: template_id (2), field_count (2)
    # Fields: field_type (2), field_length (2)
    template_id = 256
    field_count = 5
    
    template_header = struct.pack("!HH", template_id, field_count)
    
    # Fields: IPV4_SRC_ADDR(8,4), IPV4_DST_ADDR(12,4), L4_SRC_PORT(7,2), L4_DST_PORT(11,2), PROTOCOL(4,1)
    fields = struct.pack("!HHHHHHHHHH",
        8, 4,   # IPV4_SRC_ADDR
        12, 4,  # IPV4_DST_ADDR
        7, 2,   # L4_SRC_PORT
        11, 2,  # L4_DST_PORT
        4, 1,   # PROTOCOL
    )
    
    flowset_length = 4 + len(template_header) + len(fields)
    flowset_header = struct.pack("!HH", 0, flowset_length)  # ID 0 = template
    
    template_flowset = flowset_header + template_header + fields
    
    packet = header + template_flowset
    
    parser = NetFlowV9Parser()
    records = parser.parse(packet, "192.168.1.1")
    
    # Should parse template but return no data records (no data flow set)
    assert len(records) == 0
    
    # Check that template was stored
    source_id = parser._get_source_id("192.168.1.1")
    template = parser.template_manager.get_template(source_id, template_id)
    assert template is not None
    assert template.template_id == template_id
    assert template.field_count == field_count


def test_netflow_v9_invalid_version():
    """Test that invalid version is rejected."""
    header = struct.pack("!HHIIII",
        5,      # Wrong version
        1,
        1000,
        1234567890,
        1,
        0,
    )
    
    parser = NetFlowV9Parser()
    records = parser.parse(header, "192.168.1.1")
    assert len(records) == 0

