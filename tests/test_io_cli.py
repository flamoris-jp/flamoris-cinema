from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from flamoris_cinema.io import read_json, write_json
from test_core import SCENE


class IOTests(unittest.TestCase):
    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.json'
            for text in ['{"x":1,"x":2}', '{"x":NaN}', '[Infinity]', '{', '"\udcff"']:
                path.write_bytes(text.encode('utf-8', errors='surrogatepass'))
                with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                    read_json(path)

    def test_exclusive_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'output.json'
            write_json(path, {'hello': '赤'})
            with self.assertRaises(FileExistsError):
                write_json(path, {'changed': True})
            self.assertEqual(read_json(path), {'hello': '赤'})

    def test_cli_simulate_validate_reuse_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scene, output, reused = [root / f for f in ['scene.json', 'anim.json', 'reused.json']]
            write_json(scene, SCENE)
            command = [sys.executable, '-m', 'flamoris_cinema.core', str(scene)]
            subprocess.run(command + ['--out', str(output)], check=True, capture_output=True)
            subprocess.run(command + ['--animation', str(output), '--validate-only'], check=True, capture_output=True)
            subprocess.run(command + ['--animation', str(output), '--out', str(reused)], check=True, capture_output=True)
            self.assertEqual(read_json(output), read_json(reused))
            previous = output.read_bytes()
            result = subprocess.run(command + ['--out', str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), previous)
