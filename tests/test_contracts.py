from copy import deepcopy
import math
import unittest
from flamoris_cinema.contracts import motion_id, validate_animation, validate_scene
from flamoris_cinema.core import simulate
from flamoris_cinema.interchange import make_take, validate_take
from test_core import SCENE


class ContractTests(unittest.TestCase):
    def test_camera_change_reuses_performance(self):
        scene = deepcopy(SCENE)
        animation = simulate(scene)
        scene['cameras'] = [{'id': 'wide', 'position': [0, -8, 4], 'target': [0, 0, 1], 'fov_degrees': 50}]
        scene['lights'] = [{'id': 'key', 'position': [2, -3, 6], 'color': [1, 1, 1], 'energy': 500}]
        scene['actors'][0]['color'] = [0.8, 0.2, 0.1]
        self.assertEqual(animation, simulate(scene))
        self.assertEqual(validate_animation(animation, scene), animation)

    def test_physics_edit_invalidates_take(self):
        scene = deepcopy(SCENE)
        animation = simulate(scene)
        scene['actors'][0]['radius'] = 0.7
        with self.assertRaisesRegex(ValueError, 'different performance'):
            validate_animation(animation, scene)

    def test_invalid_scene_boundary(self):
        invalid = [dict(SCENE, schema_version=True), dict(SCENE, fps=True),
                   dict(SCENE, duration_seconds=0.001), dict(SCENE, duration_seconds=1.01),
                   dict(SCENE, unsupported='x'), dict(SCENE, render={'width': True, 'height': 720})]
        for field, value in [('id', '../actor'), ('position', [0, 0, -1]), ('radius', math.inf),
                             ('color', [math.nan, 0, 0]), ('velocity', [False, 0, 0]), ('restitution', 2)]:
            scene = deepcopy(SCENE)
            scene['actors'][0][field] = value
            invalid.append(scene)
        for scene in invalid:
            with self.subTest(scene=scene), self.assertRaises(ValueError):
                validate_scene(scene)

    def test_scene_ids_are_global(self):
        scene = deepcopy(SCENE)
        scene['lights'] = [{'id': 'red', 'position': [1, 2, 3], 'color': [1, 1, 1], 'energy': 10}]
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validate_scene(scene)

    def test_animation_boundary(self):
        animation = simulate(SCENE)
        variants = []
        for key, value in [('fps', True), ('schema_version', True), ('frames', []), ('unknown', 1)]:
            candidate = deepcopy(animation); candidate[key] = value; variants.append(candidate)
        for field, value in [('frame', 1), ('positions', {'intruder': [0, 0, 0]}), ('positions', {'red': [0, 0, math.inf]})]:
            candidate = deepcopy(animation); candidate['frames'][0][field] = value; variants.append(candidate)
        for candidate in variants:
            with self.subTest(candidate=str(candidate)[:50]), self.assertRaises(ValueError):
                validate_animation(candidate, SCENE)

    def test_sample_budget(self):
        scene = deepcopy(SCENE)
        scene.update(fps=120, duration_seconds=120)
        scene['actors'] = [{**scene['actors'][0], 'id': f'a{i}'} for i in range(100)]
        with self.assertRaisesRegex(ValueError, 'samples'):
            validate_scene(scene)

    def test_take_roundtrip_and_no_input_mutation(self):
        animation = simulate(SCENE)
        take = make_take(SCENE, animation)
        self.assertEqual(validate_take(take)['animation'], animation)
        take['animation']['frames'][0]['positions']['red'][0] = 25
        self.assertEqual(animation['frames'][0]['positions']['red'][0], 0)
        self.assertEqual(SCENE['actors'][0]['position'][0], 0)

    def test_legacy_motion_is_upgraded(self):
        animation = simulate(SCENE)
        del animation['motion_id']
        take = make_take(SCENE, animation)
        self.assertEqual(take['animation']['motion_id'], motion_id(SCENE))

    def test_normalized_initial_conditions(self):
        scene = deepcopy(SCENE)
        scene['duration_seconds'] = 2.0
        scene['actors'][0]['position'] = [0.0, 0.0, 3.0]
        scene['actors'][0]['velocity'] = [0.0, 0.0, 0.0]
        scene['actors'][0]['restitution'] = 0.0
        self.assertEqual(motion_id(scene), motion_id(SCENE))
