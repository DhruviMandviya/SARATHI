# AI-Powered AICTE Document Verification System - Master Development Plan

## 1. Project Overview & Objectives
An enterprise-grade, human-in-the-loop decision-support platform for the All India Council for Technical Education (AICTE) to automate the verification, consistency checking, fraud/tampering analysis, authenticity verification, and compliance assessment of institution approval applications.

**Core Philosophy:** The AI recommends. The official decides. The system must NEVER automatically approve or reject an application.

---

## 2. Environment Status & Prerequisites

- **OS:** Windows (AMD64)
- **Node.js:** v24.11.1
- **npm:** 11.7.0
- **Python:** Python 3.13.2 (selected runtime via `py -3.13` for optimal C-extension binary compatibility)
- **Git:** 2.55.0.windows.5
- **Tesseract OCR Status:** **NOT INSTALLED** on host.

### How to Install Tesseract OCR on Windows:
1. Open PowerShell / Command Prompt as Administrator and run:
   ```powershell
   winget install --id UB-Mannheim.TesseractOCR
   ```
   *Alternatively*, download the installer directly from:
   https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location: `C:\Program Files\Tesseract-OCR`
3. Add `C:\Program Files\Tesseract-OCR` to the System `PATH` environment variable.
4. Verify installation in a new terminal:
   ```powershell
   tesseract --version
   ```
5. Restart backend server if running.

> **Graceful Degradation Note:** The document processing pipeline is designed to check for Tesseract binary availability at startup and runtime. If Tesseract is missing, digital PDFs with native text layers extract cleanly via PyMuPDF. For scanned images where Tesseract is required, the OCR engine sets status to `OCR unavailable` with clear diagnostic notes, avoiding crashes.

---

## 3. Architecture & Key Decisions

1. **Backend Framework:** FastAPI with Python 3.13, Pydantic v2 schemas, SQLAlchemy 2.0 ORM with SQLite database (configured to cleanly migrate to PostgreSQL).
2. **Frontend Framework:** Next.js (App Router) + TypeScript, Tailwind CSS, Lucide icons, Recharts, with a government-grade dark navy sidebar aesthetic.
3. **Storage Strategy:** Local storage under `backend/storage/` with UUID-named non-mutated originals, and derived folder `backend/storage/derived/` for page renders and ELA heatmaps.
4. **Asynchronous Processing:** FastAPI `BackgroundTasks` with in-process status updates and frontend polling (every 2s).
5. **No Hallucination / Deterministic AI:**
   - Classification: keyword & regex matching over text and filename.
   - Extraction: regex and rule-based parsing with normalization and bounding box extraction.
   - Forensic Analysis: ELA re-compression difference, ORB keypoint copy-move matching, PDF metadata/font anomaly checks.
   - Consistency Engine: RapidFuzz fuzzy ratio with strict thresholding across documents and declared details.
   - Verification Adapters: Pluggable abstract class with 4 deterministic simulated adapters explicitly badged `SIMULATED` (`is_simulated: true`).
   - Compliance Engine: Database-backed versioned rules with source and clause citations. Placeholder rules tagged `verified_against_handbook: false`.
   - Risk Scoring: Weighted additive model based on open flags, capped at 100, presented as review priority.
   - Reporting: ReportLab deterministic PDF report generation; templated editable deficiency letter.
6. **Auditability & Security:**
   - Role-based access control (Institution, Official, Admin, Auditor) enforced on backend endpoints.
   - Institutions can only view their own applications and pre-check findings.
   - Decisions require Official role and mandatory remarks.
   - Audit log is strictly append-only (no update/delete routes).

---

## 4. Planned Folder Structure

