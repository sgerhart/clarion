# Clustering & Grouping System

## Overview

Clarion uses **unsupervised machine learning** to automatically discover endpoint groups based on behavioral patterns. These groups form the foundation for SGT (Security Group Tag) recommendations.

---

## How Clustering Works

### Algorithm: HDBSCAN

**HDBSCAN** (Hierarchical Density-Based Spatial Clustering of Applications with Noise) is used for backend clustering.

#### Why HDBSCAN?

1. **No Predefined K** - Doesn't require specifying the number of clusters upfront
2. **Variable Density** - Finds clusters of different sizes and densities
3. **Noise Detection** - Identifies outliers that don't fit any pattern (cluster -1)
4. **Soft Clustering** - Provides probability scores for cluster membership
5. **Hierarchical** - Can merge or split clusters based on density

#### Parameters

```python
EndpointClusterer(
    min_cluster_size=50,      # Minimum endpoints to form a cluster
    min_samples=10,          # Minimum neighbors for core points
    cluster_selection_epsilon=0.0,  # Distance threshold for merging
    metric="euclidean"       # Distance metric
)
```

**Default Settings:**
- `min_cluster_size=50`: At least 50 endpoints must be similar to form a cluster
- `min_samples=10`: An endpoint needs 10 similar neighbors to be a "core" point
- Smaller values = more clusters, more noise
- Larger values = fewer clusters, less noise

---

## Feature Extraction

### Behavioral Features

Endpoints are clustered based on **behavioral features** extracted from network flows:

```python
FeatureVector(
    # Communication patterns
    unique_peers=150,           # Number of unique endpoints talked to
    unique_services=25,          # Number of unique services (ports)
    peer_diversity=0.75,         # Diversity of communication (0-1)
    
    # Traffic patterns
    bytes_in=5000000,            # Bytes received
    bytes_out=1000000,           # Bytes sent
    in_out_ratio=0.83,           # bytes_in / (bytes_in + bytes_out)
    
    # Port usage
    port_diversity=0.60,         # Diversity of ports used
    top_ports=[443, 80, 22],    # Most common destination ports
    
    # Temporal patterns
    active_hours=40,             # Hours of activity
    flow_count=5000,             # Total flows observed
)
```

### Feature Calculation

1. **Unique Peers** - HyperLogLog cardinality estimate
2. **Unique Services** - HyperLogLog cardinality estimate  
3. **Port Frequency** - Count-Min Sketch for port distribution
4. **Service Frequency** - Count-Min Sketch for service distribution
5. **Bytes In/Out** - Direct counters
6. **Active Hours** - Time-based calculation
7. **Flow Count** - Direct counter

---

## Clustering Process

### Step 1: Feature Extraction

```python
extractor = FeatureExtractor()
features = extractor.extract_all(sketch_store)
# Returns: List[FeatureVector] - one per endpoint
```

### Step 2: Convert to Matrix

```python
X, endpoint_ids = extractor.to_matrix(features)
# X: numpy array (n_endpoints, n_features)
# endpoint_ids: List[str] - MAC addresses
```

### Step 3: Run HDBSCAN

```python
clusterer = EndpointClusterer()
result = clusterer.cluster(sketch_store)
# Returns: ClusterResult with labels, sizes, metrics
```

### Step 4: Semantic Labeling

```python
labeler = SemanticLabeler()
labels = labeler.label_clusters(store, result)
# Returns: Dict[int, ClusterLabel] - cluster_id -> label
```

### Step 5: SGT Mapping

```python
mapper = SGTMapper()
taxonomy = mapper.generate_taxonomy(store, result, labels)
# Returns: SGTTaxonomy with SGT recommendations
```

---

## Cluster Labeling & Justification

### How Labels Are Assigned

The `SemanticLabeler` analyzes cluster members to determine the best label:

#### Strategy 1: ISE Profile (Highest Priority)
```python
if 80% of cluster have ISE profile "Corporate-Laptop":
    label = "Corporate Laptops"
    reason = "80% have ISE profile 'Corporate-Laptop'"
    confidence = 0.80
```

#### Strategy 2: Device Type
```python
if 70% of cluster are "server" devices:
    label = "Servers"
    reason = "70% are server devices"
    confidence = 0.70
```

#### Strategy 3: AD Group Membership
```python
if 60% of cluster are in "Engineering-Users" AD group:
    label = "Engineering Users"
    reason = "60% are in 'Engineering-Users' AD group"
    confidence = 0.60
```

#### Strategy 4: Behavioral Pattern
```python
if cluster has server-like behavior (receive >> send):
    label = "Server-Like Endpoints"
    reason = "Majority have server behavior (receive > send)"
    confidence = 0.60
```

### Cluster Label Data Structure

```python
ClusterLabel(
    cluster_id=0,
    name="Engineering Users",
    primary_reason="75% are in 'Engineering-Users' AD group",
    confidence=0.75,
    member_count=150,
    
    # Supporting statistics
    top_ad_groups=[
        ("Engineering-Users", 0.75),
        ("All-Employees", 0.95),
    ],
    top_ise_profiles=[
        ("Corporate-Laptop", 0.80),
    ],
    top_device_types=[
        ("laptop", 0.85),
    ],
    
    # Behavioral metrics
    avg_peer_diversity=0.65,
    avg_in_out_ratio=0.25,  # Low = client behavior
    is_server_cluster=False,
)
```

