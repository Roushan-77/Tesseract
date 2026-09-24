import unittest

from app.prompt4 import extract_relations_and_events, resolution_suggestion, transliteration_key


def mention(entity_type: str, text: str, start: int) -> dict:
    return {"type": entity_type, "text": text, "normalizedValue": text, "start": start, "end": start + len(text)}


class Prompt4Tests(unittest.TestCase):
    def test_hindi_english_name_suggestion_is_explainable(self):
        self.assertEqual(transliteration_key("राहुल शर्मा"), transliteration_key("Rahul Sharma"))
        suggestion = resolution_suggestion(mention("PERSON", "राहुल शर्मा", 0), mention("PERSON", "Rahul Sharma", 0))
        self.assertEqual(suggestion["confidence"], 0.87)
        self.assertIn("transliterated name similarity", suggestion["reasons"])

    def test_same_name_is_not_confirmed(self):
        suggestion = resolution_suggestion(mention("PERSON", "Rahul Sharma", 0), mention("PERSON", "Rahul Sharma", 0))
        self.assertEqual(suggestion["confidence"], 0.55)
        self.assertIn("manual review required", suggestion["reasons"][0])

    def test_identifier_matches_are_strong(self):
        suggestion = resolution_suggestion(mention("PHONE", "9876543210", 0), mention("PHONE", "9876543210", 0))
        self.assertEqual(suggestion["confidence"], 1.0)

    def test_relations_are_sentence_scoped_and_provenanced(self):
        text = "Rahul Sharma met Arjun Verma at the Indore warehouse on 12 June 2026."
        mentions = [mention("PERSON", "Rahul Sharma", 0), mention("PERSON", "Arjun Verma", 18), mention("LOCATION", "Indore warehouse", 36), mention("DATE", "12 June 2026", 62)]
        relations, events = extract_relations_and_events(text, mentions)
        self.assertEqual(relations[0]["type"], "MET")
        self.assertEqual(relations[0]["sourceText"], text)
        self.assertEqual(events[0]["type"], "MEETING")
        self.assertEqual(events[0]["date"], "12 June 2026")
        self.assertEqual(events[0]["location"]["text"], "Indore warehouse")


if __name__ == "__main__":
    unittest.main()
