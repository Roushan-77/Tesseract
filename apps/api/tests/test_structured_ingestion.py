import json
import tempfile
import unittest
from pathlib import Path

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

from app.structured_ingestion import process_structured


class StructuredIngestionTests(unittest.TestCase):
    def test_csv_cdr_creates_contact_and_call(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cdr.csv"
            path.write_text("timestamp,caller,receiver,duration,cell_tower\n2026-06-12T10:32,9876543210,9123456789,245,Indore-Tower-04\n", encoding="utf-8")
            result = process_structured(path, "text/csv")
        self.assertEqual(result["structured"]["row_count"], 1)
        self.assertEqual(result["relations"][0]["type"], "CONTACTED")
        self.assertEqual(result["events"][0]["type"], "CALL")
        self.assertEqual(result["relations"][0]["sourceRow"], 2)

    def test_json_records_parse(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "social.json"
            path.write_text(json.dumps({"records": [{"username": "rahul", "location": "Indore"}]}), encoding="utf-8")
            result = process_structured(path, "application/json")
        self.assertEqual(result["structured"]["row_count"], 1)
        self.assertEqual({item["type"] for item in result["entities"]}, {"PERSON", "LOCATION"})

    @unittest.skipIf(Workbook is None, "openpyxl not installed")
    def test_xlsx_multiple_sheets_are_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transactions.xlsx"
            workbook = Workbook()
            workbook.active.append(["sender_account", "receiver_account", "amount"])
            workbook.active.append(["AC001", "AC009", 500000])
            second = workbook.create_sheet("Second")
            second.append(["name"])
            second.append(["Rahul Sharma"])
            workbook.save(path)
            result = process_structured(path, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertEqual(result["structured"]["row_count"], 2)
        self.assertEqual(result["events"][0]["type"], "TRANSACTION")


    def test_vehicle_movement_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "movement.csv"
            path.write_text("timestamp,vehicle_number,location,driver\n2026-08-20T08:42:15,MH-04-KT-2187,Warehouse 14,Sunil Deshmukh\n", encoding="utf-8")
            result = process_structured(path, "text/csv")
        self.assertEqual(result["structured"]["row_count"], 1)
        rel_types = {r["type"] for r in result["relations"]}
        self.assertIn("VISITED", rel_types)
        self.assertIn("OPERATED", rel_types)
        self.assertEqual(result["events"][0]["type"], "MOVEMENT")


if __name__ == "__main__":
    unittest.main()

