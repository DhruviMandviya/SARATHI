# AICTE Document Verification System — Project Status

**Master Prompt Completed:** Notice Intelligence, Fraud & Forensics, Document Verification, Authenticity Checks, Official Queue & Decision Consistency  
**Date:** October 2026

---

## 1. Executive Summary & Verification State

- **Backend Environment:** Python 3.13 in `.venv` with FastAPI, SQLAlchemy 2.0, Pydantic v2, PyMuPDF, OpenCV, Pillow, RapidFuzz, ImageHash, ReportLab.
- **Frontend Environment:** Next.js 14.2.15 (App Router), TypeScript, Tailwind CSS, Lucide icons, Recharts.
- **Test Suite Status:** **91 passed, 0 failed, 3 warnings** across all 15 test modules (`python -m pytest backend/tests/ -v`) including `test_notice_intelligence_and_verification.py`.
- **Frontend Build Status:** Next.js production build compiled cleanly across **16 routes** (`npm run build`, exit code 0).
- **Core Principle Enforced:** *"The AI recommends; the authorised official decides."* Automated signals (OCR, visual pHash, ELA anomalies, mock external authority adapters) serve as advisory intelligence. No application is auto-approved or auto-rejected based on an AI score. Mock registry verifications remain transparently tagged `SIMULATED`.
- **Role-Based Routing & Isolation:** Enforced backend permission verification and frontend routing. Applicants/institutions are routed directly to the Applicant Dashboard; official council members are routed to the Official Dashboard. Institutional tenant isolation strictly enforced on applications, notices, responses, and released documents.

---

## 2. Phase 1 Accomplishments

### A. Notifications System (Database-Backed & Live)
1. **Schema & Model (`notifications`):**
   - Created `Notification` model with user scoping, target role, institution ID, category, title, message, link, read/unread state, application ID, and timestamp.
2. **Backend API Endpoints:**
   - `GET /api/v1/notifications`: Paginated list of notifications for the authenticated user/institution/role.
   - `GET /api/v1/notifications/unread-count`: Returns active unread count.
   - `POST /api/v1/notifications/{id}/read`: Marks notification as read.
   - `POST /api/v1/notifications/mark-all-read`: Marks all pending notifications as read.
3. **Automated Event Triggers:**
   - When an official records a decision -> Institution is notified with decision details.
   - When an official issues an Information Request Notice -> Institution is notified with response deadline.
   - When an applicant submits an application -> Council officials are notified.
   - When an applicant submits an Information Request response -> Council officials are notified.
   - When an official resolves an Information Request -> Institution is notified.
4. **Interactive UI (`TopBar.tsx`):**
   - Bell icon with unread badge counter (only displayed when `unread_count > 0`).
   - Popover dropdown showing notification categories, timestamps, read indicators, and "Mark all as read" button.
   - Background polling every 15s to pick up live notifications without requiring page reloads.

### B. Login and Role-Based Navigation
1. **Login Redirects:**
   - Logging in as an applicant (`user.role === "institution"`) redirects to `/dashboard`, rendering `ApplicantDashboard`.
   - Logging in as an official (`official`, `admin`, `auditor`) opens the Official Scrutiny Dashboard at `/dashboard`.
2. **Backend Security & RBAC Enforcement:**
   - Officials attempting to upload or replace applicant documents through the Applications Queue receive `403 Forbidden`.
   - Officials attempting to delete applicant documents receive `403 Forbidden`.
   - Officials attempting to alter applicant declared parameters receive `403 Forbidden`.
   - Applicants attempting to access council-only ELA heatmaps (`/documents/{id}/ela`) receive `403 Forbidden`.
   - Applicants retrieving applications (`/applications/{id}`) and reports (`/applications/{id}/report`) receive redacted response data (internal risk scores, bands, and contributing factor weights set to 0/empty).
