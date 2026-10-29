# AICTE Document Verification System — API Reference Manual

Base URL: `http://127.0.0.1:8000/api/v1`  
Interactive OpenAPI Documentation: `http://127.0.0.1:8000/api/v1/docs`

---

## 1. Authentication & Identity (`/auth`)

### `POST /auth/login`
Authenticates a user and issues a signed JSON Web Token (JWT).
- **Request Body:**
  ```json
  { "email": "official@aicte.gov.in", "password": "Demo@Password123" }
  ```
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1...",
    "token_type": "bearer",
    "role": "official",
    "user_id": 3,
    "full_name": "Sanjay Deshmukh",
    "institution_id": null
  }
  ```

### `GET /auth/me`
Fetches the currently authenticated profile.
- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):** Returns User object.

---

## 2. Institutional Applications (`/applications`)

### `GET /applications/`
Lists applications. For institution users, returns strictly owned applications. For officials/admins/auditors, lists council-wide queue with search and status filters.

### `POST /applications/`
Creates a draft approval application.
- **Role:** Institution only.
- **Request Body:**
  ```json
  {
    "application_type": "new_institute",
    "academic_year": "2025-2026",
    "declared_details": {
      "institution_name": "Apex Institute of Technology",
      "land_area_acres": 3.5,
      "built_up_area_sqm": 4500.0,
      "student_faculty_ratio": 18.0
    }
  }
  ```

### `GET /applications/{id}/checklist`
Evaluates the checklist submission status (mandatory documents uploaded vs missing). Returns submit-blocker status.

### `POST /applications/{id}/submit`
Submits application for official scrutiny. Fails with 400 Bad Request if any mandatory checklist document is missing.

---

## 3. Documents & Pipeline Ingestion (`/documents`)

### `POST /applications/{id}/documents`
Uploads a document. Validates MIME type and magic bytes (PDF, JPG, PNG). Enforces UUID storage and page count limits. Dispatches ingestion pipeline.

### `POST /documents/{doc_id}/fields/{field_id}/correct`
Allows an authorized official to correct an OCR/regex-extracted field value.
- **Role:** Official or Admin only.
- **Logs:** Permanent before/after audit entry.

### `POST /documents/{doc_id}/reprocess`
Triggers full asynchronous reprocessing of document OCR and feature extraction.

---

## 4. Verification Findings & Flags (`/findings`)

### `GET /applications/{id}/findings`
Returns all detected validation, duplicate, cross-document, and forensic flags for an application.

### `POST /findings/{id}/acknowledge`
Acknowledges a review flag.

### `POST /findings/{id}/dismiss`
Dismisses a false-positive flag with mandatory official justification remarks.
- **Role:** Official or Admin only.
- **Logs:** Append-only audit record.

---

## 5. Authenticity Verification Adapters (`/applications/{id}/verification`)

### `GET /applications/{id}/verification`
Fetches external authority verification checks for all uploaded certificates. Returns results with `is_simulated: true`.

### `POST /applications/{id}/documents/{doc_id}/verify`
Triggers automated verification for a specific document against the corresponding authority adapter.

---

## 6. Regulatory Compliance Engine (`/applications/{id}/compliance`)

### `GET /applications/{id}/compliance`
Evaluates all active versioned compliance rules against declared particulars and extracted document fields. Returns outcomes: `compliant`, `non_compliant`, `needs_review`, `needs_update`.

---

## 7. Admin Rule Management (`/admin/rules`)

### `GET /admin/rules`
Lists versioned compliance rules.
- **Role:** Admin only.

### `PUT /admin/rules/{id}`
Non-mutating rule update. Deactivates current version and creates a new incremented version.
- **Role:** Admin only.

---

## 8. Reports & Deficiency Notices

### `GET /applications/{id}/report`
Returns comprehensive JSON scrutiny summary, explainable risk score (0-100), risk band, and top contributing factors.

### `GET /applications/{id}/report.pdf`
Streams formal printable ReportLab PDF Verification Dossier.

### `GET /applications/{id}/deficiency-letter`
Fetches drafted 15-day statutory cure notice deficiency letter.

### `POST /applications/{id}/deficiency-letter`
Saves official edits to the deficiency letter draft.

---

## 9. Official Decisions (`/applications/{id}/decision`)

### `POST /applications/{id}/decision`
Records binding Scrutiny Committee determination (`approved`, `rejected`, `info_requested`).
- **Role:** Official or Admin only.
- **Validation:** Remarks are mandatory (minimum 5 characters).
- **Logs:** Permanent append-only audit event.

---

## 10. Dashboard & Live Metrics (`/dashboard/summary`)

### `GET /dashboard/summary`
Returns real aggregated database counts, status distribution for Recharts donut, recent alerts, and high-risk cases queue.

---

## 11. Append-Only Audit Trail (`/audit`)

### `GET /audit`
Filterable audit log query endpoint.
- **Role:** Official, Admin, or Auditor only.
- **Note:** Strictly no POST, PUT, or DELETE routes exist for the audit log.
