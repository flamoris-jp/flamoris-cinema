"""An explicit authored seven-stroke 赤 gait: four steps, then a quiet hold."""
from copy import deepcopy
import math
from .articulation import control_points, transform_point, neutral_poses
from .contracts import frame_count, motion_id, validate_animation
from .interchange import make_take, validate_take


def _smooth(u):
    u = min(1,max(0,u))
    return u*u*(3-2*u)


def _foot_progress(t, left):
    # Two half-second swing windows per foot. Stance anchors remain constant.
    starts = (0.0,1.0) if left else (0.5,1.5)
    progress,lift = 0.0,0.0
    for start in starts:
        u = min(1,max(0,(t-start)/0.5))
        progress += 0.5*_smooth(u)
        if 0 < u < 1:
            lift = 0.18*math.sin(math.pi*u)**2
    return progress,lift


def walk_take(stage):
    """Build the fixed 3 s/24 fps acting fixture; source stage is never mutated."""
    validate_take(stage)
    if stage['version'] != 2 or len(stage['scene']['actors']) != 1:
        raise ValueError('walk fixture requires a single v2 Glyph stage')
    scene = deepcopy(stage['scene'])
    actor = scene['actors'][0]
    paths = actor['geometry']['asset']['data']['paths']
    expected = [(f'stroke{i:03d}',f's{i}') for i in range(1,8)]
    if (actor['geometry']['asset']['data']['occurrence']['character'] != '赤' or
            [(p['element_id'],p['source_id']) for p in paths] != expected):
        raise ValueError('walk roles require the explicitly authored seven-stroke 赤')
    scene.update(schema_version=3,fps=24,duration_seconds=3)
    scene['render'] = {'width':640,'height':360}
    # Explicit role binding: s4/s5 legs, s6/s7 arms; s1/s2/s3 body.
    actor['pivots'] = {}
    for path in paths:
        pid = path['element_id']
        points = control_points(actor,pid)
        xs,zs = [p[0] for p in points],[p[2] for p in points]
        actor['pivots'][pid] = [(min(xs)+max(xs))/2,0,max(zs)] if pid >= 'stroke004' else [0,0,0]
    actor['position'][0] = -0.9
    scene['cameras'] = [
        {'id':'wide','position':[4,-8,3.5],'target':[0,0,1.05],'fov_degrees':55},
        {'id':'close','position':[1.5,-6.5,2.7],'target':[0,0,1.05],'fov_degrees':55}]
    frames = []
    base_z = actor['position'][2]
    for i in range(frame_count(scene)):
        t = i/scene['fps']
        walking = min(t,2.0)
        x = -0.9+1.8*_smooth(walking/2)
        bob = 0.045*math.sin(2*math.pi*walking)**2 if t < 2 else 0.0
        position = [x,actor['position'][1],base_z+bob]
        poses = neutral_poses(actor)
        phase = math.sin(2*math.pi*walking) if t < 2 else 0.0
        for pid,left in [('stroke004',True),('stroke005',False)]:
            progress,lift = _foot_progress(walking,left)
            pose = poses[pid]
            pose['angle_degrees'] = (12 if left else -12)*phase
            raw = control_points(actor,pid)
            transformed = [transform_point(p,actor['pivots'][pid],pose) for p in raw]
            # Pin the lowest support point, allowing deliberate foot roll.
            low = min(p[2] for p in transformed)
            foot_x = sum(p[0] for p in transformed if abs(p[2]-low)<1e-9)/sum(abs(p[2]-low)<1e-9 for p in transformed)
            original_low = min(p[2] for p in raw)
            original_x = sum(p[0] for p in raw if abs(p[2]-original_low)<1e-9)/sum(abs(p[2]-original_low)<1e-9 for p in raw)
            desired_x = original_x-0.9+1.8*progress
            pose['translation'] = [desired_x-x-foot_x,0,lift-position[2]-low]
        poses['stroke006']['angle_degrees'] = -18*phase
        poses['stroke007']['angle_degrees'] = 18*phase
        frames.append({'frame':i,'positions':{actor['id']:position},'parts':{actor['id']:poses}})
    animation = {'schema_version':3,'fps':scene['fps'],'motion_id':motion_id(scene),'frames':frames}
    validate_animation(animation,scene)
    return make_take(scene,animation)
