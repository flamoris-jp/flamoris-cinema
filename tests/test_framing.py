from copy import deepcopy
import json
from pathlib import Path
import unittest
from flamoris_cinema.core import simulate
from flamoris_cinema.framing import check_framing


class FramingTests(unittest.TestCase):
    def setUp(self):
        self.scene = json.loads((Path(__file__).resolve().parents[1] / 'examples/red_falls.scene.json').read_text())

    def test_whole_sample_trajectory_fits_both_cameras(self):
        result = check_framing(self.scene, simulate(self.scene))
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['frames_checked'], 150)
        self.assertEqual(set(result['cameras']), {'wide', 'close'})

    def test_old_close_camera_clips_and_motion_is_unchanged(self):
        original = deepcopy(self.scene)
        original['cameras'][1].update(position=[3.5, -5, 2.6], target=[0.7, 0, 1.2], fov_degrees=45)
        motion = simulate(self.scene)
        self.assertEqual(motion, simulate(original))
        result = check_framing(original, motion)
        self.assertFalse(result['cameras']['close']['passed'])
        self.assertTrue(result['cameras']['wide']['passed'])
        self.assertEqual(result['cameras']['close']['first_clipped'][0]['frame'], 0)

    def test_sphere_edge_clips_even_with_center_in_view(self):
        scene = {'schema_version': 1, 'fps': 30, 'duration_seconds': 1 / 30,
                 'actors': [{'id': 'ball', 'position': [4.8, 0, 2], 'radius': .5, 'color': [1, 0, 0]}],
                 'render': {'width': 720, 'height': 720},
                 'cameras': [{'id': 'front', 'position': [0, -5, 2], 'target': [0, 0, 2], 'fov_degrees': 90}]}
        # Horizontal centre is within +-5m, but the sphere extends across the plane.
        self.assertFalse(check_framing(scene, simulate(scene), margin=0)['passed'])
        scene['actors'][0]['position'][0] = 0
        self.assertTrue(check_framing(scene, simulate(scene), margin=0)['passed'])

    def test_actor_behind_camera_fails(self):
        scene = deepcopy(self.scene)
        scene['cameras'][0]['target'] = [10, -20, 6]
        self.assertFalse(check_framing(scene, simulate(scene))['passed'])
