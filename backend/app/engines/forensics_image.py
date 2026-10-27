import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import fitz

from backend.app.core.config import settings

def perform_ela(
    image_bgr: np.ndarray,
    output_heatmap_path: str,
    quality: int = 90,
    scale: int = 18
) -> Dict[str, Any]:
    """
    Performs Error Level Analysis (ELA) by re-saving at a specified JPEG quality,
    calculating pixel difference, and amplifying difference to a visual heatmap.
    """
    derived_dir = Path(output_heatmap_path).parent
    derived_dir.mkdir(parents=True, exist_ok=True)

    # Temporary encoded image in memory
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, enc_img = cv2.imencode(".jpg", image_bgr, encode_param)
    recompressed = cv2.imdecode(enc_img, cv2.IMREAD_COLOR)

    # Compute absolute difference
    diff = cv2.absdiff(image_bgr, recompressed)

    # Amplify differences for human inspection
    amplified = cv2.convertScaleAbs(diff, alpha=scale, beta=0)

    # Generate color heatmap
    gray_diff = cv2.cvtColor(amplified, cv2.COLOR_BGR2GRAY)
    heatmap = cv2.applyColorMap(gray_diff, cv2.COLORMAP_JET)

    # Save heatmap to derived folder
    cv2.imwrite(output_heatmap_path, heatmap)

    # Numeric metrics
    mean_diff = float(np.mean(diff))
    max_diff = float(np.max(diff))
    h, w = gray_diff.shape[:2]
    high_delta_pixels = int(np.count_nonzero(gray_diff > 120))
    high_delta_ratio = float(high_delta_pixels / (h * w))

    # Identify top suspicious regions as bounding boxes
    suspicious_bboxes = []
    _, thresh = cv2.threshold(gray_diff, 130, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in contours:
        area = cv2.contourArea(c)
        if 200 < area < (h * w * 0.25):  # Filter out trivial noise or whole-image artifacts
            x, y, bw, bh = cv2.boundingRect(c)
            suspicious_bboxes.append({
                "x": round(x / w, 4),
                "y": round(y / h, 4),
                "width": round(bw / w, 4),
                "height": round(bh / h, 4),
                "area": int(area)
            })

    # Sort by area descending and keep top 3
    suspicious_bboxes = sorted(suspicious_bboxes, key=lambda b: b["area"], reverse=True)[:3]

    return {
        "heatmap_path": output_heatmap_path,
        "mean_diff": round(mean_diff, 2),
        "max_diff": round(max_diff, 2),
        "high_delta_ratio": round(high_delta_ratio, 4),
        "suspicious_bboxes": suspicious_bboxes
    }

def detect_copy_move(image_bgr: np.ndarray) -> Dict[str, Any]:
    """
    Conservative copy-move detection using ORB keypoint matching.
    Looks for spatially separated keypoint clusters with identical descriptors.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if len(image_bgr.shape) == 3 else image_bgr
    h, w = gray.shape[:2]

    orb = cv2.ORB_create(nfeatures=800)
    keypoints, descriptors = orb.detectAndCompute(gray, None)

    if descriptors is None or len(keypoints) < 20:
        return {"detected": False, "matched_clusters_count": 0, "regions": []}

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    try:
        matches = matcher.knnMatch(descriptors, descriptors, k=3)
    except Exception:
        return {"detected": False, "matched_clusters_count": 0, "regions": []}

    suspicious_pairs = []
    for m_list in matches:
        if len(m_list) >= 2:
            m1, m2 = m_list[0], m_list[1]
            # Ignore self-match
            if m1.queryIdx == m1.trainIdx:
                target = m2
            else:
                target = m1

            # Lowe's ratio test and minimum spatial displacement (at least 40 pixels apart)
            pt1 = keypoints[m1.queryIdx].pt
            pt2 = keypoints[target.trainIdx].pt
            dist_sq = (pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2

            if target.distance < 45 and dist_sq > 1600:
                suspicious_pairs.append((pt1, pt2))

    # If cluster of matches exists
    if len(suspicious_pairs) >= 8:
        # Compute bounding box around matched points
        all_pts = [p[0] for p in suspicious_pairs] + [p[1] for p in suspicious_pairs]
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        region = {
            "x": round(min_x / w, 4),
            "y": round(min_y / h, 4),
            "width": round((max_x - min_x) / w, 4),
            "height": round((max_y - min_y) / h, 4)
        }
        return {
            "detected": True,
            "matched_clusters_count": len(suspicious_pairs),
            "regions": [region]
        }

    return {"detected": False, "matched_clusters_count": len(suspicious_pairs), "regions": []}

def analyze_image_forensics(
    file_path: str,
    mime_type: str,
    document_id: int
) -> List[Dict[str, Any]]:
    """
    Runs ELA and Copy-Move analysis.
    Returns structured forensic signal flags with explicit disclaimer caveats.
    """
    flags: List[Dict[str, Any]] = []

    # Get image representation
    if "pdf" in mime_type:
        try:
            doc = fitz.open(file_path)
            if len(doc) == 0:
                doc.close()
                return []
            pix = doc[0].get_pixmap(dpi=150)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 1:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            doc.close()
        except Exception:
            return []
    else:
        img = cv2.imread(file_path)
        if img is None:
            return []

    derived_dir = Path(settings.DERIVED_DIR)
    derived_dir.mkdir(parents=True, exist_ok=True)
    ela_output_path = str(derived_dir / f"ela_doc_{document_id}.png")

    # 1. Error Level Analysis (ELA)
    ela_res = perform_ela(img, ela_output_path)
    high_delta_ratio = ela_res["high_delta_ratio"]
    mean_diff = ela_res["mean_diff"]

    # Conservative threshold: only flag if localized anomaly cluster is detected
    if high_delta_ratio > 0.04 and len(ela_res["suspicious_bboxes"]) > 0:
        top_box = ela_res["suspicious_bboxes"][0]
        flags.append({
            "category": "tampering",
            "severity": "warning",
            "title": "Compression Artifact Anomaly Detected (ELA Signal)",
            "explanation": (
                f"Error Level Analysis identified localized compression rate discrepancy (mean delta {mean_diff:.1f}, "
                f"{high_delta_ratio:.1%} anomalous pixels). Inspect the ELA heatmap overlay. "
                "Caveat: ELA heatmaps are weak heuristic signals, not proof of tampering. "
                "Legitimate scanner software and PDF compilers frequently cause compression variances."
            ),
            "evidence": {
                "ela_metrics": {
                    "mean_diff": mean_diff,
                    "max_diff": ela_res["max_diff"],
                    "high_delta_ratio": high_delta_ratio,
                    "heatmap_file": f"ela_doc_{document_id}.png"
                },
                "caveat": "Weak heuristic signal. Not proof of tampering."
            },
            "bbox": top_box,
            "confidence": 0.65,
            "confidence_meaning": "Heuristic Error Level Analysis (ELA) re-compression variance",
            "rule_ref": "Forensic_ELA_Compression"
        })

    # 2. Copy-Move Detection
    cm_res = detect_copy_move(img)
    if cm_res["detected"]:
        flags.append({
            "category": "tampering",
            "severity": "warning",
            "title": "Suspected Repeated Pattern / Copy-Move Feature Cluster",
            "explanation": (
                f"ORB keypoint matcher identified {cm_res['matched_clusters_count']} spatially displaced duplicate feature points. "
                "May indicate copied elements (e.g. repeated stamps or patched text regions). Visual inspection required."
            ),
            "evidence": {
                "matched_count": cm_res["matched_clusters_count"],
                "regions": cm_res["regions"],
                "caveat": "Heuristic keypoint clustering. Legitimate repeating headers/logos can trigger this signal."
            },
            "bbox": cm_res["regions"][0] if cm_res["regions"] else None,
            "confidence": 0.68,
            "confidence_meaning": "Heuristic ORB keypoint descriptor spatial clustering",
            "rule_ref": "Forensic_CopyMove_ORB"
        })

    return flags
