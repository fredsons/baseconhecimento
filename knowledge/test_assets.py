import io
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase,override_settings
from django.core.management import call_command,CommandError

class AssetTests(SimpleTestCase):
    def test_unknown_download_is_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp,override_settings(BASE_DIR=Path(tmp)),patch('urllib.request.urlopen',return_value=io.BytesIO(b'unexpected library')):
            with self.assertRaises(CommandError):call_command('prepare_assets',stdout=io.StringIO())
            self.assertFalse(list((Path(tmp)/'static'/'vendor').iterdir()))
    def test_check_does_not_download_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp,override_settings(BASE_DIR=Path(tmp)),patch('urllib.request.urlopen') as download:
            with self.assertRaises(CommandError):call_command('prepare_assets',check=True,stdout=io.StringIO())
            download.assert_not_called()
