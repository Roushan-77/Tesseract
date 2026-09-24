import unittest
from fastapi import HTTPException
from app.config import settings
from app.database import SessionLocal
from app.main import login
from app.models import User
from app.schemas import LoginRequest
from app.security import hash_password, verify_password


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
        req = LoginRequest(investigator_id="INV-017", password=settings.demo_password)
        result = login(req, self.db)
        self.assertIsNotNone(result.access_token)
        self.assertEqual(result.user.investigator_id, "INV-017")
        self.assertEqual(result.user.role, "LEAD_INVESTIGATOR")

    def test_login_failure_with_wrong_password(self):
        req = LoginRequest(investigator_id="INV-017", password="wrong-password-123")
        with self.assertRaises(HTTPException) as ctx:
            login(req, self.db)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Invalid investigator ID or password", ctx.exception.detail)

    def test_login_failure_with_unknown_investigator(self):
        req = LoginRequest(investigator_id="INV-UNKNOWN-999", password=settings.demo_password)
        with self.assertRaises(HTTPException) as ctx:
            login(req, self.db)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Invalid investigator ID or password", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()

