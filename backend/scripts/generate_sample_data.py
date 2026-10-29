import os
import sys
import json
import shutil
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure workspace root is in sys.path
workspace_root = str(Path(__file__).resolve().parent.parent.parent)
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

import cv2
import numpy as np
from PIL import Image, ImageDraw
import fitz

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.institution import Institution
from backend.app.models.application import Application, ChecklistItem
from backend.app.models.document import Document
from backend.app.models.finding import Flag
from backend.app.models.verification import VerificationResult
from backend.app.pipeline.orchestrator import process_document_pipeline
from backend.app.routers.documents import compute_phash_for_file
from backend.app.routers.findings import sync_validation_and_consistency
from backend.app.engines.verifiers import verify_document
from backend.app.engines.compliance import ComplianceEngine
from backend.app.engines.risk import RiskEngine

# -------------------------------------------------------------------------
# STYLES & COMMON REPORTLAB UTILITIES
# -------------------------------------------------------------------------

def get_doc_styles():
    styles = getSampleStyleSheet()
    banner_style = ParagraphStyle(
        "SyntheticBanner",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#b91c1c"),
        alignment=1
    )
    footer_style = ParagraphStyle(
        "SyntheticFooter",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#b91c1c"),
        alignment=1
    )
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
        alignment=1
    )
    heading_style = ParagraphStyle(
        "DocHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b")
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155")
    )
    cell_bold = ParagraphStyle("CellBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=colors.HexColor("#0f172a"))
    cell_text = ParagraphStyle("CellText", parent=styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=colors.HexColor("#334155"))

    return {
        "banner": banner_style,
        "footer": footer_style,
        "title": title_style,
        "subtitle": subtitle_style,
        "heading": heading_style,
        "body": body_style,
        "cell_bold": cell_bold,
        "cell_text": cell_text,
    }

def render_page_png(pdf_path: str, png_path: str):
    """Renders page 1 of a PDF to high-resolution PNG preview."""
    try:
        doc = fitz.open(pdf_path)
        if len(doc) > 0:
            pix = doc[0].get_pixmap(dpi=150)
            pix.save(png_path)
        doc.close()
    except Exception as e:
        print(f"  [WARN] Failed to render PNG preview for {pdf_path}: {e}")

# -------------------------------------------------------------------------
# DOCUMENT GENERATORS
# -------------------------------------------------------------------------

def generate_land_deed(
    filepath: str,
    institution_name: str,
    trust_name: str,
    deed_number: str,
    survey_number: str,
    land_area_acres: float,
    registration_date: str,
    landowner: str = "Shri Vitthal Rao Patil (Fictional Vendor)"
):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    st = get_doc_styles()
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=30)
    story = [
        Paragraph("SYNTHETIC DEMONSTRATION DOCUMENT — NOT AN OFFICIAL CERTIFICATE", st["banner"]),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=2, spaceAfter=6),
        Paragraph("DEPARTMENT OF REGISTRATION AND STAMPS — GOVERNMENT OF MAHARASHTRA (SIMULATED)", st["subtitle"]),
        Paragraph("REGISTERED SALE DEED &amp; CONVEYANCE INDENTURE", st["title"]),
        Spacer(1, 6),
        Paragraph(
            f"This Indenture of Sale executed on this day by and between <b>{landowner}</b> (hereinafter called the 'VENDOR') "
            f"and <b>{trust_name}</b> for the sole educational use and benefit of <b>{institution_name}</b> (hereinafter called the 'PURCHASER').",
            st["body"]
        ),
        Spacer(1, 6),
        Paragraph("<b>1. PROPERTY PARTICULARS &amp; REGISTERED PARAMETERS</b>", st["heading"]),
        Spacer(1, 4),
    ]

    table_data = [
        [Paragraph("<b>Parameter / Clause</b>", st["cell_bold"]), Paragraph("<b>Registered Record Particulars</b>", st["cell_bold"])],
        [Paragraph("Document / Deed Number:", st["cell_bold"]), Paragraph(f"<b>Deed No:</b> {deed_number}", st["cell_text"])],
        [Paragraph("Registration Date:", st["cell_bold"]), Paragraph(f"<b>Date of Registration:</b> {registration_date}", st["cell_text"])],
        [Paragraph("Institution Beneficiary:", st["cell_bold"]), Paragraph(f"<b>Institution Name:</b> {institution_name}", st["cell_text"])],
        [Paragraph("Promoting Trust / Society:", st["cell_bold"]), Paragraph(f"<b>Trust Name:</b> {trust_name}", st["cell_text"])],
        [Paragraph("Survey / Khasra / Plot Number:", st["cell_bold"]), Paragraph(f"<b>Survey Number:</b> {survey_number}", st["cell_text"])],
        [Paragraph("Total Campus Land Area:", st["cell_bold"]), Paragraph(f"<b>Area:</b> {land_area_acres:.2f} Acres (Contiguous &amp; Demarcated)", st["cell_text"])],
        [Paragraph("Landowner / Executant:", st["cell_bold"]), Paragraph(f"<b>Landowner:</b> {landowner}", st["cell_text"])],
        [Paragraph("Consideration Paid &amp; Receipted:", st["cell_bold"]), Paragraph("INR 4,50,00,000 (Rupees Four Crores Fifty Lakhs Only)", st["cell_text"])],
        [Paragraph("Purpose &amp; Land Use Category:", st["cell_bold"]), Paragraph("Technical Higher Education Campus (AICTE Approved Programs)", st["cell_text"])],
    ]
    t = Table(table_data, colWidths=[180, 350])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>2. SCHEDULE OF BOUNDARIES</b>", st["heading"]))
    story.append(Spacer(1, 3))
    boundary_data = [
        [Paragraph("<b>North:</b> Survey Plot 42/1B (Institutional Zone)", st["cell_text"]), Paragraph("<b>South:</b> 24-Meter Wide Municipal Road", st["cell_text"])],
        [Paragraph("<b>East:</b> Green Belt Reserve Buffer Zone", st["cell_text"]), Paragraph("<b>West:</b> National Highway NH-48 Link Road", st["cell_text"])],
    ]
    tb = Table(boundary_data, colWidths=[265, 265])
    tb.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tb)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>3. POSSESSION &amp; ENCUMBRANCE CLAUSE</b>", st["heading"]))
    story.append(Paragraph(
        "The Vendor covenants that the said land is free from all encumbrances, liens, mortgages, charges, and statutory attachments. "
        "Vacant, physical, unencumbered possession is hereby handed over to the Purchaser for institutional operations in perpetuity.",
        st["body"]
    ))
    story.append(Spacer(1, 10))

    exec_data = [
        [Paragraph("____________________________<br/><b>Vendor / Landowner</b><br/>(Fictional Executant)", st["cell_bold"]),
         Paragraph("____________________________<br/><b>Authorized Purchaser</b><br/>For Apex Education Trust", st["cell_bold"]),
         Paragraph("<b>Sub-Registrar (Simulated)</b><br/>Office of Sub-Registrar Haveli-4<br/>Seal &amp; Registration Stamp", st["cell_bold"])]
    ]
    te = Table(exec_data, colWidths=[175, 175, 180])
    te.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(te)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=4, spaceAfter=4))
    story.append(Paragraph("FOR SOFTWARE TESTING ONLY — NO LEGAL VALIDITY", st["footer"]))

    doc.build(story)
    png_path = filepath.replace(".pdf", "_page_1.png")
    render_page_png(filepath, png_path)


