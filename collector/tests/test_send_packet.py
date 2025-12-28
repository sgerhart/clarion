#!/usr/bin/env python3
"""
Simple script to send a test NetFlow v5 packet to the collector.

Usage:
    python test_send_packet.py [collector_host] [collector_port]
    
Example:
    python test_send_packet.py localhost 2055
"""

import socket
import struct
import sys
import ipaddress
import time


def create_netflow_v5_packet():
    """Create a minimal valid NetFlow v5 packet with one record."""
    current_time = int(time.time())
    current_time_ms = int((time.time() - current_time) * 1000)
    
    # NetFlow v5 Header (24 bytes)
    header = struct.pack("!HHIIIIII",
        5,              # version (5)
        1,              # count (1 record)
        current_time_ms,  # sys_uptime (milliseconds, simplified)
        current_time,   # unix_secs
        0,              # unix_nsecs
        1,              # flow_sequence
        0,              # engine_type
        0,              # engine_id
    )
    
    # NetFlow v5 Record (48 bytes)
    # Field layout: src_addr(4), dst_addr(4), nexthop(4), input(4), output(4),
    #                dPkts(4), dOctets(4), first(4), last(4), srcport(2), dstport(2),
    #                pad1(1), tcp_flags(1), prot(1), tos(1), src_as(2), dst_as(2),
    #                src_mask(1), dst_mask(1), pad2(2)
    src_ip = int(ipaddress.IPv4Address("10.0.0.1"))
    dst_ip = int(ipaddress.IPv4Address("10.0.0.2"))
    
    # NetFlow v5 record format (48 bytes total)
    # Match the parser format: 9 unsigned ints (36 bytes) + 12 bytes
    # Format matches clarion_collector/netflow_parser.py
    record = struct.pack("!IIIIIIIII",
        src_ip,         # src_addr (4 bytes) - int_fields[0]
        dst_ip,         # dst_addr (4 bytes) - int_fields[1]
        0,              # nexthop (4 bytes) - int_fields[2]
        0,              # input (4 bytes) - int_fields[3]
        0,              # output (4 bytes) - int_fields[4]
        10,             # dPkts (4 bytes) - int_fields[5] - 10 packets
        1500,           # dOctets (4 bytes) - int_fields[6] - 1500 bytes
        1000,           # first (4 bytes) - int_fields[7] - first seen (ms)
        2000,           # last (4 bytes) - int_fields[8] - last seen (ms)
    ) + struct.pack("!HHBBBBHHBBH",
        12345,          # srcport (2 bytes) - short_fields[0]
        80,             # dstport (2 bytes) - short_fields[1]
        0,              # pad1 (1 byte) - short_fields[2]
        0,              # tcp_flags (1 byte) - short_fields[3]
        6,              # prot (1 byte) - short_fields[4] - TCP
        0,              # tos (1 byte) - short_fields[5]
        0,              # src_as (2 bytes) - short_fields[6]
        0,              # dst_as (2 bytes) - short_fields[7]
        24,             # src_mask (1 byte) - short_fields[8] - /24
        24,             # dst_mask (1 byte) - short_fields[9] - /24
        0,              # pad2 (2 bytes) - short_fields[10] (not used)
    )
    
    return header + record


def main():
    """Send a test NetFlow v5 packet to the collector."""
    # Default values
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 2055
    
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Create and send packet
        packet = create_netflow_v5_packet()
        sock.sendto(packet, (host, port))
        
        print(f"✅ Sent NetFlow v5 packet to {host}:{port}")
        print(f"   Packet size: {len(packet)} bytes")
        print(f"   Flow: 10.0.0.1:12345 -> 10.0.0.2:80 (TCP, 10 packets, 1500 bytes)")
        
        sock.close()
        return 0
        
    except socket.gaierror as e:
        print(f"❌ Error: Could not resolve host {host}: {e}", file=sys.stderr)
        return 1
    except ConnectionRefusedError:
        print(f"❌ Error: Connection refused to {host}:{port}", file=sys.stderr)
        print(f"   Make sure the collector is running and listening on port {port}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

