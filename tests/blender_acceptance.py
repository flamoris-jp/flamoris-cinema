"""Executed inside real Blender by test_blender_integration.py; no bpy mocks."""
import json
from pathlib import Path
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from flamoris_cinema.blender_bridge import build_scene, export_take, TAG
from flamoris_cinema.core import simulate
from flamoris_cinema.interchange import validate_take

scene = json.loads((Path(__file__).resolve().parents[1] / 'examples/red_falls.scene.json').read_text())
scene.update(fps=24, duration_seconds=0.25, render={'width': 32, 'height': 32})
animation = simulate(scene)
target = build_scene(scene, animation, 'wide')
objects = {obj.get(TAG): obj for obj in target.objects}
objects['red_actor_proxy'].name = 'Renaming must preserve identity'
objects['red_actor_proxy'].location = [1, 0, 3.5]
objects['red_actor_proxy'].keyframe_insert(data_path='location', frame=1)
objects['red_actor_proxy'].data.materials[0].diffuse_color = (0.3, 0.5, 0.7, 1)
target.frame_set(3)
exported = export_take()
assert target.frame_current == 3
assert exported['animation']['frames'][0]['positions']['red_actor_proxy'][0] == 1
assert abs(exported['scene']['actors'][0]['color'][1] - 0.5) < 1e-6
validate_take(exported)
rebuilt = build_scene(exported['scene'], exported['animation'], 'close')
again = export_take()
for a, b in zip(exported['animation']['frames'], again['animation']['frames']):
    for x, y in zip(a['positions']['red_actor_proxy'], b['positions']['red_actor_proxy']):
        assert abs(x - y) < 1e-5
obj = next(o for o in rebuilt.objects if o.get(TAG) == 'red_actor_proxy')
obj.data.vertices[0].co.x += 0.1
try:
    export_take()
except ValueError as exc:
    assert 'geometry' in str(exc)
else:
    raise AssertionError('edited mesh silently exported')
print('CINEMA_BLENDER_ACCEPTANCE_OK')
