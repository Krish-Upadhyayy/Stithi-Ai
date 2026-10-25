# AI Training Centre Monitoring System (Stithi AI)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Next.js-16.4-black?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch" />
  <img src="https://img.shields.io/badge/Ultralytics-YOLO-00FFFF?style=for-the-badge&logo=yolo&logoColor=black" alt="YOLO" />
  <img src="https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

> **Smart India Hackathon (SIH)**  
> *"From passive CCTV feeds to actionable compliance intelligence — without identifying students."*

---

> [!IMPORTANT]
> **Privacy-by-Design & Transparency Guarantee (DPDP Act 2023 Conformance):**  
> - **Zero Facial Embeddings / Biometrics:** Trainee attendance is estimated using anonymous aggregate visual presence detection via fine-tuned YOLO. The system **never** captures facial vectors, identity embeddings, or individual biometric profiles.  
> - **Visual Infrastructure Verification:** Infrastructure observations evaluate apparent visual presence against sanctioned baselines; they do not attest to mechanical or electrical functionality.  
> - **Zero Fabricated Metrics:** Every reported evaluation metric and audit output stems from empirical test runs and deterministic mathematical comparison.

---

## 📌 System Vision & Objective

Government-funded vocational skilling initiatives (e.g., PMKVY, DGT, NSDC, and state skill missions) disburse public funds based on verified physical operations. Traditional manual audits are infrequent, geographically constrained, and cost-prohibitive.

The **AI Training Centre Monitoring System** automates compliance auditing by processing mandated CCTV feeds:

```
CCTV / Recorded Video Feed
          │
          ▼
Periodic Snapshot Extraction (Low-Bandwidth Sampling via OpenCV)
          │
    ┌─────┴─────────────────────────────────┐
    ▼                                       ▼
YOLO Attendance AI                 YOLO Infrastructure AI
(Anonymous Trainee Presence)        (Sanctioned Asset Detection)
    │                                       │
    └──────────────────┬────────────────────┘
                       ▼
          Deterministic Compliance Engine
         (Strict Mathematical Tolerances)
                       │
                       ▼
            Evidence-Backed Discrepancy
                       │
                       ▼
          Human Review & Verification Workflow
          (PENDING → VERIFIED / FALSE POSITIVE)
                       │
                       ▼
           National Governance Dashboard
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | **Next.js 16 (App Router)**, **React 19**, **TypeScript 5**, **Tailwind CSS** | Responsive auditor portal, dark-mode governance UI, typed API contracts |
| **Data Visualizations** | **Recharts**, **Lucide React** | Real-time compliance gauges, attendance timelines, discrepancy distributions |
| **Backend API** | **Python 3.9+**, **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0** | High-performance asynchronous REST API, decoupled AI orchestration |
| **Relational Database** | **MySQL 8.0** / **SQLite3** | Relational integrity with full foreign keys and Alembic migration control |
| **Computer Vision / AI** | **Ultralytics YOLO**, **PyTorch**, **OpenCV** | Dual AI pipelines for trainee presence counting and asset detection |
| **Baseline Inventory** | **OpenPyXL**, **Pandas** | Parsing and validating sanctioned training asset baselines (`.xlsx`) |
| **Testing & Quality** | **Pytest**, **HTTPX TestClient**, **ESLint** | 166 automated backend, integration, and E2E test suites |

---

## 📁 Repository Structure

```
.
├── backend/
│   ├── alembic/                 # Database migrations (schema evolution)
│   ├── app/
│   │   ├── api/routes/          # REST endpoints (auth, centres, sessions, AI, alerts)
│   │   ├── core/                # Config, database connection, JWT security
│   │   ├── ml/                  # YOLO models, trainers, evaluators, metrics
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── pipelines/           # Modular Attendance & Infrastructure detection pipelines
│   │   ├── schemas/             # Pydantic validation schemas
│   │   ├── services/            # Business logic (video, compliance, alerts, inventory)
│   │   └── video/               # OpenCV frame extractor & video validation
│   ├── tests/                   # Backend unit and integration test suite
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile               # Backend container configuration
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router (dashboard, monitoring, alerts, centres)
│   │   ├── components/          # Reusable UI cards, tables, charts, modals
│   │   └── lib/                 # API client, TypeScript interfaces, auth context
│   ├── package.json             # Frontend dependencies & scripts
│   └── Dockerfile               # Frontend container configuration
├── datasets/                    # Standardized YOLO dataset structures & annotations
├── docs/                        # Complete technical & architectural documentation
│   ├── ARCHITECTURE.md          # Subsystem design, security, schemas, and API contracts
│   ├── DATA_FLOW.md             # 14-stage data lifecycle diagrams
│   ├── SIH_DEMO_SCRIPT.md       # Presentation script and jury walkthrough
│   └── TEST_REPORT.md           # 166-test verification report
├── scripts/
│   ├── seed_demo.py             # Controlled demo data seeder script
│   └── run_all_tests.sh         # Unified full-stack automated test runner
├── docker-compose.yml           # Multi-service production orchestration
└── README.md                    # System documentation
```

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- **Python 3.9+**
- **Node.js 18+** & **npm**
- **MySQL 8.0+** (or SQLite fallback configured via `.env`)

---

### Step 1: Clone Repository
```bash
git clone <repository_url>
cd "SIH 2026"
```

---

### Step 2: Backend Setup

```bash
cd backend

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Run database migrations (or SQLite tables initialize automatically)
alembic upgrade head

