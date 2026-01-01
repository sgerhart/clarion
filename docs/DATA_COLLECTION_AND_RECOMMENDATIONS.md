# Data Collection, Clustering, and SGT Recommendations

## Overview

This document explains how Clarion collects data, groups devices/users, and generates SGT (Security Group Tag) and policy recommendations. It addresses the timeline, data requirements, and decision-making process.

## Key Questions Answered

### 1. Does Clarion Need Time to Collect Data Before Making Recommendations?

**Yes, but the timeline depends on your environment and configuration.**

Clarion needs sufficient data to:
- Build behavioral profiles for endpoints
- Identify communication patterns
- Form statistically meaningful clusters
- Generate confident recommendations

### 2. Is There a Specific Data Collection Period?

**Yes, but it's configurable and depends on several factors:**

- **Minimum Observation Period**: 24 hours (recommended) or when sufficient flows are collected
- **Minimum Endpoints per Cluster**: 50 endpoints (default, configurable)
- **Minimum Flows per Endpoint**: ~100 flows (for initial assignment)
- **Full Clustering Trigger**: Daily/weekly, or when >20% new endpoints

## How It Works: Step-by-Step

### Phase 1: Data Collection (Days 0-1)

**What Happens:**
1. **NetFlow/Flow Data Ingestion**
   - Clarion receives network flows from switches, collectors, or edge agents
   - Flows are processed and aggregated into **behavioral sketches** per endpoint
   - Sketches are updated incrementally as new flows arrive

2. **Identity Data Ingestion** (if available)
   - AD user/group data syncs (can be immediate or scheduled)
   - ISE session data arrives via pxGrid (real-time or near-real-time)
   - Device identity information from ISE profiling

3. **Sketch Building**
   - Each endpoint gets a behavioral sketch containing:
     - Communication patterns (who talks to whom)
     - Port/service usage
     - Traffic volumes (bytes in/out)
     - Temporal patterns (active hours)
   - Sketches are lightweight (KB, not GB) and update incrementally

**Timeline:**
- **Hour 0-6**: Initial data collection, sketches building
- **Hour 6-12**: More data, patterns emerging
- **Hour 12-24**: Sufficient data for initial clustering (recommended minimum)

**What You See:**
- Endpoints appearing in Clarion UI
- Flow counts increasing
- Sketch statistics growing
- **No clusters yet** - system is collecting data

### Phase 2: Initial Clustering (Day 1+)

**Trigger Conditions:**
Clustering runs when **any** of these conditions are met:
1. **Time-based**: 24 hours of data collected (default)
2. **Flow-based**: Minimum number of flows collected (configurable)
3. **Endpoint-based**: Minimum number of endpoints with sufficient data (default: 50)
4. **Manual trigger**: Admin clicks "Run Clustering" in UI

**What Happens:**
1. **Feature Extraction**
   - Extract 18 behavioral features from each endpoint sketch
   - Features include: unique peers, port diversity, traffic patterns, etc.

