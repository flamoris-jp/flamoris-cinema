"""Real Blender-only gate: Glyph identity, holes, dimensions and save/reload.

No mocks and no render device changes. Called before --glyph smoke rendering.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from flamoris_cinema.blender_bridge import build_scene, export_take, TAG
from flamoris_cinema.glyph_asset import digest
from flamoris_cinema.glyph_prepare import stage_take
from flamoris_cinema.io import read_json

take = read_json(Path(__file__).resolve().parents[1] / 'examples/red_glyph.take.json')
target = build_scene(take['scene'], take['animation'], 'wide')
obj = next(o for o in target.objects if o.get(TAG) == 'red_glyph')
assert len(json.loads(obj['cinema_parts'])) == 7
assert {v.value for v in obj.data.attributes['cinema_part'].data} == set(range(7))
assert abs(min((obj.matrix_world @ v.co).z for v in obj.data.vertices)) < 1e-5
assert abs(obj.dimensions.y - 0.12) < 1e-5
obj.name = 'Red renamed in native editor'
obj.location.x += 0.25
obj.keyframe_insert(data_path='location', frame=1)
returned = export_take()
assert abs(returned['animation']['frames'][0]['positions']['red_glyph'][0] - 0.25) < 1e-5
assert returned['scene']['actors'][0]['geometry'] == take['scene']['actors'][0]['geometry']
with tempfile.TemporaryDirectory() as tmp:
    path = str(Path(tmp) / 'glyph.blend')
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    reopened = export_take()
assert reopened['scene']['actors'][0]['geometry'] == take['scene']['actors'][0]['geometry']
rebuilt = build_scene(reopened['scene'], reopened['animation'], 'close')
obj = next(o for o in rebuilt.objects if o.get(TAG) == 'red_glyph')
assert abs(obj.location.x-0.25) < 1e-5
obj.data.vertices[0].co.x += 0.01
try:
    export_take()
except ValueError as exc:
    assert 'geometry' in str(exc)
else:
    raise AssertionError('edited Glyph geometry silently exported')

# A compound nonzero-filled path: opposite-winding hole. Its front cap area
# must be (600^2 - 200^2) * .003^2 = 2.88 square metres, not a filled square.
asset = deepcopy(take['scene']['actors'][0]['geometry']['asset'])
d = asset['data']
d['stroke_model'] = 'outline'
d['source']['kind'] = 'font-outline'
d['metrics']['bounds'] = [200,200,800,800]
d['paths'] = [{'element_id':'stroke001','source_id':'synthetic-hole','terminal':None,
               'commands':[['M',200,200],['L',800,200],['L',800,800],['L',200,800],['Z'],
                           ['M',400,400],['L',400,600],['L',600,600],['L',600,400],['Z']]}]
asset['sha256'] = digest(d)
hole = stage_take(asset, [0.5,0.1,0.1])
target = build_scene(hole['scene'], hole['animation'], 'wide')
obj = next(o for o in target.objects if o.get(TAG) == 'red_glyph')
front = [p for p in obj.data.polygons if p.normal.y < -0.99]
assert front and abs(sum(p.area for p in front)-2.88) < 1e-4, 'hole was filled or winding changed'
print('CINEMA_GLYPH_ACCEPTANCE_OK')
