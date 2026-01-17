# Resume Crafter Application Monitoring Report

**Report Generated:** 2026-01-12 16:20:00 UTC
**Last Updated:** 2026-01-12 16:26:00 UTC
**Monitoring Status:** ACTIVE

---

## Executive Summary

| Component | Status | Critical Issues | Warnings |
|-----------|--------|-----------------|----------|
| Backend API (FastAPI) | WARNING | 0 | 2 |
| ARQ Worker | CRITICAL | 3 | 1 |
| Frontend (Next.js) | OK | 0 | 1 |

**Overall Status: CRITICAL - ARQ Worker terminated and jobs cancelled/failed**

---

## Critical Issues

### 1. [CRITICAL] ARQ Worker Shutdown - Jobs Cancelled

**Timestamp:** 2026-01-12 16:22:36
**Component:** ARQ Worker (Background Tasks)
**Severity:** CRITICAL

**Error Message:**
```
shutdown on SIGTERM - 0 jobs complete - 2 failed - 0 retries - 3 ongoing to cancel
```

**Details:**
The ARQ worker received a SIGTERM signal and was forced to shut down with active jobs:
- 2 jobs had already failed
- 3 ongoing jobs were cancelled mid-execution
- Jobs `fc4dfdb677534df7a8a7be3b34535bc5` and `0ffdf1602f4043c88e783ecfe9308f9a` marked as "cancelled, will be run again"

**Impact:**
- Document processing was abruptly terminated
- Users' documents may be stuck in "PROCESSING" state
- Data consistency may be affected if partial commits occurred

**Suggested Fixes:**
1. Implement graceful shutdown handling with job completion timeout
2. Add transaction rollback on worker shutdown
3. Configure proper process supervision (systemd, supervisord) with appropriate shutdown signals

---

### 2. [CRITICAL] ARQ Worker - KeyError During Shutdown

**Timestamp:** 2026-01-12 16:22:36
**Component:** ARQ Worker (Background Tasks)
**Severity:** CRITICAL

**Error Message:**
```python
KeyError: '56fb77a8cc05442f9f03da02dbe7d4ab'
# Occurred in: arq/worker.py line 603: del self.job_tasks[job_id]
```

**Root Cause:**
Race condition in ARQ worker during shutdown. The job was already removed from `job_tasks` dictionary when the cleanup tried to delete it again.

**Impact:**
- Worker shutdown was not clean
- Potential for orphaned job states in Redis

**Suggested Fixes:**
1. Update ARQ version if a patch is available
2. Add defensive checks before job_tasks cleanup
3. Consider filing an issue with the ARQ project if this is a bug

---

### 3. [CRITICAL] ARQ Worker - TimeoutError in Document Processing

**Timestamp:** 2026-01-12 16:19:17
**Component:** ARQ Worker (Background Tasks)
**Severity:** CRITICAL

**Error Message:**
```
TimeoutError: process_document failed
asyncio.exceptions.CancelledError during database ping
```

**Affected Tasks:**
- `0ffdf1602f4043c88e783ecfe9308f9a:process_document` - Document UUID: `e4c1a07c-33b0-4c59-b78d-395c73f9a257` (761.94s timeout)
- `56fb77a8cc05442f9f03da02dbe7d4ab:process_document` - Document UUID: `b6c61f20-39dc-4199-a103-52ee54a32043` (619.29s timeout)

**Root Cause Analysis:**
The tasks are timing out after 600+ seconds. The stack trace shows:
1. Task attempts to commit database transaction
2. Database connection pool ping fails with `CancelledError`
3. This indicates the database connection became stale during the long-running AI classification process
4. The ARQ worker's default timeout is being exceeded

**Impact:**
- Documents uploaded by users are not being processed
- Users see documents stuck in "PROCESSING" state indefinitely
- Retry attempts (try=2) are also failing

**Suggested Fixes:**
1. **Increase ARQ job timeout** in worker configuration (currently appears to be ~600s)
2. **Add connection pool recycling** - Configure SQLAlchemy with `pool_pre_ping=True` and appropriate `pool_recycle` time
3. **Break down the processing into smaller steps** with intermediate commits to avoid long-running transactions
4. **Add progress checkpoints** that commit partial work to prevent complete data loss on timeout
5. **Configure asyncpg connection timeout** settings appropriately

**Code Location:** `/Users/saumyamehta/Gen AI/resume-crafter/backend/src/tasks/document_tasks.py`
- Line 207: `_add_processing_log` during commit
- Line 336: `_extract_experiences` during flush
- Line 134: `_add_processing_log` (second occurrence during shutdown)

---

## Warnings

### 4. [WARNING] bcrypt Version Compatibility Issue

