import io
import os
import pytest
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import fitz

from backend.app.engines.forensics_image import analyze_image_forensics, perform_ela
from backend.app.engines.forensics_pdf import analyze_pdf_forensics

def create_synthetic_image(tampered: bool = False) -> str:
    # Create realistic test certificate image
    img = Image.new("RGB", (600, 800), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 580, 780], outline=(0, 0, 120), width=3)
    draw.text((50, 60), "OFFICIAL FIRE SAFETY CLEARANCE", fill=(0, 0, 0))
    draw.text((50, 120), "Validity Period: 2026-12-31", fill=(0, 0, 0))

    if tampered:
        # Deliberately paste an altered date region saved with different compression
        patch = Image.new("RGB", (180, 40), color=(240, 240, 240))
        pdraw = ImageDraw.Draw(patch)
        pdraw.text((10, 10), "ALTERED: 2030-12-31", fill=(200, 0, 0))
        # Re-save patch at low quality
        buf = io.BytesIO()
        patch.save(buf, format="JPEG", quality=30)
        buf.seek(0)
        patch_reloaded = Image.open(buf)
        img.paste(patch_reloaded, (50, 180))

    test_path = "backend/storage/derived/test_forensics_sample.jpg"
    os.makedirs(os.path.dirname(test_path), exist_ok=True)
    img.save(test_path, "JPEG", quality=95)
    return test_path

def test_clean_image_false_positive_behavior():
    clean_path = create_synthetic_image(tampered=False)
    flags = analyze_image_forensics(clean_path, "image/jpeg", document_id=9901)
    
    # Critical flags must NEVER be raised for clean images
    critical_flags = [f for f in flags if f.get("severity") == "critical"]
    assert len(critical_flags) == 0

    # Ensure structured output shape and caveat present
    for f in flags:
        assert "caveat" in f["evidence"] or "Caveat" in f["explanation"]
        assert "confidence_meaning" in f

def test_tampered_image_ela_detection():
    tampered_path = create_synthetic_image(tampered=True)
    flags = analyze_image_forensics(tampered_path, "image/jpeg", document_id=9902)

    # Tampered image should trigger ELA signal or copy-move signal
    assert len(flags) >= 1
    flag = flags[0]
    assert flag["category"] == "tampering"
    assert flag["confidence"] > 0
    assert "heuristic" in flag["confidence_meaning"].lower()

    # Check that heatmap file was generated
    from backend.app.core.config import settings
    heatmap_path = os.path.join(settings.DERIVED_DIR, "ela_doc_9902.png")
    assert os.path.exists(heatmap_path)

def test_pdf_forensics_clean_and_incremental():
    # Create simple PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Clean Municipal Plan Sanction")
    pdf_path = "backend/storage/derived/test_clean_forensics.pdf"
    doc.save(pdf_path)
    doc.close()

    flags = analyze_pdf_forensics(pdf_path, document_id=9903)
    # Clean single-save PDF shouldn't produce critical alarms
    assert len([f for f in flags if f.get("severity") == "critical"]) == 0
