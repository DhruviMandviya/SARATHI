import os
import uuid
import hashlib
from pathlib import Path
from typing import Tuple, Optional
import fitz  # PyMuPDF
from PIL import Image
from fastapi import HTTPException, UploadFile, status

from backend.app.core.config import settings

# Magic byte signatures
MAGIC_BYTES = {
    "pdf": b"%PDF",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
}

class FileValidationResult:
    def __init__(
        self,
        is_valid: bool,
        error_message: Optional[str] = None,
        mime_type: Optional[str] = None,
        sha256: Optional[str] = None,
        page_count: int = 1,
        sanitized_filename: Optional[str] = None,
        storage_rel_path: Optional[str] = None
    ):
        self.is_valid = is_valid
        self.error_message = error_message
        self.mime_type = mime_type
        self.sha256 = sha256
        self.page_count = page_count
        self.sanitized_filename = sanitized_filename
        self.storage_rel_path = storage_rel_path

def sanitize_filename(filename: str) -> str:
    """Removes path traversal components and unsafe characters."""
    base = os.path.basename(filename)
    clean = "".join(c for c in base if c.isalnum() or c in (".", "-", "_")).strip()
    return clean or f"doc_{uuid.uuid4().hex[:8]}"

async def validate_and_save_upload(
    upload_file: UploadFile,
    allowed_types: Tuple[str, ...] = ("pdf", "png", "jpg", "jpeg")
) -> FileValidationResult:
    sanitized_name = sanitize_filename(upload_file.filename or "unknown")
    ext = sanitized_name.split(".")[-1].lower() if "." in sanitized_name else ""

    if ext not in allowed_types:
        return FileValidationResult(
            is_valid=False,
            error_message=f"Unsupported file format '.{ext}'. Allowed types are PDF, JPG, PNG."
        )

    # Read content into memory / buffer
    contents = await upload_file.read()
    file_size = len(contents)

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        return FileValidationResult(
            is_valid=False,
            error_message=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
        )

    if file_size < 10:
        return FileValidationResult(
            is_valid=False,
            error_message="Uploaded file is empty or corrupted."
        )

    # Magic byte validation
    is_magic_valid = False
    detected_mime = "application/octet-stream"

    if ext == "pdf":
        if contents.startswith(MAGIC_BYTES["pdf"]):
            is_magic_valid = True
            detected_mime = "application/pdf"
    elif ext in ("jpg", "jpeg"):
        if contents.startswith(MAGIC_BYTES["jpg"]):
            is_magic_valid = True
            detected_mime = "image/jpeg"
    elif ext == "png":
        if contents.startswith(MAGIC_BYTES["png"]):
            is_magic_valid = True
            detected_mime = "image/png"

    if not is_magic_valid:
        return FileValidationResult(
            is_valid=False,
            error_message=f"File header mismatch: File with extension '.{ext}' does not contain valid {ext.upper()} magic bytes. Spoofed extensions are prohibited."
        )

    # Content integrity and page count inspection
    page_count = 1
    if ext == "pdf":
        try:
            doc = fitz.open(stream=contents, filetype="pdf")
            if doc.is_encrypted:
                return FileValidationResult(
                    is_valid=False,
                    error_message="Password-protected or encrypted PDFs are not accepted. Please upload an unencrypted document."
                )
            page_count = len(doc)
            if page_count > settings.MAX_PDF_PAGES:
                return FileValidationResult(
                    is_valid=False,
                    error_message=f"PDF has {page_count} pages, exceeding the maximum allowed limit of {settings.MAX_PDF_PAGES} pages."
                )
            doc.close()
        except Exception as e:
            return FileValidationResult(
                is_valid=False,
                error_message=f"Corrupt or unreadable PDF: {str(e)}"
            )
    else:
        # Validate image integrity with PIL
        try:
            from io import BytesIO
            img = Image.open(BytesIO(contents))
            img.verify()
        except Exception as e:
            return FileValidationResult(
                is_valid=False,
                error_message=f"Corrupt or unreadable image file: {str(e)}"
            )

    # Calculate SHA-256 hash
    sha256 = hashlib.sha256(contents).hexdigest()

    # Generate UUID storage filename - original files are NEVER modified
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    storage_path = Path(settings.STORAGE_DIR) / unique_filename
    with open(storage_path, "wb") as f:
        f.write(contents)

    return FileValidationResult(
        is_valid=True,
        mime_type=detected_mime,
        sha256=sha256,
        page_count=page_count,
        sanitized_filename=sanitized_name,
        storage_rel_path=str(storage_path)
    )
