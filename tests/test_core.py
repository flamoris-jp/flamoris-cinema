import unittest
from flamoris_cinema.core import simulate

SCENE = {"schema_version": 1, "fps": 30, "duration_seconds": 2,
         "actors": [{"id": "red", "position": [0, 0, 3], "radius": 0.5, "color": [1, 0, 0]}]}

class SceneTests(unittest.TestCase):
    def test_reproducible(self):
        self.assertEqual(simulate(SCENE), simulate(SCENE))
    def test_floor_contact(self):
        frames = simulate(SCENE)["frames"]
        self.assertTrue(all(f["positions"]["red"][2] >= 0.5 for f in frames))
        self.assertEqual(frames[-1]["positions"]["red"][2], 0.5)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            simulate({**SCENE, "fps": 0})

    def test_unsupported_before_nondivisor_fps(self):
        frames = simulate({**SCENE, 'fps': 29})['frames']
        self.assertEqual(len(frames), 58)
        self.assertGreater(frames[0]['positions']['red'][2], frames[1]['positions']['red'][2])

    def test_horizontal_velocity_and_bounce(self):
        scene = {**SCENE, 'actors': [{**SCENE['actors'][0], 'velocity': [1, 0, 0], 'restitution': 0.6}]}
        frames = simulate(scene)['frames']
        self.assertAlmostEqual(frames[30]['positions']['red'][0], 1.0)
        heights = [f['positions']['red'][2] for f in frames]
        self.assertTrue(any(b > a for a, b in zip(heights, heights[1:])))
        self.assertTrue(all(z >= 0.5 for z in heights))

    def test_fixed_clock_across_output_rates(self):
        low = simulate({**SCENE, 'fps': 24})['frames']
        high = simulate({**SCENE, 'fps': 120})['frames']
        for index, sample in enumerate(low):
            self.assertEqual(sample['positions'], high[index * 5]['positions'])

    def test_one_frame_take(self):
        self.assertEqual(len(simulate({**SCENE, 'duration_seconds': 1 / 30})['frames']), 1)

    def test_freefall_against_discrete_reference(self):
        scene = {**SCENE, 'duration_seconds': 0.5}
        frames = simulate(scene)['frames']
        # Semi-implicit Euler after n ticks: z=z0-g*dt^2*n*(n+1)/2.
        n = 40  # output frame 10 at 30 fps
        expected = 3 - 9.81 / (120 * 120) * n * (n + 1) / 2
        self.assertAlmostEqual(frames[10]['positions']['red'][2], expected, places=10)
