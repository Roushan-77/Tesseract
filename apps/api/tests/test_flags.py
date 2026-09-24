import unittest
from app.database import SessionLocal
from app.main import create_case_flag, delete_case_flag, get_case_flags, resolve_case_flag
from app.models import InvestigationFlag, User
from app.schemas import FlagCreate, FlagResolve


class FlagsTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.user = self.db.query(User).filter(User.investigator_id == "INV-017").first()

    def tearDown(self):
        self.db.close()

    def test_flag_crud_lifecycle(self):
        self.assertIsNotNone(self.user)
        # 1. Create flag
        create_payload = FlagCreate(
            resource_type="ENTITY",
            resource_id="ent-test-001",
            resource_label="Test Suspicious Account",
            reason="Unusual high-frequency transfers detected",
        )
        flag_out = create_case_flag(n="CASE-001", p=create_payload, db=self.db, u=self.user)
        self.assertEqual(flag_out.resource_type, "ENTITY")
        self.assertEqual(flag_out.status, "ACTIVE")
        self.assertEqual(flag_out.flagged_by.investigator_id, "INV-017")
        flag_id = flag_out.id

        # 2. Get case flags
        flags = get_case_flags(n="CASE-001", db=self.db, u=self.user)
        flag_ids = [f.id for f in flags]
        self.assertIn(flag_id, flag_ids)

        # 3. Resolve flag
        resolve_payload = FlagResolve(
            resolution_notes="Verified with banking partner. Marked legitimate.",
            status="RESOLVED",
        )
        resolved_out = resolve_case_flag(n="CASE-001", fid=flag_id, p=resolve_payload, db=self.db, u=self.user)
        self.assertEqual(resolved_out.status, "RESOLVED")
        self.assertIsNotNone(resolved_out.resolved_at)
        self.assertEqual(resolved_out.resolved_by.investigator_id, "INV-017")

        # 4. Delete flag
        delete_res = delete_case_flag(n="CASE-001", fid=flag_id, db=self.db, u=self.user)
        self.assertEqual(delete_res["status"], "REMOVED")

        # Confirm deleted from DB
        deleted_flag = self.db.get(InvestigationFlag, flag_id)
        self.assertIsNone(deleted_flag)


if __name__ == "__main__":
    unittest.main()
