# Ground Truth Dataset Schema

## File Format

All datasets use CSV format matching the existing `ClarionDataset` structure.

## flows.csv

Network flow records with behavioral patterns that distinguish device types.

**Required Columns:**
- `flow_id`: Unique flow identifier
- `src_ip`: Source IP address
- `dst_ip`: Destination IP address  
- `src_port`: Source port
- `dst_port`: Destination port
- `proto`: Protocol (tcp, udp, icmp)
- `bytes`: Total bytes transferred
- `packets`: Total packets
- `src_mac`: Source MAC address (links to endpoint)
- `dst_mac`: Destination MAC address
- `start_time`: Flow start timestamp
- `end_time`: Flow end timestamp
- `vlan_id`: VLAN identifier (optional)

**Key Patterns to Model:**
- IP Phones: SIP (5060/5061), RTP (high ports), only voice servers
- Mobile Phones: HTTPS (443), various services, app-based patterns
- Servers: Receive connections, serve multiple clients
- Clients: Initiate connections, talk to many servers
- IoT: Specific protocols (MQTT, CoAP), limited destinations
- Printers: Port 9100, few destinations

## endpoints.csv

Endpoint metadata with ground truth cluster labels.

**Required Columns:**
- `endpoint_id`: MAC address (primary key)
- `ip_address`: Primary IP address
- `hostname`: Hostname (if known)
- `device_type`: Ground truth device type
- `expected_cluster_id`: Expected cluster assignment (-1 for noise/outliers)
- `expected_cluster_label`: Human-readable cluster label
- `department`: Department (if applicable)
- `location`: Physical location
- `is_server`: Boolean (server-like behavior)
- `is_client`: Boolean (client-like behavior)

**Device Types (with traffic patterns):**
- `ip_phone`: SIP/RTP traffic only, voice servers only
- `mobile_phone`: Mixed traffic, app-based patterns
- `laptop`: Corporate laptop with AD authentication
- `server`: Server behavior (receives connections)
- `printer`: Print services, few destinations
- `iot_device`: IoT-specific protocols
- `guest_device`: No AD identity, limited access

## ad_users.csv

Active Directory user and group assignments (for identity-aware clustering).

**Required Columns:**
- `user_id`: Unique user identifier
- `username`: Username
- `ad_groups`: Comma-separated AD groups
- `endpoint_id`: MAC address of primary device
- `is_privileged`: Boolean (admin/privileged user)

## ise_sessions.csv

ISE authentication sessions (optional, for identity context).

**Required Columns:**
- `session_id`: Unique session ID
- `endpoint_id`: MAC address
- `username`: Authenticated user
- `profile_name`: ISE endpoint profile
- `policy_set`: ISE policy set
- `auth_time`: Authentication timestamp

## ground_truth.json

Metadata defining expected clustering results.

```json
{
  "company_type": "enterprise",
  "description": "Enterprise Corporation with multiple departments",
  "expected_clusters": [
    {
      "cluster_id": 0,
      "label": "Corporate Laptops - Engineering",
      "device_types": ["laptop"],
      "ad_groups": ["Engineering-Users"],
      "traffic_patterns": {
        "common_ports": [443, 80, 22, 3389],
        "destinations": "many",
        "direction": "outbound_heavy"
      },
      "expected_count": 150
    },
    {
      "cluster_id": 1,
      "label": "IP Phones",
      "device_types": ["ip_phone"],
      "traffic_patterns": {
        "common_ports": [5060, 5061],
        "destinations": "voice_servers_only",
        "direction": "bidirectional",
        "no_internet": true
      },
      "expected_count": 50
    }
  ],
  "device_distinctions": {
    "ip_phone_vs_mobile_phone": {
      "ip_phone": {
        "description": "Only talks to voice servers, never Internet",
        "ports": [5060, 5061, "RTP_range"],
        "destinations": "voice_servers_only",
        "internet_access": false
      },
      "mobile_phone": {
        "description": "Talks to central servers, voice via app",
        "ports": [443, "various"],
        "destinations": "many_servers",
        "internet_access": true,
        "has_apps": true
      }
    }
  }
}
```

## Validation Rules

The validation framework checks:
1. **Cluster Separation:** IP phones should NOT cluster with mobile phones
2. **Device Type Accuracy:** Devices labeled as same type should cluster together
3. **Traffic Pattern Recognition:** Devices with similar traffic patterns cluster together
4. **Identity Awareness:** Devices with same AD groups cluster together
5. **Outlier Detection:** Obvious outliers assigned to noise cluster (-1)

