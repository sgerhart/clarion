#!/usr/bin/env python3
"""
Generate Fake ISE Session Logs

Creates realistic ISE session logs that match the traffic patterns
from the lab VMs. These logs simulate authentication and authorization
events that would be seen in a real ISE deployment.
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import argparse

# ISE session event types
EVENT_TYPES = [
    "AUTHENTICATION_SUCCESS",
    "AUTHORIZATION_SUCCESS",
    "AUTHORIZATION_FAILURE",
    "SESSION_START",
    "SESSION_END",
    "POSTURE_SUCCESS",
    "POSTURE_FAILURE",
]

# Device types based on lab roles
DEVICE_TYPES = {
    "h1": "Server",
    "h2": "Server",
    "h3": "Server",
    "h4": "Server",
    "h5": "Server",
    "h6": "Server",
    "h7": "Workstation",
    "h8": "Workstation",
    "h9": "Workstation",
    "h10": "Workstation",
    "h11": "Workstation",
    "h12": "Workstation",
    "h13": "IoT",
    "h14": "IoT",
    "h15": "IoT",
    "h16": "IoT",
    "h17": "IoT",
    "h18": "IoT",
    "h19": "IoT",
    "h20": "IoT",
    "h21": "Workstation",
    "h22": "Workstation",
    "h23": "Guest",
    "h24": "Guest",
}

# ISE profiles based on device type
ISE_PROFILES = {
    "Server": "Corporate-Servers",
    "Workstation": "Corporate-Workstations",
    "IoT": "IoT-Devices",
    "Guest": "Guest-Devices",
}

# AD groups based on device roles
AD_GROUPS = {
    "h1": ["CN=WebServers,OU=Servers,DC=corp,DC=local"],
    "h2": ["CN=AppServers,OU=Servers,DC=corp,DC=local"],
    "h3": ["CN=DatabaseServers,OU=Servers,DC=corp,DC=local"],
    "h4": ["CN=FileServers,OU=Servers,DC=corp,DC=local"],
    "h5": ["CN=DNSServers,OU=Servers,DC=corp,DC=local"],
    "h6": ["CN=PrintServers,OU=Servers,DC=corp,DC=local"],
    "h7": ["CN=Engineering,OU=Users,DC=corp,DC=local"],
    "h8": ["CN=Engineering,OU=Users,DC=corp,DC=local"],
    "h9": ["CN=Sales,OU=Users,DC=corp,DC=local"],
    "h10": ["CN=Sales,OU=Users,DC=corp,DC=local"],
    "h11": ["CN=Marketing,OU=Users,DC=corp,DC=local"],
    "h12": ["CN=Marketing,OU=Users,DC=corp,DC=local"],
    "h13": ["CN=IoT-Devices,OU=Devices,DC=corp,DC=local"],
    "h14": ["CN=IoT-Devices,OU=Devices,DC=corp,DC=local"],
    "h15": ["CN=IoT-Devices,OU=Devices,DC=corp,DC=local"],
    "h16": ["CN=IoT-Devices,OU=Devices,DC=corp,DC=local"],
    "h17": ["CN=IoT-Devices,OU=Devices,DC=corp,DC=local"],
    "h18": ["CN=IoT-Devices,OU=Devices,DC=corp,DC=local"],
    "h19": ["CN=IoT-Devices,OU=Devices,DC=corp,DC=local"],
    "h20": ["CN=IoT-Devices,OU=Devices,DC=corp,DC=local"],
    "h21": ["CN=IT-Admins,OU=Users,DC=corp,DC=local"],
    "h22": ["CN=IT-Admins,OU=Users,DC=corp,DC=local"],
    "h23": ["CN=Guests,OU=Users,DC=corp,DC=local"],
    "h24": ["CN=Guests,OU=Users,DC=corp,DC=local"],
}

# User names based on device
USERS = {
    "h7": "alice.engineer",
    "h8": "bob.engineer",
    "h9": "charlie.sales",
    "h10": "diana.sales",
    "h11": "eve.marketing",
    "h12": "frank.marketing",
    "h21": "admin1",
    "h22": "admin2",
    "h23": "guest1",
    "h24": "guest2",
}


def generate_mac(hostname: str) -> str:
    """Generate a deterministic MAC address for a host."""
    # Use hostname to generate consistent MAC
    seed = hash(hostname) % (2**24)
    return f"00:1a:2b:{seed:02x}:{seed>>8:02x}:{seed>>16:02x}"


def generate_ise_session(
    hostname: str,
    ip_address: str,
    timestamp: datetime,
    event_type: str,
) -> Dict:
    """Generate a single ISE session log entry."""
    device_type = DEVICE_TYPES.get(hostname, "Workstation")
    ise_profile = ISE_PROFILES.get(device_type, "Unknown")
    ad_groups = AD_GROUPS.get(hostname, [])
    user = USERS.get(hostname, None)
    mac = generate_mac(hostname)
    
    session = {
        "timestamp": timestamp.isoformat(),
        "event_type": event_type,
        "ip_address": ip_address,
        "mac_address": mac,
        "hostname": hostname,
        "device_type": device_type,
        "ise_profile": ise_profile,
        "ad_groups": ad_groups,
        "user_name": user,
        "switch_id": f"SW-{hostname[1:]}",
        "switch_port": random.randint(1, 48),
        "vlan": random.choice([10, 20, 30, 40, 50]),
        "auth_method": random.choice(["MAB", "802.1X", "WebAuth"]),
        "auth_status": "SUCCESS" if event_type.endswith("SUCCESS") else "FAILURE",
    }
    
    return session


def generate_ise_logs(
    output_file: str,
    duration_hours: int = 24,
    events_per_host_per_hour: int = 5,
    start_time: Optional[datetime] = None,
) -> None:
    """
    Generate ISE session logs for all lab hosts.
    
    Args:
        output_file: Path to output JSON file
        duration_hours: How many hours of logs to generate
        events_per_host_per_hour: Average events per host per hour
        start_time: Start time (defaults to now - duration_hours)
    """
    if start_time is None:
        start_time = datetime.now() - timedelta(hours=duration_hours)
    
    sessions = []
    hosts = [f"h{i}" for i in range(1, 25)]
    
    # Generate IP addresses for each host
    # Based on lab setup: VM1=10.10.0.x, VM2=10.10.1.x, VM3=10.10.2.x
    host_ips = {}
    for i, host in enumerate(hosts):
        vm = (i // 8) + 1  # 8 hosts per VM
        subnet = f"10.10.{vm-1}"
        host_num = (i % 8) + 11
        host_ips[host] = f"{subnet}.{host_num}"
    
    # Generate events
    total_events = len(hosts) * duration_hours * events_per_host_per_hour
    current_time = start_time
    
    print(f"Generating {total_events} ISE session events...")
    
    for hour in range(duration_hours):
        for host in hosts:
            # Generate events for this host this hour
            num_events = random.randint(
                events_per_host_per_hour - 2,
                events_per_host_per_hour + 2,
            )
            
            for _ in range(num_events):
                # Random time within this hour
                event_time = current_time + timedelta(
                    seconds=random.randint(0, 3600)
                )
                
                # Choose event type
                if random.random() < 0.9:  # 90% success
                    event_type = random.choice([
                        "AUTHENTICATION_SUCCESS",
                        "AUTHORIZATION_SUCCESS",
                        "SESSION_START",
                    ])
                else:
                    event_type = random.choice([
                        "AUTHORIZATION_FAILURE",
                        "POSTURE_FAILURE",
                    ])
                
                session = generate_ise_session(
                    hostname=host,
                    ip_address=host_ips[host],
                    timestamp=event_time,
                    event_type=event_type,
                )
                sessions.append(session)
        
        current_time += timedelta(hours=1)
        
        if (hour + 1) % 6 == 0:
            print(f"  Generated {len(sessions)} events so far...")
    
    # Sort by timestamp
    sessions.sort(key=lambda x: x["timestamp"])
    
    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(sessions, f, indent=2)
    
    print(f"✅ Generated {len(sessions)} ISE session events")
    print(f"   Saved to: {output_path}")
    print(f"   Time range: {sessions[0]['timestamp']} to {sessions[-1]['timestamp']}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate fake ISE session logs for lab environment"
    )
    parser.add_argument(
        "-o", "--output",
        default="lab/data/ise_sessions.json",
        help="Output file path (default: lab/data/ise_sessions.json)",
    )
    parser.add_argument(
        "-d", "--duration",
        type=int,
        default=24,
        help="Duration in hours (default: 24)",
    )
    parser.add_argument(
        "-e", "--events-per-hour",
        type=int,
        default=5,
        help="Events per host per hour (default: 5)",
    )
    
    args = parser.parse_args()
    
    generate_ise_logs(
        output_file=args.output,
        duration_hours=args.duration,
        events_per_host_per_hour=args.events_per_hour,
    )


if __name__ == "__main__":
    main()