3. **Client-Side AuthGuard:**
   - Prohibits institutions from accessing `/verification`, `/fraud`, `/compliance`, `/audit`, or `/admin`, redirecting them to `/dashboard`.

### C. Applicant Portal — New Application (Mandatory Field Enforcement)
1. **Validation Engine:**
   - Every field in the Institution Declared Details section is mandatory: Legal Institution Name, Promoting Trust, Campus Address, State/UT, Land Area (Acres), Built-Up Area (sqm), Approved Student Intake, Faculty Count, Core Laboratories Count, EWS Quota %, Joint Fixed Deposit Reserve (Lakhs), Affidavit Stamp Paper Value (INR).
2. **Field-Level Error Messages:**
   - Red highlight and contextual validation error messages appear under each offending input.
   - Form state and user inputs are strictly preserved upon validation failure.
3. **Backend Pre-Check & Submission:**
   - Added `POST /api/v1/applications/validate-declared-details` endpoint. Step transition is prevented until both client and backend pre-checks pass.
   - Applications are never marked as submitted until confirmed by the backend `POST /applications/{id}/submit` endpoint.

### D. Applicant Portal — My Applications & Document Management
1. **Per-Slot Upload & Replacement:**
   - Removed the separate bottom-level Upload/Replace Document box.
   - In the document checklist table, added independent inline `Upload` (if missing) and `Replace` (if uploaded) actions beside each document category.
   - Displays actual uploaded filename, upload date, file size, page count, and real-time validation/processing status chips.
   - Shows upload spinners, slot-level success alerts, and error alerts.
   - Replaced documents are marked as superseded and logged in the append-only audit trail.
2. **Institution Declared Parameters — Working Edit Details Flow:**
   - Populates form with existing declared values and re-syncs when application updates.
   - Allows applicants to edit permitted fields when application status allows (`draft` or `info_requested`).
   - Validates positive numerical bounds and required text fields.
   - Persists updates to the database via `PUT /api/v1/applications/{id}/declared-details` and writes an audit log entry.
   - Displays clear success alert and refreshes displayed details.

### E. Applicant Reports & Decisions
1. **Redaction of Internal Scrutiny Telemetry:**
   - For applicants, internal risk scores (e.g. 100/100), risk bands, Top Priority Contributing Factors, ELA forensic findings, and the "Full Scrutiny Dossier" button are hidden.
2. **Official Decision Card:**
   - Read-only card displaying recorded decision status (Approved / Rejected / Information Requested), date, reference number, applicant-visible remarks, issuing authority, and next regulatory steps.
   - If no decision has been issued: "No official decision has been issued yet."
3. **Released Reports & Documents Section:**
   - Displays downloadable Letter of Approval (LoA), Official Decision Order, and Statutory Deficiency Notice only when the corresponding document has been officially released.

### F. Applicant Information Requests (Complete Notice-Response Workflow)
1. **Notices List (`/information-requests`):**
   - Summary cards: Action Required, Response Submitted, Under Review, Resolved (calculated from DB records).
   - Search by ref no, title, or application ID, with status filters.
   - Lists notice reference number, application ID, title, issue date, actual deadline from notice, and status.
   - Draft notices are hidden from institutions on both frontend and backend.
2. **Request Details & Response Workspace (`/information-requests/[id]`):**
   - Read-only notice preview with reference number, authority, date, stored deadline (not hardcoded), and listed deficiencies.
   - Per-deficiency response item with explanation field and deficiency-linked file upload (`/information-requests/{id}/upload-deficiency-doc`).
   - "Save Draft" saves intermediate responses to the database.
   - "Submit Response" validates that all mandatory deficiencies have explanations or attachments, generates an official receipt number (`REC-...`), logs a submission timestamp, and notifies officials.
   - Official review panel allows authorized officials to accept/resolve the request or ask for further info.

### G. Official Dashboard (Metric Reconciliation & Telemetry Segregation)
1. **Clickable KPI Cards:**
   - Total Applications, Needs Review, Under Verification, Approved, Rejected, Info Requested all navigate directly to the filtered Applications Queue (`/applications?status=...`).
