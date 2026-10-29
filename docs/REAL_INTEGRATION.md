# Production Integration Architecture: AICTE Real Verification Gateways

> **Important Notice:** The current prototype uses pluggable mock adapters (`mock_building_plan.py`, `mock_fire_noc.py`, `mock_society_reg.py`, `mock_env_clearance.py`) that return `is_simulated = True`. This document outlines the technical specifications, authentication flows, and data schemas required to transition these adapters to live production government verification gateways.

---

## 1. DigiLocker & National Academic Depository (NAD) Integration

### Purpose
Direct cryptographic verification of institutional identity, society/trust deeds, accreditation awards, and officer credentials without relying on applicant-scanned PDFs.

### Technical Specification
- **API Standard:** DigiLocker API v2.0 (MeitY, Government of India)
- **Protocol:** RESTful HTTPS with OAuth 2.0 PKCE flow.
- **Mutual TLS (mTLS):** Required for production requester credentials (SHA-256 certificate issued by a licensed Certifying Authority under CCA India).
- **Endpoint Structure:**
  - `POST /public/oauth2/1/token`: Issue access token.
  - `POST /public/oauth2/1/xml/pull-doc`: Fetch cryptographically signed institutional document XML.
  - `POST /public/oauth2/1/xml/push-doc`: AICTE decision document deposit.

### Signature Verification
- DigiLocker documents are digitally signed using Indian IT Act compliant PKI (`ds:Signature`).
- Verification pipeline must validate the complete X.509 certificate chain against CCA India root certificates and inspect CRL / OCSP revocation status before marking a document `verified`.

---

## 2. State Land & Revenue Registries (Bhulekh / Mahabhulekh / Bhoomi / Dharani)

### Purpose
Validate title deeds, continuous single-piece land parcel declarations, encumbrance certificates, and Khasra/Survey numbers directly against state revenue land records.

### Technical Specification
- **API Standards:** National Land Record Modernization Programme (NLRMP) / Open State Land APIs.
- **Payload Parameters:**
  - `state_code`: 2-character ISO/Census code.
  - `district_code`, `taluka_code`, `village_code`.
  - `khasra_survey_number`: Unique plot identification number.
- **Verification Workflow:**
  1. Extract Survey/Khasra number and declared land area from institutional title deed.
  2. Dispatch request to state land portal gateway.
  3. Validate owner name against applicant Society/Trust name.
  4. Compare parcel area in state records against declared land area (within permissible 2% survey variance).
  5. Check encumbrance flag (`mortgaged`, `disputed`, `government_vested`).

---

## 3. Municipal Corporation & Town Planning Authorities

### Purpose
Verify sanctioned architectural building plans, floor-space index (FSI/FAR), occupational zoning (educational), and built-up area certificates.

### Technical Specification
- **Portal Integration:** State Urban Development Department / Online Building Permission System (OBPS).
- **Sanction Order Query:**
  - `GET /api/v1/sanction/verify?order_no={sanction_no}&year={year}`
- **Security:** HMAC-SHA256 signature in request header `X-Gov-Gateway-Signature` using authorized AICTE API key.
- **Data Cross-Check:**
  - Permitted built-up area vs. declared total instructional area.
  - Validity date of construction completion certificate.

---

## 4. Directorate of State Fire & Emergency Services

### Purpose
Validate active Fire Safety Compliance NOC certificates, fire hazard classification (Group B: Educational Buildings per National Building Code of India), and evacuation capacity.

### Technical Specification
- **Portal Integration:** State Disaster Management / Fire Service Portals.
- **Verification Parameters:**
  - `noc_number`: Unique dispatch number.
  - `institution_address` & `survey_plot`.
- **Validation Rules:**
  - Certificate must be currently active (not expired).
  - Hazard classification must explicitly authorize educational occupancy.
  - Built-up floor height must match sanctioned municipal building plan levels.

---

## 5. Security & Audit Requirements for Production

1. **Pluggable Architecture:** All production adapters must inherit from `backend.app.engines.verifiers.base.BaseVerifier` and populate `VerificationOutcome`.
2. **Audit Logging:** Every outbound call to external government gateways must record an append-only entry in `audit_logs` storing the timestamp, requester ID, authority code, and non-confidential response status code.
3. **Fail-Safe Neutral State:** If an external gateway fails or times out, the system must set the status to `pending` (Manual Verification Required), never auto-reject or falsely mark as counterfeit.
