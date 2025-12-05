# Schema Reuse Strategy - Team Review Summary

**Date:** November 1, 2025  
**Status:** Ready for Team Review  
**Purpose:** Review model mapping strategy before proceeding with implementation

---

## Executive Summary

This document summarizes the database schema reuse strategy for the microservices migration. The backend API will use the **same Cloud SQL database** as the original monolithic app, starting with exact schema compatibility (Phase 1) and evolving with data migrations (Phase 2).

**Key Decision:** Clean cut migration - deploy new system, switch DNS all at once, keep original app as backup.

---

## Models Mapped

### ✅ 1. ChoreographyTask
- **Original:** `choreography/models.py::ChoreographyTask`
- **Backend:** `backend/apps/choreography/models.py::ChoreographyTask`
- **Table:** `choreography_tasks`
- **Status:** ✅ MAPPED AND VERIFIED

**Critical Compatibility Points:**
- ✅ Primary key: `task_id` (CharField(36), NOT UUIDField)
- ✅ Status choices: 'started', 'running', 'completed', 'failed'
- ✅ Default status: 'started' (not 'pending')
- ✅ Foreign key: `user` with `related_name='choreography_tasks'`
- ✅ Table name: `choreography_tasks`
- ✅ New field added: `job_execution_name` (nullable, safe)

### ✅ 2. SavedChoreography
- **Original:** `choreography/models.py::SavedChoreography`
- **Backend:** `backend/apps/collections/models.py::SavedChoreography`
- **Table:** `saved_choreographies`
- **Status:** ✅ MAPPED AND VERIFIED

**Critical Compatibility Points:**
- ✅ Primary key: `id` (UUIDField with uuid4 default)
- ✅ Difficulty choices: 'beginner', 'intermediate', 'advanced'
- ✅ Foreign key: `user` with `related_name='choreographies'`
- ✅ Table name: `saved_choreographies`
- ✅ File fields: `video_path` (FileField), `thumbnail_path` (ImageField)
- ✅ No new fields added - exact mirror

### ⏳ 3. User
- **Original:** Django built-in `auth.User`
- **Backend:** `backend/apps/authentication/models.py::User`
- **Table:** `users` (custom user model)
- **Status:** ⏳ TODO - Needs implementation

---

## Critical Requirements

### Database Table Names

**ALL backend models MUST use exact table names from original app:**

| Model | Backend Location | db_table | Status |
|-------|------------------|----------|--------|
| ChoreographyTask | `backend/apps/choreography/models.py` | `choreography_tasks` | ✅ |
| SavedChoreography | `backend/apps/collections/models.py` | `saved_choreographies` | ✅ |
| User | `backend/apps/authentication/models.py` | `users` | ⏳ |

### ForeignKey Related Names

**ALL ForeignKey fields MUST use exact related_name from original app:**

| Model | Field | Related To | related_name | Status |
|-------|-------|------------|--------------|--------|
| ChoreographyTask | `user` | User | `choreography_tasks` | ✅ |
| SavedChoreography | `user` | User | `choreographies` | ✅ |

**Why This Matters:**
- Both systems use same code patterns: `user.choreography_tasks.all()`
- Changing related_name would break original app's queries
- Required for parallel operation during migration

### Field Type Compatibility

**Phase 1: Initial Compatibility (MUST MATCH EXACTLY)**

#### ChoreographyTask Fields:
- `task_id`: CharField(36) - **NOT UUIDField** (stores UUID as string)
- `status`: CharField(20) with choices ['started', 'running', 'completed', 'failed']
- `progress`: IntegerField, default=0
- `stage`: CharField(50), default='initializing'
- `message`: TextField, default='Starting choreography generation...'
- `result`: JSONField, nullable
- `error`: TextField, nullable
- `created_at`: DateTimeField, auto_now_add, indexed
- `updated_at`: DateTimeField, auto_now
- `job_execution_name`: CharField(500), nullable - **NEW** (safe to add)

#### SavedChoreography Fields:
- `id`: UUIDField, primary key, default=uuid.uuid4
- `title`: CharField(200)
- `video_path`: FileField(500) - **NOT CharField**
- `thumbnail_path`: ImageField(500), nullable
- `difficulty`: CharField(20) with choices ['beginner', 'intermediate', 'advanced']
- `duration`: FloatField (seconds)
- `music_info`: JSONField, nullable
- `generation_parameters`: JSONField, nullable
- `created_at`: DateTimeField, auto_now_add, indexed

---

## Two-Phase Approach

### Phase 1: Initial Compatibility (Start Here)

**Goal:** Backend models match original schema exactly for data compatibility

**Rules:**
- ✅ Use existing table names with `db_table`
- ✅ Match field types exactly
- ✅ Match ForeignKey `related_name` exactly
- ✅ Match status/difficulty choices exactly
- ✅ Can add new nullable fields (e.g., `job_execution_name`)
- ❌ Cannot change existing field types
- ❌ Cannot rename existing fields
- ❌ Cannot change table names

**Benefits:**
- Both systems can read/write same data
- Zero downtime migration possible
- Easy rollback if needed
- Original app continues working

### Phase 2: Schema Improvements (After Migration Success)

**Goal:** Improve schema with data migrations after original app is decommissioned

**Potential Improvements:**
1. **ChoreographyTask:**
   - Migrate `task_id` from CharField(36) → UUIDField
   - Add validators for progress (0-100 range)
   - Improve status choices ('started' → 'pending', 'running' → 'processing')
   - Add composite indexes for common queries

2. **SavedChoreography:**
   - Add full-text search on title field
   - Add tags/categories for organization
   - Add sharing/visibility options
   - Add favorites/likes functionality

