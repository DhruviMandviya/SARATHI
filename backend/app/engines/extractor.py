import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

def normalize_land_area_to_acres(val: float, unit: str) -> float:
    """Normalizes land area from various units to canonical Acres."""
    u = unit.lower().strip()
    if "sq.m" in u or "sqm" in u or "square meter" in u:
        return round(val * 0.000247105, 4)
    elif "sq.ft" in u or "sqft" in u or "square feet" in u:
        return round(val * 0.0000229568, 4)
    elif "hectare" in u or "ha" in u:
        return round(val * 2.47105, 4)
    # Default is acres
    return round(val, 4)

def parse_date_string(date_str: str) -> Optional[str]:
    """Parses various date formats into YYYY-MM-DD."""
    if not date_str:
        return None
    cleaned = date_str.strip().replace("/", "-").replace(".", "-")
    patterns = [
        r"(\d{4})-(\d{1,2})-(\d{1,2})",       # YYYY-MM-DD
        r"(\d{1,2})-(\d{1,2})-(\d{4})",       # DD-MM-YYYY
        r"(\d{1,2})-(\w{3,9})-(\d{4})"        # DD-Mon-YYYY (e.g. 15-Aug-2025)
    ]
    
    # Try direct strptime formats
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y", "%d-%B-%Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Regex extraction
    m = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", date_str)
    if m:
        try:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            dt = datetime(year, month, day)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def find_bbox_for_value(val: str, pages_data: List[Dict[str, Any]]) -> Tuple[int, Dict[str, Any]]:
    """Attempts to find the page and bbox for an extracted field value from OCR word data."""
    if not val or not pages_data:
        return 1, {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.04}

    val_tokens = val.lower().split()
    first_token = val_tokens[0] if val_tokens else ""

    for p_idx, page in enumerate(pages_data):
        page_num = page.get("page_number", p_idx + 1)
        words = page.get("words", [])
        for w in words:
            w_text = w.get("word", "").lower().strip(",.:;")
            if first_token and (first_token in w_text or w_text in first_token):
                return page_num, w.get("bbox", {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.04})

    return 1, {"x": 0.15, "y": 0.2, "width": 0.4, "height": 0.05}

