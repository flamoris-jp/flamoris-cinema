"""Portable v1 sphere/v2 Glyph contracts, without filesystem or renderer effects."""
import hashlib
import json
import math
import re

VERSION = 1
MAX_SAMPLES = 250_000
ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}$")


def fields(value, required, optional=(), path="object"):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError(f"{path}: missing or unsupported properties")


def number(value, low, high, path):
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        raise ValueError(f"{path}: expected finite number in {low}..{high}")


def vector(value, path, low=-10000, high=10000):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{path}: expected three numbers")
    for v in value:
        number(v, low, high, path)


def identifier(value, path):
    if not isinstance(value, str) or not ID.fullmatch(value) or value == "__floor__":
        raise ValueError(f"{path}: invalid stable id")


def frame_count(scene):
    # A take consists of samples at t=0 through (N-1)/fps, never t=duration.
    n = scene["duration_seconds"] * scene["fps"]
    count = round(n)
    if count < 1 or not math.isclose(n, count, abs_tol=1e-8, rel_tol=0):
        raise ValueError("duration_seconds * fps must be a positive integer")
    return count


def validate_scene(scene):
    fields(scene, ("schema_version", "fps", "duration_seconds", "actors"),
           ("cameras", "lights", "render"), "scene")
    if type(scene["schema_version"]) is not int or scene["schema_version"] not in (1, 2):
        raise ValueError("unsupported scene schema")
    fps = scene["fps"]
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError("fps must be integer in 1..120")
    number(scene["duration_seconds"], 1 / 120, 120, "duration_seconds")
    actors = scene["actors"]
    if not isinstance(actors, list) or not 1 <= len(actors) <= 100:
        raise ValueError("actors must be a bounded nonempty list")
    if frame_count(scene) * len(actors) > MAX_SAMPLES:
        raise ValueError("take exceeds 250000 actor samples")
    ids = set()
    for kind, items, limit in (("actor", actors, 100), ("camera", scene.get("cameras", []), 16),
                               ("light", scene.get("lights", []), 32)):
        if not isinstance(items, list) or len(items) > limit:
            raise ValueError(f"invalid {kind} list")
        for item in items:
            glyph = kind == 'actor' and scene['schema_version'] == 2
            required = {"actor": ("id", "position", "color", "geometry") if glyph else ("id", "position", "radius", "color"),
                        "camera": ("id", "position", "target", "fov_degrees"),
                        "light": ("id", "position", "color", "energy")}[kind]
            fields(item, required, ("velocity", "restitution") if kind == "actor" and not glyph else (), kind)
            identifier(item["id"], kind)
            if item["id"] in ids:
                raise ValueError("duplicate id across scene objects")
            ids.add(item["id"])
            vector(item["position"], kind + ".position")
            if kind == "actor":
                vector(item["color"], "color", 0, 1)
                if glyph:
                    from .glyph_asset import validate_asset, local_bounds
                    geometry = item['geometry']
                    fields(geometry, ('kind', 'asset', 'metres_per_unit', 'depth'), path='geometry')
                    if geometry['kind'] != 'glyph':
                        raise ValueError('scene v2 supports Glyph geometry only')
                    number(geometry['metres_per_unit'], 0.000001, 0.1, 'metres_per_unit')
                    number(geometry['depth'], 0.0001, 10, 'depth')
                    validate_asset(geometry['asset'])
                    if item['position'][2] + local_bounds(geometry)[0][2] < -1e-7:
                        raise ValueError('Glyph starts below floor')
                    continue
                number(item["radius"], 0.0001, 100, "radius")
                vector(item.get("velocity", [0, 0, 0]), "velocity", -100, 100)
                number(item.get("restitution", 0), 0, 1, "restitution")
                if item["position"][2] < item["radius"]:
                    raise ValueError("actor starts below floor contact height")
            elif kind == "camera":
                vector(item["target"], "target")
                delta = [b - a for a, b in zip(item["position"], item["target"])]
                if sum(v * v for v in delta[:2]) < 1e-12:
                    raise ValueError("camera direction must not be parallel to Z up")
                number(item["fov_degrees"], 1, 170, "fov_degrees")
            else:
                vector(item["color"], "color", 0, 1)
                number(item["energy"], 0, 1_000_000, "energy")
    render = scene.get("render", {"width": 1280, "height": 720})
    fields(render, ("width", "height"), path="render")
    if any(type(v) is not int or not 16 <= v <= 4096 for v in render.values()):
        raise ValueError("render dimensions must be integers in 16..4096")
    return scene


def motion_id(scene):
    """Camera/light/color edits do not invalidate an existing performance."""
    validate_scene(scene)
    if scene['schema_version'] == 2:
        payload = {'schema_version': 2, 'fps': scene['fps'], 'duration_seconds': float(scene['duration_seconds']),
                   'actors': sorted([{'id': a['id'], 'position': list(map(float, a['position'])),
                                     'geometry': {'asset_sha256': a['geometry']['asset']['sha256'],
                                                  'metres_per_unit': float(a['geometry']['metres_per_unit']),
                                                  'depth': float(a['geometry']['depth'])}}
                                    for a in scene['actors']], key=lambda a: a['id'])}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    payload = {"fps": scene["fps"], "duration_seconds": float(scene["duration_seconds"]),
               "actors": sorted([{"id": a["id"], "position": list(map(float, a["position"])),
                                  "radius": float(a["radius"]),
                                  "velocity": list(map(float, a.get("velocity", [0, 0, 0]))),
                                  "restitution": float(a.get("restitution", 0))}
                                 for a in scene["actors"]], key=lambda a: a["id"])}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_animation(animation, scene):
    validate_scene(scene)
    fields(animation, ("schema_version", "fps", "frames"), ("motion_id",), "animation")
    if type(animation["schema_version"]) is not int or animation["schema_version"] != scene['schema_version']:
        raise ValueError("unsupported animation schema")
    if type(animation["fps"]) is not int or animation["fps"] != scene["fps"]:
        raise ValueError("animation fps differs from scene")
    if "motion_id" in animation and animation["motion_id"] != motion_id(scene):
        raise ValueError("animation belongs to a different performance")
    if scene['schema_version'] == 2 and 'motion_id' not in animation:
        raise ValueError('v2 animation requires motion_id')
    frames = animation["frames"]
    if not isinstance(frames, list) or len(frames) != frame_count(scene):
        raise ValueError("animation sample count differs from scene")
    names = {a["id"] for a in scene["actors"]}
    for index, sample in enumerate(frames):
        fields(sample, ("frame", "positions"), path=f"frames[{index}]")
        if type(sample["frame"]) is not int or sample["frame"] != index:
            raise ValueError("frame indices must be contiguous from zero")
        if not isinstance(sample["positions"], dict) or set(sample["positions"]) != names:
            raise ValueError("animation actor IDs differ from scene")
        for position in sample["positions"].values():
            vector(position, "sample.position")
    return animation
