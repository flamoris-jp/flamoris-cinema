"""Camera-independent fixed-step sphere/floor prototype (not a rigid-body engine)."""
import argparse
from pathlib import Path
from .contracts import VERSION, frame_count, motion_id, validate_animation, validate_scene
from .io import read_json, write_json


def simulate(scene):
    """120 Hz semi-implicit Euler; linear interpolation to any integer output fps."""
    validate_scene(scene)
    if scene['schema_version'] != 1:
        raise ValueError('reference simulation supports v1 sphere actors only; supply a sampled Glyph take')
    states = {a["id"]: (list(map(float, a["position"])),
                         list(map(float, a.get("velocity", [0, 0, 0])))) for a in scene["actors"]}
    count = frame_count(scene)
    tick = 0
    before = after = {name: p[:] for name, (p, _) in states.items()}
    frames = []
    for frame in range(count):
        numerator = frame * 120
        lo, remainder = divmod(numerator, scene["fps"])
        needed = lo + bool(remainder)
        while tick < needed:
            before = after
            for actor in scene["actors"]:
                p, v = states[actor["id"]]
                v[2] -= 9.81 / 120
                for axis in range(3):
                    p[axis] += v[axis] / 120
                if p[2] < actor["radius"]:
                    p[2] = float(actor["radius"])
                    v[2] = -v[2] * actor.get("restitution", 0)
                    if v[2] < 9.81 / 120:
                        v[2] = 0.0
            after = {name: p[:] for name, (p, _) in states.items()}
            tick += 1
        alpha = remainder / scene["fps"]
        positions = {name: ([x + (y - x) * alpha for x, y in zip(before[name], after[name])]
                             if remainder else after[name][:]) for name in states}
        frames.append({"frame": frame, "positions": positions})
    result = {"schema_version": VERSION, "fps": scene["fps"], "motion_id": motion_id(scene), "frames": frames}
    return validate_animation(result, scene)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--animation", type=Path, help="validate or reuse a baked performance")
    args = parser.parse_args(argv)
    if not args.validate_only and args.out is None:
        parser.error("--out is required unless --validate-only")
    try:
        scene = validate_scene(read_json(args.scene))
        animation = validate_animation(read_json(args.animation), scene) if args.animation else None
        if not args.validate_only:
            write_json(args.out, animation if animation is not None else simulate(scene))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