def extract_fields_from_text(
    full_text: str,
    doc_type: str,
    pages_data: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Extracts key fields per document type with confidence, page number, and bounding boxes.
    """
    pages_data = pages_data or []
    extracted: List[Dict[str, Any]] = []

    def add_field(key: str, val: Optional[str], conf: float = 0.95, method: str = "regex"):
        if not val:
            return
        clean_val = str(val).strip()
        page, bbox = find_bbox_for_value(clean_val, pages_data)
        needs_review = conf < 0.70
        extracted.append({
            "key": key,
            "value": clean_val,
            "ocr_confidence": round(conf, 2),
            "extraction_method": method,
            "page": page,
            "bbox": bbox,
            "needs_review": needs_review
        })

    # Common fields: Institution Name
    inst_match = re.search(
        r"(?:institution\s+name|name\s+of\s+(?:the\s+)?institution|college\s+name|in\s+favour\s+of)\s*[:\-]?\s*([A-Za-z0-9\s&,.'\-]+?)(?=\n|district|state|trust|\.|$)",
        full_text,
        re.IGNORECASE
    )
    if inst_match:
        inst_name = inst_match.group(1).strip()
        if len(inst_name) > 3 and not inst_name.lower().startswith("the "):
            add_field("institution_name", inst_name, conf=0.92)

    # Trust / Society Name
    trust_match = re.search(
        r"(?:trust\s+name|society\s+name|name\s+of\s+(?:the\s+)?(?:trust|society|promoter))\s*[:\-]?\s*([A-Za-z0-9\s&,.'\-]+?)(?=\n|having|registered|\.|$)",
        full_text,
        re.IGNORECASE
    )
    if trust_match:
        add_field("trust_name", trust_match.group(1).strip(), conf=0.90)

    # Document type specific extraction
    if doc_type == "land_document":
        # Deed / Document number
        deed_match = re.search(
            r"(?:deed\s*(?:no|number)\.?|document\s*(?:no|number)\.?|indenture\s*(?:no|number)\.?|reg(?:istration)?\s*(?:no|number)\.?)\s*[:\-]?\s*([A-Za-z0-9\/\-_]+)",
            full_text,
            re.IGNORECASE
        )
        if deed_match:
            deed_val = deed_match.group(1).strip()
            add_field("reference_no", deed_val, conf=0.95)
            add_field("deed_number", deed_val, conf=0.95)

        # Land area (Acres, Hectares, Sq.m)
        area_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(acres?|hectares?|ha|sq\.?\s*m(?:eters?)?|sq\.?\s*ft|square\s+meters?)",
            full_text,
            re.IGNORECASE
        )
        if area_match:
            raw_val = float(area_match.group(1))
            raw_unit = area_match.group(2)
            normalized_acres = normalize_land_area_to_acres(raw_val, raw_unit)
            add_field("land_area_raw", f"{raw_val} {raw_unit}", conf=0.95)
            add_field("land_area_acres", str(normalized_acres), conf=0.95)

        # Survey / Khasra / Patta Number
        survey_match = re.search(
            r"(?:survey\s*(?:no[s]?|number)\.?|khasra\s*(?:no|number)\.?|patta\s*(?:no|number)\.?|gat\s*(?:no|number)\.?|plot\s*(?:no|number)\.?)\s*[:\-]?\s*([A-Za-z0-9\/\-_]+)",
            full_text,
            re.IGNORECASE
        )
        if survey_match:
            add_field("survey_number", survey_match.group(1).strip(), conf=0.95)

        # Landowner / Lessor / Vendor
        owner_match = re.search(
            r"(?:land\s*owner|lessor|vendor|executant|purchaser|in\s+ownership\s+of)\s*[:\-]?\s*([A-Za-z0-9\s&,.'\-]+?)(?=\n|residing|son\s+of|\.|$)",
            full_text,
            re.IGNORECASE
        )
        if owner_match:
            add_field("landowner", owner_match.group(1).strip(), conf=0.88)

        # Sub-Registrar / Registration Date
        date_match = re.search(
            r"(?:registered\s+on|date\s+of\s+registration|execution\s+date|registration\s+date)\s*[:\-]?\s*([0-9\/\-\.A-Za-z]+)",
            full_text,
            re.IGNORECASE
        )
        if date_match:
            parsed_d = parse_date_string(date_match.group(1))
            if parsed_d:
                add_field("registration_date", parsed_d, conf=0.92)

    elif doc_type == "building_plan":
        # Built-up area in Sq.m
        bua_match = re.search(
            r"(?:built-?up\s+area|total\s+covered\s+area|plinth\s+area|sanctioned\s+built-?up\s+area)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(sq\.?\s*m(?:eters?)?|sq\.?\s*ft)?",
            full_text,
            re.IGNORECASE
        )
        if bua_match:
            bua_val = float(bua_match.group(1))
            unit = bua_match.group(2) or "sq.m"
            if "ft" in unit.lower():
                bua_val = round(bua_val * 0.092903, 1)  # Convert sq ft to sq m
            add_field("built_up_area_sqm", str(bua_val), conf=0.95)

        # Sanction / Approval Number
        sanction_match = re.search(
            r"(?:sanction\s*(?:order\s*)?(?:no|number)\.?|plan\s*approval\s*(?:no|number)\.?|file\s*(?:no|number)\.?)\s*[:\-]?\s*([A-Za-z0-9\/\-_]+)",
            full_text,
            re.IGNORECASE
        )
        if sanction_match:
            s_val = sanction_match.group(1).strip()
            add_field("sanction_number", s_val, conf=0.95)
            add_field("sanction_no", s_val, conf=0.95)
            add_field("reference_no", s_val, conf=0.95)

    elif doc_type == "fire_noc":
        # Reference No / Certificate No / NOC Number
        ref_match = re.search(
            r"(?:noc\s*(?:number|no|ref|reference)?|certificate\s*(?:number|no)?|reference\s*(?:number|no)?)\.?[ \t]*[:\-][ \t]*([A-Za-z0-9\/\-_]+)",
            full_text,
            re.IGNORECASE
        )
        if ref_match:
            r_val = ref_match.group(1).strip()
            add_field("reference_no", r_val, conf=0.95)
            add_field("noc_number", r_val, conf=0.95)

        # Issue Date
        issue_match = re.search(
            r"(?:dated|date\s+of\s+issue|issued\s+on|issued\s+date|issue\s+date)[^\d\n]*[:\-]?[ \t]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})",
            full_text,
            re.IGNORECASE
        )
        if issue_match:
            parsed_issue = parse_date_string(issue_match.group(1))
            if parsed_issue:
                add_field("issue_date", parsed_issue, conf=0.92)

        # Validity / Expiry Date (valid until, valid up to, valid till, expiry date)
        val_match = re.search(
            r"(?:valid\s*(?:up\s*to|till|until)|expiry\s*date|validity\s*(?:period\s*up\s*to|date|period))[^\d\n]*[:\-]?[ \t]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})",
            full_text,
            re.IGNORECASE
        )
        if val_match:
            parsed_val = parse_date_string(val_match.group(1))
            if parsed_val:
                add_field("validity_date", parsed_val, conf=0.95)

    elif doc_type == "society_registration":
        reg_match = re.search(
            r"(?:registration\s*(?:no|number)\.?|society\s*registration\s*(?:no|number)\.?|cert(?:ificate)?\s*(?:no|number)\.?)\s*[:\-]?\s*([A-Za-z0-9\/\-_]+)",
            full_text,
            re.IGNORECASE
        )
        if reg_match:
            reg_val = reg_match.group(1).strip()
            add_field("registration_no", reg_val, conf=0.95)
            add_field("reference_no", reg_val, conf=0.95)

        date_match = re.search(
            r"(?:date\s+of\s+registration|registered\s+on|registration\s+date)\s*[:\-]?\s*([0-9\/\-\.A-Za-z]+)",
            full_text,
            re.IGNORECASE
        )
        if date_match:
            parsed_d = parse_date_string(date_match.group(1))
            if parsed_d:
                add_field("registration_date", parsed_d, conf=0.92)

    elif doc_type == "affidavit":
        # Stamp paper value
        stamp_match = re.search(
            r"(?:rs\.?|inr)\s*(\d+)(?:\s*\/-)?\s*(?:non-?judicial\s+stamp)?",
            full_text,
            re.IGNORECASE
        )
        if stamp_match:
            add_field("affidavit_stamp_value_inr", stamp_match.group(1), conf=0.92)

        # Deponent name
        dep_match = re.search(
            r"(?:deponent(?:\s*name)?|affiant(?:\s*name)?|sworn\s+by|declared\s+by)\.?[ \t]*[:\-][ \t]*([A-Za-z\s\.\-_]+?)(?=\n|$)",
            full_text,
            re.IGNORECASE
        )
        if not dep_match:
            dep_match = re.search(
                r"I,\s*([A-Za-z0-9\s\.\-]{3,50}?),\s*(?:Deponent|Affiant)",
                full_text,
                re.IGNORECASE
            )
        if dep_match:
            dep_name = re.sub(r"^[^\w]+|[^\w]+$", "", dep_match.group(1).strip())
            if len(dep_name) > 2:
                add_field("deponent_name", dep_name, conf=0.90)

        # Notary details
        notary_match = re.search(
            r"(?:notary\s*public|attested\s+by|before\s+me)\s*[:\-]?\s*([A-Za-z0-9\s&,.'\-]+?)(?=\n|advocate|\.|$)",
            full_text,
            re.IGNORECASE
        )
        if notary_match:
            add_field("notary_name", notary_match.group(1).strip(), conf=0.88)

    elif doc_type in ["environmental_clearance", "env_clearance"]:
        # Consent / Clearance order number
        order_match = re.search(
            r"(?:consent\s*(?:order\s*)?(?:no|number)\.?|clearance\s*(?:order\s*)?(?:no|number)\.?|ref(?:erence)?\s*(?:no|number)\.?|order\s*(?:no|number)\.?)\s*[:\-]?\s*([A-Za-z0-9\/\-_]+)",
            full_text,
            re.IGNORECASE
        )
        if order_match:
            o_val = order_match.group(1).strip()
            add_field("reference_no", o_val, conf=0.95)
            add_field("order_no", o_val, conf=0.95)

        val_match = re.search(
            r"(?:valid\s*(?:up\s*to|till|until)|expiry\s*date|validity\s*(?:period\s*up\s*to|date))\s*[:\-]?\s*([0-9\/\-\.A-Za-z]+)",
            full_text,
            re.IGNORECASE
        )
        if val_match:
            parsed_val = parse_date_string(val_match.group(1))
            if parsed_val:
                add_field("validity_date", parsed_val, conf=0.95)

    # Heuristic signature presence cue (NOT a fact, phrased carefully)
    sig_present = bool(re.search(r"\b(signature|signed|seal|sub-registrar|notary\s+public|chief\s+fire\s+officer|member\s+secretary|town\s+planner)\b", full_text, re.IGNORECASE))
    add_field("signature_cue", "Signature/Stamp cue detected" if sig_present else "No signature detected, please verify", conf=0.65, method="heuristic_cue")

    return extracted