---

## User Modification Capabilities

### ✅ Currently Supported

The system **already supports** user modification through the `CustomizationSession`:

#### 1. Rename SGTs
```python
session.rename_sgt(
    cluster_id=0,
    new_name="Engineering Team - Updated",
    modified_by="admin@company.com"
)
```

#### 2. Reassign SGT Values
```python
session.reassign_sgt_value(
    cluster_id=0,
    new_value=15,
    modified_by="admin@company.com"
)
```

#### 3. Merge Clusters
```python
session.merge_clusters(
    source_cluster_id=5,
    target_cluster_id=0,
    modified_by="admin@company.com"
)
```

#### 4. Approve/Reject Recommendations
```python
session.approve_sgt(cluster_id=0, modified_by="admin")
session.reject_sgt(cluster_id=1, reason="Too broad", modified_by="admin")
```

#### 5. Modify SGACL Rules
```python
session.add_permit_rule(
    src_sgt=10,
    dst_sgt=20,
    protocol="tcp",
    port=443,
    reason="Allow HTTPS for compliance"
)
```

### Customization Workflow

```python
# 1. Create review session
session = create_review_session(taxonomy, created_by="admin")

# 2. User makes modifications
session.rename_sgt(0, "Engineering Team")
session.merge_clusters(5, 0)
session.add_permit_rule(10, 20, "tcp", 443)

# 3. Apply customizations
customizer = PolicyCustomizer(session)
final_taxonomy = customizer.apply_to_taxonomy(original_taxonomy)
final_policies = customizer.apply_to_policies(original_policies)

# 4. Generate report
report = generate_review_report(session)
```

---

## Explainability: Why Are Devices Grouped?

### Current Explainability

Each cluster has:
- **Primary Reason** - Why the cluster was formed
- **Confidence Score** - How certain the label is
- **Supporting Statistics** - AD groups, ISE profiles, device types
- **Behavioral Metrics** - Communication patterns

### Example Explanation

```
Cluster 0: Engineering Users
├── Primary Reason: "75% are in 'Engineering-Users' AD group"
├── Confidence: 0.75
├── Member Count: 150 endpoints
│
├── AD Groups:
│   ├── Engineering-Users: 75%
│   └── All-Employees: 95%
│
├── ISE Profiles:
│   └── Corporate-Laptop: 80%
│
├── Device Types:
│   └── laptop: 85%
│
└── Behavioral Patterns:
    ├── Avg Peer Diversity: 0.65 (moderate)
    ├── Avg In/Out Ratio: 0.25 (client behavior)
    └── Server Cluster: No
```

---

## Proposed Enhancements

### 1. Enhanced Explainability

#### Cluster Formation Explanation
```python
@dataclass
class ClusterExplanation:
    """Detailed explanation of why a cluster was formed."""
    cluster_id: int
    
    # Why these endpoints are similar
    similarity_factors: List[SimilarityFactor]
    
    # Feature contributions
    top_contributing_features: List[Tuple[str, float]]
    
    # Example endpoints
    representative_endpoints: List[str]
    
    # Comparison to other clusters
    closest_cluster: Optional[int]
    distance_to_closest: float
    
    # Visualizations
    feature_distribution: Dict[str, List[float]]
    pairwise_distances: np.ndarray
```

#### Similarity Factor
```python
@dataclass
class SimilarityFactor:
    """What makes endpoints in this cluster similar."""
    factor_type: str  # "ad_group", "device_type", "behavior"
    description: str
    strength: float  # 0-1
    examples: List[str]
```

### 2. Agentic Functionality

#### What is Agentic AI?

**Agentic AI** refers to AI systems that can:
- **Autonomously make decisions** based on goals
- **Take actions** to achieve objectives
- **Learn from feedback** and adapt
- **Reason about** complex scenarios

#### Proposed Agentic Features

##### A. Autonomous Cluster Refinement
```python
class ClusterRefinementAgent:
    """Agent that autonomously refines clusters based on feedback."""
    
    def refine_clusters(
        self,
        clusters: ClusterResult,
        feedback: List[UserFeedback]
    ) -> ClusterResult:
        """
        Learn from user modifications and refine future clusters.
        
        Examples:
        - User merges clusters → learn that these should be combined
        - User splits cluster → learn that this was too broad
        - User renames → learn better naming patterns
        """
```

##### B. Policy Optimization Agent
```python
class PolicyOptimizationAgent:
    """Agent that optimizes policies based on observed traffic."""
    
    def optimize_policies(
        self,
        policies: List[SGACLPolicy],
        observed_flows: List[Flow],
        security_goals: SecurityGoals
    ) -> List[SGACLPolicy]:
        """
        Automatically optimize policies to:
        - Minimize false positives (blocked legitimate traffic)
        - Maximize security coverage
        - Reduce policy complexity
        """
```

