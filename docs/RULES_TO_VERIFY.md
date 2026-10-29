# AICTE Approval Process Handbook (APH) — Rules to Verify

> **Notice:** The compliance rules currently configured in this prototype are based on public draft reference guidelines for AICTE new institution approval. They must be validated against the officially notified AICTE Approval Process Handbook 2024–2027 by an authorized council officer before being marked `verified_against_handbook: true`.

---

## 1. Regulatory Threshold Checklist

| Rule Key | Parameter | Prototype Value | Unit | Handbook Citation | Verification Status | Notes / Edge Cases |
|---|---|---|---|---|---|---|
| `min_land_area` | `land_area_acres` | 2.5 | Acres | Clause 4.1, Appendix 4 | **Unverified placeholder** | Urban mega-cities have lower concession thresholds (e.g., 1.5 acres in Tier 1 metropolitans with higher FSI). |
| `faculty_student_ratio` | `student_faculty_ratio` | 20.0 (1:20) | Ratio | Clause 7.1, Appendix 7 | **Unverified placeholder** | 1:20 for UG Engineering; 1:15 or 1:12 applies for PG and specialized architectural/pharmaceutical courses. |
| `min_built_up_area` | `built_up_area_sqm` | 4000.0 | sq.m | Clause 4.2, Appendix 4 | **Unverified placeholder** | Scales with sanctioned division intake (e.g. 3 divisions = ~4000 sq.m; 6 divisions = ~7500 sq.m). |
| `min_laboratories` | `labs_count` | 10 | Count | Clause 6.3, Appendix 6 | **Unverified placeholder** | Depends on first-year general engineering curriculum plus core discipline-specific workshop requirements. |
| `ews_quota` | `ews_quota_percentage` | 10.0 | % | Clause 1.4.3, Chapter I | **Unverified placeholder** | Supernumerary quota as per Government of India mandate (Gazette notification 2019). |
| `corpus_fund` | `corpus_fund_lakhs` | 100.0 | Lakhs INR | Clause 4.6, Chapter IV | **Unverified placeholder** | Varies by promoter status (Government vs Society/Trust vs Section 8 Company). Joint FD with Regional AICTE Officer. |
| `affidavit_stamp` | `affidavit_stamp_value_inr` | 100.0 | INR | Clause 2.1, Appendix 2 | **Unverified placeholder** | Minimum non-judicial stamp paper value or state e-stamp duty denomination required by state law. |

---

## 2. Verification Protocol for Council Admins

1. Check the official notified handbook at `https://www.aicte-india.org/approvals/approval-process-handbook`.
2. Inspect the specific Appendix relevant to the application type (`New Technical Institution`, `Extension of Approval`, `Closure`).
3. Using the **Admin Rule Management** panel (`PUT /api/v1/admin/rules/{id}`), update:
   - Numerical threshold (`min_value`, `max_ratio`).
   - Handbook reference text (`clause`, `source`).
   - Toggle `verified_against_handbook: true`.
4. The system will immutably increment the rule version, deactivate the previous version, and record an append-only audit entry.
