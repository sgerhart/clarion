# Categorization Engine Architecture

## Executive Summary

This document analyzes the current categorization/clustering system and proposes enhancements to support:
- **Live streaming data** (vs batch processing)
- **Incremental clustering** (updates without full re-clustering)
- **Identity-aware grouping** (even when identity data arrives asynchronously)
- **SGT lifecycle management** (stable SGTs with dynamic membership)
- **Ground truth validation** (test datasets with known results)
- **First-seen tracking** (detect new devices/users)
- **Agentic AI Integration** (optional LLM support for intelligent categorization, supports local models like Llama)

---

## Current State Analysis

### What We Have

1. **Batch HDBSCAN Clustering**
   - Processes all endpoints at once
   - Requires full dataset in memory
   - No incremental update capability
   - Location: `src/clarion/clustering/clusterer.py`

2. **Feature Extraction**
   - Behavioral features from sketches (18 features)
   - Communication patterns, port usage, bytes in/out
   - Location: `src/clarion/clustering/features.py`

3. **SGT Mapping**
   - One-time SGT assignment per cluster
   - No tracking of SGT changes over time
   - Location: `src/clarion/clustering/sgt_mapper.py`

4. **Semantic Labeling**
   - Uses AD groups and ISE profiles when available
   - Rule-based labeling with confidence scoring
   - Location: `src/clarion/clustering/labeling.py`

5. **HDBSCAN Clustering Details**
   - Density-based clustering algorithm
   - No predefined number of clusters required
   - Handles variable density clusters
   - Provides soft clustering with probability scores
   - Default parameters: `min_cluster_size=50`, `min_samples=10`

### What's Missing

1. ❌ **Incremental Clustering** - No mechanism to update clusters when new data arrives
2. ❌ **First-Seen Tracking** - No detection of new devices/users
3. ❌ **Identity Timing** - No handling of identity data that arrives late
4. ❌ **SGT Lifecycle** - No tracking of SGT stability over time
5. ❌ **Ground Truth Validation** - No test datasets with known clusters
6. ❌ **Streaming Processing** - Designed for batch, not real-time
7. ❌ **Cluster Stability** - No tracking of cluster evolution

---

## Requirements

### 1. Live Data Processing

**Challenge:** Data arrives continuously, not in batches.

**Requirements:**
- Process flows as they arrive (streaming)
- Update sketches incrementally
- Trigger clustering periodically (not continuously)
- Handle bursts and lulls in traffic

**Current State:** ⚠️ Batch-only processing

### 2. Incremental Clustering

**Challenge:** Re-clustering all endpoints every time is expensive and changes SGTs unnecessarily.

**Requirements:**
- **Fast Path:** Assign new endpoints to existing clusters (nearest neighbor)
- **Slow Path:** Periodic full re-clustering (e.g., daily/weekly)
- **Merge/Split Detection:** Detect when clusters should merge or split
- **Stability Metrics:** Track how stable clusters are over time

**Current State:** ❌ Full re-cluster every time

### 3. Identity-Aware Grouping

**Challenge:** Identity data (AD users, ISE profiles) may not be available immediately.

**Requirements:**
- **Phase 1:** Group by behavior only (communication patterns)
- **Phase 2:** Refine groups when identity data arrives
- **Hybrid Approach:** Use both behavior and identity when available
- **Confidence Scoring:** Higher confidence when behavior + identity align

**Current State:** ⚠️ Uses identity if available, but no phased approach

### 4. When to Start Grouping

**Questions:**
- How much data before first clustering? (Minimum observation period)
- How often to re-cluster? (Periodic refresh)
- When to trigger immediate re-cluster? (Thresholds: new endpoint %, behavior change)

**Proposed Triggers:**
1. **Initial Clustering:** After collecting N flows or T time (e.g., 24 hours)
2. **Incremental Assignment:** When new endpoint has sufficient data (e.g., 100 flows)
3. **Full Re-clustering:** Daily/weekly, or when >20% new endpoints
4. **Behavior Change Detection:** When endpoint behavior significantly shifts