def generate_building_plan(
    filepath: str,
    institution_name: str,
    sanction_no: str,
    built_up_area_sqm: float,
    sanction_date: str,
    survey_number: str = "Survey No. 42/1A"
):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    st = get_doc_styles()
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=30)
    story = [
        Paragraph("SYNTHETIC DEMONSTRATION DOCUMENT — NOT AN OFFICIAL CERTIFICATE", st["banner"]),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=2, spaceAfter=6),
        Paragraph("MUNICIPAL TOWN PLANNING &amp; INFRASTRUCTURE DEVELOPMENT AUTHORITY (SIMULATED)", st["subtitle"]),
        Paragraph("OFFICIAL BUILDING SANCTION ORDER &amp; APPROVED LAYOUT PLAN", st["title"]),
        Spacer(1, 6),
        Paragraph(
            f"Sanction is hereby accorded under Town Planning Act &amp; National Building Code 2016 for technical educational occupancy "
            f"at campus premises of <b>{institution_name}</b>.",
            st["body"]
        ),
        Spacer(1, 6),
        Paragraph("<b>1. SANCTION ORDER SPECIFICATIONS</b>", st["heading"]),
        Spacer(1, 4),
    ]

    table_data = [
        [Paragraph("<b>Approval Parameter</b>", st["cell_bold"]), Paragraph("<b>Municipal Sanction Details</b>", st["cell_bold"])],
        [Paragraph("Sanction Order Number:", st["cell_bold"]), Paragraph(f"<b>Sanction Order No:</b> {sanction_no}", st["cell_text"])],
        [Paragraph("Date of Approval / Sanction:", st["cell_bold"]), Paragraph(f"<b>Sanction Date:</b> {sanction_date}", st["cell_text"])],
        [Paragraph("Institution Occupant:", st["cell_bold"]), Paragraph(f"<b>Institution Name:</b> {institution_name}", st["cell_text"])],
        [Paragraph("Cadastral Plot / Survey Ref:", st["cell_bold"]), Paragraph(f"<b>Survey Number:</b> {survey_number}", st["cell_text"])],
        [Paragraph("Total Sanctioned Built-Up Area:", st["cell_bold"]), Paragraph(f"<b>Built-Up Area:</b> {built_up_area_sqm:.1f} sq.m", st["cell_text"])],
        [Paragraph("Occupancy Classification:", st["cell_bold"]), Paragraph("Group B Educational (Technical Institute Campus)", st["cell_text"])],
        [Paragraph("Structure Floor Height / Floors:", st["cell_bold"]), Paragraph("G + 2 Upper RCC Framed Earthquake Resistant Structure", st["cell_text"])],
    ]
    t = Table(table_data, colWidths=[180, 350])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>2. FLOOR DISTRIBUTION SCHEDULE &amp; CARPET RATIO</b>", st["heading"]))
    story.append(Spacer(1, 3))
    floor_data = [
        [Paragraph("<b>Level / Block</b>", st["cell_bold"]), Paragraph("<b>Program / Utilization</b>", st["cell_bold"]), Paragraph("<b>Built-Up Area</b>", st["cell_bold"])],
        [Paragraph("Ground Floor Level", st["cell_text"]), Paragraph("Admin Wing, Principal Cabin, Central Workshops &amp; Server Room", st["cell_text"]), Paragraph(f"{built_up_area_sqm*0.35:.1f} sq.m", st["cell_text"])],
        [Paragraph("First Floor Level", st["cell_text"]), Paragraph("Classrooms (12 units), Computer Labs (4 units) &amp; Staff Rooms", st["cell_text"]), Paragraph(f"{built_up_area_sqm*0.35:.1f} sq.m", st["cell_text"])],
        [Paragraph("Second Floor Level", st["cell_text"]), Paragraph("Central Library, Reading Hall, Seminar Hall &amp; Drawing Hall", st["cell_text"]), Paragraph(f"{built_up_area_sqm*0.30:.1f} sq.m", st["cell_text"])],
    ]
    tf = Table(floor_data, colWidths=[130, 270, 130])
    tf.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tf)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>3. STATUTORY SAFETY &amp; SETBACK COMPLIANCE</b>", st["heading"]))
    story.append(Paragraph(
        "Clear setbacks provided: Front 15.0m, Rear 9.0m, Sides 9.0m. Fire brigade access roads 6.0m clear paved. "
        "Compliant with AICTE Approval Process Handbook (APH) space norms and National Building Code 2016 Part IV.",
        st["body"]
    ))
    story.append(Spacer(1, 10))

    exec_data = [
        [Paragraph("____________________________<br/><b>Chief Municipal Town Planner</b><br/>Municipal Planning Authority", st["cell_bold"]),
         Paragraph("____________________________<br/><b>Registered Chartered Architect</b><br/>COA Reg. No. CA/2012/98421", st["cell_bold"]),
         Paragraph("<b>Municipal Sanction Seal</b><br/>Approved Under Order #5541<br/>Simulated Approval File", st["cell_bold"])]
    ]
    te = Table(exec_data, colWidths=[175, 175, 180])
    te.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(te)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=4, spaceAfter=4))
    story.append(Paragraph("FOR SOFTWARE TESTING ONLY — NO LEGAL VALIDITY", st["footer"]))

    doc.build(story)
    png_path = filepath.replace(".pdf", "_page_1.png")
    render_page_png(filepath, png_path)


