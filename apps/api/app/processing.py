import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pdfplumber
import pytesseract
from PIL import Image
try:
    from docx import Document
except ImportError:
    Document = None

from .config import settings
from .extraction_rules import (
    extract_case_ids,
    extract_dates,
    extract_money,
    extract_phone_numbers,
    extract_vehicle_numbers,
    is_domain_label,
)
from .prompt4 import extract_relations_and_events
from .structured_ingestion import process_structured


class ProcessingError(Exception):
    pass


def _configure_ocr() -> tuple[list[str], list[str]]:
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    try:
        available = set(pytesseract.get_languages(config=""))
    except (OSError, pytesseract.TesseractNotFoundError) as exc:
        raise ProcessingError("OCR engine is unavailable. Install Tesseract OCR or set TESSERACT_CMD.") from exc
    requested = [language.strip() for language in settings.tesseract_lang.split("+") if language.strip()]
    usable = [language for language in requested if language in available]
    if "eng" in available and not usable:
        usable = ["eng"]
    if not usable:
        raise ProcessingError("No configured Tesseract language data is installed.")
    warnings = [f"Configured OCR language data missing: {language}." for language in requested if language not in available]
    return usable, warnings


def _ocr_image(image: Image.Image, languages: list[str]) -> str:
    return pytesseract.image_to_string(image, lang="+".join(languages), config="--psm 6").strip()


def _pdf_pages(path: Path, languages: list[str]) -> tuple[list[str], list[str]]:
    pages: list[str] = []
    warnings: list[str] = []
    rasterizer = settings.pdftoppm_cmd or "pdftoppm"
    with pdfplumber.open(path) as document:
        for page_number, page in enumerate(document.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(text)
                continue
            with tempfile.TemporaryDirectory(prefix="tesseract-pdf-") as directory:
                prefix = str(Path(directory) / "page")
                command = [rasterizer, "-f", str(page_number), "-l", str(page_number), "-png", "-r", "200", str(path), prefix]
                try:
                    subprocess.run(command, check=True, capture_output=True, text=True)
                except FileNotFoundError as exc:
                    raise ProcessingError("PDF OCR requires pdftoppm. Install Poppler or set PDFTOPPM_CMD.") from exc
                except subprocess.CalledProcessError as exc:
                    raise ProcessingError(f"Could not render PDF page {page_number} for OCR.") from exc
                images = sorted(Path(directory).glob("page-*.png"))
                if not images:
                    raise ProcessingError(f"Could not render PDF page {page_number} for OCR.")
                with Image.open(images[0]) as image:
                    pages.append(_ocr_image(image, languages))
                    if not pages[-1]:
                        warnings.append(f"No text detected on PDF page {page_number}.")
    return pages, warnings


def ocr_file(path: Path, mime_type: str) -> tuple[list[str], list[str]]:
    if path.suffix.lower() == ".txt" or mime_type == "text/plain":
        try:
            return [path.read_text(encoding="utf-8-sig")], []
        except UnicodeDecodeError as exc:
            raise ProcessingError("The uploaded text file is not valid UTF-8.") from exc
        except OSError as exc:
            raise ProcessingError("The uploaded text file could not be read.") from exc
    if path.suffix.lower() == ".docx" or mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        try:
            document = Document(path)
            text = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text).strip()
            return [text], []
        except Exception as exc:
            raise ProcessingError("The uploaded DOCX file could not be read.") from exc
    if path.suffix.lower() == ".doc" or mime_type == "application/msword":
        converter = shutil.which("antiword")
        if not converter:
            raise ProcessingError("Legacy DOC processing requires antiword or conversion to DOCX.")
        try:
            result = subprocess.run([converter, str(path)], check=True, capture_output=True, text=True)
            return [result.stdout.strip()], []
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ProcessingError("The uploaded DOC file could not be read.") from exc
    languages, warnings = _configure_ocr()
    if mime_type == "application/pdf" or path.suffix.lower() == ".pdf":
        pages, page_warnings = _pdf_pages(path, languages)
        return pages, warnings + page_warnings
    try:
        with Image.open(path) as image:
            return [_ocr_image(image, languages)], warnings
    except (OSError, ValueError) as exc:
        raise ProcessingError("The uploaded image could not be read for OCR.") from exc