### 5. SGT Lifecycle Management

**Challenge:** SGTs should be stable; devices join/leave but SGTs remain.

**Requirements:**
- **Stable SGT Values:** Once assigned, SGT value doesn't change
- **Dynamic Membership:** Devices join/leave SGTs as they're assigned to clusters
- **Audit Trail:** Track SGT assignment history (device → SGT over time)
- **SGT Retirement:** Detect when SGT has no members (optional)

**Current State:** ❌ SGTs are regenerated each clustering run

### 6. Test Datasets with Ground Truth

**Challenge:** Need to validate clustering accuracy.

**Requirements:**
- **Known Groups:** Datasets where we know the "correct" groups
- **Metrics:** Precision, recall, F1-score for cluster assignments
- **Edge Cases:** New devices, removed devices, behavior changes
- **Validation Pipeline:** Automated testing of clustering accuracy

**Current State:** ❌ No ground truth datasets

---

## Proposed Architecture

### Phase 1: Data Ingestion & Sketch Updates

```
┌─────────────────────────────────────────────────────────────┐
│                    Live Data Ingestion                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  NetFlow/Flows → Sketch Builder → Incremental Sketch Update│
│                                                             │
│  • Update existing sketches (add flows)                     │
│  • Create new sketches (first-seen endpoints)               │
│  • Track: endpoint_first_seen, endpoint_last_seen           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- `IncrementalSketchStore` - Updates sketches as flows arrive
- `FirstSeenTracker` - Detects new endpoints/users
- `SketchFreshness` - Tracks when sketches were last updated

### Phase 2: Incremental Clustering Engine

```
┌─────────────────────────────────────────────────────────────┐
│              Incremental Clustering Engine                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  Fast Path       │      │  Slow Path       │           │
│  │  (New Endpoints) │      │  (Full Re-cluster)│          │
│  │                  │      │                  │           │
│  │  1. Extract      │      │  1. Extract all  │           │
│  │     features     │      │     features     │           │
│  │  2. Find nearest │      │  2. Run HDBSCAN  │           │
│  │     cluster      │      │  3. Merge with   │           │
│  │  3. Assign with  │      │     existing     │           │
│  │     confidence   │      │     SGTs         │           │
│  └──────────────────┘      └──────────────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- `IncrementalClusterer` - Fast path for new endpoints
- `ClusterCentroidStore` - Maintains cluster centroids for fast lookup
- `ClusterStabilityTracker` - Tracks cluster evolution
- `FullClusterer` - Slow path (existing HDBSCAN)

### Phase 3: Identity-Aware Refinement

