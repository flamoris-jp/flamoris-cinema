"""Small v3 rigid Glyph-part poses: local translation and rotation about Y.

This is sampled cartoon acting, not a skeleton, deformation or collision solver.
"""
import math


def part_tag(actor_id, element_id):
    return actor_id + '::' + element_id


def control_points(actor, element_id):
    """Source Bezier control hull in actor-local X/Z, including extrusion depth."""
    g = actor['geometry']
    path = next(p for p in g['asset']['data']['paths'] if p['element_id'] == element_id)
    scale, half = g['metres_per_unit'], g['depth']/2
    return [[(cmd[i]-500)*scale, depth, (500-cmd[i+1])*scale]
            for cmd in path['commands'] for i in range(1,len(cmd),2) for depth in (-half,half)]


def transform_point(point, pivot, pose):
    angle = math.radians(pose['angle_degrees'])
    c,s = math.cos(angle),math.sin(angle)
    x,y,z = [v-p for v,p in zip(point,pivot)]
    t = pose['translation']
    return [pivot[0]+c*x+s*z+t[0], pivot[1]+y+t[1], pivot[2]-s*x+c*z+t[2]]


def posed_points(actor, poses):
    return [transform_point(v,actor['pivots'][pid],pose)
            for pid,pose in poses.items() for v in control_points(actor,pid)]


def neutral_poses(actor):
    return {pid:{'translation':[0.0,0.0,0.0],'angle_degrees':0.0} for pid in actor['pivots']}
