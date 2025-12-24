"""
Administrative Console UI

Production-ready admin interface for managing Clarion system.
Built with Streamlit for rapid development, but designed for production use.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from clarion.storage import get_database

# Page configuration
st.set_page_config(
    page_title="Clarion Admin Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for professional look
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .status-good { color: #28a745; }
    .status-warning { color: #ffc107; }
    .status-error { color: #dc3545; }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = get_database()

db = st.session_state.db


def render_header():
    """Render the main header."""
    st.markdown('<div class="main-header">🛡️ Clarion Admin Console</div>', unsafe_allow_html=True)
    st.markdown("**TrustSec Policy Copilot - Administrative Dashboard**")
    st.divider()


def render_dashboard():
    """Main dashboard view."""
    st.header("📊 System Dashboard")
    
    # Get statistics
    sketch_stats = db.get_sketch_stats()
    clusters = db.get_clusters()
    policies = db.get_policies()
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Endpoints",
            f"{sketch_stats.get('unique_endpoints', 0):,}",
            delta=None,
        )
    
    with col2:
        st.metric(
            "Total Sketches",
            f"{sketch_stats.get('total_sketches', 0):,}",
            delta=None,
        )
    
    with col3:
        st.metric(
            "Active Clusters",
            len(clusters),
            delta=None,
        )
    
    with col4:
        st.metric(
            "Policies",
            len(policies),
            delta=None,
        )
    
    st.divider()
    
    # System health
    st.subheader("System Health")
    
    health_col1, health_col2, health_col3 = st.columns(3)
    
    with health_col1:
        switch_count = sketch_stats.get('total_switches', 0)
        status = "✅ Healthy" if switch_count > 0 else "⚠️ No Data"
        st.markdown(f"**Switches Connected:** {switch_count} {status}")
    
    with health_col2:
        total_flows = sketch_stats.get('total_flows', 0)
        st.markdown(f"**Total Flows Processed:** {total_flows:,}")
    
    with health_col3:
        if sketch_stats.get('latest_flow'):
            latest = datetime.fromtimestamp(sketch_stats['latest_flow'])
            age = datetime.now() - latest
            status = "✅ Recent" if age < timedelta(hours=1) else "⚠️ Stale"
            st.markdown(f"**Latest Flow:** {latest.strftime('%Y-%m-%d %H:%M')} {status}")
        else:
            st.markdown("**Latest Flow:** N/A")
    
    st.divider()
    
    # Recent activity
    st.subheader("Recent Activity")
    
    # Get recent sketches
    recent_sketches = db.list_sketches(limit=50)
    if recent_sketches:
        df = pd.DataFrame(recent_sketches)
        df['received_at'] = pd.to_datetime(df['received_at'])
        df = df.sort_values('received_at', ascending=False)
        
        st.dataframe(
            df[['endpoint_id', 'switch_id', 'flow_count', 'unique_peers', 'received_at']].head(20),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No sketches received yet.")


def render_sketches():
    """Sketches management view."""
    st.header("📝 Edge Sketches")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        switch_filter = st.selectbox(
            "Filter by Switch",
            options=[None] + list(set(s['switch_id'] for s in db.list_sketches(limit=10000))),
        )
    with col2:
        limit = st.number_input("Limit", min_value=10, max_value=10000, value=1000, step=10)
    
    # Get sketches
    sketches = db.list_sketches(switch_id=switch_filter, limit=limit)
    
    if sketches:
        st.metric("Sketches Found", len(sketches))
        
        # Summary statistics
        df = pd.DataFrame(sketches)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Flows", f"{df['flow_count'].sum():,}")
        with col2:
            st.metric("Total Bytes In", f"{df['bytes_in'].sum():,}")
        with col3:
            st.metric("Total Bytes Out", f"{df['bytes_out'].sum():,}")
        
        # Data table
        st.subheader("Sketches")
        st.dataframe(
            df[['endpoint_id', 'switch_id', 'flow_count', 'unique_peers', 'unique_ports', 'last_seen']],
            use_container_width=True,
            hide_index=True,
        )
        
        # Charts
        st.subheader("Visualizations")
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Flows per switch
            switch_flows = df.groupby('switch_id')['flow_count'].sum().reset_index()
            fig = px.bar(
                switch_flows,
                x='switch_id',
                y='flow_count',
                title="Flows per Switch",
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with chart_col2:
            # Endpoints per switch
            switch_endpoints = df.groupby('switch_id')['endpoint_id'].count().reset_index()
            switch_endpoints.columns = ['switch_id', 'endpoint_count']
            fig = px.pie(
                switch_endpoints,
                values='endpoint_count',
                names='switch_id',
                title="Endpoints per Switch",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sketches found.")


def render_netflow():
    """NetFlow records view."""
    st.header("🌊 NetFlow Records")
    
    col1, col2 = st.columns(2)
    with col1:
        limit = st.number_input("Limit", min_value=10, max_value=10000, value=1000, step=10)
    with col2:
        hours = st.number_input("Hours Back", min_value=1, max_value=168, value=24, step=1)
    
    since = int((datetime.now() - timedelta(hours=hours)).timestamp())
    records = db.get_recent_netflow(limit=limit, since=since)
    
    if records:
        st.metric("Records Found", len(records))
        
        df = pd.DataFrame(records)
        
        # Summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Bytes", f"{df['bytes'].sum():,}")
        with col2:
            st.metric("Total Packets", f"{df['packets'].sum():,}")
        with col3:
            st.metric("Unique IPs", f"{df['src_ip'].nunique() + df['dst_ip'].nunique():,}")
        
        # Top talkers
        st.subheader("Top Talkers")
        top_src = df.groupby('src_ip')['bytes'].sum().sort_values(ascending=False).head(10)
        top_dst = df.groupby('dst_ip')['bytes'].sum().sort_values(ascending=False).head(10)
        
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(
                pd.DataFrame({'IP': top_src.index, 'Bytes': top_src.values}),
                use_container_width=True,
                hide_index=True,
            )
        with col2:
            st.dataframe(
                pd.DataFrame({'IP': top_dst.index, 'Bytes': top_dst.values}),
                use_container_width=True,
                hide_index=True,
            )
        
        # Records table
        st.subheader("Recent Records")
        st.dataframe(
            df[['src_ip', 'dst_ip', 'src_port', 'dst_port', 'protocol', 'bytes', 'packets', 'flow_start']].head(100),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No NetFlow records found.")


def render_clusters():
    """Clusters management view."""
    st.header("🔍 Clusters")
    
    clusters = db.get_clusters()
    
    if clusters:
        st.metric("Total Clusters", len(clusters))
        
        df = pd.DataFrame(clusters)
        
        # Cluster summary
        st.subheader("Cluster Summary")
        st.dataframe(
            df[['cluster_id', 'cluster_label', 'sgt_value', 'sgt_name', 'endpoint_count', 'created_at']],
            use_container_width=True,
            hide_index=True,
        )
        
        # Visualization
        if len(df) > 0:
            fig = px.bar(
                df,
                x='cluster_id',
                y='endpoint_count',
                title="Endpoints per Cluster",
                labels={'cluster_id': 'Cluster ID', 'endpoint_count': 'Endpoints'},
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No clusters found. Run clustering first.")


def render_policies():
    """Policies management view."""
    st.header("📋 Policies")
    
    policies = db.get_policies()
    
    if policies:
        st.metric("Total Policies", len(policies))
        
        df = pd.DataFrame(policies)
        
        # Policy summary
        st.subheader("Policy Summary")
        st.dataframe(
            df[['policy_name', 'src_sgt', 'dst_sgt', 'action', 'created_at']],
            use_container_width=True,
            hide_index=True,
        )
        
        # Action distribution
        action_counts = df['action'].value_counts()
        fig = px.pie(
            values=action_counts.values,
            names=action_counts.index,
            title="Policy Actions Distribution",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No policies found. Generate policies first.")


def render_identity():
    """Identity mappings view."""
    st.header("👤 Identity Mappings")
    
    # Get all identity records (we'll need to add a method for this)
    st.info("Identity mappings view - coming soon")
    
    # For now, show a placeholder
    st.markdown("""
    This view will show:
    - IP to MAC mappings
    - IP to User mappings
    - IP to AD Group mappings
    - ISE profile assignments
    """)


def render_settings():
    """System settings view."""
    st.header("⚙️ Settings")
    
    st.subheader("Database")
    db_path = db.db_path
    st.text(f"Database Path: {db_path}")
    st.text(f"Database Size: {db_path.stat().st_size / 1024 / 1024:.2f} MB" if db_path.exists() else "N/A")
    
    st.subheader("Data Retention")
    days = st.number_input("Retention Days", min_value=1, max_value=365, value=30, step=1)
    
    if st.button("Clean Old Data", type="secondary"):
        with st.spinner("Cleaning old data..."):
            db.cleanup_old_data(days=days)
        st.success(f"Cleaned data older than {days} days")


# Main app
def main():
    """Main application entry point."""
    render_header()
    
    # Sidebar navigation
    with st.sidebar:
        st.title("Navigation")
        page = st.radio(
            "Select Page",
            [
                "Dashboard",
                "Sketches",
                "NetFlow",
                "Clusters",
                "Policies",
                "Identity",
                "Settings",
            ],
        )
    
    # Route to appropriate page
    if page == "Dashboard":
        render_dashboard()
    elif page == "Sketches":
        render_sketches()
    elif page == "NetFlow":
        render_netflow()
    elif page == "Clusters":
        render_clusters()
    elif page == "Policies":
        render_policies()
    elif page == "Identity":
        render_identity()
    elif page == "Settings":
        render_settings()


if __name__ == "__main__":
    main()

