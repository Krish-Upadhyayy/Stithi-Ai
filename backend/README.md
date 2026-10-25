# SIH Training Centre AI Monitoring — Backend Foundation & Database (Module 2)

## Overview
This service provides the core Python FastAPI backend, SQLAlchemy ORM persistence layer, Pydantic data schemas, and Alembic database migration management for the SIH AI-Based Training Centre Monitoring System.

---

## 1. Prerequisites
- **Python:** 3.9+ (tested on Python 3.9 & 3.11)
- **MySQL:** 8.0+

---

## 2. Virtual Environment & Dependency Installation

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```

2. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

---

## 3. MySQL Database Setup

1. Log into your MySQL console:
   ```bash
   mysql -u root -p
   ```

2. Create the dedicated database manually:
   ```sql
   CREATE DATABASE sih_monitoring CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. Configure your local credentials:
   ```bash
   cp .env.example .env
   ```
   Update `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL="mysql+pymysql://USERNAME:PASSWORD@localhost:3306/sih_monitoring"
   ```

---

## 4. Alembic Database Migrations

Apply the database schema to MySQL using Alembic:

- **Run migrations to head:**
  ```bash
  alembic upgrade head
  ```

- **Roll back the initial migration:**
  ```bash
  alembic downgrade -1
  ```

- **Generate offline MySQL SQL script (dry run):**
  ```bash
  alembic upgrade head --sql
  ```

---

## 5. Running the FastAPI Application

Start the development server with hot reload:
```bash
uvicorn backend.app.main:app --reload --port 8000
```

- **Interactive API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc UI:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Root Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
- **API v1 Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 6. Running Tests

Unit tests use an isolated in-memory SQLite database and do not require external MySQL services:

```bash
PYTHONPATH=. pytest backend/tests/ -v
```

---

## 7. Database Entities Staged

| Entity | Table Name | Purpose | Key Attributes |
|---|---|---|---|
| **User** | `users` | Admin & inspector users | `name`, `email` (unique), `password_hash` (bcrypt), `role` |
| **Centre** | `centres` | Training centre registry | `centre_code` (unique), `name`, `location`, `status` |
| **Camera** | `cameras` | Video/camera feed references | `centre_id`, `name`, `source_type`, `source_url`, `is_active` |
| **MonitoringSession** | `monitoring_sessions` | Inspection session records | `centre_id`, `physical_attendance` (anonymous integer), `status` |
| **Snapshot** | `snapshots` | Periodic frame extracts | `monitoring_session_id`, `file_path`, `captured_at`, `sequence_number` |
| **AttendanceObservation** | `attendance_observations` | YOLO26 presence count results | `snapshot_id`, `observed_count` (integer count only, no identities) |
| **InventoryItem** | `inventory_items` | Sanctioned Excel baseline | `centre_id`, `item_name`, `category`, `expected_quantity` |
| **InfrastructureObservation**| `infrastructure_observations`| Detected asset counts | `snapshot_id`, `asset_type`, `detected_quantity`, `confidence` |
| **Alert** | `alerts` | Discrepancy notices | `centre_id`, `alert_type`, `expected_value`, `observed_value`, `status` |

---

## 8. Strict Module Constraints
- **Zero Fabricated Metrics:** No fake counts or accuracy scores are emitted.
- **Privacy First:** Physical attendance and observations store anonymous headcount values only. No student identities or biometric vectors are collected or stored.
- **No AI Inference Yet:** Model weights and inference execution are strictly deferred to the dedicated AI module.
