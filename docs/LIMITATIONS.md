# AICTE Document Verification System — Known Limitations & System Boundaries

In accordance with rigorous engineering ethics and Smart India Hackathon guidelines, this document provides an honest assessment of current prototype boundaries, technical limitations, and production deployment considerations.

---

## 1. Optical Character Recognition (OCR) & Scan Quality
- **Native vs. Scanned Documents:** PyMuPDF extracts text, character coordinates, and bounding boxes with near-100% precision on digitally generated PDFs. Scanned documents rely on Tesseract OCR.
- **Graceful Degradation:** When the Tesseract binary is not installed on the host system PATH, the pipeline does not crash. It extracts native digital text layers and returns status `OCR unavailable` for image-only scans.
- **Image Quality Dependencies:** Extreme motion blur, low DPI (&lt; 150 DPI), heavy skew (&gt; 15 degrees), or mobile camera glare can reduce OCR character accuracy. The system detects these conditions via Laplacian variance and issues informative quality warning flags rather than hallucinating field values.

---

## 2. Image & Document Forensics Boundaries
- **Heuristic Nature of ELA:** Error Level Analysis (ELA) highlights high-frequency compression variances across JPEG 8x8 DCT blocks. While effective at detecting digital splicing (e.g. pasted signatures or altered numbers), benign processes such as multiple re-saving, PDF printer drivers, or scanner contrast enhancement also introduce compression variance.
- **Strict Human Review Rule:** Forensic signals must never be treated as legal evidence or automated accusations of forgery. They are advisory visual flags directing human inspectors to examine specific coordinates.

---

## 3. Pluggable External Authority Adapters (Simulation Boundary)
- **Simulated MVP Adapters:** In this prototype, external government verification adapters (`mock_building_plan.py`, `mock_fire_noc.py`, `mock_society_reg.py`, `mock_env_clearance.py`) simulate registry responses and return `is_simulated = True`.
- **Production Integration Path:** Live production deployment requires DigiLocker REST API v2 credentials, state land department mTLS certificates (e.g., Mahabhulekh / Bhoomi), and Urban Development OBPS API tokens, as specified in `docs/REAL_INTEGRATION.md`.

---

## 4. Regulatory Handbook Thresholds
- **AICTE Approval Process Handbook (APH):** Regulatory rules are versioned and stored in SQLite. While based on standard AICTE engineering requirements (2.5 acres campus land, 1:20 cadre ratio, 4000 sq.m built-up area), regional concessions and state-specific relaxations (e.g., Tier-1 urban metro concessions) require council validation.
- **Unverified Placeholder Badging:** Rules not yet validated against the official gazette are explicitly labeled `Unverified placeholder threshold` in the user interface and PDF dossiers.

---

## 5. Review-Priority Scoring Semantics
- **Priority Indicator, Not Probability:** The Review-Priority Score (0-100) reflects the depth and urgency of scrutiny recommended for the Scrutiny Committee based on missing documents, validation defects, and compliance deficits.
- **Never "Fraud Probability":** The score must never be interpreted or presented as a probability of applicant fraud or institutional guilt.
