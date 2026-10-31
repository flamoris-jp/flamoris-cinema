"""Repository-owned script launched by tools/run_blender_smoke.py inside Blender."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import runpy
import sys
import time
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from flamoris_cinema.blender_bridge import build_scene, export_take, script_args
from flamoris_cinema.core import simulate
from flamoris_cinema.framing import check_framing
from flamoris_cinema.render_device import configure_cycles, verify_selection, validate_options
from flamoris_cinema.io import read_json, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--device', choices=('CPU', 'HIP'), default='CPU')
    parser.add_argument('--gpu-name')
    parser.add_argument('--threads', type=int, default=2)
    args = parser.parse_args(script_args())
    validate_options(args.device, args.gpu_name, args.threads)
    started = time.monotonic()
    # Includes edited RGB/translation, identity after rename and negative cases.
    runpy.run_path(str(ROOT / 'tests/blender_acceptance.py'), run_name='__main__')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = read_json(ROOT / 'examples/red_falls.scene.json')
    animation = simulate(scene)
    framing = check_framing(scene, animation)
    write_json(args.out / 'framing.json', framing)
    if not framing['passed']:
        raise ValueError('whole-sphere camera framing preflight failed; inspect framing.json')
    write_json(args.out / 'scene.json', scene)
    write_json(args.out / 'motion.anim.json', animation)
    count = len(animation['frames'])
    frames = list(range(1, count + 1)) if args.full else sorted({1, count // 2 + 1, count})
    project_hashes, device_reports = {}, {}
    for camera in ('wide', 'close'):
        folder = args.out / camera
        folder.mkdir()
        target = build_scene(scene, animation, camera)
        configure_cycles(target, args.device, args.gpu_name, args.threads)
        blend_path = (folder / 'scene.blend').resolve()
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        # Exercise serialization as well as an in-memory transfer.
        bpy.ops.wm.open_mainfile(filepath=str(blend_path))
        returned = export_take()
        project_hashes[camera] = hashlib.sha256(blend_path.read_bytes()).hexdigest()
        for original, restored in zip(animation['frames'], returned['animation']['frames']):
            for name, position in original['positions'].items():
                if any(not math.isclose(a, b, abs_tol=1e-5, rel_tol=0) for a, b in zip(position, restored['positions'][name])):
                    raise ValueError('saved Blender project changed sampled motion')
        write_json(folder / 'returned.take.json', returned)
        target = bpy.context.scene
        target.render.image_settings.file_format = 'PNG'
        target.render.image_settings.color_mode = 'RGBA'
        device_reports[camera] = configure_cycles(target, args.device, args.gpu_name, args.threads)
        for frame in frames:
            verify_selection(target, device_reports[camera])
            target.frame_set(frame)
            target.render.filepath = str((folder / f'frame_{frame:04d}.png').resolve())
            bpy.ops.render.render(write_still=True)
    write_json(args.out / 'result.json', {
        'success': True, 'blender_version': bpy.app.version_string,
        'blender_build_hash': bpy.app.build_hash.decode('utf-8', errors='replace'),
        'device': args.device, 'render_devices': device_reports, 'mode': 'full' if args.full else 'preview',
        'frames_per_camera': frames, 'width': scene['render']['width'], 'height': scene['render']['height'],
        'project_sha256': project_hashes,
        'framing': 'passed',
        'roundtrip': 'passed', 'edited_subset_acceptance': 'passed',
        'elapsed_seconds': time.monotonic() - started,
    })
    print('CINEMA_SMOKE_OK')


if __name__ == '__main__':
    main()
