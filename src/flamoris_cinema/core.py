"""Minimal deterministic 2.5D scene contract; Blender is an optional renderer."""
import argparse
import json
import math
from pathlib import Path

VERSION = 1

def validate_scene(scene):
    if not isinstance(scene, dict) or scene.get("schema_version") != VERSION:
        raise ValueError("unsupported scene schema")
    fps = scene.get("fps")
    duration = scene.get("duration_seconds")
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError("fps must be integer in 1..120")
    if type(duration) not in (int, float) or not math.isfinite(duration) or not 0 < duration <= 120:
        raise ValueError("invalid duration")
    actors = scene.get("actors")
    if not isinstance(actors, list) or not 1 <= len(actors) <= 100:
        raise ValueError("actors must be a bounded nonempty list")
    names = set()
    for actor in actors:
        if not isinstance(actor, dict) or set(actor) != {"id", "position", "radius", "color"}:
            raise ValueError("actor properties are invalid")
        name = actor["id"]
        if not isinstance(name, str) or not name or len(name) > 100 or name in names:
            raise ValueError("invalid or duplicate actor id")
        names.add(name)
        pos = actor["position"]
        if not isinstance(pos, list) or len(pos) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 10000 for v in pos):
            raise ValueError("invalid position")
        radius = actor["radius"]
        if type(radius) not in (int, float) or not math.isfinite(radius) or not 0 < radius <= 100:
            raise ValueError("invalid radius")
        color = actor["color"]
        if not isinstance(color, list) or len(color) != 3 or any(type(v) not in (int, float) or not 0 <= v <= 1 for v in color):
            raise ValueError("invalid RGB color")
    return scene

def simulate(scene):
    """Fixed 1/120-s vertical gravity with floor contact; spheres, no interactions."""
    validate_scene(scene)
    ticks_per_frame = 120 // scene["fps"] if 120 % scene["fps"] == 0 else None
    if ticks_per_frame is None:
        raise ValueError("prototype physics requires fps dividing 120")
    frames = []
    state = {a["id"]: [float(a["position"][2]), 0.0] for a in scene["actors"]}
    count = round(scene["duration_seconds"] * scene["fps"])
    for frame in range(count):
        current = {}
        for a in scene["actors"]:
            z, velocity = state[a["id"]]
            x, y = a["position"][:2]
            current[a["id"]] = [x, y, z]
        frames.append({"frame": frame, "positions": current})
        for _ in range(ticks_per_frame):
            for a in scene["actors"]:
                z, velocity = state[a["id"]]
                velocity -= 9.81 / 120
                z += velocity / 120
                if z < a["radius"]:
                    z, velocity = a["radius"], 0.0
                state[a["id"]] = [z, velocity]
    return {"schema_version": VERSION, "fps": scene["fps"], "frames": frames}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scene", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.scene.read_text(encoding="utf-8"))
    result = simulate(data)
    if args.out.exists():
        parser.error("output exists, refusing overwrite")
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
