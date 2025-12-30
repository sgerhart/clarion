#!/usr/bin/env python3
"""
Setup Active Directory Users and Groups for Lab Testing

Creates organizational structure, security groups, and users in AD for testing.

Usage:
    python scripts/setup_ad_lab.py
    
Requirements:
    pip install ldap3
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import ldap3
from ldap3 import Server, Connection, ALL, SUBTREE, MODIFY_ADD, MODIFY_DELETE, MODIFY_REPLACE
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Lab Configuration
DC_HOST = "192.168.100.10"
DC_USER = "Administrator"
DC_PASSWORD = "C!sco#123"
BASE_DN = "DC=netlab,DC=net"  # Default, will be auto-detected if possible

# Department Structure for Lab Testing
# OUs will be constructed dynamically using the detected base DN
DEPARTMENT_CONFIG = {
    "Engineering": {
        "groups": ["Engineering-Users", "Engineering-Admins"],
        "users": [
            {"username": "eng_user1", "firstname": "Engineering", "lastname": "User1"},
            {"username": "eng_user2", "firstname": "Engineering", "lastname": "User2"},
            {"username": "eng_admin", "firstname": "Engineering", "lastname": "Admin"},
        ]
    },
    "Finance": {
        "groups": ["Finance-Users", "Finance-Managers"],
        "users": [
            {"username": "fin_user1", "firstname": "Finance", "lastname": "User1"},
            {"username": "fin_user2", "firstname": "Finance", "lastname": "User2"},
            {"username": "fin_manager", "firstname": "Finance", "lastname": "Manager"},
        ]
    },
    "HR": {
        "groups": ["HR-Users", "HR-Admins"],
        "users": [
            {"username": "hr_user1", "firstname": "HR", "lastname": "User1"},
            {"username": "hr_user2", "firstname": "HR", "lastname": "User2"},
            {"username": "hr_admin", "firstname": "HR", "lastname": "Admin"},
        ]
    },
    "Sales": {
        "groups": ["Sales-Users", "Sales-Managers"],
        "users": [
            {"username": "sales_user1", "firstname": "Sales", "lastname": "User1"},
            {"username": "sales_user2", "firstname": "Sales", "lastname": "User2"},
            {"username": "sales_manager", "firstname": "Sales", "lastname": "Manager"},
        ]
    },
    "IT": {
        "groups": ["IT-Users", "IT-Admins"],
        "users": [
            {"username": "it_user1", "firstname": "IT", "lastname": "User1"},
            {"username": "it_admin", "firstname": "IT", "lastname": "Admin"},
        ]
    },
}

# Default password for all users (will need to be changed on first login)
DEFAULT_PASSWORD = "C!sco#123"


class ADLabSetup:
    """Setup Active Directory users and groups for lab testing."""
    
    def __init__(self, dc_host: str, username: str, password: str, base_dn: str):
        self.dc_host = dc_host
        self.username = username
        self.password = password
        self.base_dn = base_dn
        
        # LDAP connection
        self.server = None
        self.conn = None
    
    def detect_base_dn(self) -> Optional[str]:
        """Auto-detect the base DN from the domain controller by querying rootDSE."""
        try:
            # Create anonymous connection to query rootDSE
            temp_server = Server(f"ldap://{self.dc_host}", get_info=ALL)
            temp_conn = Connection(temp_server, auto_bind=True)
            
            # Query rootDSE (empty DN) to get defaultNamingContext
            temp_conn.search('', '(objectClass=*)', attributes=['defaultNamingContext'], search_scope=ldap3.BASE)
            if temp_conn.entries and hasattr(temp_conn.entries[0], 'defaultNamingContext'):
                base_dn = str(temp_conn.entries[0].defaultNamingContext)
                temp_conn.unbind()
                logger.info(f"   Auto-detected Base DN: {base_dn}")
                return base_dn
            
            temp_conn.unbind()
        except Exception as e:
            logger.debug(f"Could not auto-detect base DN: {e}")
        
        return None
    
    def connect(self) -> bool:
        """Connect to the domain controller."""
        try:
            # Auto-detect base DN if not provided or try provided one
            detected_dn = self.detect_base_dn()
            if detected_dn:
                self.base_dn = detected_dn
            
            # Use IP address directly
            server_url = f"ldap://{self.dc_host}"
            logger.info(f"Connecting to {server_url}...")
            
            self.server = Server(
                server_url,
                get_info=ALL,
                connect_timeout=10
            )
            
            # Try multiple authentication methods
            auth_methods = [
                # Method 1: username@domain.com format
                f"{self.username}@{self.base_dn.replace('DC=', '').replace(',', '.').lower()}",
                # Method 2: CN=username,CN=Users,DC=...
                f"CN={self.username},CN=Users,{self.base_dn}",
                # Method 3: Just username (sometimes works)
                self.username,
            ]
            
            connected = False
            for user_dn in auth_methods:
                try:
                    self.conn = Connection(
                        self.server,
                        user=user_dn,
                        password=self.password,
                        auto_bind=True,
                        authentication=ldap3.SIMPLE
                    )
                    connected = True
                    logger.info(f"   Authenticated as: {user_dn}")
                    break
                except Exception as e:
                    logger.debug(f"   Authentication method failed ({user_dn}): {e}")
                    continue
            
            if not connected:
                raise Exception("All authentication methods failed")
            
            logger.info(f"✅ Successfully connected to AD")
            logger.info(f"   Server: {self.server}")
            logger.info(f"   Base DN: {self.base_dn}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to AD: {e}")
            logger.info("\nTroubleshooting tips:")
            logger.info(f"   1. Verify DC is accessible: ping {self.dc_host}")
            logger.info(f"   2. Verify LDAP port is open: telnet {self.dc_host} 389")
            logger.info(f"   3. Check domain name: {self.base_dn}")
            logger.info(f"   4. Verify credentials are correct")
            logger.info(f"   5. Try specifying --base-dn explicitly")
            return False
    
    def create_ou(self, ou_dn: str, description: str = "") -> bool:
        """Create an organizational unit."""
        try:
            # Extract OU name and parent DN
            parts = ou_dn.split(',')
            ou_name = parts[0].replace('OU=', '')
            parent_dn = ','.join(parts[1:])
            
            ou_attrs = {
                'objectClass': ['organizationalUnit', 'top'],
                'ou': ou_name,
            }
            if description:
                ou_attrs['description'] = description
            
            # Try to add - if it fails due to existing entry, that's okay
            if not self.conn.add(ou_dn, attributes=ou_attrs):
                error_str = str(self.conn.result)
                if 'entryAlreadyExists' in error_str or 'already exists' in error_str.lower():
                    logger.info(f"   OU already exists: {ou_dn}")
                    return True
                logger.error(f"   Failed to create OU {ou_dn}: {self.conn.result}")
                return False
            
            logger.info(f"   ✅ Created OU: {ou_dn}")
            return True
            
        except ldap3.core.exceptions.LDAPEntryAlreadyExistsResult:
            logger.info(f"   OU already exists: {ou_dn}")
            return True
        except Exception as e:
            error_str = str(e)
            if 'entryAlreadyExists' in error_str or 'already exists' in error_str.lower():
                logger.info(f"   OU already exists: {ou_dn}")
                return True
            logger.error(f"   ❌ Error creating OU {ou_dn}: {e}")
            return False
    
    def create_group(self, group_dn: str, group_name: str, description: str = "", group_type: str = "Security") -> bool:
        """Create a security group."""
        try:
            # Determine group type (Security = -2147483648, Distribution = 2)
            group_type_value = -2147483648 if group_type == "Security" else 2
            
            # Global group scope = 2
            group_scope = 2  # Global
            
            group_attrs = {
                'objectClass': ['top', 'group'],
                'cn': group_name,
                'sAMAccountName': group_name,
                'groupType': group_type_value + group_scope,  # Global Security Group
                'description': description or f"{group_name} group",
            }
            
            # Try to add - if it fails due to existing entry, that's okay
            if not self.conn.add(group_dn, attributes=group_attrs):
                error_str = str(self.conn.result)
                if 'entryAlreadyExists' in error_str or 'already exists' in error_str.lower():
                    logger.info(f"   Group already exists: {group_name}")
                    return True
                logger.error(f"   Failed to create group {group_dn}: {self.conn.result}")
                return False
            
            logger.info(f"   ✅ Created group: {group_name}")
            return True
            
        except ldap3.core.exceptions.LDAPEntryAlreadyExistsResult:
            logger.info(f"   Group already exists: {group_name}")
            return True
        except Exception as e:
            error_str = str(e)
            if 'entryAlreadyExists' in error_str or 'already exists' in error_str.lower():
                logger.info(f"   Group already exists: {group_name}")
                return True
            logger.error(f"   ❌ Error creating group {group_dn}: {e}")
            return False
    
    def create_user(self, user_dn: str, username: str, firstname: str, lastname: str, 
                   email: str, password: str, ou_dn: str) -> bool:
        """Create a user account."""
        try:
            # User account control flags
            # Account disabled = 2 (0x2) - required when creating user
            # Normal account, password required = 512 (0x200)
            # Password never expires = 65536 (0x10000)
            uac_disabled = 2 | 512  # Disabled account with password required
            uac_enabled = 512 | 65536  # Normal account, password never expires (for lab)
            
            user_attrs = {
                'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
                'cn': f"{firstname} {lastname}",
                'givenName': firstname,
                'sn': lastname,
                'sAMAccountName': username,
                'userPrincipalName': f"{username}@{self.base_dn.replace('DC=', '').replace(',', '.').lower()}",
                'mail': email,
                'displayName': f"{firstname} {lastname}",
                'userAccountControl': str(uac_disabled),  # Create disabled first
            }
            
            # Try to add - if it fails due to existing entry, that's okay
            if not self.conn.add(user_dn, attributes=user_attrs):
                error_str = str(self.conn.result)
                if 'entryAlreadyExists' in error_str or 'already exists' in error_str.lower():
                    logger.info(f"   User already exists: {username}")
                    return True
                logger.error(f"   Failed to create user {user_dn}: {self.conn.result}")
                return False
            
            # Set password (requires special encoding and secure connection)
            # Note: This requires LDAPS or signing. Try with regular connection first.
            unicode_password = f'"{password}"'.encode('utf-16-le')
            password_mod = {'unicodePwd': [unicode_password]}
            
            # Try to set password - if it fails, we'll still enable the account
            # (user will need to reset password on first login)
            password_set = self.conn.modify(user_dn, password_mod)
            if not password_set:
                logger.warning(f"   Warning: Could not set password for {username} (may need LDAPS): {self.conn.result}")
                logger.warning(f"   User will need to reset password on first login")
            
            # Enable account and set password never expires
            if not self.conn.modify(user_dn, {'userAccountControl': [(MODIFY_REPLACE, [uac_enabled])]}):
                logger.warning(f"   Warning: Could not enable account for {username}: {self.conn.result}")
            
            logger.info(f"   ✅ Created user: {username} ({firstname} {lastname})")
            return True
            
        except ldap3.core.exceptions.LDAPEntryAlreadyExistsResult:
            logger.info(f"   User already exists: {username}")
            return True
        except Exception as e:
            error_str = str(e)
            if 'entryAlreadyExists' in error_str or 'already exists' in error_str.lower():
                logger.info(f"   User already exists: {username}")
                return True
            logger.error(f"   ❌ Error creating user {user_dn}: {e}")
            return False
    
    def add_user_to_group(self, user_dn: str, group_dn: str) -> bool:
        """Add a user to a group."""
        try:
            # Use the provided user_dn directly
            user_dn_actual = user_dn
            
            # Add user to group (member attribute)
            if not self.conn.modify(group_dn, {'member': [(MODIFY_ADD, [user_dn_actual])]}):
                # Check if user is already a member
                error_desc = str(self.conn.result.get('description', '')).lower()
                if 'attributeOrValueExists' in error_desc or 'entryAlreadyExists' in error_desc or 'already exists' in error_desc:
                    # User already in group - that's fine
                    return True
                logger.error(f"   Failed to add user to group: {self.conn.result}")
                return False
            
            logger.info(f"   ✅ Added user to group")
            return True
            
        except Exception as e:
            logger.error(f"   ❌ Error adding user to group: {e}")
            return False
    
    def setup_lab(self):
        """Setup all OUs, groups, and users for lab testing."""
        if not self.connect():
            return False
        
        logger.info("\n" + "="*60)
        logger.info("Setting up AD Lab Structure")
        logger.info("="*60)
        
        total_users = 0
        total_groups = 0
        
        # Extract domain name for email addresses
        domain_name = self.base_dn.replace('DC=', '').replace(',', '.').lower()
        
        for dept_name, dept_config in DEPARTMENT_CONFIG.items():
            logger.info(f"\n📁 Department: {dept_name}")
            
            # Construct OU DN using detected base DN
            ou_dn = f"OU={dept_name},{self.base_dn}"
            logger.info(f"  Creating OU: {ou_dn}")
            if not self.create_ou(ou_dn, f"Organizational unit for {dept_name} department"):
                logger.warning(f"  ⚠️  Failed to create OU, continuing...")
            
            # Create groups
            for group_name in dept_config['groups']:
                group_dn = f"CN={group_name},{ou_dn}"
                logger.info(f"  Creating group: {group_name}")
                if self.create_group(group_dn, group_name, f"{group_name} group for {dept_name}"):
                    total_groups += 1
            
            # Create users
            for user_info in dept_config['users']:
                username = user_info['username']
                user_dn = f"CN={user_info['firstname']} {user_info['lastname']},{ou_dn}"
                email = f"{username}@{domain_name}"
                logger.info(f"  Creating user: {username}")
                
                if self.create_user(
                    user_dn=user_dn,
                    username=username,
                    firstname=user_info['firstname'],
                    lastname=user_info['lastname'],
                    email=email,
                    password=DEFAULT_PASSWORD,
                    ou_dn=ou_dn
                ):
                    total_users += 1
                    
                    # Add user to first group (department users group)
                    if dept_config['groups']:
                        primary_group = dept_config['groups'][0]  # Usually the "-Users" group
                        group_dn = f"CN={primary_group},{ou_dn}"
                        self.add_user_to_group(user_dn, group_dn)
                        
                        # If user is admin/manager, add to admin group
                        if 'admin' in username.lower() or 'manager' in username.lower():
                            admin_groups = [g for g in dept_config['groups'] if 'admin' in g.lower() or 'manager' in g.lower()]
                            if admin_groups:
                                admin_group_dn = f"CN={admin_groups[0]},{ou_dn}"
                                self.add_user_to_group(user_dn, admin_group_dn)
        
        logger.info("\n" + "="*60)
        logger.info("✅ AD Lab Setup Complete")
        logger.info("="*60)
        logger.info(f"Total Groups Created: {total_groups}")
        logger.info(f"Total Users Created: {total_users}")
        logger.info(f"\nDefault Password for all users: {DEFAULT_PASSWORD}")
        logger.info("(Users will need to change password on first login)")
        
        self.conn.unbind()
        return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup AD users and groups for lab testing")
    parser.add_argument("--dc-host", default=DC_HOST, help="Domain Controller hostname or IP")
    parser.add_argument("--username", default=DC_USER, help="AD administrator username")
    parser.add_argument("--password", default=DC_PASSWORD, help="AD administrator password")
    parser.add_argument("--base-dn", default=BASE_DN, help="Base DN (e.g., DC=lab,DC=local)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't make changes)")
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
        logger.info(f"\nWould create (using base DN: {args.base_dn}):")
        for dept_name, dept_config in DEPARTMENT_CONFIG.items():
            ou_dn = f"OU={dept_name},{args.base_dn}"
            logger.info(f"  {dept_name}:")
            logger.info(f"    OU: {ou_dn}")
            logger.info(f"    Groups: {', '.join(dept_config['groups'])}")
            logger.info(f"    Users: {len(dept_config['users'])} users")
        return
    
    setup = ADLabSetup(
        dc_host=args.dc_host,
        username=args.username,
        password=args.password,
        base_dn=args.base_dn
    )
    
    setup.setup_lab()


if __name__ == "__main__":
    main()

