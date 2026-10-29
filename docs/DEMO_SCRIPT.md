# AICTE Document Verification System — Hackathon Live Demo Script

**Project:** AI-Powered AICTE Document Verification System (SIH Problem Statement 1)  
**Target Audience:** Smart India Hackathon Evaluation Jury & AICTE Officials

---

## 1. Demo Narrative Arc & Persona Setup

The demonstration follows three realistic institutional actors using seed credentials:

| Persona | Role | Email | Password | Responsibilities |
|---|---|---|---|---|
| **Dr. Ramesh Verma** | Applicant Institution 1 | `inst1@aicte.gov.in` | `Demo@Password123` | Creates approval applications, uploads documents, views checklist. |
| **Sanjay Deshmukh** | AICTE Scrutiny Officer | `official@aicte.gov.in` | `Demo@Password123` | Inspects verification signals, overrides flags, commits official decisions. |
| **Dr. Sunita Rao** | Council System Admin | `admin@aicte.gov.in` | `Demo@Password123` | Reconfigures handbook compliance rules, monitors audit trail. |

---

## 2. Step-by-Step Demonstration Walkthrough

### Part 1: Applicant Workflow (Institution Persona)
1. **Sign In:** Navigate to `http://localhost:3000/login` and log in as `inst1@aicte.gov.in`.
2. **Create New Application:**
   - Click **"New Application"** in the sidebar.
   - Enter Academic Year `2025-2026`, Program `Engineering & Technology (UG)`, Declared Land Area `3.5 Acres`, Built-up Area `4500.0 sq.m`, Student-Faculty Ratio `18.0`.
   - Click **"Create Application"**.
3. **Upload Documents (Stage 1):**
   - In Step 2, upload synthetic documents from `sample_data/scenario_A_pristine/`:
     - `title_deed.pdf`
     - `building_plan.pdf`
     - `fire_noc.pdf`
   - Notice the real-time magic-byte inspection validating the file format.
   - The checklist checklist marks items as uploaded.
4. **Submit Application:**
   - Click **"Submit for Official Scrutiny"**.
   - Notice the submission blocker preventing submission if mandatory items are missing.

---

### Part 2: Scrutiny Committee Review (Official Persona)
1. **Switch User:** Sign out and log in as `official@aicte.gov.in`.
2. **Dashboard Overview (Stage 9):**
   - View live aggregate KPI tiles and the Recharts donut chart showing application distribution across India.
   - Inspect the **Pipeline Performance** card showing sub-second parsing and 99%+ extraction integrity.
3. **Open Applications Queue:**
   - Navigate to `/applications` and select the submitted application.
4. **Inspect Extracted Fields (Stage 3):**
   - Click **"Stage 3: Extracted Information"**.
   - Select `title_deed.pdf`.
   - Notice the document preview side-by-side with extracted fields: Institution Name, Land Area, Registration Date.
   - Click on an extracted field &mdash; observe the visual bounding-box highlight on the PDF canvas.
   - Test inline field correction: edit a field and click save. The change is saved and tracked.
5. **Validation Matrix & Consistency (Stage 4):**
   - Click **"Stage 4: Validation Matrix"**.
   - Show the cross-document consistency checks comparing declared land area vs. title deed text, with fuzzy matching on institutional names.
6. **Forensics & Duplicate Detection (Stage 5):**
   - Click **"Stage 5: Fraud & Forensics"**.
   - Show the **Original vs ELA Heatmap** toggle for forensic inspection.
   - Highlight the prominent warning banner: *"Signals are heuristic indicators for human review. Under council regulations, the AI recommends; the authorised official decides."*
   - Show template-awareness: Affidavit layout matches are automatically categorized as Info rather than Critical forgery.
7. **Authenticity Verification (Stage 6):**
   - Click **"Stage 6: Authenticity"**.
   - Show the simulated responses from Municipal Corporation, State Fire Services, and Charity Commissioner.
   - Note the prominent `SIMULATED` badge on every card. Explain how production architecture integrates with state land portals via `docs/REAL_INTEGRATION.md`.
8. **Compliance Checking Matrix (Stage 7):**
   - Click **"Stage 7: Compliance"**.
   - Show automated evaluation against versioned AICTE Handbook clauses: Minimum Land Area, Faculty-Student Ratio, Built-up Area.
   - Note the **"Unverified placeholder threshold"** chip on clauses pending official gazette confirmation.
9. **Final Dossier & Official Decision (Stage 8 & 9):**
   - Click **"Stage 8 & 9: Report & Decision"**.
   - Show the **Review-Priority Score** (e.g. `25 / 100 - Low Priority`) with explainable top contributing factors.
   - Click **"Download Official PDF Dossier"** &mdash; open the generated ReportLab PDF showing formal AICTE headers, disclaimers, and signature block.
   - View the automated **15-Day Statutory Deficiency Notice** with editable cure notice text.
   - **Commit Official Scrutiny Decision:** Select `Approve Application`, type mandatory remarks: *"All statutory land deeds, building plans, and fire NOCs verified compliant with AICTE APH 2024 standards."*, and click **"Commit Official Decision"**.

---

### Part 3: Administrative Control & Governance (Admin Persona)
1. **Sign In as Admin:** Log in as `admin@aicte.gov.in`.
2. **Rule Versioning (`/admin/rules`):**
   - View active regulatory rules.
   - Click **"Edit Version"** on a rule, adjust the threshold, toggle *"Mark Verified against AICTE Approval Process Handbook"*, and save.
   - Demonstrate that the previous version is deactivated and a new incremented version is created non-mutatingly.
3. **Statutory Audit Trail (`/audit`):**
   - Navigate to **"Audit Trail"**.
   - Filter by actor role and entity type.
   - Click **"Inspect State"** to reveal the before/after JSON payload of the decision and rule update made moments earlier.
   - Point out that there are no buttons or endpoints to delete or edit audit records &mdash; the ledger is strictly append-only.
