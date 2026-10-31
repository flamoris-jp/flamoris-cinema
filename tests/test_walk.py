from copy import deepcopy
from pathlib import Path
import unittest
from flamoris_cinema.glyph_walk import walk_take, _foot_progress
from flamoris_cinema.articulation import control_points, posed_points, transform_point
from flamoris_cinema.contracts import motion_id, validate_animation, validate_scene
from flamoris_cinema.interchange import validate_take
from flamoris_cinema.framing import check_framing
from flamoris_cinema.io import read_json


class WalkTests(unittest.TestCase):
    def setUp(self):
        self.stage = read_json(Path(__file__).resolve().parents[1]/'examples/red_glyph.take.json')
        self.take = walk_take(self.stage)
        self.actor = self.take['scene']['actors'][0]

    def test_reproducible_staged_walk_and_hold(self):
        self.assertEqual(self.take,walk_take(self.stage))
        self.assertEqual(self.stage['version'],2)
        self.assertEqual(len(self.take['animation']['frames']),72)
        self.assertEqual(self.actor['geometry'],self.stage['scene']['actors'][0]['geometry'])
        frames = self.take['animation']['frames']
        self.assertNotEqual(frames[0]['parts'],frames[6]['parts'])
        self.assertAlmostEqual(frames[48]['positions']['red_glyph'][0]-frames[0]['positions']['red_glyph'][0],1.8)
        for frame in frames[49:]:
            self.assertEqual(frame['parts'],frames[48]['parts'])
            self.assertEqual(frame['positions'],frames[48]['positions'])

    def test_support_feet_do_not_slide_or_penetrate_floor(self):
        anchors = {}
        for frame in self.take['animation']['frames']:
            t = frame['frame']/24
            root = frame['positions']['red_glyph']
            for pid,left in [('stroke004',True),('stroke005',False)]:
                pose = frame['parts']['red_glyph'][pid]
                points = [transform_point(p,self.actor['pivots'][pid],pose) for p in control_points(self.actor,pid)]
                low = min(p[2] for p in points)
                foot_x = sum(p[0] for p in points if abs(p[2]-low)<1e-9)/sum(abs(p[2]-low)<1e-9 for p in points)+root[0]
                progress,lift = _foot_progress(min(t,2),left)
                self.assertAlmostEqual(low+root[2],lift,places=9)
                self.assertGreaterEqual(low+root[2],-1e-9)
                if lift == 0:
                    key = (pid,progress)
                    if key in anchors:
                        self.assertAlmostEqual(foot_x,anchors[key],places=9)
                    anchors[key] = foot_x

    def test_camera_independence_and_animated_part_framing(self):
        scene = deepcopy(self.take['scene'])
        key = motion_id(scene)
        scene['cameras'][0]['position'][0] += 1
        self.assertEqual(motion_id(scene),key)
        validate_animation(self.take['animation'],scene)
        self.assertTrue(check_framing(self.take['scene'],self.take['animation'])['passed'])
        bad = deepcopy(self.take['animation']);bad['frames'][5]['parts']['red_glyph']['stroke006']['translation'][0] = 30
        self.assertFalse(check_framing(self.take['scene'],bad)['passed'])

    def test_strict_part_contract_and_pivot_compatibility(self):
        for edit in (lambda t:t['animation']['frames'][0]['parts']['red_glyph'].pop('stroke004'),
                     lambda t:t['animation']['frames'][0]['parts']['red_glyph']['stroke004'].update(scale=2),
                     lambda t:t['animation']['frames'][0]['parts']['red_glyph']['stroke004'].update(angle_degrees=float('nan')),
                     lambda t:t['scene']['actors'][0]['pivots'].pop('stroke005'),
                     lambda t:t['scene']['actors'][0]['pivots']['stroke004'].__setitem__(0,1)):
            bad=deepcopy(self.take);edit(bad)
            with self.assertRaises(ValueError):validate_take(bad)

    def test_roles_are_explicit_not_guessed(self):
        stage=deepcopy(self.stage)
        stage['scene']['actors'].append(deepcopy(stage['scene']['actors'][0]))
        stage['scene']['actors'][-1]['id']='another'
        # Invalid source is rejected by take validation before any role inference.
        with self.assertRaises(ValueError):walk_take(stage)
