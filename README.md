# AI-Powered AICTE Document Verification & Decision Support System

> **Smart India Hackathon (SIH) — Problem Statement 1**  
> **Core Principle:** *The AI recommends; the authorised official decides.*  
> Under council guidelines, automated models never declare a document definitively fraudulent, nor do they automatically issue binding approval or rejection. Every flag, forensic anomaly, and regulatory deficit is presented as an explainable, traceable finding subject to human scrutiny.

---

## 1. System Overview

The platform assists AICTE officials in reviewing technical institution approval applications by:
1. Validating document completeness, integrity, and validity periods.
2. Ingesting text via native digital PDF layers with graceful OCR fallback for scanned certificates.
3. Extracting key institutional parameters with visual bounding-box highlights.
4. Performing cross-document and declared-vs-extracted consistency checks with fuzzy matching and area tolerance.
5. Detecting exact duplicates (SHA-256), perceptual near-duplicates (pHash), and image forensics (Error Level Analysis heatmaps & ORB copy-move clusters) with template-awareness for standard affidavits.
6. Performing simulated external authority verification against state land, municipal town planning, and fire directorate registries with mandatory `SIMULATED` labeling.
7. Checking regulatory compliance against versioned Approval Process Handbook (APH) rules.
8. Generating an explainable Review-Priority Score (0-100), printable ReportLab PDF Verification Dossier, and an automated 15-day statutory deficiency notice.
9. Enforcing an official decision bar with mandatory substantive remarks and an immutable append-only audit trail.

---

## 2. Technology Stack

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0 ORM, Pydantic v2.
- **Database:** SQLite (local development with `StaticPool` for concurrency) designed with a clean migration path to PostgreSQL.
- **Frontend:** Next.js 14.2.15 (App Router), TypeScript, Tailwind CSS, Lucide icons, Recharts.
- **Document Processing:** PyMuPDF (fitz) with PyTesseract graceful fallback.
- **Forensics & Computer Vision:** OpenCV (`cv2`), Pillow (`PIL`), ImageHash, RapidFuzz.
- **Report Generation:** ReportLab 5.1.
- **Authentication:** JWT (JSON Web Tokens) with PBKDF2-SHA256 password hashing.
- **Testing:** Pytest (49 passed unit and integration tests).

---

## 3. Quick Start (Windows PowerShell)

### Prerequisites
- Python 3.13 (`.venv` virtual environment)
- Node.js v24.11+ and npm 11+

### Step 1: Seed the Database
```powershell
cd c:\Dhruvi\SIH_PS1
$env:PYTHONPATH="."
.\.venv\Scripts\python backend\scripts\seed_db.py
```

### Step 2: Generate Synthetic Datasets & Run Evaluation
```powershell
cd c:\Dhruvi\SIH_PS1
$env:PYTHONPATH="."
.\.venv\Scripts\python backend\scripts\generate_sample_data.py
.\.venv\Scripts\python backend\scripts\evaluate.py
```

### Step 3: Run Backend Test Suite (49 Tests)
```powershell
cd c:\Dhruvi\SIH_PS1
.\.venv\Scripts\python -m pytest -v
```

### Step 4: Start the Backend API Server
```powershell
cd c:\Dhruvi\SIH_PS1
$env:PYTHONPATH="."
.\.venv\Scripts\uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at: `http://127.0.0.1:8000/api/v1/docs`

### Step 5: Start the Frontend Next.js Application
```powershell
cd c:\Dhruvi\SIH_PS1\frontend
npm run dev
```
Access the application at: `http://localhost:3000`

---

## 4. Test Credentials

| Role | Email | Password | Primary Workflow |
|---|---|---|---|
| **Institution 1** | `inst1@aicte.gov.in` | `Demo@Password123` | Apex Institute of Technology (Uploads, Drafts) |
| **Institution 2** | `inst2@aicte.gov.in` | `Demo@Password123` | Bharati College of Engineering (Ownership isolated) |
| **Official** | `official@aicte.gov.in` | `Demo@Password123` | Scrutiny Officer (Review, Override, Decisions) |
| **Admin** | `admin@aicte.gov.in` | `Demo@Password123` | System Administrator (Rule Versioning) |
| **Auditor** | `auditor@aicte.gov.in` | `Demo@Password123` | Oversight Officer (Append-Only Audit Trail) |

---

## 5. Documentation Directory

- [PLAN.md](file:///c:/Dhruvi/SIH_PS1/docs/PLAN.md): Detailed development roadmap across all phases.
- [ARCHITECTURE.md](file:///c:/Dhruvi/SIH_PS1/docs/ARCHITECTURE.md): Complete system architecture, 9-stage pipeline, and RBAC matrix.
- [API.md](file:///c:/Dhruvi/SIH_PS1/docs/API.md): Comprehensive REST API reference with request/response schemas.
- [RULES_TO_VERIFY.md](file:///c:/Dhruvi/SIH_PS1/docs/RULES_TO_VERIFY.md): Regulatory checklist of handbook thresholds and citations.
- [DEMO_SCRIPT.md](file:///c:/Dhruvi/SIH_PS1/docs/DEMO_SCRIPT.md): Step-by-step hackathon jury presentation script.
- [LIMITATIONS.md](file:///c:/Dhruvi/SIH_PS1/docs/LIMITATIONS.md): Transparent engineering boundaries and OCR/forensic caveats.
- [REAL_INTEGRATION.md](file:///c:/Dhruvi/SIH_PS1/docs/REAL_INTEGRATION.md): Production gateway specifications for DigiLocker and state registries.
- [EVALUATION.md](file:///c:/Dhruvi/SIH_PS1/docs/EVALUATION.md): Measured performance benchmarks on synthetic test scenarios.
- [STATUS.md](file:///c:/Dhruvi/SIH_PS1/docs/STATUS.md): Current implementation status and test logs.
