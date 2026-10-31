"""Run inside Blender: blender -b --python blender/import_scene.py -- scene.json animation.json output.blend
A one-way Blender importer for the portable scene prototype. No machine-specific paths.
"""
import json
import sys
from pathlib import Path
import bpy

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 3:
        raise SystemExit("expected scene.json animation.json output.blend")
    scene_path, anim_path, blend_path = map(Path, args)
    if blend_path.exists():
        raise SystemExit("refusing to overwrite .blend file")
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    animation = json.loads(anim_path.read_text(encoding="utf-8"))
    if scene.get("schema_version") != 1 or animation.get("schema_version") != 1:
        raise SystemExit("unsupported schema")
    if not isinstance(scene.get("actors"), list) or len(scene["actors"]) > 100:
        raise SystemExit("invalid actors")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.render.fps = animation["fps"]
    bpy.context.scene.frame_end = max(1, len(animation["frames"]))
    objects = {}
    for actor in scene["actors"]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=actor["radius"])
        obj = bpy.context.object
        obj.name = actor["id"]
        mat = bpy.data.materials.new(name=actor["id"] + "_material")
        mat.diffuse_color = (*actor["color"], 1.0)
        obj.data.materials.append(mat)
        objects[actor["id"]] = obj
    for item in animation["frames"]:
        for name, pos in item["positions"].items():
            obj = objects[name]
            obj.location = pos
            obj.keyframe_insert(data_path="location", frame=item["frame"] + 1)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, -0.1))
    bpy.context.object.name = "floor"
    bpy.context.object.scale = (10, 10, 0.1)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path.resolve()))

if __name__ == "__main__":
    main()
