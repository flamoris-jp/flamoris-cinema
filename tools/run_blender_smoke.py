"""Run the fixed Cinema acceptance job and collect a result bundle.

No shell execution, GPU switching, installation, server or caller-supplied script.
Use from a repository checkout; no pip install is required.
"""
import argparse
import hashlib
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from flamoris_cinema.interchange import validate_take
from flamoris_cinema.io import read_json, write_json
from flamoris_cinema.render_device import validate_options


def native_project_container(path):
    """Recognize Blender containers, not the inner file structure.

    Native structural validation belongs to Blender's save/reopen job. Compressed
    .blend files do not begin with BLENDER; no decompressor dependency is needed.
    """
    with Path(path).open('rb') as stream:
        prefix = stream.read(17)
    if len(prefix) < 17:
        raise ValueError('truncated native Blender project')
    if prefix.startswith(b'BLENDER'):
        return 'raw'
    if prefix.startswith(b'\x1f\x8b'):
        return 'gzip'
    if prefix.startswith(b'\x28\xb5\x2f\xfd'):
        return 'zstd'
    raise ValueError('unrecognized native Blender project container')


def validate_outputs(folder, full=False, device=None, glyph=False):
    result = read_json(folder / 'result.json')
    if (result.get('success') is not True or result.get('roundtrip') != 'passed' or
            result.get('edited_subset_acceptance') != 'passed' or result.get('device') not in ('CPU', 'HIP')):
        raise ValueError('Blender did not report successful acceptance')
    if device is not None and result.get('device') != device:
        raise ValueError('reported render device differs from the requested device')
    if glyph and (result.get('subject') != 'glyph' or result.get('glyph_acceptance') != 'passed'):
        raise ValueError('Glyph acceptance result missing')
    if result.get('device') == 'HIP':
        reports = result.get('render_devices', {})
        for camera in ('wide', 'close'):
            report = reports.get(camera, {})
            selected = report.get('devices', [])
            if (report.get('backend') != 'HIP' or report.get('cycles_device') != 'GPU' or
                    report.get('cpu_render_enabled') is not False or len(selected) != 1 or selected[0].get('type') != 'HIP'):
                raise ValueError('HIP result lacks explicit GPU-only selection evidence')
    frames = list(range(1, 151)) if full else [1, 76, 150]
    if result.get('frames_per_camera') != frames:
        raise ValueError('unexpected rendered sample set')
    if (result.get('width'), result.get('height')) != (1280, 720):
        raise ValueError('unexpected render dimensions')
    if 'framing' in result:
        framing = read_json(folder / 'framing.json')
        if result['framing'] != 'passed' or framing.get('passed') is not True:
            raise ValueError('whole-sphere framing preflight did not pass')
    for camera in ('wide', 'close'):
        root = folder / camera
        take = validate_take(read_json(root / 'returned.take.json'))
        if glyph:
            source = validate_take(read_json(ROOT / 'examples/red_glyph.take.json'))
            if (take['scene']['actors'][0]['geometry'] != source['scene']['actors'][0]['geometry'] or
                    len(take['scene']['actors']) != 1 or take['scene']['actors'][0]['id'] != 'red_glyph'):
                raise ValueError('returned Glyph differs from the fixed source snapshot')
        native_project_container(root / 'scene.blend')
        project_hashes = result.get('project_sha256')
        if project_hashes is not None:
            actual = hashlib.sha256((root / 'scene.blend').read_bytes()).hexdigest()
            if project_hashes.get(camera) != actual:
                raise ValueError('native Blender project checksum differs from reopened project')
        for frame in frames:
            with (root / f'frame_{frame:04d}.png').open('rb') as stream:
                header = stream.read(24)
            if (len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n' or
                    header[12:16] != b'IHDR' or struct.unpack('>II', header[16:24]) != (1280, 720)):
                raise ValueError('missing or invalid 720p PNG')
    return result


def verify_video(path, probe=None):
    probe = probe or shutil.which('ffprobe')
    if not probe:
        raise ValueError('ffprobe is required to verify MP4 output')
    process = subprocess.run([probe, '-v', 'error', '-select_streams', 'v:0',
                              '-show_entries', 'stream=width,height,avg_frame_rate,nb_frames:format=duration',
                              '-of', 'json', str(path)], capture_output=True, text=True, timeout=60)
    if process.returncode:
        raise ValueError('ffprobe failed to inspect encoded video')
    info = json.loads(process.stdout)
    streams = info.get('streams', [])
    if len(streams) != 1:
        raise ValueError('encoded video must have one video stream')
    stream = streams[0]
    try:
        correct = ((stream.get('width'), stream.get('height')) == (1280, 720) and
                   Fraction(stream.get('avg_frame_rate', '0')) == 30 and
                   int(stream.get('nb_frames', 0)) == 150 and
                   abs(float(info.get('format', {}).get('duration', 0)) - 5) < 0.01)
    except (ValueError, ZeroDivisionError, TypeError):
        correct = False
    if not correct:
        raise ValueError('encoded video must be 1280x720, 30fps, 150 frames and 5 seconds')
    return info


