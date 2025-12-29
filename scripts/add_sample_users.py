#!/usr/bin/env python3
"""
Add sample user data to the database for testing.

Creates sample users, user-device associations, and AD group memberships.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarion.storage import get_database

def add_sample_users():
    """Add sample user data."""
    db = get_database()
    
    # Sample users
    users = [
        {
            "user_id": "S-1-5-21-1234567890-1234567890-1234567890-1001",
            "username": "john.doe",
            "email": "john.doe@example.com",
            "display_name": "John Doe",
            "department": "Engineering",
            "title": "Senior Software Engineer",
            "source": "ad",
        },
        {
            "user_id": "S-1-5-21-1234567890-1234567890-1234567890-1002",
            "username": "jane.smith",
            "email": "jane.smith@example.com",
            "display_name": "Jane Smith",
            "department": "Sales",
            "title": "Sales Manager",
            "source": "ad",
        },
        {
            "user_id": "S-1-5-21-1234567890-1234567890-1234567890-1003",
            "username": "bob.wilson",
            "email": "bob.wilson@example.com",
            "display_name": "Bob Wilson",
            "department": "IT",
            "title": "Network Administrator",
            "source": "ad",
        },
        {
            "user_id": "S-1-5-21-1234567890-1234567890-1234567890-1004",
            "username": "alice.brown",
            "email": "alice.brown@example.com",
            "display_name": "Alice Brown",
            "department": "HR",
            "title": "HR Manager",
            "source": "ad",
        },
        {
            "user_id": "S-1-5-21-1234567890-1234567890-1234567890-1005",
            "username": "charlie.davis",
            "email": "charlie.davis@example.com",
            "display_name": "Charlie Davis",
            "department": "Engineering",
            "title": "DevOps Engineer",
            "source": "ise",
        },
    ]
    
    # Add users
    print("Adding sample users...")
    for user in users:
        db.create_user(**user)
        print(f"  ✓ Added user: {user['username']} ({user['display_name']})")
    
    # AD Groups
    ad_groups = [
        # John Doe - Engineering groups
        ("S-1-5-21-1234567890-1234567890-1234567890-1001", "CN=Engineering,OU=Groups,DC=example,DC=com", "Engineering"),
        ("S-1-5-21-1234567890-1234567890-1234567890-1001", "CN=Developers,OU=Groups,DC=example,DC=com", "Developers"),
        ("S-1-5-21-1234567890-1234567890-1234567890-1001", "CN=VPN-Users,OU=Groups,DC=example,DC=com", "VPN-Users"),
        
        # Jane Smith - Sales groups
        ("S-1-5-21-1234567890-1234567890-1234567890-1002", "CN=Sales,OU=Groups,DC=example,DC=com", "Sales"),
        ("S-1-5-21-1234567890-1234567890-1234567890-1002", "CN=Managers,OU=Groups,DC=example,DC=com", "Managers"),
        
        # Bob Wilson - IT groups
        ("S-1-5-21-1234567890-1234567890-1234567890-1003", "CN=IT,OU=Groups,DC=example,DC=com", "IT"),
        ("S-1-5-21-1234567890-1234567890-1234567890-1003", "CN=Network-Admins,OU=Groups,DC=example,DC=com", "Network-Admins"),
        ("S-1-5-21-1234567890-1234567890-1234567890-1003", "CN=VPN-Users,OU=Groups,DC=example,DC=com", "VPN-Users"),
        
        # Alice Brown - HR groups
        ("S-1-5-21-1234567890-1234567890-1234567890-1004", "CN=HR,OU=Groups,DC=example,DC=com", "HR"),
        ("S-1-5-21-1234567890-1234567890-1234567890-1004", "CN=Managers,OU=Groups,DC=example,DC=com", "Managers"),
        
        # Charlie Davis - Engineering/DevOps groups
        ("S-1-5-21-1234567890-1234567890-1234567890-1005", "CN=Engineering,OU=Groups,DC=example,DC=com", "Engineering"),
        ("S-1-5-21-1234567890-1234567890-1234567890-1005", "CN=DevOps,OU=Groups,DC=example,DC=com", "DevOps"),
        ("S-1-5-21-1234567890-1234567890-1234567890-1005", "CN=VPN-Users,OU=Groups,DC=example,DC=com", "VPN-Users"),
    ]
    
    # Add AD group memberships
    print("\nAdding AD group memberships...")
    for user_id, group_id, group_name in ad_groups:
        db.create_ad_group_membership(user_id, group_id, group_name)
    print(f"  ✓ Added {len(ad_groups)} group memberships")
    
    # User-Device Associations (associate users with some devices)
    # Note: We'll use placeholder endpoint IDs - in real usage these would be actual MAC addresses
    associations = [
        # John Doe's devices
        ("S-1-5-21-1234567890-1234567890-1234567890-1001", "00:11:22:33:44:55", "192.168.1.100", "ise_session", "sess-001"),
        ("S-1-5-21-1234567890-1234567890-1234567890-1001", "00:11:22:33:44:56", "192.168.1.101", "ise_session", "sess-002"),
        
        # Jane Smith's devices
        ("S-1-5-21-1234567890-1234567890-1234567890-1002", "00:11:22:33:44:57", "192.168.1.102", "ise_session", "sess-003"),
        
        # Bob Wilson's devices
        ("S-1-5-21-1234567890-1234567890-1234567890-1003", "00:11:22:33:44:58", "192.168.1.103", "ise_session", "sess-004"),
        ("S-1-5-21-1234567890-1234567890-1234567890-1003", "00:11:22:33:44:59", "192.168.1.104", "ad_computer", None),
        
        # Alice Brown's devices
        ("S-1-5-21-1234567890-1234567890-1234567890-1004", "00:11:22:33:44:60", "192.168.1.105", "ise_session", "sess-005"),
        
        # Charlie Davis's devices
        ("S-1-5-21-1234567890-1234567890-1234567890-1005", "00:11:22:33:44:61", "192.168.1.106", "ise_session", "sess-006"),
        ("S-1-5-21-1234567890-1234567890-1234567890-1005", "00:11:22:33:44:62", "192.168.1.107", "ise_session", "sess-007"),
    ]
    
    # Add user-device associations
    print("\nAdding user-device associations...")
    for user_id, endpoint_id, ip_address, assoc_type, session_id in associations:
        db.create_user_device_association(user_id, endpoint_id, ip_address, assoc_type, session_id)
    print(f"  ✓ Added {len(associations)} user-device associations")
    
    print("\n✅ Sample user data added successfully!")
    print(f"\nSummary:")
    print(f"  - {len(users)} users")
    print(f"  - {len(ad_groups)} AD group memberships")
    print(f"  - {len(associations)} user-device associations")

if __name__ == "__main__":
    add_sample_users()