**Timestamp:** 2026-01-12 16:22:06
**Component:** Backend API
**Severity:** WARNING (Trapped - Not Blocking)

**Error Message:**
```
(trapped) error reading bcrypt version
AttributeError: module 'bcrypt' has no attribute '__about__'
```

**Location:** `/Users/saumyamehta/Gen AI/resume-crafter/backend/.venv/lib/python3.12/site-packages/passlib/handlers/bcrypt.py`, line 620

**Analysis:**
The passlib library is trying to read the bcrypt version using an outdated API (`_bcrypt.__about__.__version__`). This error is trapped/caught, so authentication still works, but it indicates a version mismatch between passlib and bcrypt.

**Impact:**
- Authentication still works (login returned 200 OK)
- May cause issues in future updates
- Slight performance overhead from exception handling

**Suggested Fixes:**
1. Update passlib to latest version: `pip install --upgrade passlib`
2. Or pin bcrypt to a compatible version: `pip install bcrypt==4.0.1`
3. Check compatibility matrix between passlib and bcrypt versions

---

### 5. [WARNING] 401 Unauthorized Request

**Timestamp:** 2026-01-12 16:14:05
**Component:** Backend API
**Severity:** WARNING

**Request:**
```
127.0.0.1:55584 - "GET /documents HTTP/1.1" 401 Unauthorized
```

**Analysis:**
An unauthenticated request was made to the `/documents` endpoint. This occurred shortly after server startup, likely before the user session was established or a browser tab without valid auth token.

**Impact:**
- Request was properly rejected (security working correctly)
- May indicate frontend not handling auth state properly on initial load

**Suggested Fixes:**
1. Review frontend auth initialization logic
2. Ensure token refresh happens before API calls
3. This is likely normal behavior, just noting for awareness

---

### 6. [WARNING] High Polling Frequency on Documents Endpoint

**Timestamp:** 2026-01-12 16:19:XX - 16:22:XX (ongoing)
**Component:** Backend API / Frontend
**Severity:** WARNING

**Observation:**
The frontend is polling `/documents` endpoint every 3 seconds:
```
16:19:31 - GET /documents HTTP/1.1 200 OK
16:19:34 - GET /documents HTTP/1.1 200 OK
16:19:37 - GET /documents HTTP/1.1 200 OK
... (continues every 3s)
```

**Impact:**
- Unnecessary database load
- Potential connection pool exhaustion under high user load

**Suggested Fixes:**
1. Implement WebSocket or Server-Sent Events for real-time document status updates
2. Use exponential backoff for polling
3. Increase polling interval to 10-15 seconds when documents are in processing state

---

### 7. [INFO] Frontend 404 on Chrome DevTools Endpoint

**Timestamp:** 2026-01-12 16:XX:XX (recurring)
**Component:** Frontend (Next.js)
**Severity:** INFO (Expected Behavior)

**Observation:**
```
GET /.well-known/appspecific/com.chrome.devtools.json 404
```

**Analysis:**
This is a Chrome browser request for DevTools configuration. The 404 is expected and not a problem.

---

## System Health Metrics

### Backend API (FastAPI)
- **Status:** Healthy (with minor warnings)
- **Start Time:** 2026-01-12 16:14:05
- **Database Connections:** Active (cached queries performing well)
- **Response Times:** Consistent ~200ms for authenticated requests
- **HTTP Status Codes:** Mostly 200 OK, one 401 at startup, 204 for delete operations

### ARQ Worker
- **Status:** DOWN (SIGTERM received)
- **Functions Registered:** 3 (process_document, analyze_job, generate_match)
- **Redis Connection:** Was healthy (redis_version=7.4.7, clients_connected=1)
- **Failed Jobs:** 2 failed, 3 cancelled
- **Last Activity:** 16:22:36 - Shutdown

### Frontend (Next.js)
- **Status:** Healthy
- **Version:** Next.js 14.2.0
- **Compilation:** All routes compiled successfully
- **Response Times:** 12-1238ms (first load slower due to compilation)

---

## Recent Activity

### New Document Upload (Latest)
**Timestamp:** 2026-01-12 16:23:54
**Details:**
- File: `Resume-saumya-mehta-AI_Engineer.pdf`
- Document ID: `a2a31622-3e5b-429b-a27a-67887aeaac1e`
- Size: 284,684 bytes
- Status: PENDING (queued for processing)
- Background Task: `b1ff68f4-4ca8-4003-b597-98b6c09f409f`

**NOTE:** This document is waiting for the ARQ worker to restart to be processed.

### Document Deleted
**Timestamp:** 2026-01-12 16:23:56
**Details:**
- Document ID: `d0d98381-52c6-4c10-8e30-f03d7dd2f9a4`
- Status: Soft deleted (deleted_at set)

