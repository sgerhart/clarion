"""
User Traffic Aggregation Module

Aggregates network flows by user (across all their devices) to enable
user-based traffic pattern analysis and clustering.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
import logging
from collections import Counter, defaultdict
import json

from clarion.storage import get_database

logger = logging.getLogger(__name__)


class UserTrafficAggregator:
    """
    Aggregate network flows by user across all their devices.
    
    This enables user-based traffic pattern analysis for clustering
    users by their behavior, not just AD groups.
    
    Example:
        >>> aggregator = UserTrafficAggregator()
        >>> aggregator.aggregate_user_traffic()
        >>> patterns = aggregator.get_user_traffic_pattern(user_id)
    """
    
    def __init__(self):
        """Initialize the user traffic aggregator."""
        self.db = get_database()
    
    def aggregate_user_traffic(self, limit: Optional[int] = None) -> Dict[str, int]:
        """
        Aggregate traffic patterns for all users.
        
        For each user:
        1. Find all devices associated with that user
        2. Aggregate flows from all those devices
        3. Calculate traffic patterns (bytes, flows, ports, protocols, peers)
        4. Store in user_traffic_patterns table
        
        Args:
            limit: Optional limit on number of users to process (for testing)
            
        Returns:
            Dictionary with statistics: {'users_processed': int, 'total_flows': int}
        """
        logger.info("Aggregating user traffic patterns...")
        conn = self.db._get_connection()
        
        # Get all active users with their devices
        users_query = """
            SELECT DISTINCT u.user_id
            FROM users u
            JOIN user_device_associations uda ON u.user_id = uda.user_id
            WHERE u.is_active = 1 AND uda.is_active = 1
        """
        if limit:
            users_query += f" LIMIT {limit}"
        
        users = conn.execute(users_query).fetchall()
        user_ids = [row[0] for row in users]
        
        logger.info(f"Processing traffic for {len(user_ids)} users...")
        
        stats = {
            'users_processed': 0,
            'total_flows': 0,
            'users_with_traffic': 0,
        }
        
        for user_id in user_ids:
            try:
                user_stats = self._aggregate_user_traffic(user_id, conn)
                if user_stats['flow_count'] > 0:
                    stats['users_with_traffic'] += 1
                stats['total_flows'] += user_stats['flow_count']
                stats['users_processed'] += 1
                
                if stats['users_processed'] % 100 == 0:
                    logger.info(f"  Processed {stats['users_processed']} users...")
            except Exception as e:
                logger.error(f"Error aggregating traffic for user {user_id}: {e}")
                continue
        
        logger.info(f"✅ Aggregated traffic for {stats['users_processed']} users "
                   f"({stats['users_with_traffic']} with traffic, {stats['total_flows']} total flows)")
        return stats
    
    def _aggregate_user_traffic(self, user_id: str, conn) -> Dict:
        """
        Aggregate traffic for a single user.
        
        Args:
            user_id: User ID to aggregate traffic for
            conn: Database connection
            
        Returns:
            Dictionary with traffic statistics
        """
        # Get all devices for this user
        devices_query = """
            SELECT DISTINCT uda.endpoint_id, uda.ip_address
            FROM user_device_associations uda
            WHERE uda.user_id = ? AND uda.is_active = 1
        """
        devices = conn.execute(devices_query, (user_id,)).fetchall()
        
        if not devices:
            return {'flow_count': 0}
        
        # Build list of MAC addresses and IP addresses
        mac_addresses = [d[0] for d in devices]
        ip_addresses = [d[1] for d in devices if d[1]]
        
        # Aggregate flows for this user
        # Match flows where source or destination is one of the user's devices
        flows_query = """
            SELECT 
                bytes, packets,
                dst_port, protocol,
                src_ip, dst_ip,
                flow_start, flow_end
            FROM netflow
            WHERE (src_mac IN ({}) OR dst_mac IN ({}) OR src_ip IN ({}) OR dst_ip IN ({}))
        """.format(
            ','.join(['?' for _ in mac_addresses]),
            ','.join(['?' for _ in mac_addresses]),
            ','.join(['?' for _ in ip_addresses]) if ip_addresses else 'NULL',
            ','.join(['?' for _ in ip_addresses]) if ip_addresses else 'NULL'
        )
        
        params = mac_addresses + mac_addresses
        if ip_addresses:
            params.extend(ip_addresses + ip_addresses)
        
        flows = conn.execute(flows_query, params).fetchall()
        
        if not flows:
            return {'flow_count': 0}
        
        # Calculate aggregate statistics
        total_bytes_in = 0
        total_bytes_out = 0
        total_flows = len(flows)
        port_counter = Counter()
        protocol_counter = Counter()
        peer_ips = set()
        
        for flow in flows:
            bytes_count = flow[0] or 0
            dst_port = flow[2]
            protocol = flow[3]
            src_ip = flow[4]
            dst_ip = flow[5]
            
            # Determine if this is inbound or outbound
            # If src_ip is one of our IPs, it's outbound
            if src_ip in ip_addresses or any(mac in str(flow) for mac in mac_addresses):
                total_bytes_out += bytes_count
            else:
                total_bytes_in += bytes_count
            
            # Track ports and protocols
            if dst_port:
                port_counter[dst_port] += bytes_count
            if protocol:
                protocol_counter[protocol] += bytes_count
            
            # Track peer IPs (destinations)
            if dst_ip and dst_ip not in ip_addresses:
                peer_ips.add(dst_ip)
        
        # Get top ports and protocols
        top_ports = [{'port': port, 'bytes': count} 
                    for port, count in port_counter.most_common(10)]
        top_protocols = [{'protocol': proto, 'bytes': count} 
                        for proto, count in protocol_counter.most_common(5)]
        
        # Store aggregated pattern
        conn.execute("""
            INSERT OR REPLACE INTO user_traffic_patterns
            (user_id, total_bytes_in, total_bytes_out, total_flows,
             unique_peers, top_ports, top_protocols, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            user_id,
            total_bytes_in,
            total_bytes_out,
            total_flows,
            len(peer_ips),
            json.dumps(top_ports),
            json.dumps(top_protocols),
        ))
        
        return {
            'flow_count': total_flows,
            'bytes_in': total_bytes_in,
            'bytes_out': total_bytes_out,
            'unique_peers': len(peer_ips),
        }
    
    def aggregate_user_to_user_traffic(self) -> Dict[str, int]:
        """
        Aggregate user-to-user traffic patterns.
        
        Analyzes flows to determine which users communicate with which other users.
        Stores results in user_user_traffic table.
        
        Returns:
            Dictionary with statistics
        """
        logger.info("Aggregating user-to-user traffic patterns...")
        conn = self.db._get_connection()
        
        # Get user-to-device mappings
        user_devices = {}
        device_users = {}
        
        cursor = conn.execute("""
            SELECT uda.user_id, uda.endpoint_id, uda.ip_address
            FROM user_device_associations uda
            WHERE uda.is_active = 1
        """)
        
        for row in cursor.fetchall():
            user_id = row[0]
            endpoint_id = row[1]
            ip_address = row[2]
            
            if user_id not in user_devices:
                user_devices[user_id] = {'macs': [], 'ips': []}
            user_devices[user_id]['macs'].append(endpoint_id)
            if ip_address:
                user_devices[user_id]['ips'].append(ip_address)
            
            # Also build reverse mapping
            device_users[endpoint_id] = user_id
            if ip_address:
                device_users[ip_address] = user_id
        
        logger.info(f"Found {len(user_devices)} users with devices")
        
        # For each flow, try to map source and destination to users
        user_user_traffic = defaultdict(lambda: {'bytes': 0, 'flows': 0, 'ports': Counter()})
        
        flows_query = """
            SELECT src_mac, dst_mac, src_ip, dst_ip, bytes, dst_port
            FROM netflow
            WHERE src_mac IS NOT NULL OR dst_mac IS NOT NULL
        """
        flows = conn.execute(flows_query).fetchall()
        
        logger.info(f"Processing {len(flows)} flows...")
        
        for flow in flows:
            src_mac = flow[0]
            dst_mac = flow[1]
            src_ip = flow[2]
            dst_ip = flow[3]
            bytes_count = flow[4] or 0
            dst_port = flow[5]
            
            # Map source to user
            src_user = None
            if src_mac and src_mac in device_users:
                src_user = device_users[src_mac]
            elif src_ip and src_ip in device_users:
                src_user = device_users[src_ip]
            
            # Map destination to user
            dst_user = None
            if dst_mac and dst_mac in device_users:
                dst_user = device_users[dst_mac]
            elif dst_ip and dst_ip in device_users:
                dst_user = device_users[dst_ip]
            
            # If both are users, record the traffic
            if src_user and dst_user and src_user != dst_user:
                key = (src_user, dst_user)
                user_user_traffic[key]['bytes'] += bytes_count
                user_user_traffic[key]['flows'] += 1
                if dst_port:
                    user_user_traffic[key]['ports'][dst_port] += bytes_count
        
        # Store user-to-user traffic
        stored_count = 0
        for (src_user, dst_user), data in user_user_traffic.items():
            top_ports = [{'port': port, 'bytes': count} 
                        for port, count in data['ports'].most_common(10)]
            
            conn.execute("""
                INSERT OR REPLACE INTO user_user_traffic
                (src_user_id, dst_user_id, total_bytes, total_flows, top_ports, last_seen)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                src_user,
                dst_user,
                data['bytes'],
                data['flows'],
                json.dumps(top_ports),
            ))
            stored_count += 1
        
        conn.commit()
        
        logger.info(f"✅ Stored {stored_count} user-to-user traffic patterns")
        return {
            'user_pairs': stored_count,
            'total_flows': sum(d['flows'] for d in user_user_traffic.values()),
        }
    
    def get_user_traffic_pattern(self, user_id: str) -> Optional[Dict]:
        """Get aggregated traffic pattern for a user."""
        conn = self.db._get_connection()
        cursor = conn.execute("""
            SELECT * FROM user_traffic_patterns WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            # Parse JSON fields
            if result.get('top_ports'):
                result['top_ports'] = json.loads(result['top_ports'])
            if result.get('top_protocols'):
                result['top_protocols'] = json.loads(result['top_protocols'])
            return result
        return None


def aggregate_all_user_traffic(limit: Optional[int] = None) -> Dict[str, int]:
    """
    Convenience function to aggregate traffic for all users.
    
    Args:
        limit: Optional limit on number of users to process
        
    Returns:
        Statistics dictionary
    """
    aggregator = UserTrafficAggregator()
    return aggregator.aggregate_user_traffic(limit=limit)