2. **Application Scrutiny Distribution:**
   - Fully reconciled counts including Draft and Submitted applications with exact percentages. Clickable donut slices and legend items filter the queue.
3. **Pipeline Performance:**
   - Uses real measurements. Native PDF text extraction separated from OCR Tesseract jobs. Shows pending and failed jobs, reporting period, and last refresh time.
4. **Recent Discrepancy & Fraud Alerts:**
   - Segregated tabs for Document Deficiencies, Cross-Document Mismatches, Duplicate Documents, and Forensic Anomalies. Shows affected document, severity, date, and review status. Clicking alert opens the application.
5. **High Scrutiny Priority Queue:**
   - Excludes drafts, approved, and rejected applications. Displays priority score, priority band, specific contributing factors, submission date, and unresolved finding count.

---

## 3. Database Schema Updates

1. **`notifications` Table:**
   - `id`: Integer primary key
   - `user_id`: Integer foreign key -> `users.id` (nullable)
   - `target_role`: String(32) (nullable)
   - `institution_id`: Integer foreign key -> `institutions.id` (nullable)
   - `category`: String(32)
   - `title`: String(255)
   - `message`: Text
   - `link`: String(255) (nullable)
   - `application_id`: Integer foreign key -> `applications.id` (nullable)
   - `is_read`: Boolean (default False)
   - `created_at`: DateTime (default UTC now)
   - `read_at`: DateTime (nullable)
2. **`information_requests` Table:**
   - `id`: Integer primary key
   - `reference_no`: String(64) unique
   - `application_id`: Integer foreign key -> `applications.id`
   - `institution_id`: Integer foreign key -> `institutions.id`
   - `title`: String(255)
   - `reason`: Text
   - `deficiencies`: JSON
   - `status`: String(32)
   - `issued_by_id`: Integer foreign key -> `users.id` (nullable)
   - `issued_at`: DateTime (nullable)
   - `deadline`: DateTime (nullable)
   - `resolved_at`: DateTime (nullable)
   - `resolution_notes`: Text (nullable)
   - `created_at`: DateTime (default UTC now)
3. **`information_responses` Table:**
   - `id`: Integer primary key
   - `request_id`: Integer foreign key -> `information_requests.id`
   - `submitted_by_id`: Integer foreign key -> `users.id`
   - `items`: JSON
   - `status`: String(32)
   - `receipt_no`: String(64) unique (nullable)
   - `submitted_at`: DateTime (nullable)
   - `review_remarks`: Text (nullable)
   - `created_at`: DateTime (default UTC now)
   - `updated_at`: DateTime (default UTC now)

---

## 3.1 Prompt 2 Accomplishments: Information Requests Fix & Applicant Reports Workflow

### A. Root Cause of the Information Requests Bug
1. **Schema Mismatch in SQLite Database:**
   - In `backend/aicte_verifier.db`, the `information_requests` table was missing the `reason` column due to table creation prior to the Pydantic/SQLAlchemy model update.
   - Any API request to `GET /api/v1/information-requests` or `GET /api/v1/information-requests/summary-cards` failed with an internal SQLite `OperationalError: no such column: reason` (HTTP 500).
   - The frontend page caught the error silently and rendered the generic empty state: *"No official notices found. No formal Information Requests have been issued to your institution."*
2. **Disconnected Notice Issuance Pipeline:**
   - When an official committed an `info_requested` decision via `POST /api/v1/applications/{id}/decision`, the handler updated `applications.status` and inserted into `decisions`, but never created a persisted `InformationRequest` record or linked the deficiency letter.
   - Meanwhile, Application Details and Dashboard loaded `/deficiency-letter` which generated a preview on-the-fly (`.../DEF-01`), creating the illusion of an issued notice that did not exist in the database.

