"""Real Blender v3 part-pose roundtrip and physical placement assertions."""
from pathlib import Path
import sys
import tempfile
import math
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from flamoris_cinema.io import read_json
from flamoris_cinema.glyph_walk import walk_take
from flamoris_cinema.blender_bridge import build_scene,export_take,TAG
from flamoris_cinema.articulation import part_tag


def compare(a,b):
    assert a['scene']['actors'][0]['geometry'] == b['scene']['actors'][0]['geometry']
    assert a['scene']['actors'][0]['pivots'] == b['scene']['actors'][0]['pivots']
    for x,y in zip(a['animation']['frames'],b['animation']['frames']):
        for aid in x['positions']:
            assert max(abs(v-w) for v,w in zip(x['positions'][aid],y['positions'][aid]))<1e-5
            for pid,pose in x['parts'][aid].items():
                other=y['parts'][aid][pid]
                assert max(abs(v-w) for v,w in zip(pose['translation'],other['translation']))<1e-5
                assert abs(pose['angle_degrees']-other['angle_degrees'])<1e-4


take=walk_take(read_json(Path(__file__).resolve().parents[1]/'examples/red_glyph.take.json'))
target=build_scene(take['scene'],take['animation'],'wide')
objects={o.get(TAG):o for o in target.objects}
assert objects['red_glyph'].type=='EMPTY'
assert sum(o.get('cinema_kind')=='glyph_part' for o in target.objects)==7
for frame in range(1,73):
    target.frame_set(frame)
    for pid in ('stroke004','stroke005'):
        part=objects[part_tag('red_glyph',pid)]
        low=min((part.matrix_world@v.co).z for v in part.data.vertices)
        assert low >= -1e-5,('foot below floor',frame,pid,low)
target.frame_set(9)
compare(take,export_take())
assert target.frame_current==9
with tempfile.TemporaryDirectory() as tmp:
    filepath=str(Path(tmp)/'walk.blend')
    bpy.ops.wm.save_as_mainfile(filepath=filepath)
    bpy.ops.wm.open_mainfile(filepath=filepath)
    returned=export_take()
compare(take,returned)
target=build_scene(returned['scene'],returned['animation'],'close')
part=next(o for o in target.objects if o.get(TAG)==part_tag('red_glyph','stroke006'))
part.name='Arm renamed by a native editor'
part.rotation_euler.y=math.radians(10)
part.keyframe_insert(data_path='rotation_euler',frame=1)
edited=export_take()
assert abs(edited['animation']['frames'][0]['parts']['red_glyph']['stroke006']['angle_degrees']-10)<1e-4
target=build_scene(edited['scene'],edited['animation'],'wide')
compare(edited,export_take())
part=next(o for o in target.objects if o.get(TAG)==part_tag('red_glyph','stroke006'))
part.data.vertices[0].co.x+=0.01
try:export_take()
except ValueError as e:assert 'geometry' in str(e)
else:raise AssertionError('part geometry silently exported')
target=build_scene(take['scene'],take['animation'],'wide')
root=next(o for o in target.objects if o.get(TAG)=='red_glyph')
root.delta_location.x=0.1
try:export_take()
except ValueError as e:assert 'delta' in str(e)
else:raise AssertionError('root delta transform silently exported')
target=build_scene(take['scene'],take['animation'],'wide')
part=next(o for o in target.objects if o.get(TAG)==part_tag('red_glyph','stroke006'))
part.parent=None
try:export_take()
except ValueError as e:assert 'parent' in str(e) or 'hierarchy' in str(e)
else:raise AssertionError('part reparenting silently exported')
print('CINEMA_WALK_ACCEPTANCE_OK')