```
┌─────────────────────────────────────────────────────────────┐
│            Identity-Aware Group Refinement                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 1: Behavior-Based (Immediate)                       │
│    • Cluster by communication patterns                      │
│    • Assign temporary cluster IDs                           │
│                                                             │
│  Phase 2: Identity Enrichment (When Available)             │
│    • Enrich with AD groups, ISE profiles                    │
│    • Refine clusters using identity                         │
│    • Higher confidence when behavior + identity align       │
│                                                             │
│  Phase 3: AI-Enhanced Categorization (Optional)            │
│    • LLM analyzes cluster characteristics                   │
│    • Suggests semantic labels and SGT names                 │
│    • Provides justification for categorizations             │
│                                                             │
│  Phase 4: SGT Assignment (After Review)                    │
│    • Map clusters to stable SGTs                            │
│    • Track SGT membership over time                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- `IdentityEnricher` - Adds identity context to sketches
- `HybridClusterer` - Combines behavior + identity features
- `AICategorizationAgent` - Optional LLM-powered categorization
- `SGTLifecycleManager` - Manages stable SGT assignments

### Phase 4: SGT Lifecycle Management

```
┌─────────────────────────────────────────────────────────────┐
│                  SGT Lifecycle Management                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SGT Registry (Stable)                                     │
│    • SGT 2:  "Corp-Users"    (created: 2025-01-01)        │
│    • SGT 10: "Servers"        (created: 2025-01-01)        │
│                                                             │
│  SGT Membership (Dynamic)                                  │
│    • device-1 → SGT 2   (assigned: 2025-01-05)            │
│    • device-2 → SGT 10  (assigned: 2025-01-06)            │
│    • device-1 → SGT 2   (still, updated: 2025-01-10)      │
│                                                             │
│  Audit Trail                                               │
│    • device-1: [2025-01-05: SGT 2]                        │
│    • device-2: [2025-01-06: SGT 10]                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Database Schema:**
```sql
CREATE TABLE sgt_registry (
    sgt_value INTEGER PRIMARY KEY,
    sgt_name TEXT NOT NULL,
    created_at TIMESTAMP,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE sgt_membership (
    endpoint_id TEXT,
    sgt_value INTEGER,
    assigned_at TIMESTAMP,
    assigned_by TEXT,  -- 'clustering', 'manual', 'ise'
    confidence FLOAT,
    FOREIGN KEY (sgt_value) REFERENCES sgt_registry(sgt_value)
);

CREATE TABLE sgt_assignment_history (
    endpoint_id TEXT,
    sgt_value INTEGER,
    assigned_at TIMESTAMP,
    unassigned_at TIMESTAMP,
    assigned_by TEXT
);
```

### Phase 5: Ground Truth Validation