def generate_fire_noc(
    filepath: str,
    institution_name: str,
    noc_number: str,
    issue_date: str,
    valid_until: str,
    address: str = "Sector 14, Plot 8, Navi Mumbai, Maharashtra - 400714"
):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    st = get_doc_styles()
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=30)
    story = [
        Paragraph("SYNTHETIC DEMONSTRATION DOCUMENT — NOT AN OFFICIAL CERTIFICATE", st["banner"]),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=2, spaceAfter=6),
        Paragraph("STATE DIRECTORATE OF FIRE SERVICES &amp; DISASTER MANAGEMENT (SIMULATED)", st["subtitle"]),
        Paragraph("FIRE SAFETY CLEARANCE / NO OBJECTION CERTIFICATE (NOC)", st["title"]),
        Spacer(1, 6),
        Paragraph(
            f"This Fire Safety Certificate is issued to <b>{institution_name}</b> situated at <b>{address}</b> "
            f"following satisfactory on-site inspection of active firefighting installations and passive life safety features.",
            st["body"]
        ),
        Spacer(1, 6),
        Paragraph("<b>1. CERTIFICATE PARTICULARS &amp; VALIDITY SCHEDULE</b>", st["heading"]),
        Spacer(1, 4),
    ]

    table_data = [
        [Paragraph("<b>Certification Clause</b>", st["cell_bold"]), Paragraph("<b>Fire Safety Particulars</b>", st["cell_bold"])],
        [Paragraph("NOC Reference Number:", st["cell_bold"]), Paragraph(f"<b>NOC Number:</b> {noc_number}", st["cell_text"])],
        [Paragraph("Institution Name &amp; Campus:", st["cell_bold"]), Paragraph(f"<b>Institution Name:</b> {institution_name}", st["cell_text"])],
        [Paragraph("Date of Issuance:", st["cell_bold"]), Paragraph(f"<b>Issue Date:</b> {issue_date}", st["cell_text"])],
        [Paragraph("Valid Until / Expiry Date:", st["cell_bold"]), Paragraph(f"<b>Valid Until:</b> {valid_until}", st["cell_text"])],
        [Paragraph("Hazard Classification:", st["cell_bold"]), Paragraph("Group B Educational (Low Hazard Occupancy)", st["cell_text"])],
        [Paragraph("Underground Static Water Tank:", st["cell_bold"]), Paragraph("1,50,000 Litres Dedicated Fire Reserve + 25,000L Overhead Tank", st["cell_text"])],
        [Paragraph("Emergency Evacuation Stairways:", st["cell_bold"]), Paragraph("2 Separate Enclosed Fire Escape Staircases (Width 2.0m each)", st["cell_text"])],
    ]
    t = Table(table_data, colWidths=[180, 350])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>2. INSPECTION FINDINGS &amp; SAFETY CONDITIONS</b>", st["heading"]))
    story.append(Paragraph(
        "1. Automatic fire sprinkler system in high-hazard electrical and chemical storage labs is functional.<br/>"
        "2. Fire hose reel systems, yard hydrants, and manual call points are tested at 7.0 bar operating pressure.<br/>"
        "3. Illuminated emergency exit signages and battery-backed emergency lighting operational on all stairwells.<br/>"
        "4. This certificate is valid subject to periodic bi-annual mock drill execution and maintenance log submission.",
        st["body"]
    ))
    story.append(Spacer(1, 10))

    exec_data = [
        [Paragraph("____________________________<br/><b>Divisional Fire Officer</b><br/>Fire Prevention Wing (Simulated)", st["cell_bold"]),
         Paragraph("____________________________<br/><b>Chief Fire Officer</b><br/>Directorate of Fire Services", st["cell_bold"]),
         Paragraph("<b>Directorate Fire Stamp</b><br/>NOC Reference Verified<br/>Simulated Authority Record", st["cell_bold"])]
    ]
    te = Table(exec_data, colWidths=[175, 175, 180])
    te.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(te)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=4, spaceAfter=4))
    story.append(Paragraph("FOR SOFTWARE TESTING ONLY — NO LEGAL VALIDITY", st["footer"]))

    doc.build(story)
    png_path = filepath.replace(".pdf", "_page_1.png")
    render_page_png(filepath, png_path)


def generate_society_reg(
    filepath: str,
    institution_name: str,
    trust_name: str,
    registration_no: str,
    registration_date: str,
    registered_office: str = "Plot 8, Sector 14, Navi Mumbai, Maharashtra - 400714"
):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    st = get_doc_styles()
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=30)
    story = [
        Paragraph("SYNTHETIC DEMONSTRATION DOCUMENT — NOT AN OFFICIAL CERTIFICATE", st["banner"]),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=2, spaceAfter=6),
        Paragraph("OFFICE OF THE CHARITY COMMISSIONER &amp; REGISTRAR OF SOCIETIES (SIMULATED)", st["subtitle"]),
        Paragraph("CERTIFICATE OF REGISTRATION OF PUBLIC CHARITABLE TRUST / SOCIETY", st["title"]),
        Spacer(1, 6),
        Paragraph(
            f"It is hereby certified that <b>{trust_name}</b>, sponsoring body of <b>{institution_name}</b>, "
            f"has been registered under the Societies Registration Act, XXI of 1860 and Bombay Public Trusts Act, 1950.",
            st["body"]
        ),
        Spacer(1, 6),
        Paragraph("<b>1. REGISTRATION PARTICULARS</b>", st["heading"]),
        Spacer(1, 4),
    ]

    table_data = [
        [Paragraph("<b>Registration Parameter</b>", st["cell_bold"]), Paragraph("<b>Statutory Record Particulars</b>", st["cell_bold"])],
        [Paragraph("Registration Number:", st["cell_bold"]), Paragraph(f"<b>Registration No:</b> {registration_no}", st["cell_text"])],
        [Paragraph("Date of Registration:", st["cell_bold"]), Paragraph(f"<b>Registration Date:</b> {registration_date}", st["cell_text"])],
        [Paragraph("Name of Registered Entity:", st["cell_bold"]), Paragraph(f"<b>Trust Name:</b> {trust_name}", st["cell_text"])],
        [Paragraph("Supported Technical College:", st["cell_bold"]), Paragraph(f"<b>Institution Name:</b> {institution_name}", st["cell_text"])],
        [Paragraph("Registered Head Office:", st["cell_bold"]), Paragraph(registered_office, st["cell_text"])],
        [Paragraph("Aims and Objects:", st["cell_bold"]), Paragraph("Establishment and operation of non-profit technical educational institutions", st["cell_text"])],
        [Paragraph("Legal Character:", st["cell_bold"]), Paragraph("Non-Government Public Charitable Trust with Pan-India jurisdiction", st["cell_text"])],
    ]
    t = Table(table_data, colWidths=[180, 350])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>2. LIST OF FOUNDING TRUSTEES / GOVERNING BODY</b>", st["heading"]))
    trustee_data = [
        [Paragraph("<b>Name of Trustee</b>", st["cell_bold"]), Paragraph("<b>Designation</b>", st["cell_bold"]), Paragraph("<b>Occupation</b>", st["cell_bold"])],
        [Paragraph("Dr. S. K. Sharma", st["cell_text"]), Paragraph("President &amp; Managing Trustee", st["cell_text"]), Paragraph("Educationist / Academician", st["cell_text"])],
        [Paragraph("Smt. Sunita Sharma", st["cell_text"]), Paragraph("Secretary", st["cell_text"]), Paragraph("Social Worker", st["cell_text"])],
        [Paragraph("Shri R. N. Deshmukh", st["cell_text"]), Paragraph("Treasurer", st["cell_text"]), Paragraph("Chartered Accountant", st["cell_text"])],
    ]
    tt = Table(trustee_data, colWidths=[180, 180, 170])
    tt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tt)
    story.append(Spacer(1, 10))

    exec_data = [
        [Paragraph("____________________________<br/><b>Superintendent of Registration</b><br/>Charity Commissioner's Office", st["cell_bold"]),
         Paragraph("____________________________<br/><b>Assistant Charity Commissioner</b><br/>Division Region (Simulated)", st["cell_bold"]),
         Paragraph("<b>Registrar Official Seal</b><br/>Registration Certificate Active<br/>Simulated Statutory Record", st["cell_bold"])]
    ]
    te = Table(exec_data, colWidths=[175, 175, 180])
    te.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(te)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=4, spaceAfter=4))
    story.append(Paragraph("FOR SOFTWARE TESTING ONLY — NO LEGAL VALIDITY", st["footer"]))

    doc.build(story)
    png_path = filepath.replace(".pdf", "_page_1.png")
    render_page_png(filepath, png_path)


