import io
import os
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
    Image as RLImage,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.finding import Flag
from backend.app.models.compliance import ComplianceResult, ComplianceRule
from backend.app.models.verification import VerificationResult
from backend.app.models.decision import Decision
from backend.app.engines.risk import RiskEngine

def generate_application_pdf_report(application_id: int, db: Session) -> bytes:
    """
    Generates a formal, printable AICTE Decision-Support Verification Dossier in PDF format.
    Adheres strictly to the core philosophy: The AI recommends; the authorised official decides.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise ValueError(f"Application {application_id} not found")

    # Ensure risk score is up-to-date
    risk_engine = RiskEngine(db)
    risk_breakdown = risk_engine.calculate_application_risk(application_id)

    # Fetch all relevant records
    docs = db.query(Document).filter(
        Document.application_id == application_id,
        Document.superseded_by.is_(None)
    ).all()

    flags = db.query(Flag).filter(
        Flag.application_id == application_id,
        Flag.status.in_(["open", "acknowledged"])
    ).all()

    comp_results = db.query(ComplianceResult).filter(
        ComplianceResult.application_id == application_id
    ).all()

    doc_ids = [d.id for d in docs]
    ver_results = db.query(VerificationResult).filter(
        VerificationResult.document_id.in_(doc_ids)
    ).all() if doc_ids else []

    decision = db.query(Decision).filter(Decision.application_id == application_id).first()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    header_title_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        alignment=1
    )
    header_sub_style = ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )
    section_title_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#991b1b")
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b")
    )
    cell_bold_style = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    # 1. Header & Official Title with AICTE Logo
    logo_path = os.path.join(os.path.dirname(__file__), "..", "static", "aicte_logo.png")
    if os.path.exists(logo_path):
        logo_img = RLImage(logo_path, width=42, height=42)
        header_table = Table(
            [[
                logo_img,
                [
                    Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)", header_title_style),
                    Paragraph("Statutory Body Under Ministry of Education, Government of India", header_sub_style),
                    Paragraph("SARATHI — AI-POWERED DOCUMENT VERIFICATION & SCRUTINY DOSSIER", header_title_style),
                ]
            ]],
            colWidths=[50, 490]
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
    else:
        story.append(Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)", header_title_style))
        story.append(Paragraph("Statutory Body Under Ministry of Education, Government of India", header_sub_style))
        story.append(Paragraph("SARATHI — AI-POWERED DOCUMENT VERIFICATION & SCRUTINY DOSSIER", header_title_style))
    story.append(Spacer(1, 8))

    # 2. Disclaimer Callout Banner
    disclaimer_text = (
        "<b>DECISION-SUPPORT NOTICE:</b> This dossier is generated by SARATHI (AICTE Automated Document "
        "Verification Decision Support System). In accordance with council regulations, <b>The AI recommends; "
        "the authorised official decides.</b> No application or document is automatically approved, rejected, "
        "or declared fraudulent without human review by the competent Scrutiny Committee."
    )
    disclaimer_table = Table(
        [[Paragraph(disclaimer_text, disclaimer_style)]],
        colWidths=[540]
    )
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
        ("BORDER", (0, 0), (-1, -1), 1, colors.HexColor("#fecaca")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(disclaimer_table)
    story.append(Spacer(1, 10))

    # 3. Institutional Application Summary Table
    inst_name = app.institution.name if app.institution else "Apex Institute of Technology"
    app_meta_data = [
        [
            Paragraph("<b>Application No:</b>", cell_style),
            Paragraph(app.application_no, cell_bold_style),
            Paragraph("<b>Academic Year:</b>", cell_style),
            Paragraph(app.academic_year, cell_style)
        ],
        [
            Paragraph("<b>Institution Name:</b>", cell_style),
            Paragraph(inst_name, cell_bold_style),
            Paragraph("<b>Application Type:</b>", cell_style),
            Paragraph(app.type.replace("_", " ").title(), cell_style)
        ],
        [
            Paragraph("<b>Review Status:</b>", cell_style),
            Paragraph(f"<b>{app.status.upper()}</b>", cell_bold_style),
            Paragraph("<b>Generated On:</b>", cell_style),
            Paragraph(datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M UTC"), cell_style)
        ]
    ]
    app_meta_table = Table(app_meta_data, colWidths=[110, 160, 110, 160])
    app_meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(app_meta_table)
    story.append(Spacer(1, 12))

    # 4. Review-Priority Score Card
    score = risk_breakdown.get("score", 0)
    band = risk_breakdown.get("band", "Low")
    band_color = colors.HexColor("#dc2626") if band == "High" else (colors.HexColor("#d97706") if band == "Medium" else colors.HexColor("#16a34a"))

    risk_card_data = [
        [
            Paragraph("<b>Review Priority Score:</b>", cell_style),
            Paragraph(f"<font color='{band_color}' size='12'><b>{score} / 100 ({band} Priority)</b></font>", cell_style),
            Paragraph("<b>Identified Open Flags:</b>", cell_style),
            Paragraph(f"Critical: {risk_breakdown.get('critical_flags_count', 0)} | Warning: {risk_breakdown.get('warning_flags_count', 0)} | Info: {risk_breakdown.get('info_flags_count', 0)}", cell_style)
        ]
    ]
    risk_table = Table(risk_card_data, colWidths=[120, 150, 120, 150])
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 12))

    # 5. Top Contributing Risk Factors
    top_factors = risk_breakdown.get("top_contributing_factors", [])
    if top_factors:
        story.append(Paragraph("Priority Contributing Factors (Explainability Breakdown):", section_title_style))
        factor_rows = [[
            Paragraph("<b>Weight</b>", cell_bold_style),
            Paragraph("<b>Source</b>", cell_bold_style),
            Paragraph("<b>Finding / Issue</b>", cell_bold_style),
            Paragraph("<b>Details</b>", cell_bold_style)
        ]]
        for tf in top_factors:
            factor_rows.append([
                Paragraph(f"+{tf.get('points', 0)} pts", cell_bold_style),
                Paragraph(tf.get("source", ""), cell_style),
                Paragraph(tf.get("title", ""), cell_bold_style),
                Paragraph(tf.get("detail", ""), cell_style)
            ])
        factor_table = Table(factor_rows, colWidths=[55, 110, 155, 220])
        factor_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(factor_table)
        story.append(Spacer(1, 12))

    # 6. Document Validation Matrix
    story.append(Paragraph("Uploaded Document Verification Matrix:", section_title_style))
    doc_rows = [[
        Paragraph("<b>Document Type</b>", cell_bold_style),
        Paragraph("<b>Filename</b>", cell_bold_style),
        Paragraph("<b>Pages</b>", cell_bold_style),
        Paragraph("<b>Validation Status</b>", cell_bold_style),
        Paragraph("<b>Fields Extracted</b>", cell_bold_style)
    ]]
    for d in docs:
        doc_rows.append([
            Paragraph(d.doc_type.replace("_", " ").title(), cell_style),
            Paragraph(d.original_filename[:25] + ("..." if len(d.original_filename) > 25 else ""), cell_style),
            Paragraph(str(d.page_count), cell_style),
            Paragraph(d.validation_status.upper(), cell_bold_style),
            Paragraph(str(len(d.extracted_fields)), cell_style)
        ])
    if len(doc_rows) == 1:
        doc_rows.append([Paragraph("No documents uploaded.", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style)])
    doc_table = Table(doc_rows, colWidths=[120, 150, 40, 110, 120])
    doc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(doc_table)
    story.append(Spacer(1, 12))

    # 7. Authenticity Verification Summary (SIMULATED)
    story.append(Paragraph("External Authority Verification Summary [SIMULATED]:", section_title_style))
    ver_rows = [[
        Paragraph("<b>Authority / Repository</b>", cell_bold_style),
        Paragraph("<b>Reference Extracted</b>", cell_bold_style),
        Paragraph("<b>Status</b>", cell_bold_style),
        Paragraph("<b>Simulated Remarks</b>", cell_bold_style)
    ]]
    for vr in ver_results:
        ver_rows.append([
            Paragraph(f"{vr.authority}<br/><font size='6' color='#64748b'>(SIMULATED)</font>", cell_style),
            Paragraph(vr.reference_no or "None", cell_style),
            Paragraph(vr.status.upper(), cell_bold_style),
            Paragraph(vr.message or "", cell_style)
        ])
    if len(ver_rows) == 1:
        ver_rows.append([Paragraph("No external authority verification recorded.", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style)])
    ver_table = Table(ver_rows, colWidths=[150, 110, 80, 200])
    ver_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(ver_table)
    story.append(Spacer(1, 12))

    # 8. Regulatory Compliance Audit
    story.append(Paragraph("AICTE Regulatory Compliance Audit:", section_title_style))
    comp_rows = [[
        Paragraph("<b>Regulation / Clause</b>", cell_bold_style),
        Paragraph("<b>Required Standard</b>", cell_bold_style),
        Paragraph("<b>Provided / Extracted</b>", cell_bold_style),
        Paragraph("<b>Audit Outcome</b>", cell_bold_style)
    ]]
    for cr in comp_results:
        rule = db.query(ComplianceRule).filter(ComplianceRule.id == cr.rule_id).first()
        r_name = rule.name if rule else f"Rule #{cr.rule_id}"
        clause = rule.clause if rule else ""
        handbook_badge = " [Unverified Draft]" if rule and not rule.verified_against_handbook else ""
        comp_rows.append([
            Paragraph(f"<b>{r_name}</b><br/><font size='7' color='#475569'>{clause}{handbook_badge}</font>", cell_style),
            Paragraph(cr.required_value, cell_style),
            Paragraph(cr.provided_value or "None", cell_style),
            Paragraph(cr.outcome.upper().replace("_", " "), cell_bold_style)
        ])
    if len(comp_rows) == 1:
        comp_rows.append([Paragraph("No compliance checks recorded.", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style)])
    comp_table = Table(comp_rows, colWidths=[160, 130, 130, 120])
    comp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 14))

    # 9. Official Decision & Remarks Signature Block
    dec_status = decision.decision.upper() if decision else "PENDING SCRUTINY COMMITTEE"
    dec_officer = decision.officer.full_name if decision and decision.officer else "Pending Officer Assignment"
    dec_date = decision.decided_at.strftime("%d-%b-%Y %H:%M UTC") if decision else "Not Recorded"
    dec_remarks = decision.remarks if decision else "Official scrutiny remarks have not yet been submitted."

    story.append(Paragraph("Competent Official Scrutiny Decision:", section_title_style))
    dec_data = [
        [
            Paragraph("<b>Scrutiny Finding:</b>", cell_style),
            Paragraph(f"<b>{dec_status}</b>", cell_bold_style),
            Paragraph("<b>Authorised Officer:</b>", cell_style),
            Paragraph(dec_officer, cell_style)
        ],
        [
            Paragraph("<b>Decision Date:</b>", cell_style),
            Paragraph(dec_date, cell_style),
            Paragraph("<b>Authority Mandate:</b>", cell_style),
            Paragraph("AICTE Regional Scrutiny Committee", cell_style)
        ],
        [
            Paragraph("<b>Official Remarks:</b>", cell_style),
            Paragraph(dec_remarks, cell_style),
            Paragraph("<b>Signature:</b>", cell_style),
            Paragraph("________________________", cell_style)
        ]
    ]
    dec_table = Table(dec_data, colWidths=[110, 160, 110, 160])
    dec_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(dec_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