### B. Notice Persistence, Migration & Synchronization
1. **Auto-Migration & Database Health Check:**
   - Added automatic column migration check in `backend/app/services/notice_sync.py` to ensure `information_requests.reason` is always created if missing.
2. **Authoritative Notice Persist Service:**
   - Created `persist_official_notice_for_application()` in `backend/app/services/notice_sync.py`:
     - Generates unique reference `AICTE/RO/SCRUTINY/{academic_year}/{app_no}/DEF-01`.
     - Calculates explicit statutory deadline (stored date, default 15 calendar days from issuance).
     - Extracts structured deficiency items from compliance results and fraud flags.
     - Sets notice status to `action_required`.
     - Links `DeficiencyLetter` status to `sent`.
     - Dispatches formal notification to institution.
     - Logs append-only audit trail event.
     - Idempotent: retries will not duplicate notices.
3. **Synchronized Startup Lifespan & Query Hooks:**
   - `backend/app/main.py`: Lifespan context manager runs `sync_unpersisted_info_requested_notices()` on server startup.
   - `backend/app/routers/information_requests.py`: Calls `sync_unpersisted_info_requested_notices()` during list and summary requests so `AICTE-2026-A6BCAF` and any other existing `info_requested` applications are immediately populated.
   - `backend/app/routers/decisions.py`: When official selects `info_requested`, calls `persist_official_notice_for_application()`. When official selects `approved`, automatically resolves any pending information requests to keep lifecycle consistent.

### C. Information Requests Frontend (`/information-requests` & `[id]`)
1. **Authoritative List & Summary Cards:**
   - Displays real backend counts: Action Required, Response Submitted, Under Review, Resolved.
   - Search by Notice Reference, Application No, or Title.
   - Filter tabs: All, Action Required, Submitted, Under Review, Resolved.
   - Renders Notice Reference, Application ID, Institution Name, Issue Date, Actual Deadline, and "Respond to Notice" button.
   - Distinct loading skeleton, error banner with Retry button, and empty state.
   - Refresh button fetches fresh backend data.
2. **Per-Deficiency Response Workspace:**
   - Official read-only notice preview with download notice action.
   - Per-deficiency items with requirement, explanation textarea, slot-specific document upload, replacement button, and completion status.
   - **Save Draft:** Persists intermediate responses without submitting.
   - **Review Response:** Opens a modal summarizing all explanations and attachments before final commitment.
   - **Submit Response:** Validates required items, commits to database, generates official receipt number (`RCP-2026-XXXXX`), logs submission timestamp, locks response, and notifies council officials.
   - Controlled review: Submitting a response transitions request to `submitted` / `under_review`; only an authorized official can resolve the request.
   - Official review panel with resolve / further-info controls and audit history table.

### D. Applicant Reports & Decisions (`/reports` & `ReportView.tsx`)
1. **Full Redaction of Internal Scrutiny Telemetry:**
   - Internal scrutiny risk score (100/100), risk band, contributing factors with point weights, committee notes, and fraud flags are completely hidden from applicants.
   - Removed the "Full Scrutiny Dossier" button from the applicant portal.
   - Enforced at backend API (`GET /applications/{id}/report` and `GET /deficiency-letter`): applicants receive 404 for unissued drafts.
2. **Official Decision Card:**
   - Read-only card with Application ID, Institution Name, recorded decision (Approved, Rejected, Information Requested, Pending), decision date, applicant-visible remarks, issuing authority, and next regulatory steps.
   - Displays "No official decision has been issued yet" if no decision is recorded.
3. **Formal Deficiency Notice Card:**
   - Rendered only after formal issuance by an authorized official.
   - Shows notice reference, issue date, actual deadline, read-only preview, Download Notice button, and "Respond to Notice" action link.
4. **Released Reports & Documents Section:**
   - Displays official Letter of Approval (LoA), Official Decision Order, Released Scrutiny Summary, and Issued Deficiency Notice.
   - Download buttons are enabled only when the file or document exists.