def generate_affidavit(
    filepath: str,
    institution_name: str,
    trust_name: str,
    deponent_name: str = "Dr. S. K. Sharma",
    stamp_value_inr: int = 100,
    execution_date: str = "15-01-2025"
):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    st = get_doc_styles()
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=30)
    story = [
        Paragraph("SYNTHETIC DEMONSTRATION DOCUMENT — NOT AN OFFICIAL CERTIFICATE", st["banner"]),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=2, spaceAfter=6),
        Paragraph("BEFORE THE HON'BLE NOTARY PUBLIC (SIMULATED)", st["subtitle"]),
        Paragraph("STATUTORY COMPLIANCE AFFIDAVIT (AICTE PRESCRIBED FORMAT 1)", st["title"]),
        Paragraph(f"<b>NON-JUDICIAL STAMP VALUE: RS. {stamp_value_inr}/- ONLY</b>", st["subtitle"]),
        Paragraph(f"<b>Deponent Name:</b> {deponent_name} &bull; <b>Institution:</b> {institution_name}", st["subtitle"]),
        Spacer(1, 6),
        Paragraph(
            f"I, <b>{deponent_name}</b>, Deponent, Son of Late Sh. M. P. Sharma, aged 56 years, residing at Mumbai, "
            f"in my capacity as President of <b>{trust_name}</b> and authorized representative of <b>{institution_name}</b>, "
            f"do hereby solemnly affirm and declare on oath as under:",
            st["body"]
        ),
        Spacer(1, 6),
        Paragraph(
            "1. That the applicant trust possesses clear, unencumbered, and undisputed title and possession to the designated campus land.<br/>"
            "2. That the building infrastructure, laboratory equipment, library volumes, and computing facilities conform strictly to AICTE Approval Process Handbook norms.<br/>"
            "3. That the faculty appointments and student enrollment cadre ratios are maintained without deficit.<br/>"
            "4. That all statutory approvals, including Fire Safety NOC, Sanctioned Building Plan, and Society Registration are valid and currently in force.<br/>"
            "5. That no commercial, political, or unauthorized activity shall be conducted on the institutional campus premises.",
            st["body"]
        ),
        Spacer(1, 6),
        Paragraph("<b>VERIFICATION &amp; ATTESTATION</b>", st["heading"]),
        Paragraph(
            f"Verified at Pune on this <b>Execution Date: {execution_date}</b> that the contents of paragraphs 1 to 5 are true to my personal knowledge, "
            "no material fact has been concealed, and no part thereof is false.",
            st["body"]
        ),
        Spacer(1, 10),
    ]

    exec_data = [
        [Paragraph(f"____________________________<br/><b>{deponent_name}</b><br/>Deponent / Authorized Signatory", st["cell_bold"]),
         Paragraph("<b>Solemnly Affirmed Before Me</b><br/>Advocate M. R. Kulkarni<br/>Notary Public, Gov. of Maharashtra", st["cell_bold"]),
         Paragraph("<b>Notary Seal &amp; Stamp</b><br/>Reg. Notary No: NOT-2018-441<br/>Simulated Stamp", st["cell_bold"])]
    ]
    te = Table(exec_data, colWidths=[175, 175, 180])
    te.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(te)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=4, spaceAfter=4))
    story.append(Paragraph("FOR SOFTWARE TESTING ONLY — NO LEGAL VALIDITY", st["footer"]))

    doc.build(story)
    png_path = filepath.replace(".pdf", "_page_1.png")
    render_page_png(filepath, png_path)


