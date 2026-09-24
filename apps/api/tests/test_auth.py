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

    def test_demo_password_synchronization_and_verification(self):
        # Verify that whatever settings.demo_password is set to, INV-017 verifies against it
        user = self.db.query(User).filter(User.investigator_id == "INV-017").first()
        self.assertIsNotNone(user)
        # Update user's hash as seed does
        user.password_hash = hash_password(settings.demo_password)
        self.db.commit()

        # Login with active DEMO_PASSWORD
        req = LoginRequest(investigator_id="INV-017", password=settings.demo_password)
        res = login(req, self.db)
        self.assertEqual(res.user.investigator_id, "INV-017")

        # Login with wrong password must fail
        req_bad = LoginRequest(investigator_id="INV-017", password="wrong-" + settings.demo_password)
        with self.assertRaises(HTTPException):
            login(req_bad, self.db)


if __name__ == "__main__":
    unittest.main()