##### C. Anomaly Detection Agent
```python
class AnomalyDetectionAgent:
    """Agent that detects and responds to anomalies."""
    
    def detect_anomalies(
        self,
        current_behavior: EndpointSketch,
        historical_patterns: List[EndpointSketch]
    ) -> List[Anomaly]:
        """
        Detect:
        - New communication patterns
        - Unusual traffic volumes
        - Policy violations
        - Potential security threats
        """
    
    def recommend_response(self, anomaly: Anomaly) -> Response:
        """
        Recommend actions:
        - Create new SGT for new device type
        - Update policy for new traffic pattern
        - Alert on potential security issue
        """
```

##### D. Continuous Learning Agent
```python
class ContinuousLearningAgent:
    """Agent that continuously learns and adapts."""
    
    def update_model(
        self,
        new_data: List[Flow],
        user_feedback: List[Feedback],
        performance_metrics: Metrics
    ) -> UpdatedModel:
        """
        Continuously improve:
        - Clustering accuracy
        - Label quality
        - Policy recommendations
        - Anomaly detection
        """
```

### 3. Visual Explainability

#### Cluster Visualization
- **Feature Space Plot** - Show endpoints in 2D/3D feature space
- **Dendrogram** - Hierarchical cluster relationships
- **Similarity Matrix** - Heatmap of endpoint similarities
- **Feature Importance** - Which features contributed most

#### Example Endpoint View
```
Endpoint: 00:11:22:33:44:55
├── Cluster: Engineering Users (Cluster 0)
├── SGT: 10 - Engineering-Users
│
├── Why in this cluster:
│   ├── ✓ In "Engineering-Users" AD group
│   ├── ✓ Has "Corporate-Laptop" ISE profile
│   ├── ✓ Similar communication pattern (65% match)
│   └── ✓ Similar device type (laptop)
│
├── Behavioral Summary:
│   ├── Talks to: 150 unique endpoints
│   ├── Uses: 25 unique services
│   ├── Traffic: 1MB out, 5MB in (client pattern)
│   └── Active: 40 hours/week
│
└── Similar Endpoints:
    ├── 00:11:22:33:44:56 (95% similar)
    ├── 00:11:22:33:44:57 (92% similar)
    └── 00:11:22:33:44:58 (88% similar)
```

---

## Implementation Plan

### Phase 1: Enhanced Explainability (2-3 weeks)
- [ ] Add `ClusterExplanation` dataclass
- [ ] Implement similarity factor analysis
- [ ] Add feature contribution calculation
- [ ] Create cluster comparison logic
- [ ] Build explainability API endpoints
- [ ] Add UI components for explanations

### Phase 2: Agentic Foundation (3-4 weeks)
- [ ] Design agent architecture
- [ ] Implement feedback learning system
- [ ] Create agent decision framework
- [ ] Build agent action system
- [ ] Add agent monitoring/logging

### Phase 3: Specific Agents (4-6 weeks)
- [ ] Cluster Refinement Agent
- [ ] Policy Optimization Agent
- [ ] Anomaly Detection Agent
- [ ] Continuous Learning Agent

### Phase 4: Integration & Testing (2-3 weeks)
- [ ] Integrate agents into main pipeline
- [ ] Add agent configuration UI
- [ ] Create agent performance metrics
- [ ] Test with synthetic data
- [ ] Document agent behavior

---

## Benefits of Agentic Approach

1. **Reduced Manual Effort** - Agents learn from user actions
2. **Continuous Improvement** - System gets better over time
3. **Proactive Recommendations** - Agents suggest optimizations
4. **Adaptive Security** - Responds to new threats/patterns
5. **Self-Healing Policies** - Automatically fixes policy issues

---

## Example: Agentic Workflow

```
1. User merges two clusters
   ↓
2. Cluster Refinement Agent learns:
   - These endpoint types should be combined
   - Similar naming patterns
   - Similar behavioral patterns
   ↓
3. Next clustering run:
   - Agent suggests merging similar clusters
   - Agent proposes better cluster names
   - Agent optimizes cluster parameters
   ↓
4. User reviews agent suggestions
   ↓
5. Agent learns from approval/rejection
   ↓
6. Continuous improvement cycle
```

---

## Questions to Consider

1. **Agent Autonomy Level**
   - Fully autonomous (agents make all decisions)?
   - Semi-autonomous (agents suggest, users approve)?
   - Advisory only (agents provide insights)?

2. **Learning Rate**
   - How quickly should agents adapt?
   - How much historical data to consider?
   - How to balance new patterns vs. established patterns?

3. **Trust & Safety**
   - How to ensure agents don't make harmful changes?
   - What safeguards are needed?
   - How to audit agent decisions?

4. **Explainability Requirements**
   - How detailed should explanations be?
   - What format (text, visual, interactive)?
   - Who needs explanations (admins, auditors, end users)?

---

## Next Steps

1. **Review current explainability** - Is it sufficient?
2. **Define agent requirements** - What should agents do?
3. **Design agent architecture** - How should agents work?
4. **Prototype one agent** - Start with Cluster Refinement
5. **Gather feedback** - Test with users
6. **Iterate and improve** - Refine based on feedback

