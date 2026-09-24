import re
from datetime import datetime
from decimal import Decimal
from typing import Any


DOMAIN_STOPLIST = {
    "accused more",
    "adalat wear",
    "address",
    "address type",
    "acts",
    "all persons",
    "analytical notes",
    "analytical summary",
    "applicable sections",
    "associated case",
    "beat no",
    "case information",
    "case reference",
    "complaint statement",
    "complaint circumstances",
    "complainant informant",
    "connected case",
    "contact number",
    "corruption act",
    "cross case",
    "date from",
    "date of issue",
    "date of report",
    "date to",
    "day",
    "disclaimer",
    "district",
    "document details",
    "document id",
    "driving license",
    "economic offences",
    "eow special",
    "executive summary",
    "father's name",
    "field inspection",
    "first information",
    "geographic scope",
    "husband's name",
    "id details",
    "indian penal",
    "indian penal code",
    "information technology",
    "technology act",
    "information technology act",
    "initial known",
    "initial reconnaissance",
    "inquiry period",
    "investigation id",
    "investigation status",
    "item information",
    "known subject",
    "lead analyst",
    "lead investigator",
    "logistics contact",
    "monitoring team",
    "monitoring unit",
    "name",
    "nationality",
    "nature of complaint",
    "observation date",
    "observation details",
    "observation period",
    "observation summary",
    "observation timeline",
    "observed activity",
    "occupation",
    "passport",
    "passport no",
    "permanent address",
    "phone number",
    "place of issue",
    "place of occurrence",
    "police station",
    "police verification",
    "present address",
    "primary vehicle",
    "private employee",
    "ration card",
    "report date",
    "report reference",
    "scene",
    "section",
    "security classification",
    "source context",
    "special intelligence",
    "special squad",
    "state mumbai",
    "surveillance log",
    "synthetic data",
    "synthetic demonstration",
    "synthetic document",
    "target conduit",
    "target entity",
    "target location",
    "time of occurrence",
    "time period",
    "under section",
    "uid no",
    "verification report",
    "voter id card",
    "year",
}

_MONTHS = {month.lower(): index for index, month in enumerate((
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
), start=1)}
_MONTHS.update({month[:3].lower(): index for month, index in _MONTHS.items()})


def _normalise(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value.title() if re.search(r"[A-Za-z]", value) else value


def _mention(entity_type: str, text: str, normalized: str, confidence: float, start: int, end: int) -> dict[str, Any]:
    return {
        "mentionId": f"rule-{entity_type.lower()}-{start}",
        "type": entity_type,
        "text": text,
        "normalizedValue": normalized,
        "start": start,
        "end": end,
        "confidence": confidence,
    }


def extract_phone_numbers(text: str) -> list[dict[str, Any]]:
    pattern = r"(?<!\d)(?:(?:\+?91)[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"
    mentions = []
    for match in re.finditer(pattern, text):
        digits = re.sub(r"\D", "", match.group())
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if len(digits) == 10 and digits[0] in "6789":
            mentions.append(_mention("PHONE", match.group(), digits, 0.99, match.start(), match.end()))
    return mentions


def extract_vehicle_numbers(text: str) -> list[dict[str, Any]]:
    pattern = r"(?<![A-Za-z0-9])[A-Z]{2}[ -]?\d{2}[ -]?[A-Z]{1,3}[ -]?\d{4}(?![A-Za-z0-9])"
    return [
        _mention("VEHICLE", match.group(), re.sub(r"[ -]", "", match.group()).upper(), 0.98, match.start(), match.end())
        for match in re.finditer(pattern, text, flags=re.IGNORECASE)
    ]


def extract_case_ids(text: str) -> list[dict[str, Any]]:
    patterns = (
        r"\bFIR\s*(?:NO\.?|NUMBER)?\s*[:#-]?\s*(\d{1,5}[/-]\d{2,4})\b",
        r"\bCASE\s*(?:NO\.?|NUMBER)?\s*[:#-]?\s*(\d{1,5}[/-]\d{2,4})\b",
        r"\bCASE[- ]\d+\b",
    )
    mentions = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            normalized = match.group(1) if match.lastindex else re.sub(r"\s+", "-", match.group()).upper()
            mentions.append(_mention("CASE_ID", match.group(), normalized, 0.98, match.start(), match.end()))
    return mentions


def _normalise_date(day: str, month: str, year: str) -> str:
    numeric_year = int(year)
    if len(year) == 2:
        numeric_year += 2000
    return datetime(numeric_year, int(month), int(day)).date().isoformat()


def extract_dates(text: str) -> list[dict[str, Any]]:
    mentions = []
    numeric = r"\b(\d{1,2})([/.\-])(\d{1,2})\2(\d{2,4})\b"
    for match in re.finditer(numeric, text):
        try:
            normalized = _normalise_date(match.group(1), match.group(3), match.group(4))
        except ValueError:
            continue
        mentions.append(_mention("DATE", match.group(), normalized, 0.97, match.start(), match.end()))
    words = r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\b"
    for match in re.finditer(words, text, flags=re.IGNORECASE):
        try:
            normalized = _normalise_date(match.group(1), str(_MONTHS[match.group(2).lower()]), match.group(3))
        except (KeyError, ValueError):
            continue
        mentions.append(_mention("DATE", match.group(), normalized, 0.97, match.start(), match.end()))
    return mentions


def extract_money(text: str) -> list[dict[str, Any]]:
    pattern = "(?<![A-Za-z])(?:\u20b9|Rs" + r"\.?" + "|INR)" + r"\s*([0-9][0-9,]*(?:\.\d{1,2})?)(?![A-Za-z])"
    mentions = []
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        amount = Decimal(match.group(1).replace(",", ""))
        normalized_amount = format(amount, "f").rstrip("0").rstrip(".") if amount % 1 else str(int(amount))
        mentions.append(_mention("MONEY", match.group(), f"{normalized_amount} INR", 0.97, match.start(), match.end()))
    return mentions


GENERIC_HEADER_TOKENS = {
    "demonstration", "report", "summary", "reference", "status", "disclaimer",
    "table", "section", "sections", "police", "station", "details", "analysis",
    "heading", "inspection", "log", "information", "observation", "squad", "unit",
    "team", "authority", "classification", "scope", "statement", "circumstances",
    "complaint", "informant", "occurrence", "lead", "synthesis", "document", "notes"
}


def is_domain_label(value: str) -> bool:
    normalized = re.sub(r"\s+", " ", value).strip().casefold().rstrip(":")
    if normalized in DOMAIN_STOPLIST or any(label in normalized for label in DOMAIN_STOPLIST if len(label) > 5):
        return True
    tokens = set(re.findall(r"[a-z]+", normalized))
    if tokens and tokens.issubset(GENERIC_HEADER_TOKENS):
        return True
    if len(tokens) >= 2 and any(t in GENERIC_HEADER_TOKENS for t in tokens) and any(t in {"synthetic", "first", "initial", "known", "nature", "place", "date", "time", "lead", "report", "field", "observation", "surveillance", "item", "case", "investigation"} for t in tokens):
        return True
    return False

