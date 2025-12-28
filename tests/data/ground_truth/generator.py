"""
Ground Truth Dataset Generator

Generates synthetic datasets with known device groups for validation.
Each dataset models a specific company type with realistic traffic patterns.
"""

import csv
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set
import ipaddress

# Base MAC address prefixes for device types
MAC_PREFIXES = {
    'laptop': '00:1B:44',  # Example corporate laptop prefix
    'ip_phone': '00:1E:13',  # Example IP phone prefix
    'mobile_phone': '00:1A:2B',  # Example mobile device prefix
    'server': '00:0C:29',  # Example server prefix
    'printer': '00:1F:16',  # Example printer prefix
    'iot': '00:1C:42',  # Example IoT device prefix
}


class GroundTruthGenerator:
    """Generate ground truth datasets with known clusters."""
    
    def __init__(self, company_type: str, output_dir: Path):
        self.company_type = company_type
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Network configuration
        self.base_ip = ipaddress.IPv4Network('10.0.0.0/16')
        self.voice_server_ips = ['10.0.1.10', '10.0.1.11']  # Voice servers
        self.internet_gateway = '10.0.0.1'
        self.dns_server = '10.0.0.2'
        
        # Time window
        self.start_time = datetime.now() - timedelta(days=7)
        self.end_time = datetime.now()
        
        # Generated data
        self.endpoints: List[Dict] = []
        self.flows: List[Dict] = []
        self.ad_users: List[Dict] = []
        self.ground_truth: Dict = {}
    
    def generate_mac(self, device_type: str, index: int) -> str:
        """Generate MAC address with device type prefix."""
        prefix = MAC_PREFIXES.get(device_type, '00:00:00')
        suffix = f'{index:06X}'
        return f"{prefix}:{suffix[:2]}:{suffix[2:4]}:{suffix[4:6]}"
    
    def generate_ip(self, index: int) -> str:
        """Generate IP address from base network."""
        host = 10 + index  # Start at 10.0.0.10
        return str(self.base_ip.network_address + host)
    
    def generate_flows_for_ip_phone(
        self,
        endpoint_id: str,
        ip: str,
        expected_cluster_id: int,
    ) -> List[Dict]:
        """
        Generate flows for IP Phone.
        
        Key characteristics:
        - Only talks to voice servers
        - SIP ports (5060, 5061)
        - RTP ports (high port range)
        - NEVER talks to Internet
        - Bidirectional traffic (signaling + media)
        """
        flows = []
        flow_id = len(self.flows)
        
        # SIP signaling (TCP 5060/5061)
        for voice_server in self.voice_server_ips:
            # SIP REGISTER/INVITE (outbound)
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': voice_server,
                'src_port': random.randint(50000, 60000),
                'dst_port': 5060,  # SIP
                'proto': 'tcp',
                'bytes': random.randint(500, 2000),
                'packets': random.randint(10, 30),
                'src_mac': endpoint_id,
                'dst_mac': '00:00:00:00:00:00',  # Server MAC
                'start_time': (self.start_time + timedelta(hours=random.randint(0, 168))).isoformat(),
                'end_time': (self.start_time + timedelta(hours=random.randint(0, 168), minutes=5)).isoformat(),
            })
            flow_id += 1
            
            # RTP media (UDP, high ports, bidirectional)
            for _ in range(random.randint(5, 15)):  # Multiple RTP sessions
                rtp_port = random.randint(16384, 32767)  # RTP port range
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': voice_server,
                    'src_port': rtp_port,
                    'dst_port': rtp_port,
                    'proto': 'udp',
                    'bytes': random.randint(50000, 200000),  # High byte count for audio
                    'packets': random.randint(500, 2000),
                    'src_mac': endpoint_id,
                    'dst_mac': '00:00:00:00:00:00',
                    'start_time': (self.start_time + timedelta(hours=random.randint(0, 168))).isoformat(),
                    'end_time': (self.start_time + timedelta(hours=random.randint(0, 168), minutes=30)).isoformat(),
                })
                flow_id += 1
        
        # NO Internet traffic (this is the key distinction!)
        # NO HTTPS, NO general web traffic
        
        return flows
    
    def generate_flows_for_mobile_phone(
        self,
        endpoint_id: str,
        ip: str,
        expected_cluster_id: int,
    ) -> List[Dict]:
        """
        Generate flows for Mobile Phone.
        
        Key characteristics:
        - Talks to central servers (cloud services)
        - HTTPS (443) to various services
        - May have voice app (different pattern than IP phone)
        - Internet access
        - App-based communication patterns
        """
        flows = []
        flow_id = len(self.flows)
        
        # HTTPS to central servers (cloud services)
        central_servers = ['10.0.2.10', '10.0.2.11', '10.0.2.12']  # Central/cloud servers
        for server in central_servers:
            for _ in range(random.randint(20, 100)):  # Many HTTPS connections
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': server,
                    'src_port': random.randint(40000, 50000),
                    'dst_port': 443,  # HTTPS
                    'proto': 'tcp',
                    'bytes': random.randint(1000, 50000),
                    'packets': random.randint(20, 200),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(minutes=random.randint(1, 60))).timestamp()),
                })
                flow_id += 1
        
        # Voice app traffic (if app installed) - different pattern than IP phone
        if random.random() > 0.3:  # 70% have voice app
            voice_app_server = random.choice(['10.0.2.20', '10.0.2.21'])  # Voice app servers
            # Voice app uses HTTPS, not SIP
            for _ in range(random.randint(10, 50)):
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': voice_app_server,
                    'src_port': random.randint(40000, 50000),
                    'dst_port': 443,  # HTTPS-based voice (not SIP!)
                    'proto': 'tcp',
                    'bytes': random.randint(5000, 50000),
                    'packets': random.randint(50, 300),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(minutes=random.randint(5, 60))).timestamp()),
                })
                flow_id += 1
        
        # Internet access (via gateway)
        for _ in range(random.randint(50, 200)):
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': self.internet_gateway,
                'src_port': random.randint(40000, 50000),
                'dst_port': 443,  # HTTPS to Internet
                'proto': 'tcp',
                'bytes': random.randint(1000, 100000),
                'packets': random.randint(20, 500),
                'src_mac': endpoint_id,
                'dst_mac': '00:00:00:00:00:00',
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(1, 30))).timestamp()),
            })
            flow_id += 1
        
        return flows
    
    def generate_flows_for_laptop(
        self,
        endpoint_id: str,
        ip: str,
        expected_cluster_id: int,
        department: str = None,
    ) -> List[Dict]:
        """
        Generate flows for Corporate Laptop.
        
        Key characteristics:
        - HTTPS (443) to many destinations
        - RDP (3389) for remote access
        - SSH (22) for development
        - File shares (SMB/CIFS)
        - AD authentication traffic
        """
        flows = []
        flow_id = len(self.flows)
        
        # HTTPS to many destinations
        web_servers = [f'10.0.{i}.10' for i in range(3, 10)]
        for server in web_servers:
            for _ in range(random.randint(10, 50)):
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': server,
                    'src_port': random.randint(50000, 60000),
                    'dst_port': 443,
                    'proto': 'tcp',
                    'bytes': random.randint(5000, 100000),
                    'packets': random.randint(50, 500),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(minutes=random.randint(5, 60))).timestamp()),
                })
                flow_id += 1
        
        # RDP (3389) for remote access
        rdp_server = '10.0.3.10'  # RDP server
        start = self.start_time + timedelta(hours=random.randint(0, 168))
        flows.append({
            'flow_id': flow_id,
            'src_ip': ip,
            'dst_ip': rdp_server,
            'src_port': random.randint(50000, 60000),
            'dst_port': 3389,
            'proto': 'tcp',
            'bytes': random.randint(10000, 500000),
            'packets': random.randint(100, 1000),
            'src_mac': endpoint_id,
            'dst_mac': '00:00:00:00:00:00',
            'start_time': int(start.timestamp()),
            'end_time': int((start + timedelta(minutes=random.randint(30, 240))).timestamp()),
        })
        flow_id += 1
        
        # SSH (22) for development (if engineering)
        if department == 'Engineering':
            ssh_servers = ['10.0.4.10', '10.0.4.11']
            for server in ssh_servers:
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': server,
                    'src_port': random.randint(50000, 60000),
                    'dst_port': 22,
                    'proto': 'tcp',
                    'bytes': random.randint(1000, 50000),
                    'packets': random.randint(20, 500),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(minutes=random.randint(10, 120))).timestamp()),
                })
                flow_id += 1
        
        # File share (SMB/CIFS) - port 445
        file_server = '10.0.5.10'
        start = self.start_time + timedelta(hours=random.randint(0, 168))
        flows.append({
            'flow_id': flow_id,
            'src_ip': ip,
            'dst_ip': file_server,
            'src_port': random.randint(50000, 60000),
            'dst_port': 445,
            'proto': 'tcp',
            'bytes': random.randint(50000, 1000000),
            'packets': random.randint(100, 2000),
            'src_mac': endpoint_id,
            'dst_mac': '00:00:00:00:00:00',
            'start_time': int(start.timestamp()),
            'end_time': int((start + timedelta(minutes=random.randint(5, 60))).timestamp()),
        })
        flow_id += 1
        
        # AD authentication (LDAP/LDAPS)
        ad_server = '10.0.6.10'
        start = self.start_time + timedelta(hours=random.randint(0, 168))
        flows.append({
            'flow_id': flow_id,
            'src_ip': ip,
            'dst_ip': ad_server,
            'src_port': random.randint(50000, 60000),
            'dst_port': 389,  # LDAP
            'proto': 'tcp',
            'bytes': random.randint(500, 5000),
            'packets': random.randint(5, 50),
            'src_mac': endpoint_id,
            'dst_mac': '00:00:00:00:00:00',
            'start_time': int(start.timestamp()),
            'end_time': int((start + timedelta(minutes=1)).timestamp()),
        })
        flow_id += 1
        
        return flows
    
    def generate_flows_for_server(
        self,
        endpoint_id: str,
        ip: str,
        expected_cluster_id: int,
    ) -> List[Dict]:
        """
        Generate flows for Server.
        
        Key characteristics:
        - Receives connections (inbound heavy)
        - Serves multiple clients
        - Common server ports (80, 443, 22, etc.)
        - Higher total traffic
        """
        flows = []
        flow_id = len(self.flows)
        
        # Server receives connections from many clients
        client_ips = [f'10.0.{i}.{j}' for i in range(10, 50) for j in range(10, 20)][:100]
        
        # Web server (80, 443)
        for client_ip in client_ips:
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': client_ip,
                'dst_ip': ip,  # Server receives
                'src_port': random.randint(50000, 60000),
                'dst_port': 443,  # HTTPS
                'proto': 'tcp',
                'bytes': random.randint(10000, 500000),
                'packets': random.randint(100, 2000),
                'src_mac': '00:00:00:00:00:00',  # Client MAC
                'dst_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(1, 60))).timestamp()),
            })
            flow_id += 1
        
        return flows
    
    def generate_flows_for_printer(
        self,
        endpoint_id: str,
        ip: str,
        expected_cluster_id: int,
    ) -> List[Dict]:
        """
        Generate flows for Printer.
        
        Key characteristics:
        - Port 9100 (raw printing)
        - Few destinations (print servers only)
        - Low traffic volume
        """
        flows = []
        flow_id = len(self.flows)
        
        # Print server
        print_server = '10.0.7.10'
        
        # Receives print jobs (port 9100)
        for _ in range(random.randint(5, 30)):  # Few print jobs
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': print_server,
                'dst_ip': ip,  # Printer receives
                'src_port': random.randint(50000, 60000),
                'dst_port': 9100,  # Raw printing
                'proto': 'tcp',
                'bytes': random.randint(100000, 5000000),  # Large print jobs
                'packets': random.randint(100, 1000),
                'src_mac': '00:00:00:00:00:00',
                'dst_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(1, 10))).timestamp()),
            })
            flow_id += 1
        
        return flows
    
    def generate_flows_for_guest_device(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for guest device - limited destinations, Internet only."""
        flows = []
        flow_id = len(self.flows)
        
        # Guest devices only talk to Internet gateway
        for _ in range(random.randint(10, 50)):  # Limited traffic
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': self.internet_gateway,
                'src_port': random.randint(40000, 50000),
                'dst_port': 443,  # HTTPS only
                'proto': 'tcp',
                'bytes': random.randint(1000, 50000),
                'packets': random.randint(20, 300),
                'src_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(1, 30))).timestamp()),
            })
            flow_id += 1
        
        # NO internal server access
        
        return flows
    
    def generate_flows_for_warehouse_device(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for warehouse device - barcode scanners, inventory systems."""
        flows = []
        flow_id = len(self.flows)
        
        # Warehouse devices talk to inventory servers
        inventory_servers = ['10.0.25.10', '10.0.25.11']
        
        for server in inventory_servers:
            # Periodic inventory updates
            for _ in range(random.randint(20, 100)):
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': server,
                    'src_port': random.randint(50000, 60000),
                    'dst_port': 443,  # HTTPS
                    'proto': 'tcp',
                    'bytes': random.randint(500, 5000),  # Small inventory updates
                    'packets': random.randint(5, 50),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(seconds=random.randint(1, 10))).timestamp()),
                })
                flow_id += 1
        
        return flows
    
    def save_dataset(self):
        """Save all generated data to CSV files."""
        # Save flows - add missing columns and convert timestamps
        flows_path = self.output_dir / 'flows.csv'
        if self.flows:
            # Add required columns that may be missing
            required_flow_cols = [
                'flow_id', 'src_ip', 'dst_ip', 'src_port', 'dst_port', 'proto',
                'bytes', 'packets', 'vlan', 'exporter_switch_id', 'ingress_interface',
                'start_time', 'end_time', 'src_mac', 'dst_sgt', 'src_sgt'
            ]
            for flow in self.flows:
                # Convert Unix timestamps to datetime strings
                if isinstance(flow.get('start_time'), int):
                    flow['start_time'] = datetime.fromtimestamp(flow['start_time']).isoformat() + '+00:00'
                if isinstance(flow.get('end_time'), int):
                    flow['end_time'] = datetime.fromtimestamp(flow['end_time']).isoformat() + '+00:00'
                # Add missing columns with defaults
                flow.setdefault('vlan', 0)
                flow.setdefault('exporter_switch_id', 'SW001')
                flow.setdefault('ingress_interface', 'Gi1/0/1')
                flow.setdefault('dst_sgt', 0)
                flow.setdefault('src_sgt', 0)
                # Remove dst_mac if present (not in required columns)
                flow.pop('dst_mac', None)
            
            with open(flows_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=required_flow_cols)
                writer.writeheader()
                writer.writerows(self.flows)
        
        # Save endpoints - map to expected column names
        endpoints_path = self.output_dir / 'endpoints.csv'
        if self.endpoints:
            # Map endpoint_id -> mac and device_id
            required_endpoint_cols = [
                'device_id', 'device_type', 'os', 'mac', 'hostname',
                'owner_user_id', 'attached_switch_id', 'attached_interface', 'vlan'
            ]
            endpoint_rows = []
            for ep in self.endpoints:
                endpoint_row = {
                    'device_id': f"D{ep['endpoint_id'].replace(':', '')[:10]}",  # Generate device_id
                    'device_type': ep.get('device_type', 'unknown'),
                    'os': 'Windows' if ep.get('device_type') == 'laptop' else 'Unknown',
                    'mac': ep['endpoint_id'],  # endpoint_id is the MAC
                    'hostname': ep.get('hostname', ''),
                    'owner_user_id': ep.get('user_id', ''),
                    'attached_switch_id': ep.get('attached_switch_id', 'SW001'),
                    'attached_interface': ep.get('attached_interface', 'Gi1/0/1'),
                    'vlan': ep.get('vlan', 0),
                }
                endpoint_rows.append(endpoint_row)
            
            with open(endpoints_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=required_endpoint_cols)
                writer.writeheader()
                writer.writerows(endpoint_rows)
        
        # Save AD users - map to expected column names
        ad_users_path = self.output_dir / 'ad_users.csv'
        if self.ad_users:
            required_ad_cols = ['user_id', 'first_name', 'last_name', 'samaccountname', 'email', 'department', 'title', 'ad_domain']
            ad_rows = []
            for ad_user in self.ad_users:
                username = ad_user.get('username', '')
                ad_row = {
                    'user_id': ad_user.get('user_id', ''),
                    'first_name': username.split('-')[0].capitalize() if '-' in username else username[:5],
                    'last_name': username.split('-')[1].capitalize() if '-' in username and len(username.split('-')) > 1 else 'User',
                    'samaccountname': username,
                    'email': f'{username}@example.com',
                    'department': ad_user.get('department', ''),
                    'title': 'Employee',
                    'ad_domain': 'corp.example.com',
                }
                ad_rows.append(ad_row)
            
            with open(ad_users_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=required_ad_cols)
                writer.writeheader()
                writer.writerows(ad_rows)
        
        # Save ground truth metadata
        ground_truth_path = self.output_dir / 'ground_truth.json'
        with open(ground_truth_path, 'w') as f:
            json.dump(self.ground_truth, f, indent=2)
        
        # Create minimal required CSV files for loader compatibility
        self._create_minimal_csvs()
        
        print(f"Generated dataset saved to {self.output_dir}")
        print(f"  Flows: {len(self.flows)}")
        print(f"  Endpoints: {len(self.endpoints)}")
        print(f"  AD Users: {len(self.ad_users)}")
    
    def _create_minimal_csvs(self):
        """Create minimal required CSV files for loader compatibility."""
        # ISE sessions (minimal)
        ise_path = self.output_dir / 'ise_sessions.csv'
        if not ise_path.exists():
            with open(ise_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['session_id', 'mac', 'ip', 'device_id', 'username', 'auth_method', 'endpoint_profile', 'location', 'vlan', 'session_start', 'session_end', 'sgt'])
                writer.writeheader()
        
        # IP assignments (minimal)
        ip_path = self.output_dir / 'ip_assignments.csv'
        if not ip_path.exists():
            with open(ip_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['device_id', 'mac', 'ip', 'vlan', 'switch_id', 'interface', 'lease_start', 'lease_end', 'assignment_type'])
                writer.writeheader()
        
        # AD groups (from ad_users)
        ad_groups_path = self.output_dir / 'ad_groups.csv'
        if not ad_groups_path.exists():
            groups = set()
            for user in self.ad_users:
                if 'ad_groups' in user:
                    for group in user['ad_groups'].split(','):
                        groups.add(group.strip())
            with open(ad_groups_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['group_id', 'group_name', 'group_type'])
                writer.writeheader()
                for idx, group_name in enumerate(sorted(groups)):
                    writer.writerow({'group_id': f'G{idx:04d}', 'group_name': group_name, 'group_type': 'department'})
        
        # AD group membership (minimal)
        ad_membership_path = self.output_dir / 'ad_group_membership.csv'
        if not ad_membership_path.exists():
            with open(ad_membership_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['user_id', 'group_id'])
                writer.writeheader()
        
        # Services (minimal)
        services_path = self.output_dir / 'services.csv'
        if not services_path.exists():
            with open(services_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['service_id', 'service_name', 'ports'])
                writer.writeheader()
                writer.writerow({'service_id': 'S001', 'service_name': 'HTTPS', 'ports': '443'})
                writer.writerow({'service_id': 'S002', 'service_name': 'HTTP', 'ports': '80'})
        
        # Switches (minimal)
        switches_path = self.output_dir / 'switches.csv'
        if not switches_path.exists():
            with open(switches_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['switch_id', 'hostname', 'site', 'role'])
                writer.writeheader()
                writer.writerow({'switch_id': 'SW001', 'hostname': 'switch-001', 'site': 'Headquarters', 'role': 'access'})
        
        # Interfaces (minimal)
        interfaces_path = self.output_dir / 'interfaces.csv'
        if not interfaces_path.exists():
            with open(interfaces_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['switch_id', 'interface', 'if_role', 'admin_state', 'port_channel'])
                writer.writeheader()
        
        # TrustSec SGTs (minimal)
        sgts_path = self.output_dir / 'trustsec_sgts.csv'
        if not sgts_path.exists():
            with open(sgts_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['sgt_id', 'sgt_name', 'sgt_value'])
                writer.writeheader()


