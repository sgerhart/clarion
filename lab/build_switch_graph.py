#!/usr/bin/env python3
"""
build_switch_graph.py

Builds a per-switch graph snapshot in the canonical "switch-graph-1.0"
JSON schema, based on NetFlow data read via nfdump.

Intended to run on (or near) a "switch" (in your lab: the VM) and
produce a compact summary per time window.

Example usage:

  sudo ./build_switch_graph.py \
    --netflow-dir /var/log/netflow \
    --window-seconds 600 \
    --switch-id VM1 \
    --site-id LabSite \
    --site-name "Lab Campus" > vm1_graph.json

Improvements over original:
  - Better error handling and logging
  - Validates nfdump availability
  - Handles empty/missing NetFlow directories gracefully
  - More robust timestamp parsing
  - Configurable server port list
  - Output to file option
  - Summary statistics to stderr
  - IPv6 awareness (skip or handle)
"""

import argparse
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Default server ports (commonly indicate server role)
DEFAULT_SERVER_PORTS = {
    22,     # SSH
    23,     # Telnet
    25,     # SMTP
    53,     # DNS
    80,     # HTTP
    110,    # POP3
    123,    # NTP
    143,    # IMAP
    161,    # SNMP
    443,    # HTTPS
    445,    # SMB
    514,    # Syslog
    515,    # LPD
    554,    # RTSP
    631,    # IPP
    1433,   # MSSQL
    1521,   # Oracle
    1812,   # RADIUS Auth
    1813,   # RADIUS Acct
    1883,   # MQTT
    3306,   # MySQL
    3389,   # RDP
    5432,   # PostgreSQL
    5683,   # CoAP
    8080,   # HTTP Alt
    8443,   # HTTPS Alt
    9100,   # RAW Print
}


def check_nfdump_available():
    """Verify nfdump is installed and accessible."""
    if shutil.which("nfdump") is None:
        logger.error("nfdump is not installed or not in PATH")
        raise RuntimeError("nfdump command not found. Install with: apt-get install nfdump")
    
    # Check version
    try:
        result = subprocess.run(["nfdump", "-V"], capture_output=True, text=True)
        version_line = result.stdout.strip() or result.stderr.strip()
        logger.info(f"Using nfdump: {version_line}")
    except Exception as e:
        logger.warning(f"Could not determine nfdump version: {e}")


def validate_netflow_dir(netflow_dir: str) -> bool:
    """Check if NetFlow directory exists and has data files."""
    path = Path(netflow_dir)
    
    if not path.exists():
        logger.error(f"NetFlow directory does not exist: {netflow_dir}")
        return False
    
    if not path.is_dir():
        logger.error(f"NetFlow path is not a directory: {netflow_dir}")
        return False
    
    # Check for nfcapd files
    nfcapd_files = list(path.glob("nfcapd.*"))
    if not nfcapd_files:
        logger.warning(f"No nfcapd.* files found in {netflow_dir}")
        return False
    
    logger.info(f"Found {len(nfcapd_files)} nfcapd files in {netflow_dir}")
    return True


def run_nfdump(netflow_dir: str, window_seconds: int):
    """
    Run nfdump over the given directory for the last `window_seconds`
    and return (stdout, start_dt, end_dt).
    """
    check_nfdump_available()
    
    if not validate_netflow_dir(netflow_dir):
        logger.warning("Proceeding with potentially empty NetFlow data")
    
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(seconds=window_seconds)

    # nfdump time format: YYYY/MM/DD.hh:mm:ss
    t_start = start_dt.strftime("%Y/%m/%d.%H:%M:%S")
    t_end = end_dt.strftime("%Y/%m/%d.%H:%M:%S")

    # Custom output format: CSV-like, easy to parse
    fmt = "fmt:%ts,%te,%sa,%sp,%da,%dp,%pr,%pkt,%byt"

    cmd = [
        "nfdump",
        "-R", netflow_dir,
        "-t", f"{t_start}-{t_end}",
        "-o", fmt,
        "-q",  # Quiet mode - suppress header/footer
    ]

    logger.info(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode != 0:
            # nfdump returns non-zero for various reasons, including no matching flows
            if "No matching flows" in result.stderr or "Empty file list" in result.stderr:
                logger.warning("No matching flows in time window")
                return "", start_dt, end_dt
            logger.warning(f"nfdump stderr: {result.stderr}")
        
        return result.stdout, start_dt, end_dt
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("nfdump timed out after 120 seconds")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"nfdump failed: {e.stderr}") from e