**When to Start Phase 2:**
- ✅ Migration successful (1-2 weeks of stable operation)
- ✅ Original app decommissioned
- ✅ All users migrated to new system
- ✅ No rollback risk

---

## Testing Requirements

### Data Compatibility Tests

**MUST TEST before cutover:**

1. **Backend reads original app's data:**
   - ✅ Backend can query ChoreographyTask records created by original app
   - ✅ Backend can query SavedChoreography records created by original app
   - ✅ Status values are interpreted correctly
   - ✅ Foreign key relationships work

2. **Original app reads backend's data:**
   - ✅ Original app can query ChoreographyTask records created by backend
   - ✅ Original app can query SavedChoreography records created by backend
   - ✅ New fields (job_execution_name) don't break original app
   - ✅ Foreign key relationships work

3. **Concurrent writes:**
   - ✅ Both systems can write simultaneously without conflicts
   - ✅ No data corruption
   - ✅ Database transactions work correctly

4. **Elasticsearch compatibility:**
   - ✅ Both systems query same Elasticsearch index
   - ✅ Queries return same results
   - ✅ Embeddings work for both systems

5. **Cloud Storage compatibility:**
   - ✅ Both systems access same GCS bucket
   - ✅ Video files accessible from both systems
   - ✅ File paths work for both systems

---

## Migration Approach

### Clean Cut Migration Strategy

**Phase 1: Parallel Operation (Week 5-6)**
1. Original app continues on Compute Engine
2. Backend API deployed to Cloud Run
3. **Both connect to SAME Cloud SQL database**
4. Both can read/write ChoreographyTask and SavedChoreography
5. Both query same Elasticsearch index
6. Both use same GCS bucket
7. Test thoroughly

**Phase 2: Cutover (Week 6)**
1. Verify new system works correctly
2. **Switch DNS to new system** (all traffic at once)
3. Original app kept running as backup (no traffic)
4. Monitor closely for 24-48 hours

**Phase 3: Verification (Week 6-7)**
1. Monitor new system for 1-2 weeks
2. Fix any issues
3. Verify all features working
4. Original app remains as backup for rollback

**Phase 4: Cleanup (Week 8)**
1. Confirm migration successful
2. Archive original app codebase
3. Delete original app from Compute Engine
4. Keep database (still in use by new system)

---

## Rollback Strategy

**Original app kept running as backup for quick rollback if needed.**

### Rollback Procedure

**If Critical Issues Occur:**

1. **Immediate Action** (< 15 minutes):
   - Update DNS to point back to original app
   - Verify original app responding correctly
   - Notify team of rollback

2. **Investigation** (1-2 hours):
   - Identify root cause
   - Document issues
   - Assess impact

3. **Fix** (1-2 weeks):
   - Fix issues in new system
   - Test thoroughly
   - Retry cutover when ready

### When to Delete Original App

**Wait 1-2 weeks after cutover, then:**
- ✅ New system running smoothly
- ✅ All features verified working
- ✅ No critical bugs
- ✅ Team confident in new system

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Schema mismatch** | Critical | High | Document schema first, mirror exactly, verify db_table names |
| **Data corruption** | Critical | Medium | Test concurrent writes, use transactions, monitor |
| **Breaking original app** | Critical | Medium | Never change existing fields, only add nullable fields |
| **related_name conflicts** | High | Medium | Match related_name exactly, test reverse queries |
| **Status value mismatch** | High | Medium | Match status choices exactly, test status updates |
| **File path issues** | Medium | Low | Use same FileField types, test file access |

---

## Review Questions for Team

### 1. Model Mapping
- ✅ Do the mapped models cover all necessary functionality?
- ✅ Are there any missing models we need to map?
- ✅ Do the field types match the original schema exactly?

### 2. Database Strategy
- ✅ Is the shared database approach acceptable?
- ✅ Are the table names correct?
- ✅ Are the related_name values correct?

### 3. Migration Approach
- ✅ Is the clean cut migration strategy acceptable?
- ✅ Is keeping the original app as backup acceptable?
- ✅ Is the 1-2 week verification period sufficient?

### 4. Testing Strategy
- ✅ Are the data compatibility tests sufficient?
- ✅ Do we need additional tests?
- ✅ Who will perform the testing?

### 5. Rollback Strategy
- ✅ Is the rollback procedure clear?
- ✅ Is the rollback timeline acceptable?
- ✅ Who has authority to trigger rollback?

### 6. Phase 2 Improvements
- ✅ Are the proposed schema improvements valuable?
- ✅ Should we plan Phase 2 improvements now or later?
- ✅ What priority should Phase 2 have?

### 7. Risks
- ✅ Are there additional risks we should consider?
- ✅ Are the mitigation strategies sufficient?
- ✅ Do we need additional safeguards?

---

## Next Steps

**After Team Review:**

1. ✅ Address any concerns or questions
2. ✅ Update MODEL_REUSE_STRATEGY.md if needed
3. ✅ Get team sign-off on approach
4. ✅ Proceed to Phase 0.3: Set Up Local Development Environment

**Before Implementation:**

1. ✅ Verify access to existing Cloud SQL database
2. ✅ Document exact schema from production database
3. ✅ Create test data for local development
4. ✅ Set up local PostgreSQL with same schema

---

## Sign-Off

**Required Approvals:**

- [ ] Tech Lead: _____________________
- [ ] Backend Developer: _____________________
- [ ] Database Administrator: _____________________
- [ ] DevOps Engineer: _____________________

**Date:** _____________________

**Notes:**
_____________________
_____________________
_____________________

