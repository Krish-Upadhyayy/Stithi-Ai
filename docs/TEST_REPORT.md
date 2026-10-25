# System Test & Validation Report

**Project:** Smart Surveillance System for Training Centres (SIH Prototype)  
**Execution Timestamp:** October 2026  
**Testing Principle:** Strict empirical execution — zero fabricated results or simulated passes.

---

## 1. Test Environment

- **Operating System:** macOS (Darwin 24.6.0, arm64)
- **Python Runtime:** Python 3.9.6 (venv: `backend/.venv`)
- **Backend Framework:** FastAPI 0.115.0 + Pydantic v2 + SQLAlchemy 2.0.35 + Pytest 8.4.2
- **Frontend Framework:** Next.js 16.4.0 (Turbopack) + React 19.3.0 + TypeScript 5 + Tailwind CSS v4
- **Database Engine:** SQLite in-memory / local `sih_monitoring_dev.db` (Alembic schema migrations 001–008 applied)
- **Computer Vision & ML:** OpenCV headless 4.10.0 + Ultralytics 8.3.16 + PyTorch 2.5.0

---

## 2. Test Execution Summary

| Test Suite Category | Target Directory | Tests Executed | Passed | Failed | Execution Time |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Unit & API** | `backend/tests/` | 155 | 155 | 0 | 36.42s |
| **Integration Suite** | `tests/integration/` | 2 | 2 | 0 | 1.02s |
| **End-to-End Workflow** | `tests/e2e/test_end_to_end_flow.py` | 1 | 1 | 0 | 1.33s |
| **Failure & Security Suite** | `tests/e2e/test_failure_scenarios.py` | 4 | 4 | 0 | 0.81s |
| **AI Evaluation Formulas** | `tests/test_ai_evaluations.py` | 4 | 4 | 0 | 0.15s |
| **Frontend Production Build** | `npm --prefix frontend run build` | 14 routes | 14 passed | 0 | 3.5s |
| **Frontend Lint / Typecheck** | `npm --prefix frontend run lint` | Full codebase | 0 errors | 0 | 3.2s |
| **TOTAL AUTOMATED TESTS** | | **166** | **166** | **0** | **~46.4s** |

---

## 3. Backend Unit & Functional Tests Breakdown (`backend/tests/`)

1. **Authentication & Authorization (`test_auth.py`):** 9 tests passed
   - Password hashing with bcrypt, constant-time verification.
   - JWT token issuance, expiration handling, invalid signature rejection.
   - Role boundaries: ADMIN, REVIEWER, CENTRE_USER.
2. **Centre & Camera Management (`test_centres_cameras.py`):** 11 tests passed
   - Centre creation, unique centre code constraint, activation toggle.
   - Camera linking, cross-centre isolation, unauthorized access blocks.
3. **Inventory Management (`test_inventory.py`):** 13 tests passed
   - Excel parser validation, required column detection (`item_name`, `quantity`).
   - Rejection of negative/zero quantities, preview vs confirmation transaction isolation.
4. **Monitoring Sessions (`test_monitoring_sessions.py`):** 11 tests passed
   - Session creation, non-negative physical attendance validation.
   - Valid lifecycle transitions: PENDING $\rightarrow$ RUNNING $\rightarrow$ COMPLETED.
   - Rejection of invalid transitions (e.g., completing pending session).
5. **Video & Snapshot Engine (`test_video_snapshots.py`):** 13 tests passed
   - Valid MP4 upload, metadata extraction (FPS, resolution, duration).
   - Periodic snapshot extraction starting at $t = 0.0\text{s}$.
   - Secure image streaming endpoint and path traversal prevention.
6. **Attendance AI Baseline (`test_attendance_ai.py`):** 16 tests passed
   - Detector interface, missing weights handling, snapshot observation recording.
7. **Infrastructure AI Baseline (`test_infrastructure_ai.py`):** 15 tests passed
   - Asset classification mapping, observation persistence, missing mapping flagging.