```
┌─────────────────────────────────────────────────────────────┐
│              Ground Truth Test Datasets                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Dataset 1: Synthetic Campus Network                       │
│    • Known groups: Engineering, Sales, IT, Servers         │
│    • Expected clusters: 8 groups                           │
│    • Validation: Precision, Recall, F1-score               │
│                                                             │
│  Dataset 2: Simulated Device Lifecycle                     │
│    • Add devices over time                                 │
│    • Remove devices                                         │
│    • Change device behavior                                │
│    • Validation: Assignment accuracy over time             │
│                                                             │
│  Dataset 3: Identity Timing Scenarios                      │
│    • Identity data arrives late                            │
│    • Identity data conflicts with behavior                 │
│    • Validation: Identity integration accuracy             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- `GroundTruthDataset` - Test datasets with known clusters
- `ClusteringValidator` - Validates clustering against ground truth
- `MetricsCalculator` - Precision, recall, F1-score

---

## Implementation Plan

### Step 1: First-Seen Tracking & Incremental Sketches

**Goal:** Track when devices/users appear for the first time.

**Tasks:**
1. Add `endpoint_first_seen` and `endpoint_last_seen` to database
2. Add `user_first_seen` and `user_last_seen` to database
3. Update sketch builder to detect new endpoints
4. Add API endpoints to query first-seen events

**Files to Create/Modify:**
- `src/clarion/storage/database.py` - Add first_seen fields
- `src/clarion/ingest/sketch_builder.py` - Detect new endpoints
- `src/clarion/api/routes/devices.py` - First-seen queries

### Step 2: Incremental Clustering Fast Path

**Goal:** Assign new endpoints to existing clusters without full re-clustering.

**Tasks:**
1. Create `IncrementalClusterer` class
2. Store cluster centroids in database
3. Implement nearest-neighbor assignment
4. Add confidence scoring for assignments

**Files to Create:**
- `src/clarion/clustering/incremental.py` - Incremental clustering logic
- Update `src/clarion/storage/database.py` - Store centroids

### Step 3: Identity-Aware Clustering

**Goal:** Handle identity data that arrives asynchronously.

**Tasks:**
1. Create `IdentityEnricher` class
2. Implement phased clustering (behavior → identity → SGT)
3. Add confidence scoring based on identity alignment

**Files to Create:**
- `src/clarion/clustering/identity_clusterer.py` - Identity-aware clustering

### Step 3.5: AI/LLM Integration (Optional)

**Goal:** Add agentic AI to assist with categorization, labeling, and SGT naming.

**Tasks:**
1. Create `AICategorizationAgent` class with pluggable LLM backend
2. Support local models (Llama, Mistral) via Ollama/Transformers
3. Support cloud models (OpenAI, Anthropic) via API
4. Implement RAG (optional) for context-aware categorization
5. Add configuration for AI enablement

**Architecture:**
- **Optional Feature:** AI can be disabled via config
- **Local Models:** Supports Llama, Mistral via Ollama or direct model loading
- **Cloud Models:** Supports OpenAI GPT-4, Anthropic Claude via API
- **RAG (Optional):** Can use database context for better categorization
- **Fallback:** If AI unavailable or disabled, use rule-based labeling

**Files to Create:**
- `src/clarion/clustering/ai_agent.py` - AI categorization agent
- `src/clarion/clustering/llm_backend.py` - LLM backend abstraction
- `src/clarion/clustering/rag_context.py` - RAG context builder (optional)
- `src/clarion/config.py` - AI configuration options

### Step 4: SGT Lifecycle Management

**Goal:** Stable SGTs with dynamic membership.

**Tasks:**
1. Create `SGTLifecycleManager` class
2. Update database schema for SGT registry and membership
3. Implement assignment history tracking
4. Add API endpoints for SGT lifecycle queries

**Files to Create:**
- `src/clarion/clustering/sgt_lifecycle.py` - SGT lifecycle management
- Update `src/clarion/storage/database.py` - SGT tables

### Step 5: Ground Truth Test Datasets

**Goal:** Validate clustering accuracy.

**Tasks:**
1. Create synthetic datasets with known groups
2. Create `ClusteringValidator` class
3. Implement metrics calculation (precision, recall, F1)
4. Add automated validation tests

**Files to Create:**
- `tests/data/ground_truth/` - Test datasets
- `src/clarion/clustering/validator.py` - Validation logic
- `tests/integration/test_clustering_accuracy.py` - Validation tests

### Step 6: Clustering Triggers & Scheduling

**Goal:** Define when clustering should run.

**Tasks:**
1. Create `ClusteringScheduler` class
2. Implement trigger conditions:
   - Initial clustering (after N flows or T time)
   - Incremental assignment (new endpoints with sufficient data)
   - Full re-clustering (periodic or threshold-based)
3. Add configuration for thresholds

**Files to Create:**
- `src/clarion/clustering/scheduler.py` - Clustering triggers

---

## Database Schema Changes

### New Tables

```sql
-- Track endpoint first-seen
ALTER TABLE endpoints ADD COLUMN first_seen TIMESTAMP;
ALTER TABLE endpoints ADD COLUMN last_seen TIMESTAMP;
ALTER TABLE endpoints ADD COLUMN flow_count INTEGER DEFAULT 0;

-- SGT Registry (stable SGTs)
CREATE TABLE sgt_registry (
    sgt_value INTEGER PRIMARY KEY,
    sgt_name TEXT NOT NULL,
    category TEXT,  -- 'users', 'servers', 'devices', 'special'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- SGT Membership (dynamic assignments)
CREATE TABLE sgt_membership (
    endpoint_id TEXT NOT NULL,
    sgt_value INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by TEXT,  -- 'clustering', 'manual', 'ise', 'incremental'
    confidence FLOAT,
    cluster_id INTEGER,  -- Which cluster this came from
    PRIMARY KEY (endpoint_id),
    FOREIGN KEY (sgt_value) REFERENCES sgt_registry(sgt_value)
);

-- SGT Assignment History (audit trail)
CREATE TABLE sgt_assignment_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint_id TEXT NOT NULL,
    sgt_value INTEGER NOT NULL,
    assigned_at TIMESTAMP NOT NULL,
    unassigned_at TIMESTAMP,
    assigned_by TEXT,
    FOREIGN KEY (sgt_value) REFERENCES sgt_registry(sgt_value)
);