def generate_env_clearance(
    filepath: str,
    institution_name: str,
    reference_no: str,
    issue_date: str,
    valid_until: str
):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    st = get_doc_styles()
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=30)
    story = [
        Paragraph("SYNTHETIC DEMONSTRATION DOCUMENT — NOT AN OFFICIAL CERTIFICATE", st["banner"]),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=2, spaceAfter=6),
        Paragraph("STATE POLLUTION CONTROL BOARD — ENVIRONMENTAL CLEARANCE DIVISION (SIMULATED)", st["subtitle"]),
        Paragraph("CONSENT TO OPERATE &amp; ENVIRONMENTAL CLEARANCE ORDER", st["title"]),
        Spacer(1, 6),
        Paragraph(
            f"Consent is hereby granted under Section 25 of the Water Act 1974 &amp; Section 21 of the Air Act 1981 to <b>{institution_name}</b>.",
            st["body"]
        ),
        Spacer(1, 6),
    ]

    table_data = [
        [Paragraph("<b>Consent Parameter</b>", st["cell_bold"]), Paragraph("<b>Statutory Particulars</b>", st["cell_bold"])],
        [Paragraph("Consent Order Number:", st["cell_bold"]), Paragraph(f"<b>Reference No:</b> {reference_no}", st["cell_text"])],
        [Paragraph("Institution Name:", st["cell_bold"]), Paragraph(f"<b>Institution Name:</b> {institution_name}", st["cell_text"])],
        [Paragraph("Date of Consent:", st["cell_bold"]), Paragraph(f"<b>Issue Date:</b> {issue_date}", st["cell_text"])],
        [Paragraph("Valid Until Date:", st["cell_bold"]), Paragraph(f"<b>Valid Until:</b> {valid_until}", st["cell_text"])],
        [Paragraph("Effluent Treatment Plant (ETP):", st["cell_bold"]), Paragraph("50 KLD Sewage Treatment Plant installed and operational", st["cell_text"])],
    ]
    t = Table(table_data, colWidths=[180, 350])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    exec_data = [
        [Paragraph("____________________________<br/><b>Member Secretary</b><br/>Pollution Control Board", st["cell_bold"]),
         Paragraph("<b>Environmental Board Stamp</b><br/>Consent Active<br/>Simulated Authority Record", st["cell_bold"])]
    ]
    te = Table(exec_data, colWidths=[265, 265])
    te.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(te)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#b91c1c"), spaceBefore=4, spaceAfter=4))
    story.append(Paragraph("FOR SOFTWARE TESTING ONLY — NO LEGAL VALIDITY", st["footer"]))

    doc.build(story)
    png_path = filepath.replace(".pdf", "_page_1.png")
    render_page_png(filepath, png_path)


