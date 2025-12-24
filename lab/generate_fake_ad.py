#!/usr/bin/env python3
"""
Generate Fake AD Logs

Creates realistic Active Directory logs that match the traffic patterns
from the lab VMs. These logs simulate authentication, group membership,
and user activity events.
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import argparse

# AD event types
EVENT_TYPES = [
    "LOGON",
    "LOGOFF",
    "ACCOUNT_LOCKOUT",
    "GROUP_MEMBERSHIP_CHANGE",
    "PASSWORD_CHANGE",
    "ACCOUNT_CREATED",
    "ACCOUNT_DISABLED",
]

# AD groups
AD_GROUPS = {
    "Engineering": {
        "members": ["alice.engineer", "bob.engineer"],
        "description": "Engineering Department",
    },
    "Sales": {
        "members": ["charlie.sales", "diana.sales"],
        "description": "Sales Department",
    },
    "Marketing": {
        "members": ["eve.marketing", "frank.marketing"],
        "description": "Marketing Department",
    },
    "IT-Admins": {
        "members": ["admin1", "admin2"],
        "description": "IT Administrators",
    },
    "Guests": {
        "members": ["guest1", "guest2"],
        "description": "Guest Users",
    },
    "WebServers": {
        "members": ["svc_web1", "svc_web2"],
        "description": "Web Server Service Accounts",
    },
    "AppServers": {
        "members": ["svc_app1", "svc_app2"],
        "description": "Application Server Service Accounts",
    },
    "DatabaseServers": {
        "members": ["svc_db1", "svc_db2"],
        "description": "Database Server Service Accounts",
    },
    "FileServers": {
        "members": ["svc_file1", "svc_file2"],
        "description": "File Server Service Accounts",
    },
    "DNSServers": {
        "members": ["svc_dns1", "svc_dns2"],
        "description": "DNS Server Service Accounts",
    },
    "PrintServers": {
        "members": ["svc_print1", "svc_print2"],
        "description": "Print Server Service Accounts",
    },
    "IoT-Devices": {
        "members": ["iot_camera1", "iot_camera2", "iot_sensor1", "iot_sensor2"],
        "description": "IoT Device Accounts",
    },
}

# User to host mapping
USER_TO_HOST = {
    "alice.engineer": "h7",
    "bob.engineer": "h8",
    "charlie.sales": "h9",
    "diana.sales": "h10",
    "eve.marketing": "h11",
    "frank.marketing": "h12",
    "admin1": "h21",
    "admin2": "h22",
    "guest1": "h23",
    "guest2": "h24",
}

# Host to IP mapping (same as ISE generator)
def get_host_ip(hostname: str) -> str:
    """Get IP address for a hostname."""
    host_num = int(hostname[1:])
    vm = (host_num - 1) // 8 + 1
    subnet = f"10.10.{vm-1}"
    host_ip_num = ((host_num - 1) % 8) + 11
    return f"{subnet}.{host_ip_num}"


def generate_ad_log(
    user: str,
    event_type: str,
    timestamp: datetime,
    source_ip: Optional[str] = None,
) -> Dict:
    """Generate a single AD log entry."""
    hostname = USER_TO_HOST.get(user, None)
    if source_ip is None and hostname:
        source_ip = get_host_ip(hostname)
    
    # Determine which groups this user belongs to
    user_groups = []
    for group_name, group_data in AD_GROUPS.items():
        if user in group_data["members"]:
            user_groups.append(f"CN={group_name},OU=Groups,DC=corp,DC=local")
    
    log_entry = {
        "timestamp": timestamp.isoformat(),
        "event_type": event_type,
        "user_name": user,
        "source_ip": source_ip,
        "hostname": hostname,
        "ad_groups": user_groups,
        "domain": "corp.local",
        "event_id": random.randint(4624, 4768),  # Windows security event IDs
        "status": "SUCCESS" if event_type in ["LOGON", "PASSWORD_CHANGE"] else "INFO",
    }
    
    # Add event-specific fields
    if event_type == "LOGON":
        log_entry["logon_type"] = random.choice([2, 3, 10])  # Interactive, Network, RemoteInteractive
        log_entry["authentication_package"] = "Kerberos"
    elif event_type == "LOGOFF":
        log_entry["logoff_type"] = "Normal"
    elif event_type == "GROUP_MEMBERSHIP_CHANGE":
        log_entry["group_name"] = random.choice(user_groups) if user_groups else None
        log_entry["action"] = random.choice(["ADDED", "REMOVED"])
    
    return log_entry


def generate_ad_logs(
    output_file: str,
    duration_hours: int = 24,
    events_per_user_per_hour: int = 3,
    start_time: Optional[datetime] = None,
) -> None:
    """
    Generate AD logs for all users.
    
    Args:
        output_file: Path to output JSON file
        duration_hours: How many hours of logs to generate
        events_per_user_per_hour: Average events per user per hour
        start_time: Start time (defaults to now - duration_hours)
    """
    if start_time is None:
        start_time = datetime.now() - timedelta(hours=duration_hours)
    
    logs = []
    users = list(USER_TO_HOST.keys())
    
    # Add service accounts
    for group_name, group_data in AD_GROUPS.items():
        for member in group_data["members"]:
            if member.startswith("svc_") or member.startswith("iot_"):
                users.append(member)
    
    # Generate events
    total_events = len(users) * duration_hours * events_per_user_per_hour
    current_time = start_time
    
    print(f"Generating {total_events} AD log events...")
    
    for hour in range(duration_hours):
        for user in users:
            # Generate events for this user this hour
            num_events = random.randint(
                events_per_user_per_hour - 1,
                events_per_user_per_hour + 1,
            )
            
            for _ in range(num_events):
                # Random time within this hour
                event_time = current_time + timedelta(
                    seconds=random.randint(0, 3600)
                )
                
                # Choose event type (mostly logons/logoffs)
                if random.random() < 0.7:
                    event_type = random.choice(["LOGON", "LOGOFF"])
                elif random.random() < 0.9:
                    event_type = "GROUP_MEMBERSHIP_CHANGE"
                else:
                    event_type = random.choice([
                        "PASSWORD_CHANGE",
                        "ACCOUNT_LOCKOUT",
                    ])
                
                log_entry = generate_ad_log(
                    user=user,
                    event_type=event_type,
                    timestamp=event_time,
                )
                logs.append(log_entry)
        
        current_time += timedelta(hours=1)
        
        if (hour + 1) % 6 == 0:
            print(f"  Generated {len(logs)} events so far...")
    
    # Sort by timestamp
    logs.sort(key=lambda x: x["timestamp"])
    
    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(logs, f, indent=2)
    
    print(f"✅ Generated {len(logs)} AD log events")
    print(f"   Saved to: {output_path}")
    print(f"   Time range: {logs[0]['timestamp']} to {logs[-1]['timestamp']}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate fake AD logs for lab environment"
    )
    parser.add_argument(
        "-o", "--output",
        default="lab/data/ad_logs.json",
        help="Output file path (default: lab/data/ad_logs.json)",
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
        default=3,
        help="Events per user per hour (default: 3)",
    )
    
    args = parser.parse_args()
    
    generate_ad_logs(
        output_file=args.output,
        duration_hours=args.duration,
        events_per_user_per_hour=args.events_per_hour,
    )


if __name__ == "__main__":
    main()