def parse_timestamp(ts_raw: str) -> str:
    """
    Parse and normalize timestamp to ISO format.
    
    Handles formats:
      - "YYYY-MM-DD hh:mm:ss" -> "YYYY-MM-DDThh:mm:ssZ"
      - "YYYY-MM-DDThh:mm:ss" -> "YYYY-MM-DDThh:mm:ssZ"
    """
    ts_raw = ts_raw.strip()
    
    if not ts_raw:
        return ""
    
    # Replace space with T if present
    ts_iso = ts_raw.replace(" ", "T")
    
    # Add Z suffix if not present
    if not ts_iso.endswith("Z"):
        ts_iso += "Z"
    
    return ts_iso


def is_valid_ipv4(ip: str) -> bool:
    """Check if string is a valid IPv4 address."""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def parse_flows(nfdump_output: str, skip_ipv6: bool = True):
    """
    Parse nfdump custom output lines into a list of flow dicts.

    Each valid line should look like:
      ts,te,sa,sp,da,dp,pr,pkt,byt
    """
    flows = []
    skipped_lines = 0
    ipv6_skipped = 0

    for line in nfdump_output.splitlines():
        line = line.strip()
        if not line:
            continue

        # Skip obvious header/summary lines from nfdump
        if any(line.startswith(prefix) for prefix in [
            "Date", "Summary", "Time window", "Total flows",
            "Sys:", "Time:", "Flows:", "Packets:", "Bytes:"
        ]):
            continue

        # Split and strip every field
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 9:
            skipped_lines += 1
            continue

        ts_raw, te_raw, sa, sp, da, dp, pr, pkt, byt = parts

        # Skip IPv6 if requested
        if skip_ipv6 and (":" in sa or ":" in da):
            ipv6_skipped += 1
            continue

        # Validate and clean IPs
        sa_clean = sa.strip()
        da_clean = da.strip()
        
        if not is_valid_ipv4(sa_clean) or not is_valid_ipv4(da_clean):
            skipped_lines += 1
            continue

        # Parse timestamps
        ts_iso = parse_timestamp(ts_raw)
        te_iso = parse_timestamp(te_raw)

        # Parse numeric fields
        try:
            sp_i = int(sp)
            dp_i = int(dp)
            pkt_i = int(pkt)
            byt_i = int(byt)
        except ValueError:
            skipped_lines += 1
            continue

        # Validate port ranges
        if not (0 <= sp_i <= 65535 and 0 <= dp_i <= 65535):
            skipped_lines += 1
            continue

        # Normalize proto to lowercase
        pr_clean = pr.strip().lower()

        flows.append({
            "ts": ts_iso,
            "te": te_iso,
            "sa": sa_clean,
            "sp": sp_i,
            "da": da_clean,
            "dp": dp_i,
            "pr": pr_clean,
            "pkt": pkt_i,
            "byt": byt_i,
        })

    if skipped_lines > 0:
        logger.debug(f"Skipped {skipped_lines} malformed lines")
    if ipv6_skipped > 0:
        logger.debug(f"Skipped {ipv6_skipped} IPv6 flows")
    
    logger.info(f"Parsed {len(flows)} valid flows")
    return flows