def generate_tampered_fixture(filepath: str):
    """
    Creates a controlled test image fixture with a documented, reproducible digital image modification
    for exercising the forensic ELA and copy-move pipelines.
    Prominently labelled as synthetic.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    base = Image.new("RGB", (800, 600), color=(250, 252, 255))
    draw = ImageDraw.Draw(base)

    # Outer border & header banner
    draw.rectangle([40, 40, 760, 560], outline=(15, 23, 42), width=2)
    draw.text((60, 55), "SYNTHETIC DEMONSTRATION DOCUMENT — NOT AN OFFICIAL CERTIFICATE", fill=(185, 28, 28))
    draw.text((60, 85), "REVENUE RECORD & LAND POSSESSION CERTIFICATE (FICTIONAL TEST FIXTURE)", fill=(15, 23, 42))
    draw.text((60, 130), "Institution: Solaris Institute of Technology", fill=(15, 23, 42))
    draw.text((60, 160), "Survey Plot No: 88/B | Registered Land Area: 2.50 Acres", fill=(15, 23, 42))
    draw.text((60, 200), "Registered Executant: Apex Education Trust", fill=(15, 23, 42))

    # Base stamp shape
    draw.ellipse([580, 400, 720, 540], outline=(20, 50, 120), width=3)
    draw.text((600, 460), "OFFICIAL SEAL", fill=(20, 50, 120))
    draw.text((60, 535), "FOR SOFTWARE TESTING ONLY — NO LEGAL VALIDITY", fill=(185, 28, 28))

    # Save initial base image with heavy initial compression (quality 60)
    temp_base = filepath + ".base.jpg"
    base.save(temp_base, "JPEG", quality=60)

    # Read base image back via OpenCV
    base_img = cv2.imread(temp_base)

    # Create spliced text patch with fresh high-contrast text and high-frequency noise
    # (Altering '2.50 Acres' to '5.50 Acres (TAMPERED)')
    patch = np.full((40, 280, 3), 250, dtype=np.uint8)
    cv2.putText(patch, "5.50 Acres (SPLICED FIXTURE)", (5, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 190), 2)
    noise = np.random.normal(0, 14, patch.shape).astype(np.uint8)
    patch = cv2.add(patch, noise)

    # Splice patch into the image
    base_img[150:190, 310:590] = patch

    # Also clone the official seal to top right to exercise copy-move detection
    seal_patch = base_img[400:540, 580:720].copy()
    base_img[220:360, 580:720] = seal_patch

    # Save final modified JPEG
    cv2.imwrite(filepath, base_img)

    if os.path.exists(temp_base):
        os.remove(temp_base)
    print(f"Created Controlled Tampered Fixture: {filepath}")

# -------------------------------------------------------------------------
# GENERATE ALL SYNTHETIC SCENARIO FILES
# -------------------------------------------------------------------------

def generate_all_scenario_files() -> Path:
    base_dir = Path(__file__).resolve().parent.parent.parent / "sample_data"
    os.makedirs(base_dir, exist_ok=True)

    # =========================================================================
    # SCENARIO A: Pristine Complete Application (Apex Institute of Technology)
    # =========================================================================
    scen_a = base_dir / "scenario_A_pristine"
    generate_land_deed(
        str(scen_a / "title_deed.pdf"),
        institution_name="Apex Institute of Technology",
        trust_name="Apex Education Trust",
        deed_number="DEED/PUN/2018/8892",
        survey_number="Survey No. 42/1A",
        land_area_acres=3.5,
        registration_date="12-05-2018"
    )
    generate_building_plan(
        str(scen_a / "building_plan.pdf"),
        institution_name="Apex Institute of Technology",
        sanction_no="SAN/PUN/2020/5541",
        built_up_area_sqm=4500.0,
        sanction_date="18-02-2020",
        survey_number="Survey No. 42/1A"
    )
    generate_fire_noc(
        str(scen_a / "fire_noc.pdf"),
        institution_name="Apex Institute of Technology",
        noc_number="FS-NOC-7821",
        issue_date="01-01-2024",
        valid_until="31-12-2027"
    )
    generate_society_reg(
        str(scen_a / "society_registration.pdf"),
        institution_name="Apex Institute of Technology",
        trust_name="Apex Education Trust",
        registration_no="SOC-REG-2015-88",
        registration_date="10-01-2015"
    )
    generate_affidavit(
        str(scen_a / "affidavit.pdf"),
        institution_name="Apex Institute of Technology",
        trust_name="Apex Education Trust",
        deponent_name="Dr. S. K. Sharma",
        stamp_value_inr=100,
        execution_date="15-01-2025"
    )
    generate_env_clearance(
        str(scen_a / "env_clearance.pdf"),
        institution_name="Apex Institute of Technology",
        reference_no="PCB-ENV-2024-912",
        issue_date="01-03-2024",
        valid_until="28-02-2029"
    )

    # =========================================================================
    # SCENARIO B: Missing Mandatory Document (Bharati Technical Campus)
    # Deliberately omits Fire NOC
    # =========================================================================
    scen_b = base_dir / "scenario_B_missing_doc"
    generate_land_deed(
        str(scen_b / "title_deed.pdf"),
        institution_name="Bharati Technical Campus",
        trust_name="Zenith Foundation",
        deed_number="DEED/BLR/2019/1102",
        survey_number="Survey No. 12/4B",
        land_area_acres=3.0,
        registration_date="14-06-2019"
    )
    generate_building_plan(
        str(scen_b / "building_plan.pdf"),
        institution_name="Bharati Technical Campus",
        sanction_no="SAN/BLR/2021/1102",
        built_up_area_sqm=4200.0,
        sanction_date="10-04-2021",
        survey_number="Survey No. 12/4B"
    )
    generate_society_reg(
        str(scen_b / "society_registration.pdf"),
        institution_name="Bharati Technical Campus",
        trust_name="Zenith Foundation",
        registration_no="SOC-REG-2016-12",
        registration_date="15-03-2016"
    )
    generate_affidavit(
        str(scen_b / "affidavit.pdf"),
        institution_name="Bharati Technical Campus",
        trust_name="Zenith Foundation",
        deponent_name="Prof. R. V. Patel",
        stamp_value_inr=100,
        execution_date="20-01-2025"
    )

    # =========================================================================
    # SCENARIO C: Expired Fire NOC (Zenith Polytechnic)
    # Fire NOC valid_until 15-01-2023 is lapsed
    # =========================================================================
    scen_c = base_dir / "scenario_C_expired_noc"
    generate_land_deed(
        str(scen_c / "title_deed.pdf"),
        institution_name="Zenith Polytechnic",
        trust_name="Zenith Foundation",
        deed_number="DEED/BPL/2017/5521",
        survey_number="Survey No. 55/2A",
        land_area_acres=3.0,
        registration_date="11-08-2017"
    )
    generate_building_plan(
        str(scen_c / "building_plan.pdf"),
        institution_name="Zenith Polytechnic",
        sanction_no="SAN/BPL/2019/2201",
        built_up_area_sqm=4100.0,
        sanction_date="12-09-2019",
        survey_number="Survey No. 55/2A"
    )
    generate_fire_noc(
        str(scen_c / "fire_noc_expired.pdf"),
        institution_name="Zenith Polytechnic",
        noc_number="FS-NOC-3310",
        issue_date="15-01-2020",
        valid_until="15-01-2023"  # Intentionally lapsed
    )
    generate_society_reg(
        str(scen_c / "society_registration.pdf"),
        institution_name="Zenith Polytechnic",
        trust_name="Zenith Foundation",
        registration_no="SOC-REG-2016-12",
        registration_date="15-03-2016"
    )
    generate_affidavit(
        str(scen_c / "affidavit.pdf"),
        institution_name="Zenith Polytechnic",
        trust_name="Zenith Foundation",
        deponent_name="Dr. M. K. Rao",
        stamp_value_inr=100,
        execution_date="18-01-2025"
    )

    # =========================================================================
    # SCENARIO D: Cross-Document Land Area Mismatch (Zenith Polytechnic College)
    # Declared 4.5 acres vs Deed 2.2 acres
    # =========================================================================
    scen_d = base_dir / "scenario_D_area_mismatch"
    generate_land_deed(
        str(scen_d / "title_deed_mismatch.pdf"),
        institution_name="Zenith Polytechnic College",
        trust_name="Apex Education Trust",
        deed_number="DEED/LKO/2020/8911",
        survey_number="Survey No. 89/1C",
        land_area_acres=2.2,  # Intentionally 2.2 Acres (declared is 4.5 Acres)
        registration_date="20-03-2020"
    )
    generate_building_plan(
        str(scen_d / "building_plan.pdf"),
        institution_name="Zenith Polytechnic College",
        sanction_no="SAN/LKO/2021/3311",
        built_up_area_sqm=4200.0,
        sanction_date="15-05-2021",
        survey_number="Survey No. 89/1C"
    )
    generate_fire_noc(
        str(scen_d / "fire_noc.pdf"),
        institution_name="Zenith Polytechnic College",
        noc_number="FS-NOC-4421",
        issue_date="01-02-2024",
        valid_until="31-12-2028"
    )
    generate_society_reg(
        str(scen_d / "society_registration.pdf"),
        institution_name="Zenith Polytechnic College",
        trust_name="Apex Education Trust",
        registration_no="SOC-REG-2015-88",
        registration_date="10-01-2015"
    )
    generate_affidavit(
        str(scen_d / "affidavit.pdf"),
        institution_name="Zenith Polytechnic College",
        trust_name="Apex Education Trust",
        deponent_name="Dr. A. P. Verma",
        stamp_value_inr=100,
        execution_date="15-01-2025"
    )

    # =========================================================================
    # SCENARIO E: Intentional Cross-Institution Duplicate Document (Zenith Satellite Campus)
    # Exact byte duplicate of Scenario A title_deed.pdf
    # =========================================================================
    scen_e = base_dir / "scenario_E_duplicate"
    os.makedirs(scen_e, exist_ok=True)
    with open(str(scen_a / "title_deed.pdf"), "rb") as f_src:
        with open(str(scen_e / "duplicate_title_deed.pdf"), "wb") as f_dst:
            f_dst.write(f_src.read())
    render_page_png(str(scen_e / "duplicate_title_deed.pdf"), str(scen_e / "duplicate_title_deed_page_1.png"))

    generate_building_plan(
        str(scen_e / "building_plan.pdf"),
        institution_name="Zenith Satellite Campus",
        sanction_no="SAN/JPR/2021/4412",
        built_up_area_sqm=4200.0,
        sanction_date="10-06-2021",
        survey_number="Survey No. 42/1A"
    )
    generate_fire_noc(
        str(scen_e / "fire_noc.pdf"),
        institution_name="Zenith Satellite Campus",
        noc_number="FS-NOC-5531",
        issue_date="01-02-2024",
        valid_until="31-12-2028"
    )
    generate_society_reg(
        str(scen_e / "society_registration.pdf"),
        institution_name="Zenith Satellite Campus",
        trust_name="Zenith Foundation",
        registration_no="SOC-REG-2016-12",
        registration_date="15-03-2016"
    )
    generate_affidavit(
        str(scen_e / "affidavit.pdf"),
        institution_name="Zenith Satellite Campus",
        trust_name="Zenith Foundation",
        deponent_name="Prof. N. K. Joshi",
        stamp_value_inr=100,
        execution_date="22-01-2025"
    )

    # =========================================================================
    # SCENARIO F: Controlled Suspicious Document (Solaris Institute of Technology)
    # Image forensic ELA anomaly and copy-move feature cluster
    # =========================================================================
    scen_f = base_dir / "scenario_F_tampered"
    generate_tampered_fixture(str(scen_f / "tampered_land_record.jpg"))
    generate_building_plan(
        str(scen_f / "building_plan.pdf"),
        institution_name="Solaris Institute of Technology",
        sanction_no="SAN/NGP/2021/5511",
        built_up_area_sqm=4000.0,
        sanction_date="12-07-2021",
        survey_number="Plot 88/B"
    )
    generate_fire_noc(
        str(scen_f / "fire_noc.pdf"),
        institution_name="Solaris Institute of Technology",
        noc_number="FS-NOC-6641",
        issue_date="01-02-2024",
        valid_until="31-12-2028"
    )
    generate_society_reg(
        str(scen_f / "society_registration.pdf"),
        institution_name="Solaris Institute of Technology",
        trust_name="Apex Education Trust",
        registration_no="SOC-REG-2015-88",
        registration_date="10-01-2015"
    )
    generate_affidavit(
        str(scen_f / "affidavit.pdf"),
        institution_name="Solaris Institute of Technology",
        trust_name="Apex Education Trust",
        deponent_name="Dr. Vikram Deshmukh",
        stamp_value_inr=100,
        execution_date="15-01-2025"
    )

    print(f"\n[FILES] All synthetic scenario PDF and PNG fixtures successfully generated at: {base_dir}")
    return base_dir

# -------------------------------------------------------------------------
# IDEMPOTENT DATABASE SEEDING
# -------------------------------------------------------------------------

def get_mime_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "application/pdf"
    elif ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    return "application/octet-stream"

def seed_synthetic_scenarios(db: Optional[Session] = None):
    owns_db = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        owns_db = True

    try:
        # Step 1: Generate all files
        base_sample_dir = generate_all_scenario_files()

        # Step 2: Ensure core institutions and users exist
        inst_apex = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-1001").first()
        inst_zenith = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-1002").first()

        if not inst_apex or not inst_zenith:
            print("[INFO] Core institutions missing. Running base seed...")
            from backend.scripts.seed_db import seed_database
            seed_database(db_session=db)
            inst_apex = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-1001").first()
            inst_zenith = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-1002").first()

        storage_dir = Path(settings.STORAGE_DIR)
        storage_dir.mkdir(parents=True, exist_ok=True)

        scenarios_config = [
            {
                "key": "Scenario A — Complete",
                "app_no": "APP-2025-SCEN-A",
                "institution_id": inst_apex.id,
                "folder": "scenario_A_pristine",
                "declared_details": {
                    "institution_name": "Apex Institute of Technology",
                    "trust_name": "Apex Education Trust",
                    "survey_no": "Survey No. 42/1A",
                    "land_area_acres": 3.5,
                    "built_up_area_sqm": 4500.0,
                    "program": "Engineering",
                    "faculty_count": 60,
                    "student_enrollment": 300,
                },
                "documents": [
                    {"filename": "title_deed.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                    {"filename": "env_clearance.pdf", "doc_type": "env_clearance"},
                ]
            },
            {
                "key": "Scenario B — Missing Documents",
                "app_no": "APP-2025-SCEN-B",
                "institution_id": inst_zenith.id,
                "folder": "scenario_B_missing_doc",
                "declared_details": {
                    "institution_name": "Bharati Technical Campus",
                    "trust_name": "Zenith Foundation",
                    "survey_no": "Survey No. 12/4B",
                    "land_area_acres": 3.0,
                    "built_up_area_sqm": 4200.0,
                    "program": "Engineering",
                    "faculty_count": 50,
                    "student_enrollment": 240,
                },
                "documents": [
                    {"filename": "title_deed.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                    # Fire NOC intentionally omitted
                ]
            },
            {
                "key": "Scenario C — Expired Certificate",
                "app_no": "APP-2025-SCEN-C",
                "institution_id": inst_zenith.id,
                "folder": "scenario_C_expired_noc",
                "declared_details": {
                    "institution_name": "Zenith Polytechnic",
                    "trust_name": "Zenith Foundation",
                    "survey_no": "Survey No. 55/2A",
                    "land_area_acres": 3.0,
                    "built_up_area_sqm": 4100.0,
                    "program": "Engineering",
                    "faculty_count": 45,
                    "student_enrollment": 200,
                },
                "documents": [
                    {"filename": "title_deed.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc_expired.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                ]
            },
            {
                "key": "Scenario D — Land Area Mismatch",
                "app_no": "APP-2025-SCEN-D",
                "institution_id": inst_apex.id,
                "folder": "scenario_D_area_mismatch",
                "declared_details": {
                    "institution_name": "Zenith Polytechnic College",
                    "trust_name": "Apex Education Trust",
                    "survey_no": "Survey No. 89/1C",
                    "land_area_acres": 4.5,  # Declared 4.5 vs Deed 2.2
                    "built_up_area_sqm": 4200.0,
                    "program": "Engineering",
                    "faculty_count": 55,
                    "student_enrollment": 250,
                },
                "documents": [
                    {"filename": "title_deed_mismatch.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                ]
            },
            {
                "key": "Scenario E — Duplicate Document",
                "app_no": "APP-2025-SCEN-E",
                "institution_id": inst_zenith.id,
                "folder": "scenario_E_duplicate",
                "declared_details": {
                    "institution_name": "Zenith Satellite Campus",
                    "trust_name": "Zenith Foundation",
                    "survey_no": "Survey No. 42/1A",
                    "land_area_acres": 3.5,
                    "built_up_area_sqm": 4200.0,
                    "program": "Engineering",
                    "faculty_count": 50,
                    "student_enrollment": 240,
                },
                "documents": [
                    {"filename": "duplicate_title_deed.pdf", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                ]
            },
            {
                "key": "Scenario F — Suspicious Document",
                "app_no": "APP-2025-SCEN-F",
                "institution_id": inst_apex.id,
                "folder": "scenario_F_tampered",
                "declared_details": {
                    "institution_name": "Solaris Institute of Technology",
                    "trust_name": "Apex Education Trust",
                    "survey_no": "Plot 88/B",
                    "land_area_acres": 5.5,
                    "built_up_area_sqm": 4000.0,
                    "program": "Engineering",
                    "faculty_count": 50,
                    "student_enrollment": 200,
                },
                "documents": [
                    {"filename": "tampered_land_record.jpg", "doc_type": "land_document"},
                    {"filename": "building_plan.pdf", "doc_type": "building_plan"},
                    {"filename": "fire_noc.pdf", "doc_type": "fire_noc"},
                    {"filename": "society_registration.pdf", "doc_type": "society_registration"},
                    {"filename": "affidavit.pdf", "doc_type": "affidavit"},
                ]
            },
        ]

        summary_results = []

        for sc in scenarios_config:
            app_no = sc["app_no"]
            app = db.query(Application).filter(Application.application_no == app_no).first()

            if not app:
                app = Application(
                    application_no=app_no,
                    institution_id=sc["institution_id"],
                    type="New Technical Institution",
                    academic_year="2025-2026",
                    status="under_verification",
                    risk_score=0.0,
                    risk_band="Low",
                    risk_breakdown={},
                    declared_details=sc["declared_details"],
                )
                db.add(app)
                db.commit()
                db.refresh(app)
                print(f"[SEED] Created application {app_no} (ID: {app.id})")
            else:
                app.declared_details = sc["declared_details"]
                db.commit()

            # Clean stale flags for this application before reprocessing
            db.query(Flag).filter(Flag.application_id == app.id).delete()
            db.commit()

            created_or_updated_doc_ids = []
            for doc_spec in sc["documents"]:
                src_path = base_sample_dir / sc["folder"] / doc_spec["filename"]
                if not src_path.exists():
                    print(f"  [WARN] File not found: {src_path}")
                    continue

                existing_doc = db.query(Document).filter(
                    Document.application_id == app.id,
                    Document.doc_type == doc_spec["doc_type"],
                    Document.superseded_by.is_(None)
                ).first()

                with open(src_path, "rb") as f:
                    file_bytes = f.read()
                    sha256 = hashlib.sha256(file_bytes).hexdigest()

                mime_type = get_mime_type(src_path.name)

                if existing_doc:
                    # Update file content on disk and refresh hashes
                    dest_path = Path(existing_doc.stored_path)
                    if not dest_path.is_absolute():
                        dest_path = (Path(settings.STORAGE_DIR) / dest_path.name).resolve()
                    shutil.copy2(src_path, dest_path)
                    existing_doc.stored_path = str(dest_path)
                    existing_doc.original_filename = doc_spec["filename"]
                    existing_doc.mime_type = mime_type
                    existing_doc.size = len(file_bytes)
                    existing_doc.sha256 = sha256
                    existing_doc.phash = compute_phash_for_file(str(dest_path), mime_type)
                    db.commit()
                    created_or_updated_doc_ids.append(existing_doc.id)
                else:
                    file_ext = src_path.suffix.lower()
                    target_filename = f"{uuid.uuid4().hex}{file_ext}"
                    dest_path = storage_dir / target_filename
                    shutil.copy2(src_path, dest_path)

                    phash = compute_phash_for_file(str(dest_path), mime_type)
                    page_count = 1
                    if "pdf" in mime_type:
                        try:
                            pdf_doc = fitz.open(str(dest_path))
                            page_count = len(pdf_doc)
                            pdf_doc.close()
                        except Exception:
                            page_count = 1

                    doc = Document(
                        application_id=app.id,
                        doc_type=doc_spec["doc_type"],
                        original_filename=doc_spec["filename"],
                        stored_path=str(dest_path),
                        mime_type=mime_type,
                        size=len(file_bytes),
                        sha256=sha256,
                        phash=phash,
                        page_count=page_count,
                        processing_status="queued",
                        processing_stage="Queued",
                        validation_status="valid"
                    )
                    db.add(doc)
                    db.commit()
                    db.refresh(doc)
                    created_or_updated_doc_ids.append(doc.id)
                    print(f"  [SEED] Ingested document: {doc_spec['filename']} -> Doc ID {doc.id}")

            # Process pipeline for each document synchronously
            for doc_id in created_or_updated_doc_ids:
                process_document_pipeline(doc_id)

            db.refresh(app)

            # Run document validation and cross-document consistency checks
            sync_validation_and_consistency(app.id, db)

            # Run simulated authority verifications
            docs = db.query(Document).filter(
                Document.application_id == app.id,
                Document.superseded_by.is_(None)
            ).all()

            for d in docs:
                db.query(VerificationResult).filter(VerificationResult.document_id == d.id).delete()
                extracted = d.extracted_data or {}
                ref_no = (
                    extracted.get("reference_no") or
                    extracted.get("sanction_no") or
                    extracted.get("noc_number") or
                    extracted.get("registration_no") or
                    extracted.get("order_no")
                )
                outcome = verify_document(doc_type=d.doc_type, reference_no=ref_no, document_context=extracted)
                v_res = VerificationResult(
                    document_id=d.id,
                    authority=outcome.authority,
                    adapter_name=outcome.adapter_name,
                    reference_no=outcome.reference_no,
                    status=outcome.status,
                    is_simulated=True,
                    raw_response=outcome.raw_response,
                    message=outcome.message
                )
                db.add(v_res)
            db.commit()

            # Run compliance engine
            ComplianceEngine(db).evaluate_application(app.id)

            # Run risk scoring engine
            risk_info = RiskEngine(db).calculate_application_risk(app.id)

            if risk_info["score"] >= 25 or risk_info["critical_flags_count"] > 0:
                app.status = "needs_review"
            else:
                app.status = "under_verification"
            db.commit()

            total_flags = risk_info.get("critical_flags_count", 0) + risk_info.get("warning_flags_count", 0) + risk_info.get("info_flags_count", 0)
            summary_results.append({
                "scenario": sc["key"],
                "app_no": app_no,
                "app_id": app.id,
                "risk_score": risk_info["score"],
                "risk_band": risk_info["band"],
                "status": app.status,
                "open_flags": total_flags
            })
            print(f"  [SEEDED] {sc['key']} ({app_no}): Risk {risk_info['score']}/100 ({risk_info['band']}) | Open Flags: {total_flags}")

        # Summary printout
        print("\n" + "="*80)
        print("SYNTHETIC DEMONSTRATION DATASET — SEED SUMMARY")
        print("="*80)
        for s in summary_results:
            print(f"{s['app_no']} | {s['scenario']:<34} | Score: {s['risk_score']:>4.1f}/100 | Band: {s['risk_band']:<6} | Status: {s['status']}")
        print("="*80 + "\n")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seeding failed: {e}")
        raise e
    finally:
        if owns_db:
            db.close()

if __name__ == "__main__":
    seed_synthetic_scenarios()