```
aicte-verifier/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── database.py
│   │   │   └── permissions.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── institution.py
│   │   │   ├── application.py
│   │   │   ├── document.py
│   │   │   ├── finding.py
│   │   │   ├── verification.py
│   │   │   ├── compliance.py
│   │   │   ├── decision.py
│   │   │   └── audit.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── application.py
│   │   │   ├── document.py
│   │   │   ├── finding.py
│   │   │   ├── verification.py
│   │   │   ├── compliance.py
│   │   │   ├── decision.py
│   │   │   └── dashboard.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── applications.py
│   │   │   ├── documents.py
│   │   │   ├── findings.py
│   │   │   ├── verification.py
│   │   │   ├── compliance.py
│   │   │   ├── reports.py
│   │   │   ├── decisions.py
│   │   │   ├── dashboard.py
│   │   │   ├── admin.py
│   │   │   └── audit.py
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   └── orchestrator.py
│   │   ├── engines/
│   │   │   ├── __init__.py
│   │   │   ├── ocr.py
│   │   │   ├── classifier.py
│   │   │   ├── extractor.py
│   │   │   ├── validator.py
│   │   │   ├── consistency.py
│   │   │   ├── forensics_image.py
│   │   │   ├── forensics_pdf.py
│   │   │   ├── duplicates.py
│   │   │   ├── compliance.py
│   │   │   ├── risk.py
│   │   │   └── verifiers/
│   │   │       ├── __init__.py
│   │   │       ├── base.py
│   │   │       ├── mock_building_plan.py
│   │   │       ├── mock_society_reg.py
│   │   │       ├── mock_fire_noc.py
│   │   │       └── mock_env_clearance.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── storage.py
│   │       ├── audit.py
│   │       ├── pdf_report.py
│   │       ├── deficiency_letter.py
│   │       └── file_validation.py
│   ├── rules/
│   │   ├── compliance_rules.json
│   │   ├── checklists.json
│   │   └── classifier_keywords.json
│   ├── scripts/
│   │   ├── seed_db.py
│   │   ├── generate_sample_data.py
│   │   └── evaluate.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_file_validation.py
│   │   ├── test_auth_permissions.py
│   │   ├── test_classifier.py
│   │   ├── test_extractor.py
│   │   ├── test_validator.py
│   │   ├── test_consistency.py
│   │   ├── test_duplicates.py
│   │   ├── test_forensics.py
│   │   ├── test_verifiers.py
│   │   ├── test_compliance.py
│   │   ├── test_risk.py
│   │   ├── test_audit_append_only.py
│   │   ├── test_decisions.py
│   │   ├── test_pdf_report.py
│   │   └── test_pipeline_integration.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── ui/
│   │   │   └── viewer/
│   │   ├── features/
│   │   │   ├── upload/
│   │   │   ├── processing/
│   │   │   ├── extraction/
│   │   │   ├── validation/
│   │   │   ├── fraud/
│   │   │   ├── verification/
│   │   │   ├── compliance/
│   │   │   ├── report/
│   │   │   └── dashboard/
│   │   └── lib/
│   │       ├── api.ts
│   │       ├── auth.tsx
│   │       └── types.ts
│   ├── package.json
│   └── .env.example
├── sample_data/
│   ├── ground_truth.json
│   └── scenario_[a-i]/
├── docs/
│   ├── PLAN.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── RULES_TO_VERIFY.md
│   ├── DEMO_SCRIPT.md
│   ├── LIMITATIONS.md
│   ├── REAL_INTEGRATION.md
│   ├── EVALUATION.md
│   └── STATUS.md
├── README.md
└── .gitignore
```

---

## 5. Implementation Phases & Milestones

- **Phase 1: Setup, DB, Auth & Base Shell**
  - Git repository setup, `.gitignore`, `.env.example`.
  - Python virtual environment & backend dependencies.
  - SQLAlchemy models, SQLite database initialization, seed script (users for Institution 1 & 2, Official, Admin, Auditor; checklists; placeholder rules).
  - JWT auth endpoints (`/auth/login`, `/auth/me`), RBAC middleware.
  - Next.js frontend setup with Tailwind CSS, dark navy sidebar, authentication context, login page, and protected routing.
  - Verify: Login works, unauthorized access returns 401/403, Pytest passing.

- **Phase 2: Applications, Uploads, Checklist & Status UI**
  - Application CRUD (role-filtered), declared-details form.
  - Secure multipart file upload with magic byte validation (PDF, JPG, PNG, 10MB limit, page limits).
  - Checklist API and checklist UI (tick, amber, red).
  - Pre-submission check endpoint shell.
  - Status endpoint with polling support.
  - Verify: Institutions can create applications and upload documents; cannot view other institutions' files.

- **Phase 3: OCR, Classification & Extraction Pipeline**
  - PyMuPDF text layer extraction + Tesseract OCR fallback with quality checks (blur, resolution).
  - Rule & keyword-based classifier with confidence and keyword trace.
  - Regex and layout extractor with unit normalization and bounding box coordinates.
  - Pipeline orchestrator updating document stages.
  - Extracted Information UI (Stage 3) with document viewer, bbox overlay, and official field correction with audit logging.
  - Verify: Sample documents classify accurately; low-confidence triggers review.