def encode_videos(folder, encoder, probe):
    outputs = {}
    for camera in ('wide', 'close'):
        output = folder / f'{camera}.mp4'
        command = [encoder, '-nostdin', '-v', 'error', '-n', '-framerate', '30', '-start_number', '1',
                   '-i', str(folder / camera / 'frame_%04d.png'), '-frames:v', '150',
                   '-c:v', 'libx264', '-threads', '2', '-filter_threads', '2', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)]
        with (folder / f'ffmpeg-{camera}.log').open('wb') as log:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=300)
        if process.returncode:
            raise ValueError(f'MP4 encoding failed; inspect ffmpeg-{camera}.log (PNG renders are retained)')
        verify_video(output, probe)
        outputs[camera] = output.name
    return outputs


def run(blender, folder, full=False, timeout=900, encode=False, device='CPU', gpu_name=None, threads=2, glyph=False):
    validate_options(device, gpu_name, threads)
    executable = shutil.which(str(blender))
    if executable is None:
        raise ValueError('Blender executable not found; pass --blender PATH')
    encoder, probe = shutil.which('ffmpeg'), shutil.which('ffprobe')
    if encode:
        if not full or not encoder or not probe:
            raise ValueError('--encode requires --full and ffmpeg/ffprobe on PATH')
        available = subprocess.run([encoder, '-hide_banner', '-encoders'], capture_output=True, text=True, timeout=10)
        if available.returncode or 'libx264' not in available.stdout:
            raise ValueError('FFmpeg libx264 encoder is required before rendering')
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    command = [executable, '-b', '--factory-startup', '-t', str(threads), '--disable-autoexec', '--python-exit-code', '1',
               '--python', str(ROOT / 'blender/smoke_test.py'), '--', '--out', str(folder), '--device', device, '--threads', str(threads)]
    if gpu_name is not None:
        command.extend(['--gpu-name', gpu_name])
    if full:
        command.append('--full')
    if glyph:
        command.append('--glyph')
    started = time.monotonic()
    receipt = {'success': False, 'command': command, 'mode': 'full' if full else 'preview',
               'requested_device': device, 'threads': threads}
    try:
        print(f'{device} render job started. Progress log: {folder / "blender.log"}', flush=True)
        with (folder / 'blender.log').open('wb') as log:
            environment = os.environ.copy()
            for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
                environment[name] = str(threads)
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False, env=environment)
        if process.returncode != 0:
            raise ValueError(f'Blender exited with code {process.returncode}; inspect blender.log')
        result = validate_outputs(folder, full, device, glyph)
        receipt['blender_result'] = result
        if encode:
            receipt['videos'] = encode_videos(folder, encoder, probe)
        receipt['success'] = True
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        receipt['error'] = str(exc)
    receipt['elapsed_seconds'] = time.monotonic() - started
    receipt['source_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for parent in (ROOT / 'src', ROOT / 'blender', ROOT / 'tests', ROOT / 'tools')
                                for p in sorted(parent.rglob('*.py'))}
    write_json(folder / 'receipt.json', receipt)
    # Separate reusable native projects and PNGs remain available uncompressed.
    manifest = [{'path': str(p.relative_to(folder)), 'bytes': p.stat().st_size,
                 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in sorted(folder.rglob('*')) if p.is_file()]
    write_json(folder / 'manifest.json', manifest)
    with zipfile.ZipFile(folder / 'cinema-smoke.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in manifest:
            archive.write(folder / entry['path'], entry['path'])
        archive.write(folder / 'manifest.json', 'manifest.json')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', default='blender', help='executable name or absolute path')
    parser.add_argument('--out', required=True, type=Path, help='NEW job directory, or existing directory with --check-only')
    parser.add_argument('--check-only', action='store_true', help='recheck existing output without Blender or changing files')
    parser.add_argument('--device', choices=('CPU', 'HIP'), default='CPU')
    parser.add_argument('--gpu-name', help='unique HIP GPU name/id fragment')
    parser.add_argument('--threads', type=int, default=2, help='render/helper thread setting, 1..64; default 2')
    parser.add_argument('--full', action='store_true', help='render 150 frames per camera; default is 3 previews per camera')
    parser.add_argument('--glyph', action='store_true', help='use the fixed static Glyph stage and Glyph native acceptance')
    parser.add_argument('--encode', action='store_true', help='with --full, make and verify two 5-second MP4s using ffmpeg/ffprobe')
    parser.add_argument('--timeout', type=int, default=900, help='process timeout seconds (1..7200)')
    args = parser.parse_args(argv)
    if args.encode and (not args.full or args.check_only):
        parser.error('--encode requires --full and cannot be used with --check-only')
    if not 1 <= args.timeout <= 7200:
        parser.error('--timeout must be in 1..7200')
    try:
        if args.check_only:
            result = read_json(args.out / 'result.json')
            result = validate_outputs(args.out, full=result.get('mode') == 'full', device=args.device if args.device != 'CPU' else None,
                                      glyph=args.glyph or result.get('subject') == 'glyph')
            print(json.dumps({'success': True, 'check_only': True, 'output': str(args.out.resolve()),
                              'blender_result': result}, ensure_ascii=False))
            return 0
        receipt = run(args.blender, args.out, args.full, args.timeout, args.encode, args.device, args.gpu_name, args.threads, args.glyph)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({'success': receipt['success'], 'output': str(args.out.resolve()),
                      'bundle': str(args.out.resolve() / 'cinema-smoke.zip'),
                      'videos': receipt.get('videos', {}), 'error': receipt.get('error')}, ensure_ascii=False))
    return 0 if receipt['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
