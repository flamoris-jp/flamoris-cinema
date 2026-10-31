"""Run the fixed Cinema acceptance job and collect a result bundle.

No shell execution, GPU switching, installation, server or caller-supplied script.
Use from a repository checkout; no pip install is required.
"""
import argparse
import hashlib
import json
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


def validate_outputs(folder, full=False):
    result = read_json(folder / 'result.json')
    if (result.get('success') is not True or result.get('roundtrip') != 'passed' or
            result.get('edited_subset_acceptance') != 'passed' or result.get('device') != 'CPU'):
        raise ValueError('Blender did not report successful CPU acceptance')
    frames = list(range(1, 151)) if full else [1, 76, 150]
    if result.get('frames_per_camera') != frames:
        raise ValueError('unexpected rendered sample set')
    if (result.get('width'), result.get('height')) != (1280, 720):
        raise ValueError('unexpected render dimensions')
    for camera in ('wide', 'close'):
        root = folder / camera
        validate_take(read_json(root / 'returned.take.json'))
        with (root / 'scene.blend').open('rb') as stream:
            if stream.read(7) != b'BLENDER':
                raise ValueError('missing native Blender project')
        for frame in frames:
            with (root / f'frame_{frame:04d}.png').open('rb') as stream:
                header = stream.read(24)
            if (len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n' or
                    header[12:16] != b'IHDR' or struct.unpack('>II', header[16:24]) != (1280, 720)):
                raise ValueError('missing or invalid 720p PNG')
    return result


def run(blender, folder, full=False, timeout=900):
    executable = shutil.which(str(blender))
    if executable is None:
        raise ValueError('Blender executable not found; pass --blender PATH')
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    command = [executable, '-b', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
               '--python', str(ROOT / 'blender/smoke_test.py'), '--', '--out', str(folder)]
    if full:
        command.append('--full')
    started = time.monotonic()
    receipt = {'success': False, 'command': command, 'mode': 'full' if full else 'preview'}
    try:
        with (folder / 'blender.log').open('wb') as log:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
        if process.returncode != 0:
            raise ValueError(f'Blender exited with code {process.returncode}; inspect blender.log')
        result = validate_outputs(folder, full)
        receipt.update(success=True, blender_result=result)
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
    parser.add_argument('--out', required=True, type=Path, help='NEW job directory')
    parser.add_argument('--full', action='store_true', help='render 150 frames per camera; default is 3 previews per camera')
    parser.add_argument('--timeout', type=int, default=900, help='process timeout seconds (1..7200)')
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 7200:
        parser.error('--timeout must be in 1..7200')
    try:
        receipt = run(args.blender, args.out, args.full, args.timeout)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({'success': receipt['success'], 'output': str(args.out.resolve()),
                      'bundle': str(args.out.resolve() / 'cinema-smoke.zip'), 'error': receipt.get('error')}, ensure_ascii=False))
    return 0 if receipt['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
