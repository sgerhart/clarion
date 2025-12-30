#!/usr/bin/env python3
"""
Setup Cisco ISE for Lab Testing

Configures ISE for lab use, including:
- Basic connectivity test
- Creating SGTs (Security Group Tags)
- Creating authorization profiles
- Basic authorization policies
- Optional: AD identity source configuration guidance

Usage:
    python scripts/setup_ise_lab.py
    
Note: Some configurations (like AD identity source) may need to be done via ISE Admin GUI
      as they're not fully supported via ERS API.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarion.integration.ise_client import ISEClient, ISEAuthenticationError, ISEAPIError
import logging
from typing import Optional, Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Lab Configuration
ISE_URL = "https://192.168.10.31:9060"  # ERS API port
ISE_USERNAME = "admin"
ISE_PASSWORD = "C!sco#123"
VERIFY_SSL = False  # For lab with self-signed certs

# Department SGTs to create (aligned with AD groups)
# Note: ISE only allows alphanumeric and underscore characters in SGT names
DEPARTMENT_SGTS = {
    "Engineering": {"name": "Engineering_Users", "value": 10, "description": "Engineering department users"},
    "Finance": {"name": "Finance_Users", "value": 20, "description": "Finance department users"},
    "HR": {"name": "HR_Users", "value": 30, "description": "HR department users"},
    "Sales": {"name": "Sales_Users", "value": 40, "description": "Sales department users"},
    "IT": {"name": "IT_Users", "value": 50, "description": "IT department users"},
}

# Additional SGTs for infrastructure
INFRASTRUCTURE_SGTS = {
    "Servers": {"name": "Servers", "value": 100, "description": "Server infrastructure"},
    "Printers": {"name": "Printers", "value": 110, "description": "Network printers"},
    "IP_Phones": {"name": "IP_Phones", "value": 120, "description": "IP phones"},
    "Guests": {"name": "Guests", "value": 200, "description": "Guest users"},
}


class ISELabSetup:
    """Setup Cisco ISE for lab testing."""
    
    def __init__(self, ise_url: str, username: str, password: str, verify_ssl: bool = False):
        self.ise_url = ise_url
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.client: Optional[ISEClient] = None
    
    def connect(self) -> bool:
        """Connect to ISE and test authentication."""
        try:
            logger.info(f"Connecting to ISE at {self.ise_url}...")
            self.client = ISEClient(
                base_url=self.ise_url,
                username=self.username,
                password=self.password,
                verify_ssl=self.verify_ssl,
            )
            logger.info("✅ Successfully connected to ISE")
            return True
        except ISEAuthenticationError as e:
            logger.error(f"❌ Authentication failed: {e}")
            logger.info("\nTroubleshooting:")
            logger.info(f"   1. Verify credentials: {self.username}")
            logger.info(f"   2. Verify ISE URL: {self.ise_url}")
            logger.info(f"   3. Verify ERS API is enabled in ISE")
            logger.info(f"   4. Check if account has ERS API access")
            return False
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test ISE connection by listing SGTs."""
        try:
            if not self.client:
                logger.error("Not connected to ISE")
                return False
            
            logger.info("Testing connection by listing existing SGTs...")
            sgts = self.client.get_all_sgts()
            logger.info(f"✅ Connection test successful - Found {len(sgts)} existing SGTs")
            return True
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def create_sgts(self, sgt_definitions: Dict[str, Dict]) -> int:
        """Create Security Group Tags in ISE."""
        if not self.client:
            logger.error("Not connected to ISE")
            return 0
        
        created_count = 0
        skipped_count = 0
        
        logger.info(f"\nCreating {len(sgt_definitions)} SGTs...")
        
        for dept_name, sgt_info in sgt_definitions.items():
            sgt_name = sgt_info['name']
            sgt_value = sgt_info['value']
            description = sgt_info.get('description', '')
            
            try:
                # Check if SGT already exists
                existing = self.client.get_sgt(value=sgt_value)
                if existing:
                    logger.info(f"   SGT {sgt_value} ({sgt_name}) already exists - skipping")
                    skipped_count += 1
                    continue
                
                # Create SGT
                logger.info(f"   Creating SGT {sgt_value}: {sgt_name}")
                result = self.client.create_sgt(
                    name=sgt_name,
                    value=sgt_value,
                    description=description
                )
                logger.info(f"   ✅ Created SGT {sgt_value}: {sgt_name}")
                created_count += 1
                
            except ISEAPIError as e:
                error_str = str(e).lower()
                if 'duplicate' in error_str or 'already exists' in error_str:
                    logger.info(f"   SGT {sgt_value} ({sgt_name}) already exists - skipping")
                    skipped_count += 1
                else:
                    logger.error(f"   ❌ Failed to create SGT {sgt_name}: {e}")
            except Exception as e:
                logger.error(f"   ❌ Error creating SGT {sgt_name}: {e}")
        
        logger.info(f"\nSGT Creation Summary:")
        logger.info(f"   Created: {created_count}")
        logger.info(f"   Skipped (already exists): {skipped_count}")
        
        return created_count
    
    def create_authorization_profiles(self, sgt_definitions: Dict[str, Dict]) -> int:
        """Create authorization profiles for SGTs."""
        if not self.client:
            logger.error("Not connected to ISE")
            return 0
        
        created_count = 0
        skipped_count = 0
        
        logger.info(f"\nCreating authorization profiles for {len(sgt_definitions)} SGTs...")
        
        for dept_name, sgt_info in sgt_definitions.items():
            sgt_name = sgt_info['name']
            sgt_value = sgt_info['value']
            profile_name = f"Profile-{sgt_name}"
            description = f"Authorization profile for {sgt_info.get('description', sgt_name)}"
            
            try:
                # Check if profile already exists (by trying to list and filter)
                # Note: ERS API doesn't have a direct "get by name" for profiles
                # We'll try to create and catch duplicate errors
                logger.info(f"   Creating profile: {profile_name} (SGT {sgt_value})")
                result = self.client.create_authorization_profile(
                    name=profile_name,
                    description=description,
                    sgt_value=sgt_value
                )
                logger.info(f"   ✅ Created profile: {profile_name}")
                created_count += 1
                
            except ISEAPIError as e:
                error_str = str(e).lower()
                if 'duplicate' in error_str or 'already exists' in error_str:
                    logger.info(f"   Profile {profile_name} already exists - skipping")
                    skipped_count += 1
                else:
                    logger.error(f"   ❌ Failed to create profile {profile_name}: {e}")
            except Exception as e:
                logger.error(f"   ❌ Error creating profile {profile_name}: {e}")
        
        logger.info(f"\nAuthorization Profile Creation Summary:")
        logger.info(f"   Created: {created_count}")
        logger.info(f"   Skipped (already exists): {skipped_count}")
        
        return created_count
    
    def list_existing_config(self):
        """List existing ISE configuration."""
        if not self.client:
            logger.error("Not connected to ISE")
            return
        
        logger.info("\n" + "="*60)
        logger.info("Existing ISE Configuration")
        logger.info("="*60)
        
        try:
            # List SGTs
            sgts = self.client.get_all_sgts()
            logger.info(f"\nSGTs ({len(sgts)} total):")
            for sgt in sgts[:10]:  # Show first 10
                logger.info(f"   - {sgt.get('name', 'N/A')} (Value: {sgt.get('value', 'N/A')})")
            if len(sgts) > 10:
                logger.info(f"   ... and {len(sgts) - 10} more")
            
            # List Authorization Profiles
            profiles = self.client.get_all_authorization_profiles()
            logger.info(f"\nAuthorization Profiles ({len(profiles)} total):")
            for profile in profiles[:10]:  # Show first 10
                logger.info(f"   - {profile.get('name', 'N/A')}")
            if len(profiles) > 10:
                logger.info(f"   ... and {len(profiles) - 10} more")
            
        except Exception as e:
            logger.error(f"Error listing configuration: {e}")
    
    def print_manual_steps(self):
        """Print manual configuration steps that can't be automated via ERS API."""
        logger.info("\n" + "="*60)
        logger.info("Manual Configuration Steps (via ISE Admin GUI)")
        logger.info("="*60)
        logger.info("""
The following steps need to be completed manually via the ISE Admin GUI
as they're not fully supported via ERS API:

1. **Add Active Directory as Identity Source**:
   - Administration → Identity Management → External Identity Sources → Active Directory
   - Add your AD domain: netlab.net
   - Use credentials: Administrator / C!sco#123
   - Test connection and join to domain
   - Enable "Retrieve groups from this identity source"

2. **Add Network Devices** (switches, wireless controllers):
   - Administration → Network Resources → Network Devices → Add
   - Add your switches/WLCs:
     * Name: Switch-01 (or WLC-01)
     * IP Address: <device IP>
     * Device Type: Switch (or Wireless Controller)
     * RADIUS Shared Secret: <secret>
     * Enable "Enable TrustSec"

3. **Create Authorization Policies** (or use the ones created via script):
   - Policy → Policy Elements → Results → Authorization → Authorization Profiles
   - Verify profiles created by script are present
   - Policy → Authorization → Create policy rules:
     * Rule Name: Engineering-Users-Policy
     * Conditions: User AD Groups EQUALS Engineering-Users
     * Result: Profile-Engineering-Users (assigns SGT 10)
     * Repeat for other departments

4. **Enable TrustSec on Network Devices**:
   - Administration → Network Resources → Network Devices
   - Edit each device
   - Under "TrustSec Settings":
     * Enable TrustSec
     * Configure TrustSec Device ID (SXP)

5. **Verify Configuration**:
   - Operations → Authentications → View recent authentications
   - Monitor → TrustSec → View SGT assignments
   - Policy → Policy Elements → Results → Security Group Access → Security Groups
     * Verify SGTs created by script are present

Note: The script has created SGTs and authorization profiles via ERS API.
      You still need to create authorization policies and configure AD/network devices.
""")
    
    def setup_lab(self):
        """Run the complete lab setup."""
        logger.info("="*60)
        logger.info("Cisco ISE Lab Setup")
        logger.info("="*60)
        
        # Connect to ISE
        if not self.connect():
            return False
        
        # Test connection
        if not self.test_connection():
            return False
        
        # List existing configuration
        self.list_existing_config()
        
        # Create department SGTs
        all_sgts = {**DEPARTMENT_SGTS, **INFRASTRUCTURE_SGTS}
        self.create_sgts(all_sgts)
        
        # Create authorization profiles
        self.create_authorization_profiles(all_sgts)
        
        # Print manual steps
        self.print_manual_steps()
        
        logger.info("\n" + "="*60)
        logger.info("✅ ISE Lab Setup Complete (Automated Parts)")
        logger.info("="*60)
        logger.info("\nNext Steps:")
        logger.info("1. Review the manual configuration steps above")
        logger.info("2. Add AD as identity source via ISE Admin GUI")
        logger.info("3. Add network devices via ISE Admin GUI")
        logger.info("4. Create authorization policies (or verify they were created)")
        logger.info("5. Test authentication and verify SGT assignment")
        
        return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Cisco ISE for lab testing")
    parser.add_argument("--ise-url", default=ISE_URL, help="ISE server URL (e.g., https://192.168.10.31:9060)")
    parser.add_argument("--username", default=ISE_USERNAME, help="ISE admin username")
    parser.add_argument("--password", default=ISE_PASSWORD, help="ISE admin password")
    parser.add_argument("--verify-ssl", action="store_true", help="Verify SSL certificates")
    parser.add_argument("--list-only", action="store_true", help="Only list existing configuration, don't create")
    
    args = parser.parse_args()
    
    setup = ISELabSetup(
        ise_url=args.ise_url,
        username=args.username,
        password=args.password,
        verify_ssl=args.verify_ssl,
    )
    
    if args.list_only:
        if setup.connect():
            setup.list_existing_config()
    else:
        setup.setup_lab()


if __name__ == "__main__":
    main()

