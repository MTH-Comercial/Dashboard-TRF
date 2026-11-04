"""Regression checks for private Transforma V6 staging database."""
import unittest
from unittest.mock import patch
from storage import DEFAULT_SHEET_ID, connect

V6_ID = "1_KEm7fLJpglz89vG-67hXIKrWOVSpcEkUXNILbSF1QE"
LEGACY_ID = "1LgXQeTJ4FK1h8VLGRWijU3oGaE_FNg5gBTuB6XhEiKI"

class StagingTargetTest(unittest.TestCase):
    def test_staging_default_is_native_v6(self):
        self.assertEqual(DEFAULT_SHEET_ID,V6_ID)
        self.assertNotEqual(DEFAULT_SHEET_ID, LEGACY_ID)

    def test_rejects_legacy_sheet_even_when_secrets_override(self):
        def fake_secret(key, default=None):
            if key == 'gcp_service_account': return {'type':'service_account'}
            if key == 'SHEET_ID': return LEGACY_ID
            return default
        with patch('storage.secret',side_effect=fake_secret), \
             patch('storage.gspread.service_account_from_dict') as creds:
            with self.assertRaisesRegex(RuntimeError, 'não é a V6'):
                connect()
            creds.assert_not_called()

if __name__ == '__main__':
    unittest.main()
