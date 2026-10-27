import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

class ClassificationResult:
    def __init__(
        self,
        doc_type: str,
        confidence: float,
        matched_keywords: List[str],
        needs_review: bool,
        scores_by_type: Dict[str, float],
        mismatch_flag: Optional[Dict[str, Any]] = None
    ):
        self.doc_type = doc_type
        self.confidence = confidence
        self.matched_keywords = matched_keywords
        self.needs_review = needs_review
        self.scores_by_type = scores_by_type
        self.mismatch_flag = mismatch_flag

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_type": self.doc_type,
            "confidence": round(self.confidence, 4),
            "matched_keywords": self.matched_keywords,
            "needs_review": self.needs_review,
            "scores_by_type": {k: round(v, 4) for k, v in self.scores_by_type.items()},
            "mismatch_flag": self.mismatch_flag
        }

def load_classifier_rules() -> Dict[str, Any]:
    rules_path = Path(__file__).resolve().parent.parent.parent / "rules" / "classifier_keywords.json"
    if rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def classify_document(
    text: str,
    filename: str = "",
    uploaded_slot: Optional[str] = None
) -> ClassificationResult:
    """
    Pure rule/keyword/regex based classifier.
    Computes explainable scores per document category.
    """
    rules = load_classifier_rules()
    text_lower = (text or "").lower()
    filename_lower = (filename or "").lower()

    scores: Dict[str, float] = {}
    matched_by_type: Dict[str, List[str]] = {}

    for doc_type, rule_def in rules.items():
        score = 0.0
        matched_words = []

        # 1. Keyword count and weighting
        keywords = rule_def.get("keywords", [])
        for kw in keywords:
            kw_clean = kw.lower()
            if kw_clean in text_lower:
                count = text_lower.count(kw_clean)
                score += min(count * 0.15, 0.45)
                matched_words.append(kw)

        # 2. Regex patterns
        patterns = rule_def.get("patterns", [])
        for pat in patterns:
            try:
                if re.search(pat, text_lower):
                    score += 0.30
                    matched_words.append(f"pattern({pat})")
            except re.error:
                pass

        # 3. Filename cues
        cues = rule_def.get("filename_cues", [])
        for cue in cues:
            if cue in filename_lower:
                score += 0.25
                matched_words.append(f"filename_cue({cue})")

        scores[doc_type] = score
        matched_by_type[doc_type] = matched_words

    if not scores or max(scores.values()) == 0.0:
        return ClassificationResult(
            doc_type="unknown",
            confidence=0.0,
            matched_keywords=[],
            needs_review=True,
            scores_by_type=scores
        )

    # Find highest scoring type
    best_type, raw_score = max(scores.items(), key=lambda item: item[1])
    
    # Normalize confidence into [0.0, 1.0]
    confidence = min(raw_score / 1.2, 0.99)
    needs_review = confidence < 0.40 or best_type == "unknown"
    final_type = best_type if confidence >= 0.25 else "unknown"

    mismatch_flag = None
    if uploaded_slot and final_type != "unknown" and uploaded_slot != final_type:
        # Check if classifier strongly indicates another document type
        if confidence >= 0.55:
            mismatch_flag = {
                "category": "mismatch",
                "severity": "warning",
                "title": "Document Type Slot Mismatch",
                "explanation": f"File was uploaded under '{uploaded_slot}', but classifier identified content as '{final_type}' (Confidence: {confidence:.0%}). Matched cues: {', '.join(matched_by_type[best_type][:3])}.",
                "confidence": confidence,
                "confidence_meaning": "Keyword & pattern classification score divergence from selected slot",
                "evidence": {
                    "uploaded_slot": uploaded_slot,
                    "classified_as": final_type,
                    "matched_cues": matched_by_type[best_type]
                }
            }

    return ClassificationResult(
        doc_type=final_type,
        confidence=confidence,
        matched_keywords=matched_by_type.get(best_type, []),
        needs_review=needs_review,
        scores_by_type=scores,
        mismatch_flag=mismatch_flag
    )
