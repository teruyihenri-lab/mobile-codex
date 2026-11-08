import base64
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import io
import urllib.error
from unittest.mock import patch
import unittest

spec = importlib.util.spec_from_file_location('runtime', Path(__file__).parents[1] / 'tools/prepare_runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

class PackagingTests(unittest.TestCase):
    def test_runtime_download_retries_504_and_verifies_integrity(self):
        data=b'approved runtime archive'
        integrity='sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode()
        with tempfile.TemporaryDirectory() as directory:
            archive=Path(directory)/'archive.tgz'
            failing=urllib.error.HTTPError('https://example.test/asset',504,'Gateway Timeout',{},None)
            with patch.object(runtime.urllib.request,'urlopen',side_effect=[failing,io.BytesIO(data)]) as get, patch.object(runtime.time,'sleep') as sleep:
                runtime.download_runtime('https://example.test/asset',archive,integrity)
            self.assertEqual(get.call_count,2)
            sleep.assert_called_once()
            self.assertEqual(archive.read_bytes(),data)
            self.assertFalse(archive.with_suffix('.partial').exists())

    def test_runtime_download_rejects_wrong_hash_and_non_retryable_404(self):
        data=b'wrong runtime bytes'
        integrity='sha512-' + base64.b64encode(hashlib.sha512(b'approved').digest()).decode()
        with tempfile.TemporaryDirectory() as directory:
            archive=Path(directory)/'archive.tgz'
            with patch.object(runtime.urllib.request,'urlopen',return_value=io.BytesIO(data)):
                with self.assertRaisesRegex(ValueError,'checksum mismatch'):
                    runtime.download_runtime('https://example.test/asset',archive,integrity)
            self.assertFalse(archive.exists())
            self.assertFalse(archive.with_suffix('.partial').exists())
            missing=urllib.error.HTTPError('https://example.test/asset',404,'Missing',{},None)
            with patch.object(runtime.urllib.request,'urlopen',side_effect=missing) as get:
                with self.assertRaises(urllib.error.HTTPError):
                    runtime.download_runtime('https://example.test/asset',archive,integrity)
            self.assertEqual(get.call_count,1)

    def test_runtime_retrieves_same_sha512_archive_via_pinned_github_asset_api(self):
        data=b'verified runtime bytes'
        integrity='sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode()
        missing=urllib.error.HTTPError('https://github.com/example/project/releases/download/tag/a.tgz',504,'Gateway timeout',{},None)
        with tempfile.TemporaryDirectory() as directory:
            archive=Path(directory)/'runtime.tgz'
            with patch.object(runtime.urllib.request,'urlopen',side_effect=[missing,missing,missing,io.BytesIO(data)]) as get, patch.object(runtime.time,'sleep'):
                runtime.download_runtime('https://github.com/example/project/releases/download/tag/a.tgz',archive,integrity,retries=3,github_asset_id=1234)
            self.assertEqual(get.call_count,4)
            self.assertTrue(get.call_args.args[0].full_url.endswith('/repos/example/project/releases/assets/1234'))
            self.assertEqual(archive.read_bytes(),data)

    def test_archive_integrity_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'runtime.tgz'
            path.write_bytes(b'approved archive')
            integrity = 'sha512-' + base64.b64encode(hashlib.sha512(path.read_bytes()).digest()).decode()
            runtime.verify(path, integrity)
            path.write_bytes(b'changed archive')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                runtime.verify(path, integrity)

    def test_host_patch_preserves_offsets_and_refuses_new_layouts(self):
        original = b'ELFprefix\0codex-code-mode-host\0padding\0codex-code-mode-host\0suffix'
        patched = runtime.patch_host_name(original)
        self.assertEqual(len(original), len(patched))
        self.assertEqual(original, patched.replace(b'libcodexmodehostx.so', b'codex-code-mode-host'))
        with self.assertRaises(ValueError):
            runtime.patch_host_name(b'new unknown binary')

    def test_reviewed_0162_layout_requires_three_fixed_width_replacements(self):
        original = b'ELF\0' + b'codex-code-mode-host\0' * 3
        with self.assertRaises(ValueError):
            runtime.patch_host_name(original)
        patched = runtime.patch_host_name(original, expected_occurrences=3)
        self.assertEqual(len(original), len(patched))
        self.assertEqual(patched.count(b'libcodexmodehostx.so'), 3)

if __name__ == '__main__':
    unittest.main()
