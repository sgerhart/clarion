#!/usr/bin/env python3
"""
Load Flow Data into Database

Loads flow records from the dataset into the netflow table
so they can be viewed in the admin console.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from clarion.ingest.loader import load_dataset
from clarion.storage import get_database
import pandas as pd
from datetime import datetime

def main():
    """Load flows into database."""
    print("Loading flow data into database...")
    
    db = get_database()
    
    # Load dataset
    data_path = Path(__file__).parent.parent / "data" / "raw" / "trustsec_copilot_synth_campus"
    print(f"Loading dataset from: {data_path}")
    dataset = load_dataset(str(data_path))
    
    print(f"Loaded {len(dataset.flows)} flows")
    
    # Store flows in netflow table
    print("Storing flows in database...")
    stored = 0
    
    # Check available columns
    print(f"Flow columns: {list(dataset.flows.columns)}")
    
    for idx, flow in dataset.flows.iterrows():
        # Get timestamps - use start_time and end_time
        flow_start = 0
        flow_end = 0
        
        if 'start_time' in flow and pd.notna(flow['start_time']):
            flow_start = int(flow['start_time'].timestamp())
        else:
            flow_start = int(datetime.now().timestamp()) - (len(dataset.flows) - idx) * 60
        
        if 'end_time' in flow and pd.notna(flow['end_time']):
            flow_end = int(flow['end_time'].timestamp())
        else:
            flow_end = flow_start + 60
        
        # Get protocol number - use 'proto' column
        protocol_map = {"TCP": 6, "UDP": 17, "ICMP": 1, "tcp": 6, "udp": 17, "icmp": 1}
        protocol_str = str(flow.get('proto', 'TCP')).upper()
        protocol = protocol_map.get(protocol_str, 6)
        
        # Get ports
        src_port = int(flow['src_port']) if pd.notna(flow.get('src_port')) else 0
        dst_port = int(flow['dst_port']) if pd.notna(flow.get('dst_port')) else 0
        
        # Get bytes/packets
        bytes_count = int(flow.get('bytes', 0)) if pd.notna(flow.get('bytes')) else 0
        packets = int(flow.get('packets', 0)) if pd.notna(flow.get('packets')) else 0
        
        # Get switch ID - use exporter_switch_id
        switch_id = str(flow.get('exporter_switch_id', 'SW-UNKNOWN'))
        
        db.store_netflow(
            src_ip=str(flow['src_ip']),
            dst_ip=str(flow['dst_ip']),
            src_port=src_port,
            dst_port=dst_port,
            protocol=protocol,
            bytes=bytes_count,
            packets=packets,
            flow_start=flow_start,
            flow_end=flow_end,
            switch_id=switch_id,
        )
        
        stored += 1
        if stored % 10000 == 0:
            print(f"  Stored {stored:,} flows...")
    
    print(f"\n✅ Stored {stored:,} flows in database")
    print("Now you can view flows in the admin console!")

if __name__ == "__main__":
    main()

