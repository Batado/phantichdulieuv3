import unittest

from modules.control_center import _normalize_database_url


class DatabaseUrlTests(unittest.TestCase):
    def test_raw_at_sign_in_password_is_encoded(self):
        raw = "postgresql://postgres:abc@123@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres?sslmode=require"
        normalized = _normalize_database_url(raw)
        self.assertIn("postgresql+psycopg://postgres:abc%40123@", normalized)
        self.assertIn("@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres", normalized)

    def test_already_encoded_password_is_not_double_encoded(self):
        raw = "postgresql://postgres:abc%40123@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
        normalized = _normalize_database_url(raw)
        self.assertIn("postgres:abc%40123@", normalized)
        self.assertNotIn("%2540", normalized)


if __name__ == "__main__":
    unittest.main()