- **Phase 4: Validation & Consistency Engine**
  - Checklist item validator (Valid / Incomplete / Expired / Mismatch / Missing).
  - Consistency engine comparing institutions, land areas, survey numbers, and declared details.
  - Flag creation with full evidence, severity, and rule references.
  - Validation UI (Stage 4) with status chips and evidence drill-down.
  - Verify: Scenarios B (missing), C (expired), and F (mismatch) produce exact expected flags.

- **Phase 5: Fraud & Tampering Signals**
  - Duplicate detection: SHA-256 exact match, pHash visual similarity, text similarity.
  - Template awareness to prevent false alarms on standard affidavits.
  - Image forensics: Error Level Analysis (ELA) heatmap generation, copy-move ORB keypoints.
  - PDF forensics: Metadata inspection, font mix, incremental update checks.
  - Fraud Detection UI (Stage 5) with prominent caveat banner, ELA toggle, side-by-side duplicate viewer.
  - Verify: Scenarios D (tampered date) and E (cross-institution duplicate) flagged; Scenario H (shared template) not Critical.

- **Phase 6: Authenticity Verification & Compliance Checking**
  - Abstract Verifier interface + 4 deterministic mock adapters with `SIMULATED` badges.
  - Pending status handling for unreachable authorities.
  - Compliance engine evaluating versioned DB rules across check types (`min_value`, `ratio_max`, etc.).
  - Admin rule editing (new versioning).
  - Authenticity UI (Stage 6) & Compliance UI (Stage 7) with clause references and "Unverified placeholder" badges.
  - Write `docs/RULES_TO_VERIFY.md` and `docs/REAL_INTEGRATION.md`.
  - Verify: All 4 verification statuses and 4 compliance outcomes demonstrated.

- **Phase 7: Explainable Risk Scoring, PDF Report & Deficiency Letter**
  - Additive explainable risk scoring capped at 100 with top contributing flags.
  - ReportLab PDF generator with complete summary tables, caveat notices, and simulated badges.
  - Deterministic deficiency letter generator from open flags with official editing capabilities.
  - Final Report UI (Stage 8).
  - Verify: PDF generated cleanly; risk score updates dynamically on flag acknowledgment/dismissal.

- **Phase 8: Official Workflow, Audit Log & Dashboard**
  - Official decision bar (Approve / Reject / Request More Info) with mandatory remarks.
  - Strict append-only audit log with before/after state capture.
  - Resubmission logic superseding old documents and re-running dependent checks.
  - Dashboard UI (Stage 9) with real DB statistics, Recharts status donut, high-risk queue, and search filters.
  - Verify: Full audit trail generated; dashboard metrics match DB queries.

- **Phase 9: Sample Data Suite, Integration Testing & Evaluation**
  - Synthetic sample generator (`generate_sample_data.py`) for Scenarios A through I.
  - Ground truth benchmark (`sample_data/ground_truth.json`).
  - Automated evaluation script (`evaluate.py`) recording measured precision/recall to `docs/EVALUATION.md`.
  - Comprehensive documentation (`README.md`, `DEMO_SCRIPT.md`, `LIMITATIONS.md`, `STATUS.md`).
  - End-to-end verification and hardening.

---

## 6. Key Risks & Mitigation

| Risk | Impact | Mitigation Strategy |
|------|--------|---------------------|
| Missing Tesseract binary on target OS | OCR failure on scanned images | Detect binary availability; gracefully degrade with informative `OCR unavailable` flag; extract digital text layers via PyMuPDF. |
| Inaccurate forensic conclusions | Accusing legitimate applicants | Explicit caveat banners everywhere: "Flagged for Review", never "Fraud". ELA & metadata labeled as weak heuristic signals. |
| False positive duplicate on standard templates | Legitimate affidavits flagged as critical fraud | Template-aware duplicate logic compares extracted field values rather than layout-only pHash. |
| Compliance rule misalignment with AICTE handbook | Incorrect regulatory decisions | Clear `verified_against_handbook: false` tag, distinct UI badge, and explicit checklist in `docs/RULES_TO_VERIFY.md`. |
| Cross-institution data leakage | Confidentiality breach | Strict RBAC enforced at SQLAlchemy query level on every backend endpoint; covered by negative unit tests. |
