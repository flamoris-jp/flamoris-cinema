"""Runner failure/collection tests. These do not emulate Blender acceptance."""
import importlib.util
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('cinema_smoke_runner', Path(__file__).resolve().parents[1] / 'tools/run_blender_smoke.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class SmokeRunnerTests(unittest.TestCase):
    def test_missing_executable_does_not_create_job(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'job'
            with self.assertRaisesRegex(ValueError, 'not found'):
                runner.run('missing-cinema-blender-7f1bd29', output)
            self.assertFalse(output.exists())

    def test_failed_process_keeps_receipt_and_logs(self):
        # A real Python process rejects Blender flags; never report this as a
        # native Blender test. This verifies the launcher's failure contract.
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'job'
            result = runner.run(sys.executable, output)
            self.assertFalse(result['success'])
            self.assertIn('exited', result['error'])
            self.assertGreater((output / 'blender.log').stat().st_size, 0)
            self.assertFalse(json.loads((output / 'receipt.json').read_text())['success'])
            with zipfile.ZipFile(output / 'cinema-smoke.zip') as archive:
                self.assertIn('blender.log', archive.namelist())
                self.assertIn('receipt.json', archive.namelist())
                self.assertIn('manifest.json', archive.namelist())
            with self.assertRaises(FileExistsError):
                runner.run(sys.executable, output)

    def test_timeout_is_failed_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'job'
            with patch.object(runner.subprocess, 'run', side_effect=subprocess.TimeoutExpired('Blender', 1)):
                result = runner.run(sys.executable, output, timeout=1)
            self.assertFalse(result['success'])
            self.assertIn('timed out', result['error'])
            self.assertTrue((output / 'cinema-smoke.zip').is_file())

    def test_zero_exit_without_result_is_not_success(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(runner.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
                result = runner.run(sys.executable, Path(temp) / 'job')
            self.assertFalse(result['success'])
            self.assertIn('result.json', result['error'])

    def test_native_container_variants(self):
        # Tiny file-signature fixtures, not Blender scene parsing/acceptance.
        raw = b'BLENDER17-01v0502' + b'fixture-only' * 8
        zstd = bytes.fromhex('28b52ffd2071250100e8424c454e44455231372d30317630353032666978747572652d6f6e6c790100c5a7e204')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'scene.blend'
            for container, payload in [('raw', raw), ('gzip', gzip.compress(raw)), ('zstd', zstd)]:
                with self.subTest(container=container):
                    path.write_bytes(payload)
                    self.assertEqual(runner.native_project_container(path), container)

    def test_native_container_rejects_other_files(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'scene.blend'
            for payload in [b'', b'BLENDER', b'not a Blender container' * 3]:
                path.write_bytes(payload)
                with self.subTest(payload=payload), self.assertRaises(ValueError):
                    runner.native_project_container(path)
