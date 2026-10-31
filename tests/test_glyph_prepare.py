"""Optional preparation dependency tests; CI has a dedicated real-Glyph job."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

HAS_DEPS = bool(importlib.util.find_spec('fontTools') and importlib.util.find_spec('pathops'))
HAS_GLYPH = bool(importlib.util.find_spec('flamoris_glyph'))


@unittest.skipUnless(HAS_DEPS, 'optional Glyph preparation dependencies absent')
class PreparationTests(unittest.TestCase):
    def test_nonzero_holes_overlap_and_curve_conversion(self):
        from flamoris_cinema.glyph_prepare import path_commands
        from flamoris_cinema.glyph_blender import check_fill_topology
        from fontTools.pens.areaPen import AreaPen
        from fontTools.svgLib.path import parse_path
        from fontTools.pens.svgPathPen import SVGPathPen
        from fontTools.pens.recordingPen import RecordingPen
        # Same-winding inner contour remains filled, opposite winding is a hole.
        outer = 'M100 100L900 100L900 900L100 900Z'
        examples = [(outer+'M300 300L700 300L700 700L300 700Z',640000),
                    (outer+'M300 300L300 700L700 700L700 300Z',480000),
                    ('M100 100L900 900L900 100L100 900Z',320000)]
        for source, area in examples:
            commands = path_commands(source)
            if source == examples[-1][0]:
                # PathOps can produce point-touching components; this first
                # native adapter rejects that boundary instead of mis-filling.
                with self.assertRaisesRegex(ValueError, 'intersecting'):
                    check_fill_topology(commands)
            else:
                check_fill_topology(commands)
            pen = AreaPen(None)
            for cmd in commands:
                {'M':pen.moveTo, 'L':pen.lineTo, 'C':pen.curveTo, 'Z':pen.closePath}[cmd[0]](
                    *[tuple(cmd[i:i+2]) for i in range(1,len(cmd),2)])
            self.assertAlmostEqual(abs(pen.value), area, places=2)
        curves = path_commands('M100 100 Q200 0 300 100 L300 300 L100 300Z')
        self.assertTrue(any(c[0]=='C' for c in curves))
        self.assertFalse(any(c[0]=='Q' for c in curves))

    @unittest.skipUnless(HAS_GLYPH and os.environ.get('GLYPH_SOURCE'), 'set GLYPH_SOURCE to pinned Glyph checkout for real bundle integration')
    def test_real_bundle_immutable_import_and_tamper_rejection(self):
        from flamoris_glyph.bundle import compile_bundle, write_bundle
        from flamoris_glyph.geometry import SkeletonSource
        from flamoris_glyph.lyrics import parse_cues
        from flamoris_glyph.style import StyleDNA
        from flamoris_cinema.glyph_prepare import prepare_asset, stage_take
        from flamoris_cinema.interchange import validate_take
        source_root = Path(os.environ['GLYPH_SOURCE'])
        source = SkeletonSource(json.loads((source_root/'examples/skeletons.json').read_text()))
        style = StyleDNA.from_dict(json.loads((source_root/'examples/tango.style.json').read_text()))
        cues = parse_cues((source_root/'examples/demo.srt').read_text(), srt=True)
        manifest, assets = compile_bundle(cues,source,song='Cinema Glyph source fixture',style=style,seed=42)
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)/'bundle';write_bundle(bundle,manifest,assets)
            before = {str(p.relative_to(bundle)):hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.rglob('*') if p.is_file()}
            asset,color = prepare_asset(bundle,'cue0002-char0001')
            validate_take(stage_take(asset,color))
            after = {str(p.relative_to(bundle)):hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.rglob('*') if p.is_file()}
            self.assertEqual(before,after)
            self.assertEqual(asset['data']['svg_sha256'], '7eb51f6adf0bd7c7dc97c49473f970b2dc41f9c891a34becd227d8ab88b22f30')
            fixture = json.loads((Path(__file__).resolve().parents[1]/'examples/red_glyph.take.json').read_text())
            self.assertEqual(asset['data']['paths'], fixture['scene']['actors'][0]['geometry']['asset']['data']['paths'])
            with self.assertRaisesRegex(ValueError,'occurrence'):
                prepare_asset(bundle,'missing')
            path = bundle/manifest['glyphs'][0]['asset'];path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'SHA'):
                prepare_asset(bundle,'cue0002-char0001')
