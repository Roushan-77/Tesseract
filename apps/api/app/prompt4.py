import re
import unicodedata
from typing import Any


_DEVANAGARI = {
    "अ":"a", "आ":"aa", "इ":"i", "ई":"ee", "उ":"u", "ऊ":"oo", "ए":"e", "ऐ":"ai", "ओ":"o", "औ":"au",
    "क":"k", "ख":"kh", "ग":"g", "घ":"gh", "च":"ch", "छ":"chh", "ज":"j", "झ":"jh", "ट":"t", "ठ":"th", "ड":"d", "ढ":"dh", "ण":"n",
    "त":"t", "थ":"th", "द":"d", "ध":"dh", "न":"n", "प":"p", "फ":"ph", "ब":"b", "भ":"bh", "म":"m", "य":"y", "र":"r", "ल":"l", "व":"v",
    "श":"sh", "ष":"sh", "स":"s", "ह":"h", "ळ":"l", "ं":"n", "ः":"h", "़":"", "्":"", "ा":"a", "ि":"i", "ी":"i", "ु":"u", "ू":"u", "े":"e", "ै":"ai", "ो":"o", "ौ":"au",
}
_RELATION_RULES = (
    ("CONTACTED", r"\b(contacted|called|spoke\s+to|communicated\s+with)\b|ने\s+.*?से\s+संपर्क", 0.84),
    ("MET", r"\b(met|meeting|met\s+with)\b|ने\s+.*?से\s+मुलाकात", 0.82),
    ("VISITED", r"\b(visited|went\s+to|travelled\s+to)\b|गया|गई|भ्रमण", 0.88),
    ("WORKED_FOR", r"\b(worked\s+for|employee\s+of)\b", 0.80),
    ("USED", r"\b(used|using)\b", 0.76),
    ("OBSERVED", r"\b(observed|seen|spotted)\b", 0.78),
)
_CONSONANTS = set("कखगघचछजझटठडढणतथदधनपफबभमयरलवशषसहळ")
_MATRAS = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "े": "e", "ै": "ai", "ो": "o", "ौ": "au"}


def transliteration_key(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    result: list[str] = []
    chars = list(value)
    index = 0
    while index < len(chars):
        char = chars[index]
        if char in _CONSONANTS:
            result.append(_DEVANAGARI[char])
            next_char = chars[index + 1] if index + 1 < len(chars) else ""
            if next_char in _MATRAS:
                result.append(_MATRAS[next_char])
                index += 2
                continue
            if next_char not in {"", "्"} and not next_char.isspace() and not unicodedata.category(next_char).startswith("P"):
                result.append("a")
        elif char != "्":
            result.append(_DEVANAGARI.get(char, char))
        index += 1
    return re.sub(r"[^a-z0-9]+", "", "".join(result))


def resolution_suggestion(source: dict[str, Any], target: dict[str, Any]) -> dict[str, Any] | None:
    if source["type"] != target["type"] or source["type"] not in {"PERSON", "PHONE", "VEHICLE", "ORGANIZATION", "LOCATION"}:
        return None
    source_val = source.get("normalizedValue", "").strip()
    target_val = target.get("normalizedValue", "").strip()
    if not source_val or not target_val:
        return None

    # Exact transliteration match
    source_key = transliteration_key(source_val)
    target_key = transliteration_key(target_val)
    if source_key and source_key == target_key:
        if source["type"] in {"PHONE", "VEHICLE"}:
            return {"confidence": 1.0, "reasons": ["exact normalized identifier match"]}
        elif source["text"] != target["text"]:
            return {"confidence": 0.87, "reasons": ["transliterated name similarity"]}
        else:
            return {"confidence": 0.55, "reasons": ["same normalized name only; manual review required"]}

    # Person initial + surname matching (e.g. "R. Mehta" / "R Mehta" vs "Rohan Mehta")
    if source["type"] == "PERSON":
        s_parts = re.sub(r"[^\w\s]", " ", source_val).split()
        t_parts = re.sub(r"[^\w\s]", " ", target_val).split()
        if len(s_parts) >= 2 and len(t_parts) >= 2:
            # Check if surnames match and one of the first names is an initial
            if s_parts[-1].casefold() == t_parts[-1].casefold():
                if (len(s_parts[0]) == 1 and s_parts[0].casefold() == t_parts[0][0].casefold()) or \
                   (len(t_parts[0]) == 1 and t_parts[0].casefold() == s_parts[0][0].casefold()):
                    return {
                        "confidence": 0.88,
                        "reasons": ["High name similarity", "Shared surname with matching first initial", "Candidate entity match"]
                    }

    # Organization substring match (e.g. "Apex Logistics" vs "Apex Logistics Mumbai")
    if source["type"] == "ORGANIZATION":
        s_clean = re.sub(r"[^\w\s]", "", source_val).casefold()
        t_clean = re.sub(r"[^\w\s]", "", target_val).casefold()
        if (s_clean in t_clean or t_clean in s_clean) and len(min(s_clean, t_clean, key=len)) >= 6:
            return {
                "confidence": 0.91,
                "reasons": ["Substring match on organization name", "Matching primary organization brand", "Candidate entity match"]
            }

    return None


def _sentences(text: str) -> list[tuple[int, str]]:
    return [(match.start(), match.group().strip()) for match in re.finditer(r"[^.!?\n]+(?:[.!?]|$)", text)]


def extract_relations_and_events(text: str, mentions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    relations: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for sentence_start, sentence in _sentences(text):
        local = [mention for mention in mentions if sentence_start <= mention["start"] < sentence_start + len(sentence)]
        people = [mention for mention in local if mention["type"] == "PERSON"]
        locations = [mention for mention in local if mention["type"] == "LOCATION"]
        date = next((mention["normalizedValue"] for mention in local if mention["type"] == "DATE"), None)
        for relation_type, pattern, confidence in _RELATION_RULES:
            if not re.search(pattern, sentence, flags=re.IGNORECASE):
                continue
            if len(people) >= 2:
                source, target = people[0], people[1]
                relations.append({"type": relation_type, "source": source, "target": target, "sourceText": sentence, "confidence": confidence})
                if relation_type == "MET":
                    events.append({"type": "MEETING", "date": date, "location": locations[0] if locations else None, "participants": people[:], "sourceText": sentence, "confidence": confidence})
            elif relation_type in {"VISITED", "OBSERVED"} and people and locations:
                relations.append({"type": relation_type, "source": people[0], "target": locations[0], "sourceText": sentence, "confidence": confidence})
                events.append({"type": "VISIT" if relation_type == "VISITED" else "OBSERVATION", "date": date, "location": locations[0], "participants": people[:], "sourceText": sentence, "confidence": confidence})
    return relations, events