def aggregate_graph(flows, server_ports: set):
    """
    Build per-IP node stats and per (src,dst,proto,dst_port) edges.

    Returns:
      nodes_dict: { ip -> node_obj }
      edges_list: [ edge_obj ]
    """

    nodes = {}
    node_services = defaultdict(lambda: defaultdict(lambda: {
        "flows": 0,
        "bytes": 0,
        "packets": 0,
    }))
    edges = {}

    def ensure_node(ip: str):
        if ip not in nodes:
            nodes[ip] = {
                "id": ip,
                "ip": ip,
                "mac": None,
                "vlans": [],
                "attachments": [],
                "metrics": {
                    "total_flows": 0,
                    "total_bytes": 0,
                    "total_packets": 0,
                    "as_client_flows": 0,
                    "as_server_flows": 0,
                },
                "services": [],
                "identity": None,
                "tags": []
            }

    for f in flows:
        sa = f["sa"]
        da = f["da"]
        sp = f["sp"]
        dp = f["dp"]
        pr = f["pr"]
        pkt = f["pkt"]
        byt = f["byt"]
        ts = f["ts"]
        te = f["te"]

        ensure_node(sa)
        ensure_node(da)

        # --- Update edge ---
        ekey = (sa, da, pr, dp)
        if ekey not in edges:
            edges[ekey] = {
                "src": sa,
                "dst": da,
                "proto": pr,
                "dst_port": dp,
                "flows": 0,
                "bytes": 0,
                "packets": 0,
                "first_seen": None,
                "last_seen": None,
                "src_ports_sample": set(),
                "vlan_id": None,
                "direction": "unknown",
                "ingress_ifindex": None,
                "egress_ifindex": None,
                "src_sgt": None,
                "dst_sgt": None,
            }

        e = edges[ekey]
        e["flows"] += 1
        e["bytes"] += byt
        e["packets"] += pkt

        if ts and (e["first_seen"] is None or ts < e["first_seen"]):
            e["first_seen"] = ts
        if te and (e["last_seen"] is None or te > e["last_seen"]):
            e["last_seen"] = te

        if len(e["src_ports_sample"]) < 10:
            e["src_ports_sample"].add(sp)

        # --- Update source node metrics ---
        sn = nodes[sa]["metrics"]
        sn["total_flows"] += 1
        sn["total_bytes"] += byt
        sn["total_packets"] += pkt
        # Heuristic: high source port → likely client
        if sp >= 1024:
            sn["as_client_flows"] += 1
        else:
            sn["as_server_flows"] += 1

        # --- Update destination node metrics ---
        dn = nodes[da]["metrics"]
        dn["total_flows"] += 1
        dn["total_bytes"] += byt
        dn["total_packets"] += pkt
        # Heuristic: well-known port or common app port → server
        if dp < 1024 or dp in server_ports:
            dn["as_server_flows"] += 1
        else:
            dn["as_client_flows"] += 1

        # --- Destination services ---
        svc = node_services[da][(pr, dp)]
        svc["flows"] += 1
        svc["bytes"] += byt
        svc["packets"] += pkt

    # Finalize node "services" arrays
    for ip, node in nodes.items():
        services_list = []
        for (pr, port), s in node_services[ip].items():
            role = "server" if port < 1024 or port in server_ports else "client"
            services_list.append({
                "proto": pr,
                "port": port,
                "role": role,
                "flows": s["flows"],
                "bytes": s["bytes"],
                "packets": s["packets"],
            })
        # Sort services by flow count descending
        services_list.sort(key=lambda x: x["flows"], reverse=True)
        node["services"] = services_list

    # Convert edges dict to list and sets to lists
    edges_list = []
    for e in edges.values():
        e["src_ports_sample"] = sorted(e["src_ports_sample"])
        edges_list.append(e)

    return nodes, edges_list


