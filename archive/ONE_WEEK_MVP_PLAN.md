# One-Week MVP Plan

## Goal
Build a working MVP of the categorization engine enhancements in one week, focusing on the most critical foundational pieces.

---

## MVP Scope (Critical Path Only)

### ✅ Week 1 MVP Goals

1. **Database Schema Updates** (Day 1-2)
   - First-seen tracking (endpoints, users)
   - SGT registry table (stable SGT definitions)
   - SGT membership table (dynamic assignments)
   - Cluster centroids table (for incremental clustering)
   - Basic SGT assignment history

2. **First-Seen Tracking** (Day 2)
   - Detect new endpoints/users
   - Track first_seen and last_seen timestamps
   - API endpoints to query first-seen events

3. **SGT Lifecycle Management** (Day 3-4)
   - Stable SGT registry
   - Dynamic endpoint → SGT assignments
   - Basic assignment history tracking
   - API endpoints for SGT lifecycle

4. **Incremental Clustering (Basic)** (Day 4-5)
   - Fast path: assign new endpoints to existing clusters
   - Store and retrieve cluster centroids
   - Nearest neighbor assignment
   - Basic confidence scoring for assignments

5. **Basic Confidence & Explanation** (Day 5-6)
   - Add confidence scores to cluster assignments
   - Add confidence scores to SGT assignments
   - Basic explanation generation

6. **Integration & Testing** (Day 6-7)
   - Update API endpoints
   - Integration tests
   - Documentation updates

---

## Out of Scope (Defer to Post-MVP)

- Full quality assurance framework (basic validation only)
- Full edge case handling (basic noise handling exists)
- Override feedback loop (basic override tracking only)
- AI integration (defer to after MVP)
- Full explainability system (basic explanations only)
- Streaming data processing (batch mode sufficient for MVP)

---

## Daily Breakdown

### Day 1: Database Schema Foundation
**Goal:** Update database schema with all new tables

**Tasks:**
- [ ] Add `first_seen` and `last_seen` to endpoints table
- [ ] Create `sgt_registry` table
- [ ] Create `sgt_membership` table
- [ ] Create `sgt_assignment_history` table
- [ ] Create `cluster_centroids` table
- [ ] Create migration script
- [ ] Test schema updates

**Files:**
- `src/clarion/storage/database.py`
- `scripts/migrate_schema_v2.py` (new)

### Day 2: First-Seen Tracking
**Goal:** Track when endpoints/users are first seen

**Tasks:**
- [ ] Update sketch builder to detect new endpoints
- [ ] Implement first-seen detection logic
- [ ] Store first_seen/last_seen in database
- [ ] Create API endpoints for first-seen queries
- [ ] Unit tests

**Files:**
- `src/clarion/ingest/sketch_builder.py` (update)
- `src/clarion/api/routes/devices.py` (new/update)
- `tests/unit/test_first_seen.py` (new)

### Day 3: SGT Lifecycle Management (Part 1)
**Goal:** Stable SGT registry and basic membership tracking

**Tasks:**
- [ ] Create `SGTLifecycleManager` class
- [ ] Implement SGT registry management (create, read, update)
- [ ] Implement basic SGT membership (assign, unassign)
- [ ] Store assignments in database
- [ ] Unit tests

**Files:**
- `src/clarion/clustering/sgt_lifecycle.py` (new)
- `tests/unit/test_sgt_lifecycle.py` (new)

### Day 4: SGT Lifecycle Management (Part 2) + Incremental Clustering Foundation
**Goal:** Complete SGT lifecycle, start incremental clustering

**Tasks:**
- [ ] SGT assignment history tracking
- [ ] API endpoints for SGT lifecycle
- [ ] Create `IncrementalClusterer` class structure
- [ ] Implement cluster centroid storage
- [ ] Implement centroid retrieval

**Files:**
- `src/clarion/clustering/sgt_lifecycle.py` (continue)
- `src/clarion/api/routes/sgt.py` (new)
- `src/clarion/clustering/incremental.py` (new, partial)

### Day 5: Incremental Clustering Implementation
**Goal:** Fast path for assigning new endpoints to existing clusters

**Tasks:**
- [ ] Implement nearest neighbor assignment
- [ ] Calculate distances to cluster centroids
- [ ] Assign endpoints to clusters
- [ ] Update centroids after assignment
- [ ] Basic confidence scoring (distance-based)
- [ ] Unit tests

**Files:**
- `src/clarion/clustering/incremental.py` (complete)
- `src/clarion/clustering/confidence.py` (new, basic)
- `tests/unit/test_incremental.py` (new)

### Day 6: Confidence Scoring & Basic Explanations
**Goal:** Add confidence and explanations to all decisions