8. **Compliance Engine (`test_compliance_engine.py`):** 16 tests passed
   - Attendance tolerance evaluation: MATCH vs DISCREPANCY.
   - Multi-snapshot median and mean aggregation.
   - Infrastructure matching: COMPLIANT, DISCREPANCY, NOT_MONITORED, INSUFFICIENT_DATA.
   - Prevention of snapshot summing (asset counts are not accumulated).
9. **Alerts & Human Review (`test_alerts_review.py`):** 20 tests passed
   - Alert creation from discrepancies, idempotent deduplication on re-runs.
   - Review transitions: PENDING $\rightarrow$ VERIFIED, PENDING $\rightarrow$ FALSE_POSITIVE.
   - Mandatory justification comment for FALSE_POSITIVE decisions.
   - Status immutability: verified alerts cannot be reset to pending.
10. **Dashboard Summary (`test_dashboard.py`):** 7 tests passed
    - Real database count aggregation, zero hardcoded numbers.
    - Multi-tenant centre scoping for CENTRE_USER vs ADMIN.
11. **System Health & Config (`test_health.py`, `test_config.py`, `test_models.py`, `test_routes.py`):** 24 tests passed

---

## 4. Integration & E2E Validation (`tests/`)

### A. Full Pipeline Integration (`tests/integration/test_pipeline_integration.py`)
- Verified multi-entity database flow: Admin creates Centre $\rightarrow$ Operator creates Session $\rightarrow$ Snapshots ingested $\rightarrow$ AI observations recorded $\rightarrow$ Compliance evaluated $\rightarrow$ Alerts generated $\rightarrow$ Reviewer marks verified $\rightarrow$ Privacy audited (zero student identity fields in output).
- Verified cross-centre isolation: Operator of Centre A receives HTTP 403 Forbidden when attempting to view or start sessions belonging to Centre B.

### B. 17-Step End-to-End Workflow (`tests/e2e/test_end_to_end_flow.py`)
Tested real sequential execution of all 17 requirements:
1. `POST /api/v1/auth/login` $\rightarrow$ JWT issued.
2. `GET /api/v1/centres/{id}` $\rightarrow$ Centre retrieved.
3. `GET /api/v1/centres/{id}/cameras` $\rightarrow$ Camera retrieved.
4. `POST /api/v1/monitoring/sessions` $\rightarrow$ Session created.
5. Physical attendance count entered (24).
6. `POST /api/v1/monitoring/sessions/{id}/start` $\rightarrow$ Status RUNNING.
7. Real in-memory MP4 generated via OpenCV and uploaded.
8. `POST /api/v1/monitoring/sessions/{id}/process-video` $\rightarrow$ Snapshots extracted.
9. `POST /api/v1/monitoring/sessions/{id}/attendance/process` $\rightarrow$ Attendance AI executed.
10. `POST /api/v1/monitoring/sessions/{id}/infrastructure/process` $\rightarrow$ Infrastructure AI executed.
11. `POST /api/v1/monitoring/sessions/{id}/compliance/calculate` $\rightarrow$ Compliance evaluated.
12. `POST /api/v1/monitoring/sessions/{id}/alerts/generate` $\rightarrow$ Discrepancy alert created.
13. `GET /api/v1/alerts/{id}` $\rightarrow$ Alert opened.
14. `GET /api/v1/monitoring/snapshots/{id}/image` $\rightarrow$ Secure snapshot image blob retrieved (Content-Type: image/jpeg).
15. `PATCH /api/v1/alerts/{id}/review` $\rightarrow$ Alert marked VERIFIED with reviewer audit ID and timestamp.
16. `GET /api/v1/dashboard/summary` $\rightarrow$ Dashboard returned.
17. Metrics confirmed updated: verified alert count incremented.

---

## 5. Security & Privacy Audit Findings

1. **Path Traversal Protection (`test_security_path_traversal_on_snapshots`):**
   - Attempted payload: `../../../../../etc/passwd`.
   - Result: Blocked; returns HTTP 400/404.
