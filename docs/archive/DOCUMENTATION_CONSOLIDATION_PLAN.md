# Documentation Consolidation Plan

## Current State
**Total active .md files:** ~25 (excluding archives and node_modules)

## Consolidation Strategy

### 🎯 High Priority Consolidations

#### 1. ISE Documentation (3 files → 1 file) ⭐
**Files to merge:**
- `docs/ISE_SGT_ASSIGNMENT.md` (227 lines)
- `docs/ISE_INTEGRATION.md` (322 lines)
- `docs/CLARION_ISE_WORKFLOW.md` (likely ~200+ lines)

**Action:** Merge all into `docs/ISE_INTEGRATION.md`
- Add ISE_SGT_ASSIGNMENT content as a section
- Add CLARION_ISE_WORKFLOW scenarios as a section
- Keep as single comprehensive ISE integration guide

#### 2. CI/CD Setup Documentation (4 files → 1 file) ⭐
**Files to merge:**
- `.github/workflows/BENCHMARK_SETUP.md`
- `.github/workflows/NOTIFICATIONS_SETUP.md`
- `.github/workflows/QUICK_START_SECRETS.md`
- `GITHUB_SECRETS_SETUP.md` (root level - duplicate?)

**Action:** Merge into `.github/workflows/SETUP.md`
- Single comprehensive CI/CD setup guide
- Include all optional features setup

#### 3. Root-Level Setup Files (5 files → merge into QUICK_START.md)
**Files to review/merge:**
- `SETUP_CHECKLIST.md`
- `SETUP_OPTIONAL_FEATURES.md`
- `TESTING_SETUP.md`
- `GITHUB_SECRETS_SETUP.md` (if different from workflows version)
- `ONE_WEEK_MVP_PLAN.md` (historical, can archive)

**Action:** 
- Merge relevant content into `QUICK_START.md`
- Archive `ONE_WEEK_MVP_PLAN.md` (historical reference)
- Remove duplicates

#### 4. ISE Workflow Documentation (1 file → merge)
**File:** `docs/CLUSTER_ASSIGNMENT_WORKFLOW.md`

**Action:** Merge into `docs/ISE_INTEGRATION.md` as it's about policy recommendations triggered by cluster changes

#### 5. Testing Documentation (1 file → move)
**File:** `TESTING_WITHOUT_AD_ISE.md` (root level)

**Action:** Move to `docs/TESTING.md` and expand to comprehensive testing guide

#### 6. Collector Documentation (3 files → 1-2 files)
**Files:**
- `collector/README.md` (keep as main)
- `collector/SCALABILITY.md` (merge into README)
- `collector/TESTING.md` (merge into README or keep separate section)

**Action:** Merge SCALABILITY and TESTING into README.md as sections

---

### 📋 Medium Priority (Review & Decision)

#### 7. Engine Review Documentation
**File:** `docs/CATEGORIZATION_ENGINE_REVIEW.md`

**Decision:** Keep if it has unique review insights, otherwise merge into `docs/CATEGORIZATION_ENGINE.md`

#### 8. Architecture Documentation
**Files:**
- `docs/DESIGN.md` - General system design
- `docs/DATA_ARCHITECTURE.md` (527 lines) - Data architecture
- `docs/TOPOLOGY_ARCHITECTURE.md` (707 lines) - Topology architecture
- `docs/ADMIN_GUIDE.md` (385 lines) - Admin guide

**Decision:** 
- Keep `docs/DESIGN.md` if it's a high-level overview
- Keep `docs/DATA_ARCHITECTURE.md` (extensive, >500 lines)
- Keep `docs/TOPOLOGY_ARCHITECTURE.md` (extensive, >500 lines)
- Keep `docs/ADMIN_GUIDE.md` (extensive, admin-focused)

---

### ❌ Files to Archive (Historical/Completed)

1. `ONE_WEEK_MVP_PLAN.md` - Historical MVP plan (completed)
2. `docs/CATEGORIZATION_ENGINE_REVIEW.md` - If merged into main doc
3. Any duplicate setup files after consolidation

---

## Final Structure

### Root Level (5 files)
- ✅ `README.md` - Main entry point
- ✅ `QUICK_START.md` - Enhanced with all setup info
- ✅ `CAPABILITIES_ROADMAP.md` - Feature inventory
- ✅ `PRIORITIZED_ROADMAP.md` - Development priorities
- ❌ Remove: Setup checklist files (merge into QUICK_START)
- ❌ Archive: `ONE_WEEK_MVP_PLAN.md`

### docs/ (8 files)
- ✅ `docs/CATEGORIZATION_ENGINE.md` - Core engine
- ✅ `docs/AI_INTEGRATION.md` - AI integration
- ✅ `docs/ISE_INTEGRATION.md` - **CONSOLIDATED** ISE guide (merge 3 files)
- ✅ `docs/TESTING.md` - **NEW** Testing guide (from TESTING_WITHOUT_AD_ISE.md)
- ✅ `docs/DESIGN.md` - System design
- ✅ `docs/DATA_ARCHITECTURE.md` - Data architecture
- ✅ `docs/TOPOLOGY_ARCHITECTURE.md` - Topology architecture
- ✅ `docs/ADMIN_GUIDE.md` - Admin guide

### Component Docs (Keep)
- ✅ `collector/README.md` - **ENHANCED** (merge SCALABILITY, TESTING)
- ✅ `frontend/README.md`
- ✅ `lab/README.md`
- ✅ `lab/VM_ARCHITECTURE.md`
- ✅ `tests/data/ground_truth/README.md`
- ✅ `tests/data/ground_truth/SCHEMA.md`

### CI/CD Docs (2 files)
- ✅ `.github/workflows/README.md` - CI/CD overview
- ✅ `.github/workflows/SETUP.md` - **NEW** Consolidated setup (merge 3-4 files)

---

## Action Plan

### Phase 1: High Priority (Do First)
1. ✅ Merge ISE docs → `docs/ISE_INTEGRATION.md`
2. ✅ Merge CI/CD setup docs → `.github/workflows/SETUP.md`
3. ✅ Move TESTING_WITHOUT_AD_ISE.md → `docs/TESTING.md`
4. ✅ Merge collector docs → `collector/README.md`
5. ✅ Merge setup files into QUICK_START.md
6. ✅ Archive `ONE_WEEK_MVP_PLAN.md`

### Phase 2: Cleanup
7. ✅ Update all internal links
8. ✅ Update README.md documentation section
9. ✅ Remove duplicates from root level

---

## Expected Result

**Before:** ~25 active .md files
**After:** ~18-19 .md files
**Reduction:** ~24-28% fewer files

**Benefits:**
- Easier navigation
- Less duplication
- More comprehensive guides
- Better maintainability