**Tasks:**
- [ ] Add confidence scoring to cluster assignments
- [ ] Add confidence scoring to SGT assignments
- [ ] Create basic explanation generator
- [ ] Update ClusterLabel with confidence and explanation
- [ ] Update API responses to include confidence/explanations
- [ ] Unit tests

**Files:**
- `src/clarion/clustering/confidence.py` (enhance)
- `src/clarion/clustering/explanation.py` (update existing, enhance)
- `src/clarion/clustering/labeling.py` (update)
- `tests/unit/test_confidence.py` (new)

### Day 7: Integration, Testing & Documentation
**Goal:** Integrate everything and test end-to-end

**Tasks:**
- [ ] Update API routes to use new functionality
- [ ] Integration tests (full workflow)
- [ ] Update existing tests
- [ ] Fix any bugs
- [ ] Update API documentation
- [ ] Quick README updates

**Files:**
- `src/clarion/api/routes/clustering.py` (update)
- `tests/integration/test_categorization_mvp.py` (new)
- `README.md` (update)
- Various test files

---

## Success Criteria for MVP

### Must Have (Required for MVP)
- [ ] Database schema updated and migrated
- [ ] First-seen tracking working (detects new endpoints)
- [ ] SGT lifecycle working (stable registry, dynamic membership)
- [ ] Incremental clustering fast path working (assign new endpoints)
- [ ] Basic confidence scores on all assignments
- [ ] Basic explanations available
- [ ] All API endpoints functional
- [ ] Basic integration tests passing

### Nice to Have (If Time Permits)
- [ ] Enhanced explanations (detailed "why")
- [ ] Confidence thresholds (high/medium/low)
- [ ] Edge case handling (beyond basic noise cluster)
- [ ] Override tracking (basic, not full feedback loop)

---

## Risk Mitigation

### If Behind Schedule
1. **Day 1-2 delay:** Skip migration script, do schema updates manually
2. **Day 3-4 delay:** Simplify SGT lifecycle (skip history tracking initially)
3. **Day 5 delay:** Simplify incremental clustering (basic nearest neighbor only)
4. **Day 6 delay:** Minimal confidence scoring (just distance-based)
5. **Day 7 delay:** Focus on core functionality, skip some tests

### Critical Path
The absolute minimum for a working MVP:
1. Database schema ✅
2. First-seen tracking ✅
3. SGT lifecycle (registry + membership) ✅
4. Incremental clustering (basic fast path) ✅

Everything else can be simplified or deferred.

---

## Implementation Approach

1. **Start with database schema** - Everything depends on this
2. **Build incrementally** - Each day builds on previous day
3. **Test as we go** - Don't wait until Day 7
4. **Keep it simple** - MVP means "minimum viable", not "perfect"
5. **Focus on core workflow** - New endpoint → assign to cluster → assign SGT

---

## Files to Create/Modify

### New Files
- `scripts/migrate_schema_v2.py` - Database migration
- `src/clarion/clustering/sgt_lifecycle.py` - SGT lifecycle management
- `src/clarion/clustering/incremental.py` - Incremental clustering
- `src/clarion/clustering/confidence.py` - Confidence scoring
- `src/clarion/api/routes/devices.py` - Device/first-seen endpoints
- `src/clarion/api/routes/sgt.py` - SGT lifecycle endpoints
- `tests/unit/test_first_seen.py`
- `tests/unit/test_sgt_lifecycle.py`
- `tests/unit/test_incremental.py`
- `tests/unit/test_confidence.py`
- `tests/integration/test_categorization_mvp.py`

### Files to Modify
- `src/clarion/storage/database.py` - Schema updates, new methods
- `src/clarion/ingest/sketch_builder.py` - First-seen detection
- `src/clarion/clustering/explanation.py` - Enhanced explanations
- `src/clarion/clustering/labeling.py` - Add confidence
- `src/clarion/api/routes/clustering.py` - Use new functionality
- `README.md` - Update with new capabilities

---

## Daily Checkpoints

### End of Day 1
- Schema updates complete
- Migration script works
- Can query new tables

### End of Day 2
- First-seen tracking working
- New endpoints detected
- API endpoint returns first-seen events

### End of Day 3
- SGT registry working
- Can create/read SGTs
- Basic membership tracking working

### End of Day 4
- SGT lifecycle complete
- API endpoints functional
- Cluster centroids stored/retrieved

### End of Day 5
- Incremental clustering working
- New endpoints assigned to clusters
- Confidence scores calculated

### End of Day 6
- All assignments have confidence
- Basic explanations generated
- API responses include confidence/explanations

### End of Day 7
- Full integration working
- Tests passing
- MVP complete!

---

Let's build this! 🚀

