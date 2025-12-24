"""
Streamlit UI for Clarion

Rapid prototyping UI for exploring clusters, policies, and visualizations.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import os
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from clarion.ingest.loader import load_dataset
from clarion.ingest.sketch_builder import build_sketches
from clarion.identity import enrich_sketches
from clarion.clustering.clusterer import EndpointClusterer
from clarion.clustering.labeling import SemanticLabeler
from clarion.clustering.sgt_mapper import generate_sgt_taxonomy
from clarion.policy.matrix import build_policy_matrix
from clarion.policy.sgacl import SGACLGenerator
from clarion.policy.impact import ImpactAnalyzer
from clarion.visualization.clusters import create_cluster_plotly
from clarion.visualization.policy import create_policy_plotly


st.set_page_config(
    page_title="Clarion TrustSec Policy Copilot",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ Clarion TrustSec Policy Copilot")
st.markdown("Scale-first network segmentation using edge processing and unsupervised learning")

# Sidebar
st.sidebar.header("Configuration")

# Data path
default_data_path = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "data", "raw", "trustsec_copilot_synth_campus"
)

data_path = st.sidebar.text_input(
    "Data Path",
    value=default_data_path if os.path.exists(default_data_path) else "",
)

# Clustering parameters
st.sidebar.subheader("Clustering")
min_cluster_size = st.sidebar.slider("Min Cluster Size", 10, 200, 50)
min_samples = st.sidebar.slider("Min Samples", 5, 50, 10)

# Policy parameters
st.sidebar.subheader("Policy Generation")
min_flow_count = st.sidebar.slider("Min Flow Count", 1, 100, 10)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview",
    "🔍 Clustering",
    "📋 Policies",
    "📈 Visualizations",
    "⚙️ Export",
])

# Overview Tab
with tab1:
    st.header("Overview")
    
    if st.button("Load Data", type="primary"):
        if not data_path or not os.path.exists(data_path):
            st.error(f"Data path not found: {data_path}")
        else:
            with st.spinner("Loading dataset..."):
                dataset = load_dataset(data_path)
                
                st.session_state['dataset'] = dataset
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Flows", f"{len(dataset.flows):,}")
                with col2:
                    st.metric("Endpoints", len(dataset.endpoints))
                with col3:
                    st.metric("Users", len(dataset.ad_users))
                with col4:
                    st.metric("AD Groups", len(dataset.ad_groups))
                
                st.success("Data loaded successfully!")

# Clustering Tab
with tab2:
    st.header("Clustering Analysis")
    
    if 'dataset' not in st.session_state:
        st.warning("Please load data first in the Overview tab")
    else:
        if st.button("Run Clustering", type="primary"):
            dataset = st.session_state['dataset']
            
            with st.spinner("Building sketches..."):
                store = build_sketches(dataset)
                enrich_sketches(store, dataset)
            
            with st.spinner("Clustering endpoints..."):
                clusterer = EndpointClusterer(
                    min_cluster_size=min_cluster_size,
                    min_samples=min_samples,
                )
                result = clusterer.cluster(store)
                
                labeler = SemanticLabeler(dataset)
                labels = labeler.label_clusters(store, result)
                
                taxonomy = generate_sgt_taxonomy(store, result)
            
            st.session_state['store'] = store
            st.session_state['result'] = result
            st.session_state['labels'] = labels
            st.session_state['taxonomy'] = taxonomy
            
            st.success("Clustering complete!")
            
            # Display results
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Clusters", result.n_clusters)
            with col2:
                st.metric("Noise Points", result.n_noise)
            with col3:
                st.metric("Silhouette Score", f"{result.silhouette:.3f}" if result.silhouette else "N/A")
            
            # Cluster sizes
            st.subheader("Cluster Sizes")
            cluster_df = pd.DataFrame([
                {"Cluster": cid, "Size": size}
                for cid, size in sorted(result.cluster_sizes.items())
            ])
            st.bar_chart(cluster_df.set_index("Cluster"))
            
            # SGT Taxonomy
            st.subheader("SGT Taxonomy")
            taxonomy_data = []
            for rec in taxonomy.recommendations:
                taxonomy_data.append({
                    "Cluster": rec.cluster_id,
                    "SGT Value": rec.sgt_value,
                    "SGT Name": rec.sgt_name,
                    "Endpoints": rec.endpoint_count,
                    "Confidence": f"{rec.confidence:.2f}",
                })
            st.dataframe(pd.DataFrame(taxonomy_data), use_container_width=True)

# Policies Tab
with tab3:
    st.header("Policy Generation")
    
    if 'taxonomy' not in st.session_state:
        st.warning("Please run clustering first")
    else:
        if st.button("Generate Policies", type="primary"):
            dataset = st.session_state['dataset']
            store = st.session_state['store']
            result = st.session_state['result']
            taxonomy = st.session_state['taxonomy']
            
            with st.spinner("Building policy matrix..."):
                matrix = build_policy_matrix(dataset, store, result, taxonomy)
            
            with st.spinner("Generating SGACLs..."):
                generator = SGACLGenerator(min_flow_count=min_flow_count)
                policies = generator.generate(matrix)
                
                analyzer = ImpactAnalyzer()
                impact = analyzer.analyze(matrix, policies)
            
            st.session_state['matrix'] = matrix
            st.session_state['policies'] = policies
            st.session_state['impact'] = impact
            
            st.success("Policies generated!")
            
            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("SGACL Policies", len(policies))
            with col2:
                st.metric("Matrix Cells", matrix.n_cells)
            with col3:
                st.metric("Traffic Permitted", f"{impact.permit_ratio()*100:.1f}%")
            
            # Impact analysis
            st.subheader("Impact Analysis")
            if impact.has_critical_issues():
                st.error(f"⚠️ {impact.critical_blocks} critical ports would be blocked!")
            
            impact_df = pd.DataFrame([
                {"Risk Level": "Critical", "Count": impact.critical_blocks},
                {"Risk Level": "High", "Count": impact.high_risk_blocks},
                {"Risk Level": "Medium", "Count": impact.medium_risk_blocks},
                {"Risk Level": "Low", "Count": impact.low_risk_blocks},
            ])
            st.bar_chart(impact_df.set_index("Risk Level"))
            
            # Policy list
            st.subheader("Generated Policies")
            policy_data = []
            for p in policies[:20]:  # Show first 20
                policy_data.append({
                    "Policy": p.name,
                    "Source SGT": f"{p.src_sgt} ({p.src_sgt_name})",
                    "Dest SGT": f"{p.dst_sgt} ({p.dst_sgt_name})",
                    "Permit Rules": len([r for r in p.rules if r.action == "permit"]),
                    "Coverage": f"{p.coverage_ratio()*100:.1f}%",
                })
            st.dataframe(pd.DataFrame(policy_data), use_container_width=True)

# Visualizations Tab
with tab4:
    st.header("Visualizations")
    
    if 'result' not in st.session_state:
        st.warning("Please run clustering first")
    else:
        result = st.session_state['result']
        store = st.session_state['store']
        
        # Cluster visualization
        st.subheader("Cluster Visualization")
        
        viz_method = st.selectbox("Method", ["pca", "tsne"], index=0)
        
        if st.button("Generate Cluster Plot"):
            from clarion.clustering.features import FeatureExtractor
            
            extractor = FeatureExtractor()
            features = extractor.extract_all(store)
            X, endpoint_ids = extractor.to_matrix(features)
            
            fig = create_cluster_plotly(
                X,
                result.labels,
                endpoint_ids,
                method=viz_method,
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Policy matrix heatmap
        if 'matrix' in st.session_state:
            st.subheader("Policy Matrix Heatmap")
            matrix = st.session_state['matrix']
            
            fig = create_policy_plotly(matrix)
            st.plotly_chart(fig, use_container_width=True)

# Export Tab
with tab5:
    st.header("Export Policies")
    
    if 'policies' not in st.session_state:
        st.warning("Please generate policies first")
    else:
        policies = st.session_state['policies']
        taxonomy = st.session_state['taxonomy']
        matrix = st.session_state['matrix']
        impact = st.session_state.get('impact')
        
        from clarion.policy.exporter import ISEExporter
        
        exporter = ISEExporter()
        export = exporter.export(taxonomy, policies, matrix, impact)
        
        st.subheader("Cisco CLI Configuration")
        st.code(export.cisco_cli_config, language="text")
        
        st.download_button(
            label="Download CLI Config",
            data=export.cisco_cli_config,
            file_name="clarion_policy_config.txt",
            mime="text/plain",
        )
        
        st.subheader("JSON Export")
        st.json(export.to_dict())
        
        st.download_button(
            label="Download JSON",
            data=export.to_json(),
            file_name="clarion_policy_export.json",
            mime="application/json",
        )

