from pathlib import Path
import tempfile
import unittest
from flamoris_cinema.flamenco import render_job
from flamoris_cinema.glyph_walk import walk_take
from flamoris_cinema.io import read_json


class FlamencoProposalTests(unittest.TestCase):
    def test_clock_native_scene_and_explicit_shared_root(self):
        scene=walk_take(read_json(Path(__file__).resolve().parents[1]/'examples/red_glyph.take.json'))['scene']
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);blend=root/'walk.blend';blend.write_bytes(b'file-presence-fixture')
            kwargs=dict(shared_root=root,blend_file=blend,output_root=root/'renders',scene_name='Cinema.001',
                        name='Red-Walk',type_etag='current-manager-etag')
            job=render_job(scene,**kwargs)
            self.assertEqual(job['settings']['frames'],'1-72')
            self.assertEqual(job['settings']['fps'],24)
            self.assertEqual(job['settings']['scene'],'Cinema.001')
            self.assertEqual(job['settings']['render_output_path'],str(root/'renders'/'######'))
            self.assertFalse((root/'renders').exists())
            for key,value in [('output_root',root.parent/'escaped'),('type_etag',''),('chunk_size',True),('scene_name','bad\nscene')]:
                bad={**kwargs,key:value}
                with self.assertRaises(ValueError):render_job(scene,**bad)
            (root/'renders').mkdir()
            with self.assertRaisesRegex(ValueError,'must be new'):render_job(scene,**kwargs)
