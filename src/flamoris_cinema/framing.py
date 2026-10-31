"""Conservative whole-sphere framing for static Z-up perspective cameras.

This is geometric preflight, not a visibility/occlusion or final-image test.
"""
import math
from .contracts import validate_animation


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _unit(v):
    length = math.sqrt(_dot(v, v))
    return [x / length for x in v]


def check_framing(scene, animation, margin=0.05):
    """Check whole spheres against all static cameras, with a screen-edge margin.

    margin=.05 reserves 5% of image width/height along each edge. Distances to
    each inset frustum plane are normalized in metres; this includes a sphere's
    radius instead of checking its centre only. Matches bridge clip 0.1..1000m.
    """
    validate_animation(animation, scene)
    if type(margin) not in (int, float) or not math.isfinite(margin) or not 0 <= margin < 0.5:
        raise ValueError('framing margin must be finite in 0..0.5 (exclusive)')
    cameras = scene.get('cameras', [])
    if not cameras:
        raise ValueError('framing preflight requires a camera')
    size = scene.get('render', {'width': 1280, 'height': 720})
    result = {'passed': True, 'margin': margin, 'frames_checked': len(animation['frames']), 'cameras': {}}
    for camera in cameras:
        forward = _unit([b - a for a, b in zip(camera['position'], camera['target'])])
        right = _unit(_cross(forward, [0, 0, 1]))
        up = _cross(right, forward)
        horizontal = math.tan(math.radians(camera['fov_degrees']) / 2) * (1 - 2 * margin)
        vertical = horizontal * size['height'] / size['width']
        minimum, clipped, examples = math.inf, 0, []
        for sample in animation['frames']:
            for actor in scene['actors']:
                delta = [p - c for p, c in zip(sample['positions'][actor['id']], camera['position'])]
                depth = _dot(delta, forward)
                radius = actor['radius']
                clearance = min((depth * horizontal - abs(_dot(delta, right))) / math.sqrt(1 + horizontal ** 2) - radius,
                                (depth * vertical - abs(_dot(delta, up))) / math.sqrt(1 + vertical ** 2) - radius,
                                depth - radius - 0.1, 1000 - depth - radius)
                minimum = min(minimum, clearance)
                if clearance < 0:
                    clipped += 1
                    if len(examples) < 10:
                        examples.append({'frame': sample['frame'], 'actor': actor['id']})
        result['cameras'][camera['id']] = {'passed': clipped == 0, 'clipped_samples': clipped,
                                         'minimum_clearance_metres': minimum, 'first_clipped': examples}
        result['passed'] = result['passed'] and clipped == 0
    return result