### E. Portal-Wide State Synchronization
1. **Dashboard & My Applications:**
   - Dashboard Action Required counter is backed by actual pending requests.
   - Urgent banner links directly to `/information-requests?status=action_required`.
   - My Applications shows `Info Requested` badge and direct link to response workspace.
   - Application Details displays authoritative deficiency notice reference and deadline.
2. **Tenant Isolation & Security:**
   - Applicants can only view their own applications, notices, responses, and released documents.
   - Unissued drafts are hidden from applicants.

---

## 3.2 Master Prompt Accomplishments: Notice Intelligence, Forensics, Document Verification & Decision Consistency

### A. Root Cause of Excessive Deficiency Count & Resolution
1. **Root Cause Analysis:**
   - In `backend/app/services/notice_sync.py` and `backend/app/services/deficiency_letter.py`, notices previously iterated blindly over every recorded `Flag` in the database for an application.
   - For an application with multiple documents, repeated comparison runs across duplicate detection, image similarity, ELA tampering, and missing fields generated dozens of individual flags (e.g. 80 duplicate flags, 5 ELA compression flags, etc.), resulting in notices with up to 119 deficiency items.
   - Internal scrutiny signals (such as 90% pHash similarity or high ELA compression variance) were being improperly transformed into actionable applicant demands.
2. **Deficiency Classification Engine (`finding_classification.py`):**
   - Implemented rigorous classification into 6 regulatory finding categories:
     - `mandatory_compliance`: Missing statutory documents, expired certificates. (Applicant actionable)
     - `material_inconsistencies`: Conflicting land area, registration numbers, institution names. (Applicant actionable)
     - `document_clarifications`: Low OCR confidence on material fields. (Applicant actionable)
     - `internal_forensics`: ELA anomalies, copy-move clusters, compression artifacts. (`INTERNAL_REVIEW_ONLY`)
     - `duplicate_similarity`: Shared statutory templates, near-duplicate documents. (`INTERNAL_REVIEW_ONLY`)
     - `authority_pending`: External registry checks pending. (`INTERNAL_REVIEW_ONLY`)
   - Notice generation services now strictly filter for `is_actionable=True`, ensuring that internal forensics and duplicate warnings never enter applicant notices without an explicit authorized official classification.

### B. Duplicate Detection & Perceptual Similarity Overhaul
1. **Normalized Document Pair Comparison:**
   - In `backend/app/engines/duplicates.py`, pairs are ordered deterministically using `pair_key = f"{min(doc_a_id, doc_b_id)}_{max(doc_a_id, doc_b_id)}"`.
   - Explicitly excludes self-comparisons (`doc_a.id == doc_b.id`).
   - Grouping prevents A vs B and B vs A from creating two duplicate findings.
2. **Cryptographic vs Perceptual Similarity:**
   - SHA-256 byte-hash equality reports 100% cryptographic match.
   - Perceptual image hashes (pHash) are capped at 98.5% and labeled as visual similarity, never 100% cryptographic match.
   - Standard statutory templates (e.g., standard AICTE anti-ragging affidavits, land declarations) sharing common layout are classified as `standard_template` (`severity="info"` and `actionability="INTERNAL_REVIEW_ONLY"`).
3. **Risk Score Deduplication (`risk.py`):**
   - Deduplicates findings by normalized pair key so the same underlying document pair is never scored multiple times.
   - Standard templates contribute 0 risk points.
   - Total duplicate contribution is capped at a maximum of 30 risk points.

### C. Official Interactive Notice Builder
1. **Notice Candidates & Issuance Endpoints:**
   - `GET /api/v1/applications/{id}/notice-candidates`: Returns grouped findings across the 6 categories, showing severity, rule version, evidence, actionability, and default suggested title/explanation.
   - `POST /api/v1/applications/{id}/issue-notice-builder`: Validates authorized role, requires >= 1 actionable item, enforces non-empty applicant explanation and action, derives cure period (default 15 days), generates notice reference (`AICTE/RO/SCRUTINY/{year}/{app_no}/DEF-01`), creates `InformationRequest`, sets application to `info_requested`, dispatches notification, and records audit trail.