-- Cluster Centroids (for fast incremental assignment)
CREATE TABLE cluster_centroids (
    cluster_id INTEGER NOT NULL,
    sgt_value INTEGER,
    feature_vector TEXT,  -- JSON array of centroid features
    member_count INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cluster_id),
    FOREIGN KEY (sgt_value) REFERENCES sgt_registry(sgt_value)
);

-- User First-Seen
ALTER TABLE ad_users ADD COLUMN first_seen TIMESTAMP;
ALTER TABLE ad_users ADD COLUMN last_seen TIMESTAMP;
```

---

## API Endpoints

### New Endpoints

```python
# First-seen tracking
GET /api/devices/first-seen?since=2025-01-01
GET /api/users/first-seen?since=2025-01-01

# Incremental clustering
POST /api/clustering/incremental-assign
GET /api/clustering/pending-assignments  # New endpoints waiting for assignment

# SGT Lifecycle
GET /api/sgts/registry  # List all SGTs
POST /api/sgts/{sgt_value}/members  # Add member to SGT
DELETE /api/sgts/{sgt_value}/members/{endpoint_id}  # Remove member
GET /api/sgts/{sgt_value}/history  # Assignment history
GET /api/sgts/membership/{endpoint_id}  # Current SGT for endpoint

# Clustering triggers
GET /api/clustering/status  # Current clustering state
POST /api/clustering/trigger  # Manually trigger clustering
```

---

## Testing Strategy

### Unit Tests

1. **Incremental Clustering**
   - Test fast path assignment
   - Test confidence scoring
   - Test centroid updates

2. **Identity Integration**
   - Test phased clustering
   - Test identity enrichment
   - Test confidence alignment

3. **SGT Lifecycle**
   - Test SGT stability
   - Test membership tracking
   - Test assignment history

### Integration Tests

1. **Ground Truth Validation**
   - Run clustering on known datasets
   - Validate against expected clusters
   - Calculate precision/recall/F1

2. **End-to-End Workflow**
   - Simulate live data ingestion
   - Test incremental assignment
   - Test full re-clustering
   - Validate SGT assignments

### Performance Tests

1. **Incremental Assignment Speed**
   - Measure assignment time for new endpoints
   - Target: <100ms per endpoint

2. **Full Clustering Scalability**
   - Test with 10K, 100K, 1M endpoints
   - Measure clustering time
   - Target: <1 hour for 100K endpoints

---

## Configuration

```yaml
clustering:
  # Initial clustering triggers
  initial_clustering:
    min_flows: 10000
    min_time_hours: 24
    min_endpoints: 100
  
  # Incremental assignment
  incremental:
    min_flows_per_endpoint: 100
    max_assignment_delay_hours: 1
    confidence_threshold: 0.7
  
  # Full re-clustering
  full_recluster:
    interval_hours: 24
    trigger_on_new_endpoint_ratio: 0.2  # Re-cluster if >20% new endpoints
    trigger_on_behavior_change: true
  
  # Identity integration
  identity:
    wait_for_identity_hours: 1  # Wait for identity before final assignment
    identity_weight: 0.3  # Weight for identity features (0.0-1.0)
    behavior_weight: 0.7  # Weight for behavior features
  
  # AI/LLM Integration (Optional)
  ai:
    enabled: false  # Set to true to enable AI categorization
    provider: "local"  # "local", "openai", "anthropic"
    
    # Local model (Ollama or Transformers)
    local:
      model_type: "ollama"  # "ollama" or "transformers"
      model_name: "llama2"  # Model name (e.g., "llama2", "mistral")
      base_url: "http://localhost:11434"  # Ollama base URL
      timeout: 30  # Request timeout in seconds
    
    # OpenAI
    openai:
      api_key: ""  # Set via environment variable CLARION_OPENAI_API_KEY
      model: "gpt-4-turbo-preview"
      temperature: 0.3
      max_tokens: 1000
    
    # Anthropic
    anthropic:
      api_key: ""  # Set via environment variable CLARION_ANTHROPIC_API_KEY
      model: "claude-3-opus-20240229"
      max_tokens: 1000
    
    # RAG (Retrieval-Augmented Generation) - Optional
    rag:
      enabled: false  # Enable RAG for context-aware categorization
      use_database_context: true  # Use database for RAG context
      max_context_items: 50  # Max items to include in context
  
  # SGT lifecycle
  sgt:
    stability_threshold_days: 7  # SGT is "stable" after 7 days
    min_members_for_active: 1  # Minimum members to keep SGT active
