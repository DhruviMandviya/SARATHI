import os
import shutil
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import cv2
import numpy as np
import pytesseract

from backend.app.core.config import settings

def is_tesseract_available() -> bool:
    """Checks if Tesseract binary is installed and reachable."""
    if settings.TESSERACT_CMD and os.path.exists(settings.TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        return True
    return shutil.which("tesseract") is not None

def check_image_quality(cv_image: np.ndarray) -> Dict[str, Any]:
    """Computes blur variance via Laplacian and resolution metrics."""
    if len(cv_image.shape) == 3:
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = cv_image

    blur_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    h, w = gray.shape[:2]

    quality_flags = []
    # Heuristic: blur variance < 100 often indicates motion blur or defocus
    if blur_variance < 80.0:
        quality_flags.append({
            "category": "quality",
            "severity": "warning",
            "title": "Low Scan Quality / Blur Detected",
            "explanation": f"Document image Laplacian variance ({blur_variance:.1f}) is below standard clarity threshold (80.0). Text extraction may be degraded.",
            "confidence": 0.85
        })
    elif blur_variance < 150.0:
        quality_flags.append({
            "category": "quality",
            "severity": "info",
            "title": "Moderate Scan Clarity",
            "explanation": f"Scan clarity variance is {blur_variance:.1f}. Legible, but recommend high-resolution flatbed scanning for statutory archiving.",
            "confidence": 0.70
        })

    # Check minimum dimensions (under 600x600 is low resolution)
    if w < 600 or h < 600:
        quality_flags.append({
            "category": "quality",
            "severity": "warning",
            "title": "Low Image Resolution",
            "explanation": f"Document resolution ({w}x{h}) is below the recommended minimum 300 DPI standard (1200x1600+).",
            "confidence": 0.90
        })

    return {
        "blur_variance": blur_variance,
        "width": w,
        "height": h,
        "quality_flags": quality_flags
    }

def extract_text_from_document(
    file_path: str,
    mime_type: str,
    max_pages: int = 15
) -> Dict[str, Any]:
    """
    Extracts text, word confidences, and bounding boxes.
    Strategy:
    - Digital PDF: PyMuPDF text layer first (fast, accurate, no OCR needed).
    - Image or scanned PDF page (<50 chars in text layer): Renders page and uses Tesseract OCR.
    - Graceful degradation: If Tesseract is unavailable, marks ocr_available=False without crashing.
    """
    tess_available = is_tesseract_available()
    pages_result: List[Dict[str, Any]] = []
    all_quality_flags: List[Dict[str, Any]] = []
    full_text_list: List[str] = []

    if "pdf" in mime_type:
        doc = fitz.open(file_path)
        page_count = min(len(doc), max_pages)

        for p_idx in range(page_count):
            page = doc[p_idx]
            native_text = page.get_text("text").strip()
            page_words = []

            # If native text layer has substantial content
            if len(native_text) >= 40:
                words_data = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
                page_width = page.rect.width
                page_height = page.rect.height

                for w in words_data:
                    page_words.append({
                        "word": w[4],
                        "confidence": 98.0,  # Native text layer has high character confidence
                        "bbox": {
                            "x": round(float(w[0] / page_width), 4),
                            "y": round(float(w[1] / page_height), 4),
                            "width": round(float((w[2] - w[0]) / page_width), 4),
                            "height": round(float((w[3] - w[1]) / page_height), 4)
                        }
                    })

                pages_result.append({
                    "page_number": p_idx + 1,
                    "text": native_text,
                    "extraction_method": "text_layer",
                    "words": page_words,
                    "ocr_available": True
                })
                full_text_list.append(native_text)

            else:
                # Scanned page: render image and use OCR if available
                pix = page.get_pixmap(dpi=200)
                img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.n == 4:
                    img_data = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)

                quality_info = check_image_quality(img_data)
                all_quality_flags.extend(quality_info["quality_flags"])

                if not tess_available:
                    pages_result.append({
                        "page_number": p_idx + 1,
                        "text": native_text or "[Scanned page - OCR unavailable]",
                        "extraction_method": "ocr_unavailable",
                        "words": [],
                        "ocr_available": False,
                        "error": "Tesseract binary not installed on host. Install Tesseract to enable scanned image OCR."
                    })
                    full_text_list.append(native_text)
                else:
                    ocr_res = run_tesseract_ocr(img_data, page_num=p_idx + 1)
                    pages_result.append(ocr_res)
                    full_text_list.append(ocr_res["text"])

        doc.close()

    else:
        # Single image document
        cv_img = cv2.imread(file_path)
        if cv_img is None:
            # Fallback PIL load
            with Image.open(file_path) as pil_img:
                cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        quality_info = check_image_quality(cv_img)
        all_quality_flags.extend(quality_info["quality_flags"])

        if not tess_available:
            pages_result.append({
                "page_number": 1,
                "text": "[Image Document - OCR unavailable]",
                "extraction_method": "ocr_unavailable",
                "words": [],
                "ocr_available": False,
                "error": "Tesseract binary not installed on host. Scanned image OCR unavailable."
            })
            full_text_list.append("")
        else:
            ocr_res = run_tesseract_ocr(cv_img, page_num=1)
            pages_result.append(ocr_res)
            full_text_list.append(ocr_res["text"])

    return {
        "full_text": "\n\n".join(full_text_list),
        "pages": pages_result,
        "quality_flags": all_quality_flags,
        "tesseract_available": tess_available
    }

def run_tesseract_ocr(cv_image: np.ndarray, page_num: int = 1) -> Dict[str, Any]:
    """Runs pytesseract with image_to_data for word bboxes and confidence."""
    # Preprocessing: grayscale, denoise, otsu threshold
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY) if len(cv_image.shape) == 3 else cv_image
    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    
    h_img, w_img = cv_image.shape[:2]
    
    try:
        data = pytesseract.image_to_data(
            denoised,
            lang=settings.OCR_LANG,
            output_type=pytesseract.Output.DICT
        )
        words_list = []
        text_words = []
        
        n_boxes = len(data["text"])
        for i in range(n_boxes):
            word_str = data["text"][i].strip()
            conf = float(data["conf"][i])
            if word_str and conf >= 0:
                text_words.append(word_str)
                words_list.append({
                    "word": word_str,
                    "confidence": conf,
                    "bbox": {
                        "x": round(data["left"][i] / w_img, 4),
                        "y": round(data["top"][i] / h_img, 4),
                        "width": round(data["width"][i] / w_img, 4),
                        "height": round(data["height"][i] / h_img, 4),
                    }
                })

        extracted_text = " ".join(text_words)
        return {
            "page_number": page_num,
            "text": extracted_text,
            "extraction_method": "tesseract",
            "words": words_list,
            "ocr_available": True
        }
    except Exception as e:
        return {
            "page_number": page_num,
            "text": "",
            "extraction_method": "tesseract_failed",
            "words": [],
            "ocr_available": False,
            "error": str(e)
        }