class EnterpriseGenerator(GroundTruthGenerator):
    """Generate Enterprise Corporation dataset."""
    
    def generate(self):
        """Generate Enterprise Corporation dataset."""
        print(f"Generating Enterprise Corporation dataset...")
        
        self.ground_truth = {
            "company_type": "enterprise",
            "description": "Enterprise Corporation with multiple departments",
            "expected_clusters": [],
            "device_distinctions": {
                "ip_phone_vs_mobile_phone": {
                    "ip_phone": {
                        "description": "Only talks to voice servers, never Internet",
                        "ports": [5060, 5061, "RTP_range"],
                        "destinations": "voice_servers_only",
                        "internet_access": False
                    },
                    "mobile_phone": {
                        "description": "Talks to central servers, voice via app",
                        "ports": [443, "various"],
                        "destinations": "many_servers",
                        "internet_access": True,
                        "has_apps": True
                    }
                }
            }
        }
        
        cluster_id = 0
        endpoint_index = 0
        
        # Corporate Laptops - Engineering (Cluster 0)
        dept = 'Engineering'
        for i in range(150):
            endpoint_id = self.generate_mac('laptop', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'ENG-LAPTOP-{i:03d}',
                'device_type': 'laptop',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Corporate Laptops - Engineering',
                'department': dept,
                'location': 'Headquarters',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_laptop(endpoint_id, ip, cluster_id, dept)
            self.flows.extend(flows)
            
            # AD user
            self.ad_users.append({
                'user_id': f'user-{endpoint_index}',
                'username': f'eng-user-{i}',
                'ad_groups': 'Engineering-Users,Employees',
                'endpoint_id': endpoint_id,
                'is_privileged': False,
            })
        
        cluster_id += 1
        
        # Corporate Laptops - Sales (Cluster 1)
        dept = 'Sales'
        for i in range(100):
            endpoint_id = self.generate_mac('laptop', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'SALES-LAPTOP-{i:03d}',
                'device_type': 'laptop',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Corporate Laptops - Sales',
                'department': dept,
                'location': 'Headquarters',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_laptop(endpoint_id, ip, cluster_id, dept)
            self.flows.extend(flows)
            
            self.ad_users.append({
                'user_id': f'user-{endpoint_index}',
                'username': f'sales-user-{i}',
                'ad_groups': 'Sales-Users,Employees',
                'endpoint_id': endpoint_id,
                'is_privileged': False,
            })
        
        cluster_id += 1
        
        # IP Phones (Cluster 2) - Should NOT cluster with mobile phones
        for i in range(50):
            endpoint_id = self.generate_mac('ip_phone', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'IP-PHONE-{i:03d}',
                'device_type': 'ip_phone',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'IP Phones',
                'department': None,
                'location': 'Headquarters',
                'is_server': False,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_ip_phone(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Mobile Phones (Cluster 3) - Should NOT cluster with IP phones
        for i in range(50):
            endpoint_id = self.generate_mac('mobile_phone', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'MOBILE-{i:03d}',
                'device_type': 'mobile_phone',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Mobile Phones',
                'department': None,
                'location': 'Headquarters',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_mobile_phone(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Servers (Cluster 4)
        for i in range(20):
            endpoint_id = self.generate_mac('server', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'SERVER-{i:03d}',
                'device_type': 'server',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Servers',
                'department': 'IT',
                'location': 'Data Center',
                'is_server': True,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_server(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Printers (Cluster 5)
        for i in range(10):
            endpoint_id = self.generate_mac('printer', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'PRINTER-{i:03d}',
                'device_type': 'printer',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Printers',
                'department': None,
                'location': 'Headquarters',
                'is_server': False,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_printer(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        # Update ground truth with cluster info
        self.ground_truth['expected_clusters'] = [
            {
                'cluster_id': 0,
                'label': 'Corporate Laptops - Engineering',
                'device_types': ['laptop'],
                'ad_groups': ['Engineering-Users'],
                'expected_count': 150,
            },
            {
                'cluster_id': 1,
                'label': 'Corporate Laptops - Sales',
                'device_types': ['laptop'],
                'ad_groups': ['Sales-Users'],
                'expected_count': 100,
            },
            {
                'cluster_id': 2,
                'label': 'IP Phones',
                'device_types': ['ip_phone'],
                'traffic_patterns': {'no_internet': True, 'ports': [5060, 5061]},
                'expected_count': 50,
            },
            {
                'cluster_id': 3,
                'label': 'Mobile Phones',
                'device_types': ['mobile_phone'],
                'traffic_patterns': {'internet_access': True, 'has_apps': True},
                'expected_count': 50,
            },
            {
                'cluster_id': 4,
                'label': 'Servers',
                'device_types': ['server'],
                'expected_count': 20,
            },
            {
                'cluster_id': 5,
                'label': 'Printers',
                'device_types': ['printer'],
                'expected_count': 10,
            },
        ]
        
        self.save_dataset()


class HealthcareGenerator(GroundTruthGenerator):
    """Generate Healthcare Organization dataset."""
    
    def generate(self):
        """Generate Healthcare Organization dataset."""
        print(f"Generating Healthcare Organization dataset...")
        
        self.ground_truth = {
            "company_type": "healthcare",
            "description": "Healthcare Organization with medical devices, EMR systems, and BYOD",
            "expected_clusters": [],
            "device_distinctions": {
                "medical_device_vs_workstation": {
                    "medical_device": {
                        "description": "Medical devices (MRI, CT, patient monitors) - specific protocols, limited destinations",
                        "ports": ["specific_medical_ports"],
                        "destinations": "emr_servers_only",
                        "internet_access": False
                    },
                    "workstation": {
                        "description": "Clinical workstations - EMR access, general computing",
                        "ports": [443, 3389, "various"],
                        "destinations": "many_servers",
                        "internet_access": True
                    }
                }
            }
        }
        
        cluster_id = 0
        endpoint_index = 0
        
        # Clinical Workstations (Cluster 0)
        for i in range(100):
            endpoint_id = self.generate_mac('laptop', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'CLINICAL-WS-{i:03d}',
                'device_type': 'laptop',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Clinical Workstations',
                'department': 'Clinical',
                'location': 'Hospital',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_clinical_workstation(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
            
            self.ad_users.append({
                'user_id': f'user-{endpoint_index}',
                'username': f'clinical-user-{i}',
                'ad_groups': 'Clinical-Users,Employees',
                'endpoint_id': endpoint_id,
                'is_privileged': False,
            })
        
        cluster_id += 1
        
        # Medical Devices - Patient Monitors (Cluster 1)
        for i in range(50):
            endpoint_id = self.generate_mac('iot', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'MONITOR-{i:03d}',
                'device_type': 'medical_device',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Patient Monitors',
                'department': 'Clinical',
                'location': 'Hospital',
                'is_server': False,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_medical_device(endpoint_id, ip, cluster_id, 'monitor')
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # EMR Servers (Cluster 2)
        for i in range(10):
            endpoint_id = self.generate_mac('server', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'EMR-SERVER-{i:03d}',
                'device_type': 'server',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'EMR Servers',
                'department': 'IT',
                'location': 'Data Center',
                'is_server': True,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_server(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # BYOD Devices (Cluster 3)
        for i in range(75):
            endpoint_id = self.generate_mac('mobile_phone', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'BYOD-{i:03d}',
                'device_type': 'mobile_phone',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'BYOD Devices',
                'department': None,
                'location': 'Hospital',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_mobile_phone(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Guest WiFi Devices (Cluster 4)
        for i in range(30):
            endpoint_id = self.generate_mac('mobile_phone', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'GUEST-{i:03d}',
                'device_type': 'guest_device',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Guest WiFi',
                'department': None,
                'location': 'Hospital',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_guest_device(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        # Update ground truth
        self.ground_truth['expected_clusters'] = [
            {'cluster_id': 0, 'label': 'Clinical Workstations', 'device_types': ['laptop'], 'expected_count': 100},
            {'cluster_id': 1, 'label': 'Patient Monitors', 'device_types': ['medical_device'], 'expected_count': 50},
            {'cluster_id': 2, 'label': 'EMR Servers', 'device_types': ['server'], 'expected_count': 10},
            {'cluster_id': 3, 'label': 'BYOD Devices', 'device_types': ['mobile_phone'], 'expected_count': 75},
            {'cluster_id': 4, 'label': 'Guest WiFi', 'device_types': ['guest_device'], 'expected_count': 30},
        ]
        
        self.save_dataset()
    
    def generate_flows_for_clinical_workstation(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for clinical workstation - EMR access, general computing."""
        flows = []
        flow_id = len(self.flows)
        
        # EMR server access (HTTPS)
        emr_servers = ['10.0.10.10', '10.0.10.11']
        for server in emr_servers:
            for _ in range(random.randint(50, 200)):  # Heavy EMR usage
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': server,
                    'src_port': random.randint(50000, 60000),
                    'dst_port': 443,  # HTTPS to EMR
                    'proto': 'tcp',
                    'bytes': random.randint(10000, 100000),
                    'packets': random.randint(100, 1000),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(minutes=random.randint(5, 60))).timestamp()),
                })
                flow_id += 1
        
        # RDP for remote access
        rdp_server = '10.0.10.20'
        start = self.start_time + timedelta(hours=random.randint(0, 168))
        flows.append({
            'flow_id': flow_id,
            'src_ip': ip,
            'dst_ip': rdp_server,
            'src_port': random.randint(50000, 60000),
            'dst_port': 3389,
            'proto': 'tcp',
            'bytes': random.randint(50000, 500000),
            'packets': random.randint(500, 2000),
            'src_mac': endpoint_id,
            'start_time': int(start.timestamp()),
            'end_time': int((start + timedelta(minutes=random.randint(30, 240))).timestamp()),
        })
        flow_id += 1
        
        # General web traffic
        for _ in range(random.randint(20, 100)):
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': self.internet_gateway,
                'src_port': random.randint(50000, 60000),
                'dst_port': 443,
                'proto': 'tcp',
                'bytes': random.randint(5000, 50000),
                'packets': random.randint(50, 500),
                'src_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(1, 30))).timestamp()),
            })
            flow_id += 1
        
        return flows
    
    def generate_flows_for_medical_device(self, endpoint_id: str, ip: str, expected_cluster_id: int, device_type: str) -> List[Dict]:
        """Generate flows for medical device - specific protocols, EMR servers only."""
        flows = []
        flow_id = len(self.flows)
        
        # Medical devices talk to EMR servers only
        emr_servers = ['10.0.10.10', '10.0.10.11']
        
        # HL7 (port 2575) or DICOM (port 104) traffic
        medical_port = 2575 if device_type == 'monitor' else 104
        
        for server in emr_servers:
            # Continuous data transmission
            for _ in range(random.randint(100, 500)):  # Many small transmissions
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': server,
                    'src_port': random.randint(50000, 60000),
                    'dst_port': medical_port,
                    'proto': 'tcp',
                    'bytes': random.randint(1000, 10000),  # Small medical data packets
                    'packets': random.randint(10, 50),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(seconds=random.randint(1, 10))).timestamp()),
                })
                flow_id += 1
        
        # NO Internet traffic - medical devices isolated
        
        return flows
    
    def generate_flows_for_guest_device(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for guest device - limited destinations, Internet only."""
        flows = []
        flow_id = len(self.flows)
        
        # Guest devices only talk to Internet gateway
        for _ in range(random.randint(10, 50)):  # Limited traffic
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': self.internet_gateway,
                'src_port': random.randint(40000, 50000),
                'dst_port': 443,  # HTTPS only
                'proto': 'tcp',
                'bytes': random.randint(1000, 50000),
                'packets': random.randint(20, 300),
                'src_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(1, 30))).timestamp()),
            })
            flow_id += 1
        
        # NO internal server access
        
        return flows


class ManufacturingGenerator(GroundTruthGenerator):
    """Generate Manufacturing Company dataset."""
    
    def generate(self):
        """Generate Manufacturing Company dataset."""
        print(f"Generating Manufacturing Company dataset...")
        
        self.ground_truth = {
            "company_type": "manufacturing",
            "description": "Manufacturing Company with Industrial IoT, OT/IT convergence",
            "expected_clusters": [],
        }
        
        cluster_id = 0
        endpoint_index = 0
        
        # Office Workstations (Cluster 0)
        for i in range(80):
            endpoint_id = self.generate_mac('laptop', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'OFFICE-WS-{i:03d}',
                'device_type': 'laptop',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Office Workstations',
                'department': 'Office',
                'location': 'Office',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_laptop(endpoint_id, ip, cluster_id, 'Office')
            self.flows.extend(flows)
            
            self.ad_users.append({
                'user_id': f'user-{endpoint_index}',
                'username': f'office-user-{i}',
                'ad_groups': 'Office-Users,Employees',
                'endpoint_id': endpoint_id,
                'is_privileged': False,
            })
        
        cluster_id += 1
        
        # Industrial IoT - PLCs (Cluster 1)
        for i in range(40):
            endpoint_id = self.generate_mac('iot', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'PLC-{i:03d}',
                'device_type': 'iot',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'PLCs',
                'department': 'Production',
                'location': 'Factory Floor',
                'is_server': False,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_plc(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # SCADA Systems (Cluster 2)
        for i in range(15):
            endpoint_id = self.generate_mac('server', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'SCADA-{i:03d}',
                'device_type': 'server',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'SCADA Systems',
                'department': 'Production',
                'location': 'Control Room',
                'is_server': True,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_scada(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Production Servers (Cluster 3)
        for i in range(10):
            endpoint_id = self.generate_mac('server', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'PROD-SERVER-{i:03d}',
                'device_type': 'server',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Production Servers',
                'department': 'IT',
                'location': 'Data Center',
                'is_server': True,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_server(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Warehouse Devices (Cluster 4)
        for i in range(25):
            endpoint_id = self.generate_mac('iot', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'WH-{i:03d}',
                'device_type': 'iot',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Warehouse Devices',
                'department': 'Warehouse',
                'location': 'Warehouse',
                'is_server': False,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_warehouse_device(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        # Update ground truth
        self.ground_truth['expected_clusters'] = [
            {'cluster_id': 0, 'label': 'Office Workstations', 'device_types': ['laptop'], 'expected_count': 80},
            {'cluster_id': 1, 'label': 'PLCs', 'device_types': ['iot'], 'expected_count': 40},
            {'cluster_id': 2, 'label': 'SCADA Systems', 'device_types': ['server'], 'expected_count': 15},
            {'cluster_id': 3, 'label': 'Production Servers', 'device_types': ['server'], 'expected_count': 10},
            {'cluster_id': 4, 'label': 'Warehouse Devices', 'device_types': ['iot'], 'expected_count': 25},
        ]
        
        self.save_dataset()
    
    def generate_flows_for_plc(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for PLC - Modbus/TCP, limited destinations."""
        flows = []
        flow_id = len(self.flows)
        
        # PLCs talk to SCADA systems via Modbus/TCP (port 502)
        scada_servers = ['10.0.20.10', '10.0.20.11']
        
        for server in scada_servers:
            # Periodic Modbus queries
            for _ in range(random.randint(50, 200)):
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': server,
                    'src_port': random.randint(50000, 60000),
                    'dst_port': 502,  # Modbus/TCP
                    'proto': 'tcp',
                    'bytes': random.randint(100, 1000),  # Small Modbus packets
                    'packets': random.randint(2, 10),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(seconds=random.randint(1, 5))).timestamp()),
                })
                flow_id += 1
        
        # NO Internet, NO general network access
        
        return flows
    
    def generate_flows_for_scada(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for SCADA system - receives from PLCs, serves HMI clients."""
        flows = []
        flow_id = len(self.flows)
        
        # SCADA receives Modbus from PLCs
        plc_ips = [f'10.0.{i}.{j}' for i in range(30, 50) for j in range(10, 20)][:40]
        for plc_ip in plc_ips:
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': plc_ip,
                'dst_ip': ip,  # SCADA receives
                'src_port': random.randint(50000, 60000),
                'dst_port': 502,  # Modbus/TCP
                'proto': 'tcp',
                'bytes': random.randint(100, 1000),
                'packets': random.randint(2, 10),
                'src_mac': '00:00:00:00:00:00',
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(seconds=random.randint(1, 5))).timestamp()),
            })
            flow_id += 1
        
        # SCADA serves HMI clients (port 8080 or 443)
        hmi_clients = [f'10.0.{i}.{j}' for i in range(20, 30) for j in range(10, 20)][:20]
        for client_ip in hmi_clients:
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': client_ip,
                'dst_ip': ip,
                'src_port': random.randint(50000, 60000),
                'dst_port': 8080,  # HMI web interface
                'proto': 'tcp',
                'bytes': random.randint(10000, 100000),
                'packets': random.randint(100, 1000),
                'src_mac': '00:00:00:00:00:00',
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(10, 120))).timestamp()),
            })
            flow_id += 1
        
        return flows
    
    def generate_flows_for_warehouse_device(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for warehouse device - barcode scanners, inventory systems."""
        flows = []
        flow_id = len(self.flows)
        
        # Warehouse devices talk to inventory servers
        inventory_servers = ['10.0.25.10', '10.0.25.11']
        
        for server in inventory_servers:
            # Periodic inventory updates
            for _ in range(random.randint(20, 100)):
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': server,
                    'src_port': random.randint(50000, 60000),
                    'dst_port': 443,  # HTTPS
                    'proto': 'tcp',
                    'bytes': random.randint(500, 5000),  # Small inventory updates
                    'packets': random.randint(5, 50),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(seconds=random.randint(1, 10))).timestamp()),
                })
                flow_id += 1
        
        return flows
    
    def generate_flows_for_guest_device(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for guest device - limited destinations, Internet only."""
        flows = []
        flow_id = len(self.flows)
        
        # Guest devices only talk to Internet gateway
        for _ in range(random.randint(10, 50)):  # Limited traffic
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': self.internet_gateway,
                'src_port': random.randint(40000, 50000),
                'dst_port': 443,  # HTTPS only
                'proto': 'tcp',
                'bytes': random.randint(1000, 50000),
                'packets': random.randint(20, 300),
                'src_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(1, 30))).timestamp()),
            })
            flow_id += 1
        
        # NO internal server access
        
        return flows
    
    def generate_flows_for_warehouse_device(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for warehouse device - barcode scanners, inventory systems."""
        flows = []
        flow_id = len(self.flows)
        
        # Warehouse devices talk to inventory servers
        inventory_servers = ['10.0.25.10', '10.0.25.11']
        
        for server in inventory_servers:
            # Periodic inventory updates
            for _ in range(random.randint(20, 100)):
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': server,
                    'src_port': random.randint(50000, 60000),
                    'dst_port': 443,  # HTTPS
                    'proto': 'tcp',
                    'bytes': random.randint(500, 5000),  # Small inventory updates
                    'packets': random.randint(5, 50),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(seconds=random.randint(1, 10))).timestamp()),
                })
                flow_id += 1
        
        return flows


class EducationGenerator(GroundTruthGenerator):
    """Generate Education Institution dataset."""
    
    def generate(self):
        """Generate Education Institution dataset."""
        print(f"Generating Education Institution dataset...")
        
        self.ground_truth = {
            "company_type": "education",
            "description": "Education Institution with student BYOD, faculty workstations, lab computers",
            "expected_clusters": [],
        }
        
        cluster_id = 0
        endpoint_index = 0
        
        # Faculty Workstations (Cluster 0)
        for i in range(60):
            endpoint_id = self.generate_mac('laptop', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'FACULTY-{i:03d}',
                'device_type': 'laptop',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Faculty Workstations',
                'department': 'Faculty',
                'location': 'Campus',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_laptop(endpoint_id, ip, cluster_id, 'Faculty')
            self.flows.extend(flows)
            
            self.ad_users.append({
                'user_id': f'user-{endpoint_index}',
                'username': f'faculty-{i}',
                'ad_groups': 'Faculty-Users,Employees',
                'endpoint_id': endpoint_id,
                'is_privileged': False,
            })
        
        cluster_id += 1
        
        # Lab Computers (Cluster 1)
        for i in range(100):
            endpoint_id = self.generate_mac('laptop', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'LAB-{i:03d}',
                'device_type': 'laptop',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Lab Computers',
                'department': 'IT',
                'location': 'Computer Lab',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_lab_computer(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Student BYOD Devices (Cluster 2)
        for i in range(200):
            endpoint_id = self.generate_mac('mobile_phone', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'STUDENT-{i:03d}',
                'device_type': 'mobile_phone',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Student BYOD',
                'department': None,
                'location': 'Campus',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_student_device(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Library Devices (Cluster 3)
        for i in range(30):
            endpoint_id = self.generate_mac('laptop', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'LIBRARY-{i:03d}',
                'device_type': 'laptop',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Library Devices',
                'department': 'Library',
                'location': 'Library',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_library_device(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Guest Access (Cluster 4)
        for i in range(50):
            endpoint_id = self.generate_mac('mobile_phone', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'GUEST-{i:03d}',
                'device_type': 'guest_device',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Guest Access',
                'department': None,
                'location': 'Campus',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_guest_device(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        # Update ground truth
        self.ground_truth['expected_clusters'] = [
            {'cluster_id': 0, 'label': 'Faculty Workstations', 'device_types': ['laptop'], 'expected_count': 60},
            {'cluster_id': 1, 'label': 'Lab Computers', 'device_types': ['laptop'], 'expected_count': 100},
            {'cluster_id': 2, 'label': 'Student BYOD', 'device_types': ['mobile_phone'], 'expected_count': 200},
            {'cluster_id': 3, 'label': 'Library Devices', 'device_types': ['laptop'], 'expected_count': 30},
            {'cluster_id': 4, 'label': 'Guest Access', 'device_types': ['guest_device'], 'expected_count': 50},
        ]
        
        self.save_dataset()
    
    def generate_flows_for_lab_computer(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for lab computer - educational software, limited access."""
        flows = []
        flow_id = len(self.flows)
        
        # Lab computers access educational servers
        edu_servers = ['10.0.30.10', '10.0.30.11']
        for server in edu_servers:
            for _ in range(random.randint(30, 100)):
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': server,
                    'src_port': random.randint(50000, 60000),
                    'dst_port': 443,
                    'proto': 'tcp',
                    'bytes': random.randint(5000, 50000),
                    'packets': random.randint(50, 500),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(minutes=random.randint(5, 60))).timestamp()),
                })
                flow_id += 1
        
        # Limited Internet access
        for _ in range(random.randint(10, 50)):
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': self.internet_gateway,
                'src_port': random.randint(50000, 60000),
                'dst_port': 443,
                'proto': 'tcp',
                'bytes': random.randint(1000, 20000),
                'packets': random.randint(20, 200),
                'src_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(1, 20))).timestamp()),
            })
            flow_id += 1
        
        return flows
    
    def generate_flows_for_student_device(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for student device - heavy Internet usage, social media, streaming."""
        flows = []
        flow_id = len(self.flows)
        
        # Heavy Internet usage
        for _ in range(random.randint(100, 500)):  # Lots of traffic
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': self.internet_gateway,
                'src_port': random.randint(40000, 50000),
                'dst_port': 443,
                'proto': 'tcp',
                'bytes': random.randint(5000, 100000),  # Streaming/media
                'packets': random.randint(50, 1000),
                'src_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(1, 60))).timestamp()),
            })
            flow_id += 1
        
        # Some access to campus services
        campus_servers = ['10.0.30.10']
        for server in campus_servers:
            for _ in range(random.randint(5, 20)):
                start = self.start_time + timedelta(hours=random.randint(0, 168))
                flows.append({
                    'flow_id': flow_id,
                    'src_ip': ip,
                    'dst_ip': server,
                    'src_port': random.randint(40000, 50000),
                    'dst_port': 443,
                    'proto': 'tcp',
                    'bytes': random.randint(1000, 20000),
                    'packets': random.randint(20, 200),
                    'src_mac': endpoint_id,
                    'start_time': int(start.timestamp()),
                    'end_time': int((start + timedelta(minutes=random.randint(1, 10))).timestamp()),
                })
                flow_id += 1
        
        return flows
    
    def generate_flows_for_library_device(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for library device - research, catalog access."""
        flows = []
        flow_id = len(self.flows)
        
        # Library catalog server
        catalog_server = '10.0.30.20'
        for _ in range(random.randint(20, 80)):
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': catalog_server,
                'src_port': random.randint(50000, 60000),
                'dst_port': 443,
                'proto': 'tcp',
                'bytes': random.randint(2000, 20000),
                'packets': random.randint(30, 300),
                'src_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(2, 30))).timestamp()),
            })
            flow_id += 1
        
        # Research database access
        for _ in range(random.randint(10, 40)):
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': self.internet_gateway,
                'src_port': random.randint(50000, 60000),
                'dst_port': 443,
                'proto': 'tcp',
                'bytes': random.randint(5000, 50000),
                'packets': random.randint(50, 500),
                'src_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(minutes=random.randint(5, 60))).timestamp()),
            })
            flow_id += 1
        
        return flows


class RetailGenerator(GroundTruthGenerator):
    """Generate Retail Chain dataset."""
    
    def generate(self):
        """Generate Retail Chain dataset."""
        print(f"Generating Retail Chain dataset...")
        
        self.ground_truth = {
            "company_type": "retail",
            "description": "Retail Chain with POS systems, inventory, warehouse, corporate office",
            "expected_clusters": [],
        }
        
        cluster_id = 0
        endpoint_index = 0
        
        # POS Systems (Cluster 0)
        for i in range(150):
            endpoint_id = self.generate_mac('iot', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'POS-{i:03d}',
                'device_type': 'iot',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'POS Systems',
                'department': 'Retail',
                'location': 'Store',
                'is_server': False,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_pos(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Inventory Systems (Cluster 1)
        for i in range(30):
            endpoint_id = self.generate_mac('iot', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'INVENTORY-{i:03d}',
                'device_type': 'iot',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Inventory Systems',
                'department': 'Warehouse',
                'location': 'Warehouse',
                'is_server': False,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_inventory(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Corporate Office Workstations (Cluster 2)
        for i in range(50):
            endpoint_id = self.generate_mac('laptop', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'CORP-{i:03d}',
                'device_type': 'laptop',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Corporate Office',
                'department': 'Corporate',
                'location': 'Corporate Office',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_laptop(endpoint_id, ip, cluster_id, 'Corporate')
            self.flows.extend(flows)
            
            self.ad_users.append({
                'user_id': f'user-{endpoint_index}',
                'username': f'corp-user-{i}',
                'ad_groups': 'Corporate-Users,Employees',
                'endpoint_id': endpoint_id,
                'is_privileged': False,
            })
        
        cluster_id += 1
        
        # Warehouse/DC Devices (Cluster 3)
        for i in range(40):
            endpoint_id = self.generate_mac('iot', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'DC-{i:03d}',
                'device_type': 'iot',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Warehouse/DC',
                'department': 'Warehouse',
                'location': 'Distribution Center',
                'is_server': False,
                'is_client': False,
            })
            
            flows = self.generate_flows_for_warehouse_device(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        cluster_id += 1
        
        # Guest WiFi (Cluster 4)
        for i in range(60):
            endpoint_id = self.generate_mac('mobile_phone', endpoint_index)
            ip = self.generate_ip(endpoint_index)
            endpoint_index += 1
            
            self.endpoints.append({
                'endpoint_id': endpoint_id,
                'ip_address': ip,
                'hostname': f'GUEST-{i:03d}',
                'device_type': 'guest_device',
                'expected_cluster_id': cluster_id,
                'expected_cluster_label': 'Guest WiFi',
                'department': None,
                'location': 'Store',
                'is_server': False,
                'is_client': True,
            })
            
            flows = self.generate_flows_for_guest_device(endpoint_id, ip, cluster_id)
            self.flows.extend(flows)
        
        # Update ground truth
        self.ground_truth['expected_clusters'] = [
            {'cluster_id': 0, 'label': 'POS Systems', 'device_types': ['iot'], 'expected_count': 150},
            {'cluster_id': 1, 'label': 'Inventory Systems', 'device_types': ['iot'], 'expected_count': 30},
            {'cluster_id': 2, 'label': 'Corporate Office', 'device_types': ['laptop'], 'expected_count': 50},
            {'cluster_id': 3, 'label': 'Warehouse/DC', 'device_types': ['iot'], 'expected_count': 40},
            {'cluster_id': 4, 'label': 'Guest WiFi', 'device_types': ['guest_device'], 'expected_count': 60},
        ]
        
        self.save_dataset()
    
    def generate_flows_for_pos(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for POS system - payment processing, inventory updates."""
        flows = []
        flow_id = len(self.flows)
        
        # POS talks to payment server
        payment_server = '10.0.40.10'
        for _ in range(random.randint(50, 200)):  # Many transactions
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': payment_server,
                'src_port': random.randint(50000, 60000),
                'dst_port': 443,  # HTTPS for payment processing
                'proto': 'tcp',
                'bytes': random.randint(1000, 10000),  # Small transaction packets
                'packets': random.randint(10, 100),
                'src_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(seconds=random.randint(1, 10))).timestamp()),
            })
            flow_id += 1
        
        # Inventory server updates
        inventory_server = '10.0.40.11'
        for _ in range(random.randint(20, 100)):
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': inventory_server,
                'src_port': random.randint(50000, 60000),
                'dst_port': 443,
                'proto': 'tcp',
                'bytes': random.randint(500, 5000),
                'packets': random.randint(5, 50),
                'src_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(seconds=random.randint(1, 5))).timestamp()),
            })
            flow_id += 1
        
        # NO Internet access
        
        return flows
    
    def generate_flows_for_inventory(self, endpoint_id: str, ip: str, expected_cluster_id: int) -> List[Dict]:
        """Generate flows for inventory system - barcode scanners, inventory management."""
        flows = []
        flow_id = len(self.flows)
        
        # Inventory server
        inventory_server = '10.0.40.11'
        for _ in range(random.randint(30, 150)):
            start = self.start_time + timedelta(hours=random.randint(0, 168))
            flows.append({
                'flow_id': flow_id,
                'src_ip': ip,
                'dst_ip': inventory_server,
                'src_port': random.randint(50000, 60000),
                'dst_port': 443,
                'proto': 'tcp',
                'bytes': random.randint(500, 5000),
                'packets': random.randint(5, 50),
                'src_mac': endpoint_id,
                'start_time': int(start.timestamp()),
                'end_time': int((start + timedelta(seconds=random.randint(1, 10))).timestamp()),
            })
            flow_id += 1
        
        return flows


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        company_type = sys.argv[1]
    else:
        company_type = 'enterprise'
    
    if company_type == 'enterprise':
        output_dir = Path('tests/data/ground_truth/enterprise')
        generator = EnterpriseGenerator('enterprise', output_dir)
        generator.generate()
    elif company_type == 'healthcare':
        output_dir = Path('tests/data/ground_truth/healthcare')
        generator = HealthcareGenerator('healthcare', output_dir)
        generator.generate()
    elif company_type == 'manufacturing':
        output_dir = Path('tests/data/ground_truth/manufacturing')
        generator = ManufacturingGenerator('manufacturing', output_dir)
        generator.generate()
    elif company_type == 'education':
        output_dir = Path('tests/data/ground_truth/education')
        generator = EducationGenerator('education', output_dir)
        generator.generate()
    elif company_type == 'retail':
        output_dir = Path('tests/data/ground_truth/retail')
        generator = RetailGenerator('retail', output_dir)
        generator.generate()
    else:
        print(f"Unknown company type: {company_type}")
        print("Available: enterprise, healthcare, manufacturing, education, retail")