def detect_language(text: str) -> tuple[str, float]:
    devanagari = len(re.findall(r"[\u0900-\u097F]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    total = devanagari + latin
    if not total:
        return "unknown", 0.0
    if devanagari and latin and min(devanagari, latin) / total >= 0.1:
        return "mixed", round(max(devanagari, latin) / total, 2)
    if devanagari:
        return "hi", round(devanagari / total, 2)
    return "en", round(latin / total, 2)


def _normalise(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value.title() if re.search(r"[A-Za-z]", value) else value


def _add_entity(entities: list[dict[str, Any]], text: str, entity_type: str, confidence: float, start: int, end: int):
    key = (start, end, entity_type)
    if any((item["start"], item["end"], item["type"]) == key for item in entities):
        return
    entities.append({"mentionId": f"m-{len(entities) + 1}", "type": entity_type, "text": text, "normalizedValue": _normalise(text), "start": start, "end": end, "confidence": confidence})


def extract_entities(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    entities: list[dict[str, Any]] = []
    for rule in (extract_phone_numbers, extract_vehicle_numbers, extract_case_ids, extract_dates, extract_money):
        entities.extend(rule(text))

    location_suffixes = {"apartment", "city", "link", "nagar", "road", "east", "west", "warehouse", "district"}
    person_patterns = [
        r"\b[A-Z]\.?\s+[A-Z][a-z]+\b",
        r"\b[A-Z][a-z]+[ \t]+[A-Z][a-z]+\b",
        r"[\u0900-\u097F]+(?:\s+[\u0900-\u097F]+){1,3}(?=\s+(?:ने|से|को|का|की|में|और))",
    ]
    for pattern in person_patterns:
        for match in re.finditer(pattern, text):
            value = match.group()
            words = value.casefold().split()
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            line = text[line_start:] if line_end == -1 else text[line_start:line_end]
            if is_domain_label(value) or re.search(r"address|accused|id details|place of occurrence|near ", line, re.IGNORECASE):
                continue
            if words[-1] in location_suffixes:
                _add_entity(entities, value, "LOCATION", 0.76, match.start(), match.end())
                continue
            _add_entity(entities, value, "PERSON", 0.78, match.start(), match.end())

    for match in re.finditer(r"(?im)^\s*(?:district|p\.?s\.?|police station|address|place)\s*[:\-]\s*([^\n]+)", text):
        value = match.group(1).strip()
        if not is_domain_label(value):
            start = match.start(1) + len(match.group(1)) - len(match.group(1).lstrip())
            _add_entity(entities, value, "LOCATION", 0.88, start, start + len(value))

    for match in re.finditer(r"(?im)^\s*(?:name|father['’]s name|husband['’]s name)\s*[:\-]\s*([^\n]+)", text):
        value = match.group(1).strip()
        if not is_domain_label(value):
            start = match.start(1) + len(match.group(1)) - len(match.group(1).lstrip())
            _add_entity(entities, value, "PERSON", 0.9, start, start + len(value))

    context_patterns = [
        ("LOCATION", r"\b(?:in|at|near|from)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)", 0.72),
        ("LOCATION", r"(?:में|पर|से)\s+([\u0900-\u097F]+(?:\s+[\u0900-\u097F]+)?)", 0.72),
        ("ORGANIZATION", r"\b([A-Z][A-Za-z]+\s+(?:Logistics|Company|Corporation|Corp|Ltd))\b", 0.84),
    ]
    for entity_type, pattern, confidence in context_patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = match.group(1)
            start = match.start(1)
            if not is_domain_label(value):
                _add_entity(entities, value, entity_type, confidence, start, start + len(value))

    entities.sort(key=lambda item: (item["start"], item["end"]))
    for index, entity in enumerate(entities, start=1):
        entity["mentionId"] = f"m-{index}"
    warnings = ["No entities detected."] if not entities else []
    return entities, warnings


def process_document(path: Path, mime_type: str) -> dict[str, Any]:
    if path.suffix.lower() in {".csv", ".xls", ".xlsx", ".json", ".xml"}:
        try:
            return process_structured(path, mime_type)
        except ValueError as exc:
            raise ProcessingError(str(exc)) from exc
    pages, warnings = ocr_file(path, mime_type)
    text = "\n\n".join(page for page in pages if page).strip()
    language_code, language_confidence = detect_language(text)
    entities, entity_warnings = extract_entities(text)
    warnings.extend(entity_warnings)
    categories: dict[str, list[dict[str, Any]]] = {}
    for entity in entities:
        bucket = categories.setdefault(entity["type"], [])
        if not any(item["normalizedValue"] == entity["normalizedValue"] for item in bucket):
            bucket.append(entity)
    relations, events = extract_relations_and_events(text, entities)
    return {"language": {"code": language_code, "confidence": language_confidence}, "text": text, "pages": pages, "entities": entities, "categories": categories, "relations": relations, "events": events, "warnings": warnings}