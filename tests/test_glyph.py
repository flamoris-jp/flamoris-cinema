from copy import deepcopy
import json
from pathlib import Path
import unittest
from flamoris_cinema.contracts import motion_id, validate_scene, validate_animation
from flamoris_cinema.core import simulate
from flamoris_cinema.framing import check_framing
from flamoris_cinema.glyph_asset import digest, validate_asset, local_bounds, srgb_color
from flamoris_cinema.glyph_blender import bezier_contours
from flamoris_cinema.interchange import make_take, validate_take
from flamoris_cinema.io import read_json

FIXTURE = Path(__file__).resolve().parents[1] / 'examples/red_glyph.take.json'


class GlyphTests(unittest.TestCase):
    def setUp(self):
        self.take = read_json(FIXTURE)
        self.scene = self.take['scene']
        self.asset = self.scene['actors'][0]['geometry']['asset']

    def test_real_source_identity_and_floor_mapping(self):
        validate_take(self.take)
        data = self.asset['data']
        self.assertEqual(data['occurrence']['character'], '赤')
        self.assertEqual(data['occurrence']['occurrence_id'], 'cue0002-char0001')
        self.assertEqual([p['source_id'] for p in data['paths']], ['s1','s2','s3','s4','s5','s6','s7'])
        self.assertEqual(data['cue']['start_ms'], 4000)
        low, high = local_bounds(self.scene['actors'][0]['geometry'])
        self.assertAlmostEqual(low[2]+self.scene['actors'][0]['position'][2], 0)
        self.assertAlmostEqual(high[1]-low[1], 0.12)
        self.assertTrue(check_framing(self.scene, self.take['animation'])['passed'])

    def test_camera_color_change_preserves_motion(self):
        original = motion_id(self.scene)
        self.scene['cameras'][0]['position'][0] += 1
        self.scene['actors'][0]['color'] = [0.1, 0.2, 0.3]
        self.assertEqual(motion_id(self.scene), original)
        validate_animation(self.take['animation'], self.scene)

    def test_geometry_change_requires_new_take(self):
        self.scene['actors'][0]['geometry']['depth'] = 0.2
        with self.assertRaisesRegex(ValueError, 'different performance'):
            validate_take(self.take)

    def test_no_sphere_physics_for_glyph(self):
        with self.assertRaisesRegex(ValueError, 'v1 sphere'):
            simulate(self.scene)

    def test_snapshot_integrity_and_strict_geometry(self):
        bad = deepcopy(self.asset)
        bad['data']['paths'][0]['commands'][0][1] += 1
        with self.assertRaisesRegex(ValueError, 'checksum'):
            validate_asset(bad)
        for edit in (lambda d: d['paths'][0]['commands'].pop(),
                     lambda d: d['paths'][0].update(element_id=d['paths'][1]['element_id']),
                     lambda d: d['paths'][0]['commands'][0].__setitem__(1, float('nan')),
                     lambda d: d['occurrence'].update(column=999),
                     lambda d: d['paths'][0]['commands'].append(['L',0,0])):
            bad = deepcopy(self.asset); edit(bad['data'])
            # These are structural failures before checksum calculation.
            with self.assertRaises(ValueError):
                validate_asset(bad)

    def test_v2_rejects_physics_fields_and_version_mismatch(self):
        for field, value in [('radius', 1), ('velocity', [1,0,0]), ('geometry', {'kind':'sphere'})]:
            bad = deepcopy(self.scene);bad['actors'][0][field] = value
            with self.assertRaises(ValueError):
                validate_scene(bad)
        bad = deepcopy(self.take);bad['version'] = 1
        with self.assertRaisesRegex(ValueError, 'version'):
            validate_take(bad)
        bad = deepcopy(self.take);del bad['animation']['motion_id']
        with self.assertRaisesRegex(ValueError, 'motion_id'):
            validate_take(bad)

    def test_take_is_self_contained_and_independent(self):
        again = validate_take(json.loads(json.dumps(self.take)))
        copied = make_take(again['scene'], again['animation'])
        copied['scene']['actors'][0]['geometry']['asset']['data']['paths'][0]['source_id'] = 'changed'
        self.assertEqual(self.asset['data']['paths'][0]['source_id'], 's1')

    def test_compound_contour_winding_and_handles_are_retained(self):
        commands = [['M',0,0],['C',2,0,2,2,0,2],['L',0,0],['Z'],
                    ['M',0.5,0.5],['L',0.5,1],['L',1,1],['L',1,0.5],['Z']]
        contours = bezier_contours(commands)
        self.assertEqual(len(contours), 2)
        self.assertEqual(contours[0][0][2], [2,0])
        self.assertEqual(contours[0][1][1], [2,2])
        self.assertEqual(contours[1][1][0], [0.5,1])

    def test_srgb_is_converted_to_linear_shader_rgb(self):
        self.assertEqual(srgb_color('#000000'), [0,0,0])
        self.assertEqual(srgb_color('#FFFFFF'), [1,1,1])
        self.assertAlmostEqual(srgb_color('#808080')[0], 0.2158605, places=6)

    def test_glyph_framing_rejects_clipped_camera(self):
        self.scene['cameras'][0]['fov_degrees'] = 5
        self.assertFalse(check_framing(self.scene, self.take['animation'])['passed'])


if __name__ == '__main__':
    unittest.main()