```

---

## Success Metrics

1. **Clustering Accuracy**
   - Precision: >90% (correct cluster assignments)
   - Recall: >85% (all endpoints assigned to correct cluster)
   - F1-score: >87%

2. **Performance**
   - Incremental assignment: <100ms per endpoint
   - Full clustering: <1 hour for 100K endpoints
   - Memory usage: <10GB for 100K endpoints

3. **Stability**
   - SGT assignment stability: >95% (devices don't change SGTs unnecessarily)
   - Cluster stability: >80% (clusters don't merge/split frequently)

4. **Coverage**
   - Endpoint coverage: >95% (95% of endpoints have SGT assignments)
   - Identity coverage: >70% (70% of endpoints have identity context)

---

## Next Steps

1. **Immediate (Week 1-2)**
   - Implement first-seen tracking
   - Create database schema changes
   - Build incremental clustering fast path
   - **Validate AI architecture** (verify local model support before implementation)

2. **Short-term (Week 3-4)**
   - Implement SGT lifecycle management
   - Add identity-aware clustering
   - **Implement AI/LLM integration** (if architecture validated)
   - Create ground truth test datasets

3. **Medium-term (Month 2)**
   - Implement clustering triggers
   - Add validation metrics
   - Performance testing and optimization
   - Build test scenarios for multiple company types

4. **Long-term (Month 3+)**
   - Production deployment
   - Monitoring and alerting
   - Customer feedback integration

---

## Related Documentation

- **AI Integration:** See `docs/AI_INTEGRATION.md` for detailed AI/LLM architecture
- **Data Architecture:** See `docs/DATA_ARCHITECTURE.md` for database design
- **Roadmap:** See `PRIORITIZED_ROADMAP.md` for development priorities

---

## Appendix: Current Clustering Implementation Details

### HDBSCAN Algorithm

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

### Feature Extraction

Endpoints are clustered based on **behavioral features** extracted from network flows:

**18 Behavioral Features:**
- Communication patterns: unique_peers, unique_services, peer_diversity
- Traffic patterns: bytes_in, bytes_out, in_out_ratio
- Port usage: port_diversity, top_ports
- Temporal patterns: active_hours, flow_count

**Feature Calculation:**
1. **Unique Peers** - HyperLogLog cardinality estimate
2. **Unique Services** - HyperLogLog cardinality estimate  
3. **Port Frequency** - Count-Min Sketch for port distribution
4. **Service Frequency** - Count-Min Sketch for service distribution
5. **Bytes In/Out** - Direct counters
6. **Active Hours** - Time-based calculation
7. **Flow Count** - Direct counter

### Current Clustering Process

1. **Feature Extraction** - Extract 18 features from endpoint sketches
2. **Matrix Conversion** - Convert features to numpy matrix
3. **HDBSCAN Clustering** - Run HDBSCAN algorithm
4. **Semantic Labeling** - Label clusters using ISE profiles, device types, AD groups
5. **SGT Mapping** - Map clusters to Security Group Tags

### Cluster Labeling Strategy

The `SemanticLabeler` uses a priority-based approach:

1. **ISE Profile** (Highest Priority) - If 80%+ have same ISE profile
2. **Device Type** - If 70%+ are same device type
3. **AD Group Membership** - If 60%+ are in same AD group
4. **Behavioral Patterns** - Infer from communication patterns

See `src/clarion/clustering/labeling.py` for implementation details.