2. **Interactive UI (`NoticeBuilderView.tsx`):**
   - Candidate tabs for each category with item counters.
   - Interactive checkbox selection; internal-only findings are locked by default and require explicit justification to include.
   - Editable applicant-facing title and explanation per item.
   - Document category association and response requirement toggles (written explanation, document upload, or both).
   - "Preview Notice" modal rendering official AICTE letterhead and numbered statutory deficiencies.
   - "Save Draft" for saving intermediate progress.
   - Two-step confirmation modal before issuing notice.

### D. Item-Specific Applicant Responses
1. **Schema & Endpoints:**
   - Each issued notice item contains persistent deficiency ID, requirement, action, required flags, applicant response text, and attached document IDs.
   - Endpoint `POST /information-requests/{id}/upload-deficiency-doc` links uploaded files directly to the deficiency ID.
2. **Institutional Tenant Access:**
   - Institutions can only view and respond to notices belonging to their own applications.
   - Submitting responses generates an official receipt number (`RCP-2026-XXXXX`), records submission timestamp, and transitions notice to `under_review`.
   - Response submission does not auto-resolve the notice; an authorized official must explicitly review and resolve.

### E. Official Decision Consistency
1. **Persisted vs Unsaved Action Separation:**
   - In `ReportView.tsx`, persisted official determinations are displayed in a dedicated top-level card (Status, Date, Decision Reference, Official Remarks, Issuing Authority).
   - The interactive workflow selection buttons below remain independent; selecting an option does not alter the persisted decision until committed.
   - Selecting "Request More Information" smoothly transitions to the Notice Builder.
   - Mandatory official remarks are enforced on both frontend and backend.
   - Prevents contradictory states (such as displaying "Approved" while remarks say "Information requested").

### F. Official Scrutiny Queue & Dashboard Reconciliation
1. **Draft Application Scrutiny Exclusion:**
   - Applications in `draft` status are excluded from the active scrutiny queue, active totals, pending counts, and priority scoring.
   - Drafts are accessible only when officials explicitly choose the "Draft Applications" filter.
2. **Recent Discrepancy & Fraud Alerts Query Fix:**
   - In `backend/app/routers/dashboard.py`, balanced queries return up to 15 items per category (Deficiencies, Mismatches, Duplicates, Forensics).
   - Resolves the bug where Deficiencies or Mismatches tabs displayed false empty states.

### G. Removal of Official-Side Upload Controls
1. **Custody Separation:**
   - In `frontend/src/app/applications/[id]/page.tsx`, removed the official-side document upload box.
   - Replaced with an Official Document Custody Notice reminding officials that documents must be submitted by institutions.
   - Backend RBAC strictly denies document uploads from official accounts (`403 Forbidden`).

### H. Stage 5 Forensics & Fraud Layout Fix
1. **Independent Vertical Scrolling:**
   - In `frontend/src/features/fraud/FraudSignalsView.tsx`, the right-hand Duplicate & Template Similarity findings list container is bounded with `max-h-[460px] overflow-y-auto pr-1`.
   - The left-hand Forensic Signal Inspection viewer (document preview, ELA heatmap, zoom, page controls) remains visually stable and locked in place.

### I. Stage 6 Authenticity Verification
1. **Real Re-Verify Execution:**
   - `POST /api/v1/verification/verify`: Calls configured authority adapter (`rera`, `land_records`, `pci_bci`), persists outcome (`MATCH`, `MISMATCH`, `NOT_FOUND`), timestamp, and audit trail.
   - Supports manual reference number override if OCR extraction missed or misread the registration number.
