import os
from pathlib import Path
import shutil
import subprocess
import unittest

BLENDER = os.environ.get('BLENDER') or shutil.which('blender')


@unittest.skipUnless(BLENDER, 'Blender unavailable; set BLENDER to run real adapter acceptance')
class BlenderTests(unittest.TestCase):
    def test_real_glyph_roundtrip(self):
        script = Path(__file__).with_name('blender_glyph_acceptance.py').resolve()
        result = subprocess.run([BLENDER, '-b', '--factory-startup', '--python-exit-code', '1',
                                 '--python', str(script)], capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('CINEMA_GLYPH_ACCEPTANCE_OK', result.stdout)

    def test_real_roundtrip(self):
        script = Path(__file__).with_name('blender_acceptance.py').resolve()
        result = subprocess.run([BLENDER, '-b', '--factory-startup', '--python-exit-code', '1',
                                 '--python', str(script)], capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('CINEMA_BLENDER_ACCEPTANCE_OK', result.stdout)