def print_summary(nodes: dict, edges: list, raw_flows: int):
    """Print summary statistics to stderr."""
    total_bytes = sum(n["metrics"]["total_bytes"] for n in nodes.values())
    total_packets = sum(n["metrics"]["total_packets"] for n in nodes.values())
    
    # Count server vs client nodes
    servers = sum(1 for n in nodes.values() 
                  if n["metrics"]["as_server_flows"] > n["metrics"]["as_client_flows"])
    clients = len(nodes) - servers
    
    logger.info("=" * 50)
    logger.info("Graph Summary:")
    logger.info(f"  Raw flows processed: {raw_flows}")
    logger.info(f"  Unique nodes: {len(nodes)}")
    logger.info(f"  Unique edges: {len(edges)}")
    logger.info(f"  Likely servers: {servers}")
    logger.info(f"  Likely clients: {clients}")
    logger.info(f"  Total bytes: {total_bytes:,}")
    logger.info(f"  Total packets: {total_packets:,}")
    logger.info("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="Build per-switch graph from NetFlow (nfdump) "
                    "in 'switch-graph-1.0' JSON schema."
    )
    parser.add_argument(
        "--netflow-dir",
        default="/var/log/netflow",
        help="Directory containing nfcapd.* files (default: /var/log/netflow)",
    )
    parser.add_argument(
        "--window-seconds",
        type=int,
        default=600,
        help="How far back to look in seconds (default: 600 = 10 minutes)",
    )
    parser.add_argument(
        "--switch-id",
        help="Logical ID for this switch/VM (e.g. SW-1A, VM1). "
             "Defaults to hostname if not provided.",
    )
    parser.add_argument(
        "--switch-hostname",
        help="Switch hostname to report. Defaults to system hostname.",
    )
    parser.add_argument(
        "--switch-mgmt-ip",
        help="Switch management IP (optional).",
    )
    parser.add_argument(
        "--switch-platform",
        help="Switch platform/model (optional, e.g. C9300-48P).",
    )
    parser.add_argument(
        "--switch-software",
        help="Switch software version (optional, e.g. 17.9.4).",
    )
    parser.add_argument(
        "--site-id",
        help="Site ID (optional, e.g. Campus-01).",
    )
    parser.add_argument(
        "--site-name",
        help="Site name (optional, e.g. HQ-Campus).",
    )
    parser.add_argument(
        "--site-location",
        help="Site location/description (optional).",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--include-ipv6",
        action="store_true",
        help="Include IPv6 flows (default: skip IPv6)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress summary output to stderr",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    hostname = args.switch_hostname or socket.gethostname()
    switch_id = args.switch_id or hostname

    logger.info(f"Building graph for switch: {switch_id}")

    try:
        nfdump_out, start_dt, end_dt = run_nfdump(args.netflow_dir, args.window_seconds)
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)

    flows = parse_flows(nfdump_out, skip_ipv6=not args.include_ipv6)
    nodes_dict, edges_list = aggregate_graph(flows, DEFAULT_SERVER_PORTS)

    if not args.quiet:
        print_summary(nodes_dict, edges_list, len(flows))

    # Build top-level JSON
    result = {
        "schema_version": "switch-graph-1.0",

        "switch": {
            "id": switch_id,
            "hostname": hostname,
            "mgmt_ip": args.switch_mgmt_ip,
            "platform": args.switch_platform,
            "software_version": args.switch_software,
        },

        "site": {
            "id": args.site_id,
            "name": args.site_name,
            "location": args.site_location,
        },

        "time_window": {
            "start": start_dt.replace(microsecond=0).isoformat() + "Z",
            "end": end_dt.replace(microsecond=0).isoformat() + "Z",
            "duration_seconds": args.window_seconds,
        },

        "metrics": {
            "raw_flows_count": len(flows),
            "dropped_flows_count": 0,
            "nodes_count": len(nodes_dict),
            "edges_count": len(edges_list),
        },

        "capabilities": {
            "has_vlan_id": False,
            "has_ifindex": False,
            "has_sgt": False,
            "export_protocol": "netflow-v9",
            "export_sampler": "none",
        },

        "nodes": list(nodes_dict.values()),
        "edges": edges_list,
    }

    json_output = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(json_output)
        logger.info(f"Graph written to: {args.output}")
    else:
        print(json_output)


if __name__ == "__main__":
    main()

