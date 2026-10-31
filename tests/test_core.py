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
