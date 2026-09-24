import hashlib
import tempfile
import unittest
from pathlib import Path

from app.integrity import sha256_file


class IntegrityTests(unittest.TestCase):
    def test_sha256_is_based_on_file_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.bin"
            data = b"evidence bytes"
            path.write_bytes(data)
            digest, size = sha256_file(path)
        self.assertEqual(digest, hashlib.sha256(data).hexdigest())
        self.assertEqual(size, len(data))

    def test_changed_bytes_produce_different_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.bin"
            path.write_bytes(b"original")
            original, _ = sha256_file(path)
            path.write_bytes(b"modified")
            modified, _ = sha256_file(path)
        self.assertNotEqual(original, modified)


if __name__ == "__main__":
    unittest.main()