### Previous Document Upload
**Timestamp:** 2026-01-12 16:22:28
**Details:**
- File: `Saumya Mehta_Senior AI Scientist_20251227.pdf`
- Document ID: `d0d98381-52c6-4c10-8e30-f03d7dd2f9a4`
- Status: DELETED (user deleted before processing)

### Document Deleted
**Timestamp:** 2026-01-12 16:22:15
**Details:**
- Document ID: `9188504e-ce72-41ff-80fb-c472f9eabe5f`
- Status: Soft deleted (deleted_at set)

---

## Recommendations

### Immediate Actions (Priority: CRITICAL)

1. **Restart ARQ Worker**
   - The worker is currently down after SIGTERM
   - Check if it auto-restarts or needs manual intervention
   - Command: `arq src.tasks.worker.WorkerSettings`

2. **Check Pending Documents**
   - Document `d0d98381-52c6-4c10-8e30-f03d7dd2f9a4` is waiting to be processed
   - Verify status of documents `e4c1a07c-33b0-4c59-b78d-395c73f9a257` and `b6c61f20-39dc-4199-a103-52ee54a32043`

### High Priority Actions

1. **Fix Database Connection Handling in ARQ Worker**
   ```python
   # In database configuration, add:
   engine = create_async_engine(
       DATABASE_URL,
       pool_pre_ping=True,
       pool_recycle=300,  # Recycle connections every 5 minutes
       pool_size=5,
       max_overflow=10
   )
   ```

2. **Increase ARQ Job Timeout**
   ```python
   # In arq worker settings:
   class WorkerSettings:
       job_timeout = 1800  # 30 minutes for document processing
   ```

3. **Fix bcrypt/passlib Compatibility**
   ```bash
   pip install --upgrade passlib bcrypt
   ```

4. **Add Graceful Timeout Handling**
   - Implement checkpointing in `process_document` task
   - Save partial results before potential timeout
   - Mark document as FAILED with meaningful error on timeout

### Medium-Term Improvements

1. **Implement WebSocket for Status Updates** - Reduce polling overhead
2. **Add Structured Logging** - Use JSON logging for better observability
3. **Add Health Check Endpoints** - For ARQ worker and Redis connectivity
4. **Implement Dead Letter Queue** - For failed jobs analysis
5. **Add Process Supervision** - Use systemd or supervisord for automatic restarts

---

## Monitoring Log

| Time | Event | Severity | Component |
|------|-------|----------|-----------|
| 16:25:50 | Backend API restarted (changes in database.py) - possible fix for DB pooling | INFO | Backend API |
| 16:25:17 | Backend API restarted (changes detected in worker.py) | INFO | Backend API |
| 16:24:11 | File changes detected in src/tasks/worker.py | INFO | Backend API |
| 16:23:56 | Document deleted (d0d98381-52c6-4c10-8e30-f03d7dd2f9a4) | INFO | Backend API |
| 16:23:54 | New document uploaded (a2a31622-3e5b-429b-a27a-67887aeaac1e) | INFO | Backend API |
| 16:22:36 | Worker shutdown on SIGTERM - 3 jobs cancelled | CRITICAL | ARQ Worker |
| 16:22:36 | KeyError during job cleanup | CRITICAL | ARQ Worker |
| 16:22:28 | New document uploaded (d0d98381-52c6-4c10-8e30-f03d7dd2f9a4) | INFO | Backend API |
| 16:22:15 | Document deleted (9188504e-ce72-41ff-80fb-c472f9eabe5f) | INFO | Backend API |
| 16:22:06 | bcrypt version error (trapped) | WARNING | Backend API |
| 16:22:06 | User login successful | INFO | Backend API |
| 16:19:17 | TimeoutError - process_document failed (try=1) | CRITICAL | ARQ Worker |
| 16:19:17 | TimeoutError - process_document failed (try=2) | CRITICAL | ARQ Worker |
| 16:19:17 | New process_document tasks queued for retry | INFO | ARQ Worker |
| 16:14:05 | 401 Unauthorized on /documents | WARNING | Backend API |
| 16:14:05 | Backend API started | INFO | Backend API |
| 16:06:35 | Document processing started | INFO | ARQ Worker |
| 16:08:57 | Classification completed (RESUME, 95% confidence) | INFO | ARQ Worker |
| 16:15:44 | Experience extraction in progress | INFO | ARQ Worker |
| 16:04:40 | ARQ Worker started | INFO | ARQ Worker |

---

*This report is automatically updated by the monitoring agent.*
*Last scan: 2026-01-12 16:26:00 UTC*
