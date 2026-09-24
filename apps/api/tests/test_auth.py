import unittest
from fastapi import HTTPException
from app.config import settings
from app.database import SessionLocal
from app.main import cases, login, me
from app.models import AuditEvent, User
from app.schemas import LoginRequest
from app.security import current_user, hash_password, token_for, verify_password


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_password_hashing_and_verification(self):
        pw = "custom-secure-password"
        hashed = hash_password(pw)
        self.assertNotEqual(pw, hashed)
        self.assertTrue(verify_password(pw, hashed))
        self.assertFalse(verify_password("wrong-password", hashed))

    def test_seeded_user_stored_hash_is_not_plaintext(self):
        user = self.db.query(User).filter(User.investigator_id == "INV-017").first()
        self.assertIsNotNone(user)
        self.assertNotEqual(user.password_hash, settings.demo_password)
        self.assertTrue(verify_password(settings.demo_password, user.password_hash))

    def test_login_success_with_demo_password(self):
        settings.demo_mode = False
        req = LoginRequest(investigator_id="INV-017", password=settings.demo_password)
        result = login(req, self.db)
        self.assertIsNotNone(result.access_token)
        self.assertEqual(result.user.investigator_id, "INV-017")
        self.assertEqual(result.user.role, "LEAD_INVESTIGATOR")

    def test_login_failure_with_wrong_password_when_demo_mode_false(self):
        settings.demo_mode = False
        req = LoginRequest(investigator_id="INV-017", password="wrong-password-123")
        with self.assertRaises(HTTPException) as ctx:
            login(req, self.db)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Invalid investigator ID or password", ctx.exception.detail)

    def test_demo_mode_true_authenticates_valid_investigator(self):
        settings.demo_mode = True
        try:
            req = LoginRequest(investigator_id="INV-017", password="any-entered-password")
            result = login(req, self.db)
            self.assertIsNotNone(result.access_token)
            self.assertEqual(result.user.investigator_id, "INV-017")
            self.assertEqual(result.user.role, "LEAD_INVESTIGATOR")

            # Check audit event logged
            last_audit = (
                self.db.query(AuditEvent)
                .filter(AuditEvent.actor_id == result.user.id, AuditEvent.action == "LOGIN_SUCCESS")
                .order_by(AuditEvent.timestamp.desc())
                .first()
            )
            self.assertIsNotNone(last_audit)
        finally:
            settings.demo_mode = False

    def test_demo_mode_true_still_rejects_unknown_investigator(self):
        settings.demo_mode = True
        try:
            req = LoginRequest(investigator_id="INV-UNKNOWN-999", password="any-password")
            with self.assertRaises(HTTPException) as ctx:
                login(req, self.db)
            self.assertEqual(ctx.exception.status_code, 401)
        finally:
            settings.demo_mode = False

    def test_authenticated_inv017_can_access_protected_resources(self):
        user = self.db.query(User).filter(User.investigator_id == "INV-017").first()
        self.assertIsNotNone(user)
        # Test /me endpoint with authenticated user
        user_out = me(u=user)
        self.assertEqual(user_out.investigator_id, "INV-017")
        self.assertEqual(user_out.role, "LEAD_INVESTIGATOR")

        # Test /cases endpoint with authenticated user (RBAC)
        assigned_cases = cases(status=None, priority=None, search=None, db=self.db, u=user)
        self.assertTrue(len(assigned_cases) > 0)

    def test_demo_password_synchronization_and_verification(self):
        user = self.db.query(User).filter(User.investigator_id == "INV-017").first()
        self.assertIsNotNone(user)
        user.password_hash = hash_password(settings.demo_password)
        self.db.commit()

        req = LoginRequest(investigator_id="INV-017", password=settings.demo_password)
        res = login(req, self.db)
        self.assertEqual(res.user.investigator_id, "INV-017")


if __name__ == "__main__":
    unittest.main()