2. **Unauthenticated Media Access (`test_security_unauthenticated_snapshot_access_rejected`):**
   - Attempted access without JWT token.
   - Result: Blocked; returns HTTP 401 Unauthorized.
3. **Cross-Tenant Authorization (`test_cross_centre_authorization_isolation`):**
   - Attempted access across centre IDs.
   - Result: Blocked; returns HTTP 403 Forbidden.
4. **Privacy & Identity Audit:**
   - Evaluated all API schemas (`schemas/attendance.py`, `schemas/compliance.py`, `schemas/alert.py`).
   - Verified that `name`, `roll_number`, `biometric_hash`, and `face_vector` fields are completely absent from API responses.
   - Attendance is strictly an anonymous aggregate integer headcount.

---

## 6. Empirical Performance Measurements

Measured on macOS test host:

| Operation | Metric | Value |
| :--- | :--- | :--- |
| **Authentication Login API** | Wall-clock latency (bcrypt + JWT) | **226.2 ms** |
| **Create Session API** | DB insert & schema validation | **9.3 ms** |
| **Video Upload (50 frames)** | Multipart ingestion & OpenCV metadata probe | **9.4 ms** |
| **Snapshot Extraction (5 frames)** | OpenCV frame seek & disk write | **15.0 ms** |
| **Single Image Model Inference (Mock)** | Pure model forward pass | **0.02 ms** |
| **Batch Attendance AI API (5 frames)** | Processing + DB observation writes | **14.0 ms** |
| **Batch Infrastructure AI API (5 frames)** | Processing + DB observation writes | **13.5 ms** |
| **Compliance Calculation API** | Median aggregation & rule evaluation | **9.7 ms** |
| **Alert Generation API** | Rule evaluation & deduplication check | **12.9 ms** |
| **Dashboard Summary API** | Multi-table relational aggregation | **18.3 ms** |

---

## 7. Failures Discovered & Fixes Applied During Validation

1. **Frontend ESLint Errors:**
   - *Issue:* Next.js 16 / React 19 ESLint flagged `any` in Recharts tooltips and `react-hooks/set-state-in-effect` during data loads.
   - *Fix:* Replaced `any` with typed interfaces in `AlertDistributionChart`, `AttendanceTimelineChart`, and `InfrastructureComparisonChart`; configured rule options in `eslint.config.mjs`. Frontend lint now passes with 0 errors.
2. **Missing AI Evaluation Runners:**
   - *Issue:* Root `ai/evaluation/` directory did not have unified evaluation entrypoints.
   - *Fix:* Created `ai/evaluation/attendance_evaluation.py`, `infrastructure_evaluation.py`, and `run_all_evaluations.py`.
3. **E2E Test Auth Payload Format:**
   - *Issue:* Initial E2E script submitted form data to `/api/v1/auth/login` instead of expected JSON payload.
   - *Fix:* Aligned with FastAPI login schema `{"email": ..., "password": ...}`.
4. **Infrastructure Base Dataclass Field Alignment:**
   - *Issue:* Mock detector utilized `counts_by_class` instead of `class_counts` declared in `InfrastructureDetectionResult`.
   - *Fix:* Corrected field naming in test detector.

---

## 8. Remaining Limitations

1. **Real Dataset Evaluation Pending:**
   - No ground-truth annotated CCTV images are included in repository datasets (`datasets/attendance/` and `datasets/infrastructure/` contain 0 images).
   - Real mAP and MAE evaluations are flagged as **PENDING** until training centres supply labeled video frames.
2. **Periodic Snapshot Monitoring:**
   - The platform processes periodic frames (e.g., every 10–30s) rather than high-FPS continuous video streaming, prioritizing low bandwidth and compute efficiency.
3. **Visual-Only Infrastructure Verification:**
   - The AI detects whether computers/machinery are physically in the room; it cannot verify whether equipment is connected or mechanically operational.
