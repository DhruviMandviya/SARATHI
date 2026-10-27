import io
import pytest
import fitz
from PIL import Image
from fastapi import status

def create_valid_pdf_bytes(text="AICTE Verification Sample PDF", pages=1):
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_valid_png_bytes():
    img = Image.new("RGB", (100, 100), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def get_auth_token(client, email, password="Demo@Password123"):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]

def test_create_application_and_checklist(client):
    token = get_auth_token(client, "inst1@aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create application
    res = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "type": "New Technical Institution",
            "academic_year": "2026-2027",
            "declared_details": {"land_area_acres": 3.0}
        }
    )
    assert res.status_code == status.HTTP_200_OK
    app_data = res.json()
    app_id = app_data["id"]
    assert app_data["status"] == "draft"
    assert app_data["institution_id"] == 1

    # 2. Get checklist
    chk_res = client.get(f"/api/v1/applications/{app_id}/checklist", headers=headers)
    assert chk_res.status_code == status.HTTP_200_OK
    chk_data = chk_res.json()
    assert chk_data["can_submit"] is False
    assert len(chk_data["missing_mandatory"]) > 0

    # 3. Try submitting without mandatory documents (must fail)
    sub_res = client.post(f"/api/v1/applications/{app_id}/submit", headers=headers)
    assert sub_res.status_code == status.HTTP_400_BAD_REQUEST
    assert "Mandatory documents missing" in sub_res.json()["detail"]

def test_valid_pdf_and_image_upload(client):
    token = get_auth_token(client, "inst1@aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # Create app
    app_res = client.post("/api/v1/applications", headers=headers, json={"type": "New Technical Institution"})
    app_id = app_res.json()["id"]

    # Upload valid PDF
    pdf_bytes = create_valid_pdf_bytes("Land Sale Deed AICTE Content")
    files = {"file": ("land_deed.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"doc_type": "land_document"}

    up_res = client.post(f"/api/v1/applications/{app_id}/documents", headers=headers, files=files, data=data)
    assert up_res.status_code == status.HTTP_200_OK
    doc_data = up_res.json()
    assert doc_data["doc_type"] == "land_document"
    assert doc_data["page_count"] == 1
    assert doc_data["sha256"] is not None

    # Upload valid PNG
    png_bytes = create_valid_png_bytes()
    files_png = {"file": ("fire_noc.png", io.BytesIO(png_bytes), "image/png")}
    data_png = {"doc_type": "fire_noc"}

    up_res2 = client.post(f"/api/v1/applications/{app_id}/documents", headers=headers, files=files_png, data=data_png)
    assert up_res2.status_code == status.HTTP_200_OK
    assert up_res2.json()["mime_type"] == "image/png"

def test_spoofed_extension_magic_bytes_rejected(client):
    token = get_auth_token(client, "inst1@aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    app_res = client.post("/api/v1/applications", headers=headers, json={"type": "New Technical Institution"})
    app_id = app_res.json()["id"]

    # Spoofed file: plain text pretending to be PDF
    fake_pdf = b"This is plain text with no PDF header at all."
    files = {"file": ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    data = {"doc_type": "land_document"}

    res = client.post(f"/api/v1/applications/{app_id}/documents", headers=headers, files=files, data=data)
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "File header mismatch" in res.json()["detail"]

def test_corrupt_pdf_rejected(client):
    token = get_auth_token(client, "inst1@aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    app_res = client.post("/api/v1/applications", headers=headers, json={"type": "New Technical Institution"})
    app_id = app_res.json()["id"]

    # Starts with %PDF but is garbage truncated
    corrupt_pdf = b"%PDF-1.4 garbage truncated incomplete stream"
    files = {"file": ("corrupt.pdf", io.BytesIO(corrupt_pdf), "application/pdf")}
    data = {"doc_type": "land_document"}

    res = client.post(f"/api/v1/applications/{app_id}/documents", headers=headers, files=files, data=data)
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "Corrupt or unreadable PDF" in res.json()["detail"]

def test_cross_institution_upload_denial(client):
    # Institution 1 creates an application
    token1 = get_auth_token(client, "inst1@aicte.gov.in")
    app_res = client.post("/api/v1/applications", headers={"Authorization": f"Bearer {token1}"}, json={"type": "New Technical Institution"})
    app_id = app_res.json()["id"]

    # Institution 2 attempts to upload a document to Institution 1's application
    token2 = get_auth_token(client, "inst2@aicte.gov.in")
    headers2 = {"Authorization": f"Bearer {token2}"}

    pdf_bytes = create_valid_pdf_bytes("Hacker upload attempt")
    files = {"file": ("hack.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"doc_type": "land_document"}

    res = client.post(f"/api/v1/applications/{app_id}/documents", headers=headers2, files=files, data=data)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "Access denied" in res.json()["detail"]
