import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

spec = importlib.util.spec_from_file_location('download_devtools', Path(__file__).parents[1] / 'tools' / 'prepare_devtools.py')
devtools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(devtools)

class PinnedDownloadTests(unittest.TestCase):
    def test_missing_primary_uses_mirror_only_for_identical_pinned_bytes(self):
        data = b'pinned bytes'
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'input.deb'
            url = devtools.POOL_URL + 'pool/input.deb'
            with patch.object(devtools.urllib.request, 'urlopen', side_effect=[urllib.error.HTTPError(url, 404, 'missing', {}, None), io.BytesIO(data)]) as request:
                devtools.download(url, dest, hashlib.sha256(data).hexdigest())
                self.assertEqual(dest.read_bytes(), data)
                self.assertIn('ro.mirror.flokinet.net', request.call_args_list[1].args[0])
    def test_wrong_mirror_bytes_are_never_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'input.deb'
            url = devtools.POOL_URL + 'pool/input.deb'
            with patch.object(devtools.urllib.request, 'urlopen', side_effect=[urllib.error.HTTPError(url, 404, 'missing', {}, None)] + [io.BytesIO(b'wrong') for _ in range(4)]):
                with self.assertRaises(devtools.PackagingError):
                    devtools.download(url, dest, hashlib.sha256(b'right').hexdigest())
            self.assertFalse(dest.exists())
            self.assertFalse(dest.with_suffix('.deb.partial').exists())

    def test_primary_and_first_mirror_missing_uses_archived_pinned_package(self):
        data = b'archived pinned bytes'
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'input.deb'
            url = devtools.POOL_URL + 'pool/input.deb'
            missing = urllib.error.HTTPError(url, 404, 'not found', {}, None)
            with patch.object(devtools.urllib.request, 'urlopen', side_effect=[missing, missing, io.BytesIO(data)]) as request:
                devtools.download(url, dest, hashlib.sha256(data).hexdigest())
                self.assertEqual(dest.read_bytes(), data)
                self.assertEqual(request.call_count, 3)
                self.assertIn('repository.su', request.call_args_list[2].args[0])

    def test_mirror_checksum_mismatch_continues_and_does_not_keep_wrong_bytes(self):
        data = b'expected exact package'
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'input.deb'
            url = devtools.POOL_URL + 'pool/input.deb'
            missing = urllib.error.HTTPError(url, 404, 'not found', {}, None)
            with patch.object(devtools.urllib.request, 'urlopen', side_effect=[
                missing, io.BytesIO(b'wrong package'), io.BytesIO(data)]) as request:
                devtools.download(url, dest, hashlib.sha256(data).hexdigest())
                self.assertEqual(request.call_count, 3)
                self.assertEqual(dest.read_bytes(), data)

    def test_all_mirrors_fail_without_leaving_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'input.deb'
            url = devtools.POOL_URL + 'pool/input.deb'
            missing = urllib.error.HTTPError(url, 404, 'not found', {}, None)
            with patch.object(devtools.urllib.request, 'urlopen', side_effect=[missing] * 5) as request:
                with self.assertRaises(devtools.PackagingError):
                    devtools.download(url, dest, hashlib.sha256(b'expected').hexdigest())
                self.assertEqual(request.call_count, 5)
                self.assertFalse(dest.exists())
                self.assertFalse(dest.with_suffix('.deb.partial').exists())

    def test_live_packages_index_uses_https_mirror_on_network_outage(self):
        index = b'Package: fixture\nVersion: 1\nArchitecture: aarch64\n\n'
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'Packages'
            unreachable = urllib.error.URLError(OSError(101, 'Network is unreachable'))
            with patch.object(devtools.urllib.request, 'urlopen', side_effect=[unreachable, io.BytesIO(index)]) as request:
                devtools.download(devtools.INDEX_URL, dest)
                self.assertEqual(dest.read_bytes(), index)
                self.assertEqual(request.call_count, 2)
                self.assertIn('/dists/stable/main/binary-aarch64/Packages',
                              request.call_args_list[1].args[0])
                self.assertIn('ro.mirror.flokinet.net',
                              request.call_args_list[1].args[0])

    def test_live_index_fails_closed_when_every_termux_mirror_unreachable(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'Packages'
            network_error = urllib.error.URLError(OSError(101, 'Network is unreachable'))
            with patch.object(devtools.urllib.request, 'urlopen', side_effect=[network_error] * 5):
                with self.assertRaises(devtools.PackagingError):
                    devtools.download(devtools.INDEX_URL, dest)
                self.assertFalse(dest.exists())
                self.assertFalse(dest.with_suffix('.partial').exists())