2. **HDBSCAN Clustering**
   - Algorithm finds natural groupings based on behavioral similarity
   - **Default parameters:**
     - `min_cluster_size=50`: Need at least 50 similar endpoints to form a cluster
     - `min_samples=10`: Endpoint needs 10 similar neighbors to be a "core" point
   - Creates clusters of varying sizes and densities
   - Identifies outliers (devices that don't fit any pattern)

3. **Semantic Labeling**
   - Labels clusters using available identity data:
     - AD group memberships (if available)
     - ISE device profiles (if available)
     - Behavioral patterns (if identity not available)
   - Examples: "Engineering-Users", "Web-Servers", "IoT-Devices"

4. **SGT Mapping**
   - Maps clusters to Security Group Tags
   - Suggests SGT values and names
   - Creates recommendations for review

**Timeline:**
- **Clustering execution**: 5-30 minutes (depends on endpoint count)
- **Results available**: Immediately after clustering completes

**What You See:**
- Clusters appear in UI
- Endpoints assigned to clusters
- Initial SGT recommendations
- Confidence scores for each assignment

### Phase 3: Recommendations (Day 1+)

**SGT Recommendations:**
- Generated immediately after clustering
- Based on cluster assignments and identity data
- Includes:
  - Recommended SGT value and name
  - Confidence score
  - Justification (why this SGT)
  - Impact analysis (how many endpoints affected)

**Policy Recommendations:**
- Generated after SGTs are assigned/accepted
- Based on cluster-to-cluster communication patterns
- Includes:
  - SGACL (Security Group Access Control List) rules
  - Allowed/denied traffic between SGTs
  - Port-based restrictions

**Timeline:**
- **SGT Recommendations**: Available immediately after clustering
- **Policy Recommendations**: Available after SGTs are accepted/deployed

**What You See:**
- List of SGT recommendations in UI
- Policy recommendations matrix
- Impact analysis before deployment

### Phase 4: Ongoing Operations (Day 2+)

**Incremental Updates:**
- New endpoints are assigned to existing clusters (fast path)
- Full re-clustering runs periodically (slow path)
- Clusters evolve as behavior patterns change

**Re-clustering Triggers:**
1. **Periodic**: Daily or weekly (configurable)
2. **Threshold-based**: When >20% new endpoints detected
3. **Behavior change**: When endpoint behavior significantly shifts
4. **Manual**: Admin triggers re-clustering

**Timeline:**
- **Incremental assignment**: Immediate (seconds)
- **Full re-clustering**: 5-30 minutes (periodic)

## Data Requirements

### Minimum Data for Initial Clustering

**Per Endpoint:**
- **Minimum flows**: ~100 flows (for basic behavioral profile)
- **Recommended flows**: 500+ flows (for confident assignment)
- **Time period**: 24 hours (to capture daily patterns)

**Overall:**
- **Minimum endpoints**: 50 endpoints (to form at least one cluster)
- **Recommended endpoints**: 200+ endpoints (for meaningful clustering)
- **Minimum clusters**: 1 cluster (but more is better)

### Minimum Data for Incremental Assignment

**New Endpoint:**
- **Minimum flows**: 100 flows
- **Time period**: Can be as short as 1-2 hours (if traffic is heavy)
- **Assignment method**: Nearest neighbor to existing cluster

### Data Quality Considerations

**Good Data:**
- Consistent traffic patterns
- Sufficient flow volume
- Identity data available (AD/ISE)
- Multiple endpoints per device type

**Poor Data:**
- Sparse traffic (few flows per endpoint)
- Inconsistent patterns
- Missing identity data
- Too few endpoints

## Configuration Options

### Clustering Parameters

```python
# Default configuration
EndpointClusterer(
    min_cluster_size=50,      # Minimum endpoints per cluster
    min_samples=10,           # Minimum neighbors for core point
)

# For smaller environments
EndpointClusterer(
    min_cluster_size=10,      # Lower threshold
    min_samples=3,            # Lower threshold
)

# For larger environments
EndpointClusterer(
    min_cluster_size=100,     # Higher threshold
    min_samples=20,          # Higher threshold
)
```

### Trigger Configuration

```python
# Clustering triggers
TRIGGERS = {
    "initial_clustering": {
        "time_based": "24h",           # After 24 hours
        "flow_based": 10000,          # After 10,000 flows
        "endpoint_based": 50,         # After 50 endpoints
    },
    "incremental_assignment": {
        "min_flows_per_endpoint": 100,  # Minimum flows for assignment
    },
    "full_reclustering": {
        "periodic": "daily",          # Daily re-clustering
        "threshold": 0.20,            # When 20% new endpoints
    }
}
```

## Timeline Examples

### Example 1: Small Environment (50-200 endpoints)

**Day 0:**
- 00:00 - Data collection starts
- 06:00 - Initial sketches building
- 12:00 - Patterns emerging
- 24:00 - **Initial clustering triggered** (24-hour threshold)

**Day 1:**
- 00:30 - Clustering completes
- 00:35 - SGT recommendations available
- 01:00 - Admin reviews recommendations
- 02:00 - SGTs accepted/deployed
- 03:00 - Policy recommendations generated

**Day 2+:**
- Incremental updates for new endpoints
- Weekly full re-clustering

### Example 2: Large Environment (1000+ endpoints)

**Day 0:**
- 00:00 - Data collection starts
- 06:00 - Initial sketches building
- 12:00 - Patterns emerging
- 24:00 - **Initial clustering triggered**

**Day 1:**
- 01:00 - Clustering completes (larger dataset takes longer)
- 01:05 - SGT recommendations available
- 02:00 - Admin reviews recommendations
- 03:00 - SGTs accepted/deployed
- 04:00 - Policy recommendations generated

**Day 2+:**
- Incremental updates for new endpoints
- Daily full re-clustering (more frequent for large environments)

### Example 3: High-Traffic Environment

**Day 0:**
- 00:00 - Data collection starts
- 02:00 - **Initial clustering triggered** (flow-based threshold reached)
- 02:30 - Clustering completes
- 02:35 - SGT recommendations available

**Note:** In high-traffic environments, clustering can trigger earlier based on flow count rather than time.

## Current Implementation vs. Future Enhancements

### Current State (Batch Processing)

**How It Works:**
- Collects data for a period (default: 24 hours)
- Runs full clustering on all endpoints
- Generates recommendations
- Re-clusters periodically

**Limitations:**
- Must wait for initial data collection period
- Full re-clustering is expensive
- New endpoints wait for next clustering cycle

### Future Enhancements (Incremental Processing)

**How It Will Work:**
- **Fast Path**: New endpoints assigned immediately to existing clusters
- **Slow Path**: Periodic full re-clustering for refinement
- **Real-time Updates**: Clusters update as data arrives
- **Behavior Change Detection**: Automatic re-clustering when patterns shift

**Benefits:**
- Faster initial recommendations
- Immediate assignment for new endpoints
- More efficient resource usage
- Better handling of dynamic environments

## Best Practices

### 1. Initial Setup

- **Collect data for 24-48 hours** before first clustering
- Ensure sufficient endpoints (50+ minimum, 200+ recommended)
- Verify identity data sources (AD/ISE) are connected
- Check flow volume is adequate

### 2. Review Recommendations

- **Review SGT recommendations** before accepting
- Check confidence scores (higher is better)
- Verify cluster labels make sense
- Adjust clustering parameters if needed

### 3. Ongoing Operations

- **Monitor cluster stability** over time
- Review new endpoint assignments regularly
- Adjust re-clustering frequency based on environment
- Update identity data sources as needed

### 4. Troubleshooting

**No Clusters Formed:**
- Check minimum cluster size is appropriate for environment
- Verify sufficient endpoints with adequate flow data
- Review clustering parameters

**Low Confidence Scores:**
- Collect more data (longer observation period)
- Verify identity data is available
- Check for data quality issues

**Recommendations Don't Make Sense:**
- Review cluster labels and assignments
- Check identity data accuracy
- Adjust clustering parameters
- Consider manual overrides

## Summary

**Timeline for Recommendations:**
1. **Data Collection**: 24 hours (recommended minimum)
2. **Initial Clustering**: 5-30 minutes (after trigger)
3. **SGT Recommendations**: Immediate (after clustering)
4. **Policy Recommendations**: After SGTs accepted

**Key Points:**
- Clarion needs time to collect sufficient data (24 hours recommended)
- Clustering requires minimum endpoints (50 default) and flows (100+ per endpoint)
- Recommendations are generated immediately after clustering
- Ongoing updates are incremental (fast) and periodic (slow path)
- Timeline is configurable based on environment size and traffic volume

**The system is designed to:**
- Start with behavioral patterns (works even without identity data)
- Refine with identity data when available
- Provide recommendations quickly after initial data collection
- Continuously improve as more data arrives