2. **Record Manual Verification:**
   - `POST /api/v1/verification/manual-verify`: Allows authorized officials to record manual verification determinations (`MATCH_CONFIRMED`, `MISMATCH_CONFIRMED`, `UNABLE_TO_VERIFY`) with mandatory officer remarks and evidence source.
   - Mode is explicitly persisted as `MANUAL_SCRUTINY`, keeping it distinct from `SIMULATED` automated adapter results.

### J. Stage 4 / Stage 10 Document Verification Actions
1. **Document-Level Official Review:**
   - In `frontend/src/features/validation/ValidationView.tsx`, added columns for Automated Check and Official Verification.
   - Implemented `POST /api/v1/documents/{id}/official-review` supporting `Verified`, `Mismatch Confirmed` (requires conflicting field name and remarks), and `Unable to Verify`.
   - Implemented inline `POST /api/v1/documents/{id}/re-validate` to re-run validation rules on demand.
   - Document-level outcomes are kept strictly distinct from the final application-level decision in Stage 9.

### K. SARATHI Website Rebranding & Login Page Update
1. **Platform Identity:** Official platform rebranded to **SARATHI** with tagline: *"Your Digital Charioteer for Seamless AICTE Regulatory Governance."*
2. **Indian Public Sector Portal Aesthetic:**
   - Formal, trustworthy design inspired by national portals with national tri-color accent hairline, deep navy headers, and light blue-grey surfaces.
   - Distinctive SARATHI wordmark paired with an official charioteer guidance emblem (`Compass` / `Navigation`).
3. **Login Page Architecture:**
   - Prominently showcases SARATHI wordmark, tagline, and supporting description: *“An integrated digital platform for transparent document verification, regulatory compliance, and AI-assisted scrutiny of technical institutions.”*
   - Displays four core regulatory pillars:
     - **Regulatory Compliance** — Rule-based verification aligned with applicable AICTE requirements.
     - **Secure Document Verification** — Document processing, field extraction, and consistency checks.
     - **Intelligent Scrutiny Support** — AI-assisted analysis with explainable findings for authorised officials.
     - **Human-in-the-Loop Decisions** — AI supports scrutiny; authorised officials make the final decisions.
   - Retains exact working demo login personas:
     - **AICTE Official** — Scrutiny & Decisions (`official@aicte.gov.in`)
     - **Institution Applicant** — Applicant Portal (`inst1@aicte.gov.in`)
4. **Site-Wide Coherence:**
   - Browser metadata, top navigation header (`TopBar.tsx`), brand sidebar (`Sidebar.tsx`), applicant dashboard welcome banner, official scrutiny dashboard heading, user profile settings, and PDF dossiers/letters consistently reference **SARATHI** while strictly preserving all statutory references to **AICTE** as the regulatory council.

---

## 4. Tests Run & Actual Results

### Full Backend Test Suite:
```powershell
.\.venv\Scripts\python -m pytest backend/tests/ -v
```
**Result:**
- Total tests: **91**
- Passed: **91**
- Failed: **0**
- Warnings: **3** (harmless Pydantic V2 config deprecation warnings in mock schemas)
- Test modules:
  - `test_auth_permissions.py`: 7 passed
  - `test_classifier.py`: 5 passed
  - `test_compliance.py`: 2 passed
  - `test_consistency.py`: 4 passed
  - `test_decisions_dashboard_audit.py`: 3 passed
  - `test_duplicates.py`: 3 passed
  - `test_extractor.py`: 5 passed
  - `test_file_validation.py`: 5 passed
  - `test_forensics.py`: 3 passed
  - `test_integration_scenarios.py`: 6 passed
  - `test_master_prompt_regression.py`: 5 passed
  - `test_notice_intelligence_and_verification.py`: 7 passed (Master Prompt comprehensive suite)
  - `test_phase1_foundation_and_portal.py`: 8 passed
  - `test_preview_and_applicant_separation.py`: 11 passed
  - `test_prompt2_workflows.py`: 5 passed
  - `test_reports.py`: 4 passed
  - `test_validator.py`: 2 passed
  - `test_verifiers.py`: 6 passed

