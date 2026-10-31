"""Blender 4.5+ adapter. Importing this module does not require bpy.

The round trip preserves sphere translations, flat RGB, static cameras and point
lights. It is a sampled performance exchange, not a .blend serializer.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys

from .contracts import motion_id, validate_animation, validate_scene
from .interchange import make_take, validate_take
from .io import read_json, write_json

META = "cinema_take_v1"
TAG = "cinema_id"
KIND = "cinema_kind"


def _mesh_digest(obj):
    mesh = obj.data
    content = [[list(v.co) for v in mesh.vertices], [list(p.vertices) for p in mesh.polygons]]
    return hashlib.sha256(json.dumps(content, separators=(",", ":")).encode()).hexdigest()


def _mark(obj, kind, name):
    obj[TAG], obj[KIND] = name, kind
    if obj.type == "MESH":
        obj["cinema_mesh"] = _mesh_digest(obj)


def build_scene(scene, animation, camera=None):
    """Build in a NEW Blender scene. Existing scenes/objects are retained."""
    import bpy
    from mathutils import Vector

    if bpy.app.version < (4, 5, 0):
        raise ValueError("Blender 4.5 or newer is required")
    validate_animation(animation, scene)
    cameras = scene.get("cameras", [])
    if camera is not None and camera not in {c["id"] for c in cameras}:
        raise ValueError("unknown camera id")
    target = bpy.data.scenes.new("Cinema")
    bpy.context.window.scene = target
    target.render.fps = scene["fps"]
    target.render.fps_base = 1.0
    target.frame_start, target.frame_end = 1, len(animation["frames"])
    size = scene.get("render", {"width": 1280, "height": 720})
    target.render.resolution_x, target.render.resolution_y = size["width"], size["height"]
    target.render.resolution_percentage = 100
    target.render.pixel_aspect_x = target.render.pixel_aspect_y = 1.0
    target.render.use_motion_blur = False
    target.render.engine = "CYCLES"
    target.cycles.device, target.cycles.samples = "CPU", 16
    objects = {}
    for actor in scene["actors"]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=actor["radius"])
        obj = bpy.context.object
        obj.name = actor["id"]
        obj.location = actor["position"]
        mat = bpy.data.materials.new(actor["id"] + "_color")
        mat.use_nodes = False
        mat.diffuse_color = (*actor["color"], 1.0)
        obj.data.materials.append(mat)
        _mark(obj, "actor", actor["id"])
        objects[actor["id"]] = obj
    for sample in animation["frames"]:
        for name, position in sample["positions"].items():
            obj = objects[name]
            obj.location = position
            obj.keyframe_insert(data_path="location", frame=sample["frame"] + 1)
    # Every integer frame is keyed. Subframe interpolation is Blender-owned and
    # deliberately outside the portable contract (motion blur is disabled).
    for spec in cameras:
        data = bpy.data.cameras.new(spec["id"])
        data.type, data.sensor_fit = "PERSP", "HORIZONTAL"
        data.angle = math.radians(spec["fov_degrees"])
        obj = bpy.data.objects.new(spec["id"], data)
        target.collection.objects.link(obj)
        obj.location = spec["position"]
        direction = Vector(spec["target"]) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        obj["cinema_target_distance"] = direction.length
        _mark(obj, "camera", spec["id"])
        if camera == spec["id"] or (camera is None and target.camera is None):
            target.camera = obj
    for spec in scene.get("lights", []):
        data = bpy.data.lights.new(spec["id"], "POINT")
        data.energy, data.color = spec["energy"], spec["color"]
        obj = bpy.data.objects.new(spec["id"], data)
        target.collection.objects.link(obj)
        obj.location = spec["position"]
        _mark(obj, "light", spec["id"])
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, -0.1))
    floor = bpy.context.object
    floor.name, floor.scale = "Cinema floor", (10, 10, 0.1)
    _mark(floor, "floor", "__floor__")
    target[META] = json.dumps(make_take(scene, animation), allow_nan=False)
    target.frame_set(1)
    return target


def export_take():
    """Sample edited translations; reject topology/identity/rig changes.

    Cosmetic Blender settings remain in .blend; see the supported-subset table.
    Export never re-simulates physics or overwrites the .blend.
    """
    import bpy
    from mathutils import Vector

    target = bpy.context.scene
    if META not in target:
        raise ValueError("scene was not created by the Cinema bridge")
    original = validate_take(json.loads(target[META]))
    scene = deepcopy(original["scene"])
    expected = {a["id"]: "actor" for a in scene["actors"]}
    expected.update({c["id"]: "camera" for c in scene.get("cameras", [])})
    expected.update({c["id"]: "light" for c in scene.get("lights", [])})
    expected["__floor__"] = "floor"
    objects, errors = {}, []
    for obj in target.objects:
        name, kind = obj.get(TAG), obj.get(KIND)
        if name not in expected or expected.get(name) != kind or name in objects:
            errors.append(f"{obj.name}: missing/duplicate/unknown Cinema identity")
            continue
        objects[name] = obj
        if obj.parent or obj.constraints or obj.modifiers or obj.rigid_body or obj.rigid_body_constraint:
            errors.append(f"{name}: parent, constraint, modifier or rigid body is outside v1")
        expected_type = {"actor": "MESH", "floor": "MESH", "camera": "CAMERA", "light": "LIGHT"}[kind]
        if obj.type != expected_type:
            errors.append(f"{name}: object type changed")
            continue
        if obj.type == "MESH" and (_mesh_digest(obj) != obj.get("cinema_mesh") or obj.data.shape_keys):
            errors.append(f"{name}: geometry edited; v1 supports sphere proxies only")
        if kind != "actor" and (obj.animation_data or getattr(obj.data, "animation_data", None)):
            errors.append(f"{name}: only actor translation animation is supported")
        if kind in ("camera", "light") and (obj.scale - Vector((1, 1, 1))).length > 1e-6:
            errors.append(f"{name}: camera/light scale is outside v1")
        if kind == "actor" and obj.rotation_mode != "XYZ":
            errors.append(f"{name}: only XYZ rotation mode is supported")
        if kind == "camera" and obj.rotation_mode != "XYZ":
            errors.append(f"{name}: only XYZ camera rotation mode is supported")
        if obj.hide_render:
            errors.append(f"{name}: hidden render objects cannot be represented")
    if set(objects) != set(expected):
        errors.append("Cinema objects were added, removed or retagged")
    count = len(original["animation"]["frames"])
    if (target.frame_start, target.frame_end) != (1, count):
        errors.append("frame range changed; v1 keeps the original take duration")
    if target.render.fps != scene["fps"] or abs(target.render.fps_base - 1) > 1e-7:
        errors.append("fps changed; v1 keeps the original sample clock")
    if target.render.resolution_percentage != 100 or abs(target.render.pixel_aspect_x - target.render.pixel_aspect_y) > 1e-7:
        errors.append("only 100% resolution and square pixels are portable")
    if errors:
        raise ValueError("unsupported Blender edits:\n" + "\n".join(errors))
    saved_frame, saved_subframe = target.frame_current, target.frame_subframe
    try:
        target.frame_set(1)
        for actor in scene["actors"]:
            obj = objects[actor["id"]]
            materials = obj.data.materials
            if len(materials) != 1 or materials[0] is None or materials[0].use_nodes or materials[0].animation_data:
                raise ValueError(f"{actor['id']}: only one static non-node RGB material is supported")
            if abs(materials[0].diffuse_color[3] - 1) > 1e-6:
                raise ValueError("transparent materials are outside v1")
            actor["color"] = list(materials[0].diffuse_color[:3])
        floor = objects["__floor__"]
        if ((floor.location - Vector((0, 0, -0.1))).length > 1e-6 or
                (floor.scale - Vector((10, 10, 0.1))).length > 1e-6 or
                floor.rotation_euler.to_quaternion().angle > 1e-6):
            raise ValueError("floor transform changed; portable floor is fixed at z=0")
        for spec in scene.get("cameras", []):
            obj = objects[spec["id"]]
            if obj.data.type != "PERSP" or obj.data.sensor_fit != "HORIZONTAL" or obj.data.dof.use_dof:
                raise ValueError("only horizontal perspective cameras without DOF are portable")
            if abs(obj.data.shift_x) > 1e-6 or abs(obj.data.shift_y) > 1e-6:
                raise ValueError("camera lens shift is outside v1")
            direction = obj.rotation_euler.to_quaternion() @ Vector((0, 0, -1))
            rotation = direction.to_track_quat("-Z", "Y")
            if rotation.rotation_difference(obj.rotation_euler.to_quaternion()).angle > 1e-5:
                raise ValueError("camera roll is outside v1")
            spec["position"] = list(obj.location)
            spec["target"] = list(obj.location + direction * obj["cinema_target_distance"])
            spec["fov_degrees"] = math.degrees(obj.data.angle)
        for spec in scene.get("lights", []):
            obj = objects[spec["id"]]
            if obj.data.type != "POINT" or obj.data.use_nodes:
                raise ValueError("only non-node point lights are portable")
            spec.update(position=list(obj.location), color=list(obj.data.color), energy=obj.data.energy)
        frames = []
        for index in range(count):
            target.frame_set(index + 1)
            positions = {}
            for actor in scene["actors"]:
                obj = objects[actor["id"]]
                if (obj.scale - Vector((1, 1, 1))).length > 1e-6 or obj.rotation_euler.to_quaternion().angle > 1e-6:
                    raise ValueError(f"{actor['id']}: actor rotation/scale is outside v1")
                positions[actor["id"]] = list(obj.location)
            frames.append({"frame": index, "positions": positions})
        # The original simulation initial conditions remain intact. The returned
        # animation is authoritative; simulate(scene) explicitly creates a NEW take.
        scene["render"] = {"width": target.render.resolution_x, "height": target.render.resolution_y}
        animation = {"schema_version": 1, "fps": scene["fps"], "motion_id": motion_id(scene), "frames": frames}
        return make_take(scene, animation)
    finally:
        target.frame_set(saved_frame, subframe=saved_subframe)


def import_main(argv=None):
    import bpy
    parser = argparse.ArgumentParser(description="Import Cinema scene/motion or a portable take into Blender")
    parser.add_argument("inputs", type=Path, nargs="+", help="scene.json animation.json output.blend OR take.json output.blend")
    parser.add_argument("--camera")
    parser.add_argument("--render-dir", type=Path, help="optional CPU PNG sequence into a NEW directory")
    args = parser.parse_args(argv)
    try:
        if len(args.inputs) == 3:
            scene, animation = read_json(args.inputs[0]), read_json(args.inputs[1])
        elif len(args.inputs) == 2:
            take = validate_take(read_json(args.inputs[0]))
            scene, animation = take["scene"], take["animation"]
        else:
            raise ValueError("expected two or three paths")
        output = args.inputs[-1].resolve()
        if output.suffix.lower() != ".blend" or output.exists():
            raise ValueError("output must be a new .blend path")
        if args.render_dir and args.render_dir.exists():
            raise ValueError("render directory already exists")
        target = build_scene(scene, animation, args.camera)
        if args.render_dir and not target.camera:
            raise ValueError("rendering requires a scene camera")
        bpy.ops.wm.save_as_mainfile(filepath=str(output))
        if args.render_dir:
            args.render_dir.mkdir(parents=True, exist_ok=False)
            target.render.image_settings.file_format = "PNG"
            target.render.filepath = str(args.render_dir.resolve() / "frame_")
            bpy.ops.render.render(animation=True)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


def export_main(argv=None):
    parser = argparse.ArgumentParser(description="Export current Blender Cinema scene as a new portable take")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        write_json(args.output, export_take())
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


def script_args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