# Start FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc UI:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check Endpoint:** [http://localhost:8000/health](http://localhost:8000/health)

---

### Step 3: Frontend Setup

Open a new terminal window:

```bash
cd frontend

# Install Node dependencies
npm install

# Configure frontend environment
cp .env.example .env.local

# Launch Next.js development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your web browser.

---

## 🔐 Controlled Demo Mode & Credentials

To ensure zero fake data leaks into audits, a standalone controlled seeder script is provided:

```bash
# Seed controlled demo entities (Demo Centre, cameras, inventory, sample session)
python scripts/seed_demo.py --execute

# Clean / Remove all [DEMO] entities
python scripts/seed_demo.py --clean
```

**Default Demo Credentials:**
- **Login Portal:** [http://localhost:3000/login](http://localhost:3000/login)
- **Email:** `demo_admin@sih.gov.in`
- **Password:** `DemoAdmin123!`

---

## 🧪 Automated Testing & Verification

Run the unified test runner to execute unit tests, integration tests, E2E flows, and frontend production builds:

```bash
./scripts/run_all_tests.sh
```

**Verification Results:**
- ✅ **Backend Unit Tests:** 155/155 passed
- ✅ **AI & Integration Tests:** 11/11 passed
- ✅ **Total Automated Tests:** 166/166 passed (0 failures)
- ✅ **Frontend Static Analysis:** 0 lint errors
- ✅ **Frontend Build:** All static and dynamic routes compiled cleanly

---

## 🐳 Deployment via Docker Compose

Run the entire system in containers with a single command:

```bash
# Start MySQL, FastAPI Backend, and Next.js Frontend
docker compose up -d --build

# Inspect running containers
docker compose ps
```

Services exposed:
- **Web Portal:** `http://localhost:3000`
- **API Server:** `http://localhost:8000`
- **Database:** `localhost:3306`

---

## ⚖️ Standardized Terminology (Audit Compliance)

In accordance with vocational audit guidelines, all status flags adhere strictly to non-accusatory terminology:

| Domain | Standard Term | Disallowed / Inaccurate Variants |
|---|---|---|
| **Compliance Status** | `MATCH`, `DISCREPANCY`, `INSUFFICIENT DATA` | *"Fraud"*, *"Fake Attendance"*, *"Cheat"* |
| **Review Status** | `PENDING`, `VERIFIED`, `FALSE POSITIVE` | *"Definite Scam"*, *"Guilty"* |
| **Session Status** | `PENDING`, `RUNNING`, `COMPLETED`, `FAILED` | Inconsistent pipeline states |
| **Attendance Metric** | `Physical Attendance`, `AI Estimated Attendance`, `Attendance Discrepancy` | *"Fake Students"*, *"Ghost Trainees"* |
| **Infrastructure** | `Expected Quantity`, `AI Observed Quantity`, `Apparent Visual Availability` | *"Missing Equipment"*, *"Broken Gear"* |

---

## 📜 License & Governance

Developed for the **Smart India Hackathon (SIH)**.  
Built under strict adherence to ethical AI governance, aggregate presence modeling, and Digital Personal Data Protection (DPDP) Act 2023 principles.