### Frontend Production Build:
```powershell
cd frontend
npm run build
```
**Result:**
- **Zero build errors (Exit Code: 0)**.
- 16 static/dynamic routes generated cleanly.

---

## 5. Master Prompt System Completion Summary

1. **Authentication & Demo Personas:**
   - Reduced visible demo personas on `/login` to exactly two:
     - **AICTE Official — Scrutiny & Decisions** (`official@aicte.gov.in`)
     - **Institution Applicant — Applicant Portal** (`applicant@apex.edu`)
   - Underlying DB records for Zenith College and Council Auditor preserved with their roles and audit logs intact.
   - Quick demo login buttons authenticate via backend API and immediately route applicants to the Applicant Dashboard.

2. **Frontend-Backend Connectivity & Health Check:**
   - Decorated FastAPI health endpoints across `/`, `/health`, and `/api/v1/health` returning:
     `{"status": "healthy", "service": "AICTE Document Verification System", "api_docs": "/api/v1/docs"}`.
   - Replaced generic "Failed to fetch" errors with structured diagnostic messages identifying target host and port.

3. **New Application Form Validation Fix (Root Cause):**
   - **Root Cause Identified:** Backend endpoint `POST /applications/validate-declared-details` returned `{"is_valid": is_valid, "errors": errors}`, while the frontend TypeScript client checked `if (!valRes.valid)`. Because `valRes.valid` was `undefined`, `!undefined` was always `true`, causing every submission to fail with the generic validation banner even with all valid fields populated!
   - **Fix:** Backend now returns `{"is_valid": is_valid, "valid": is_valid, "errors": errors}`; frontend now checks `const isValid = valRes.valid !== undefined ? valRes.valid : valRes.is_valid;`.

4. **Institution Declared Parameters Editing:**
   - Enhanced `PUT /applications/{id}/declared-details` with individual numerical bounds validation (`land_area_acres > 0`, `built_up_area_sqm > 0`, `faculty_count >= 1`, `student_intake >= 1`, `ews_quota_percentage` 0–100) and `validate_all: bool = Query(False)`.
   - In `ApplicantApplicationView.tsx`, implemented form pre-population from saved values, form cancellation restoring previous values, bounds validation, and database updates with audit trail logging.

5. **Official Application Queue Draft Filtering:**
   - Default scrutiny queue for officials now excludes `status="draft"` applications so officials only review actionable submitted applications.
   - Draft applications remain accessible by selecting "Draft Applications" in the status filter dropdown.

6. **Decoupled Stage 8 & Stage 9 Scrutiny Workflow:**
   - **Stage 8 (Scrutiny Dossier):** Advisory evidence dossier summarizing Review Priority score, risk band, contributing factors, cross-document discrepancies, forensic anomalies, and authority verifications, with a clear button to "Proceed to Stage 9: Official Scrutiny Decision". Binding decision controls are strictly excluded from Stage 8.
   - **Stage 9 (Official Decision & Statutory Notice):** Dedicated determination interface with three options (none selected by default: Approve, Request More Information, Reject), outcome-specific guidance and placeholders, statutory deficiency notice editor for `info_requested`, and a two-step confirmation modal before final commit. Mandatory meaningful remarks validated at both frontend and backend.


---

## 6. Commands to Run Locally

### 1. Run Complete PyTest Suite:
```powershell
cd c:\Dhruvi\SIH_PS1
.\.venv\Scripts\python -m pytest -v
```

### 2. Verify Next.js Production Build:
```powershell
cd c:\Dhruvi\SIH_PS1\frontend
npm run build
```

### 3. Start Backend API Server:
```powershell
cd c:\Dhruvi\SIH_PS1
.\.venv\Scripts\uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Start Frontend Server:
```powershell
cd c:\Dhruvi\SIH_PS1\frontend
npm run dev -- -p 3000
```
