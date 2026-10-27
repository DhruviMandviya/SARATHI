import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import fitz

SUSPICIOUS_PRODUCERS = ["photoshop", "gimp", "canva", "pdfedit", "paint.net", "inkscape", "coreldraw"]

def analyze_pdf_forensics(file_path: str, document_id: int) -> List[Dict[str, Any]]:
    """
    Analyzes PDF metadata, font consistency, incremental revisions, and object streams.
    Returns structured forensic signals with non-accusatory review flags.
    """
    flags: List[Dict[str, Any]] = []

    try:
        # 1. Byte-level Incremental Update check (count %%EOF)
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()

        eof_count = pdf_bytes.count(b"%%EOF")
        if eof_count > 1:
            flags.append({
                "category": "metadata",
                "severity": "info",
                "title": f"Multiple Incremental PDF Revisions Detected ({eof_count} revisions)",
                "explanation": (
                    f"PDF file contains {eof_count} '%%EOF' markers, indicating the file underwent incremental saves or revisions after initial generation. "
                    "Caveat: Many legitimate PDF editors, form-fillers, and digital signing utilities save files incrementally."
                ),
                "evidence": {
                    "eof_marker_count": eof_count,
                    "caveat": "Weak signal. Common in multi-author workflows."
                },
                "confidence": 0.60,
                "confidence_meaning": "Cryptographic file trailer count inspection",
                "rule_ref": "PDF_Incremental_Revisions"
            })

        # 2. Metadata Inspection
        doc = fitz.open(file_path)
        meta = doc.metadata or {}
        creator = (meta.get("creator") or "").lower()
        producer = (meta.get("producer") or "").lower()

        # Check for image editing tools in PDF producer metadata
        matched_editors = [ed for ed in SUSPICIOUS_PRODUCERS if ed in creator or ed in producer]
        if matched_editors:
            flags.append({
                "category": "metadata",
                "severity": "warning",
                "title": f"Graphic Design / Image Editor Software in PDF Metadata ({', '.join(matched_editors)})",
                "explanation": (
                    f"PDF metadata identifies creation via graphic editing software ({', '.join(matched_editors)}). "
                    "Official statutory certificates are typically issued from government ERP or document scanning suites. "
                    "Review document text and dates carefully."
                ),
                "evidence": {
                    "creator": meta.get("creator"),
                    "producer": meta.get("producer"),
                    "matched_tools": matched_editors,
                    "creation_date": meta.get("creationDate"),
                    "mod_date": meta.get("modDate")
                },
                "confidence": 0.70,
                "confidence_meaning": "PDF metadata dictionary string inspection",
                "rule_ref": "PDF_Producer_Software"
            })

        # 3. Font Mix per Page Check
        page_count = len(doc)
        for p_idx in range(min(page_count, 5)):
            page = doc[p_idx]
            fonts = page.get_fonts()
            if len(fonts) > 9:
                font_names = [f[3] for f in fonts if len(f) > 3]
                flags.append({
                    "category": "metadata",
                    "severity": "info",
                    "title": f"Unusually High Font Diversity on Page {p_idx + 1} ({len(fonts)} fonts)",
                    "explanation": (
                        f"Page {p_idx + 1} utilizes {len(fonts)} distinct font families. "
                        "May occur when text fragments are spliced from differing template sources."
                    ),
                    "evidence": {
                        "page": p_idx + 1,
                        "font_count": len(fonts),
                        "fonts_detected": font_names[:6]
                    },
                    "confidence": 0.55,
                    "confidence_meaning": "PyMuPDF font catalog inspection per page",
                    "rule_ref": "PDF_Font_Diversity"
                })

        doc.close()

    except Exception as e:
        # Do not crash if PDF is unusual or malformed
        pass

    return flags
