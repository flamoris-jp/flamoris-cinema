"""Self-contained, immutable Glyph shape snapshot; no Glyph/fontTools dependency.

Source coordinates stay in the 1000-unit Y-down design box. Cinema maps them to
X/Z metres; the source anchor is the actor origin, and extrusion is along Y.
"""
import hashlib
import json
import re
from .contracts import fields, number

MAX_COMMANDS = 20000


def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_asset(asset):
    fields(asset, ('format', 'version', 'sha256', 'data'), path='glyph asset')
    if asset['format'] != 'flamoris-cinema-glyph' or type(asset['version']) is not int or asset['version'] != 1:
        raise ValueError('unsupported glyph asset format')
    data = asset['data']
    fields(data, ('manifest_sha256', 'svg_sha256', 'source', 'generator', 'conversion', 'occurrence',
                  'cue', 'variant_id', 'metrics', 'stroke_model', 'paths'), path='glyph data')
    for key in ('manifest_sha256', 'svg_sha256'):
        if not isinstance(data[key], str) or not re.fullmatch('[0-9a-f]{64}', data[key]):
            raise ValueError('invalid source checksum')
    fields(data['source'], ('kind', 'sha256', 'license_note'), path='source')
    if (data['source']['kind'] not in ('authored-skeleton', 'font-outline') or
            not isinstance(data['source']['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', data['source']['sha256']) or
            not isinstance(data['source']['license_note'], str) or not data['source']['license_note'].strip()):
        raise ValueError('invalid Glyph provenance')
    fields(data['generator'], ('name', 'version', 'fonttools'), path='generator')
    if data['generator']['name'] != 'flamoris-glyph' or any(not isinstance(v, str) or not v for v in data['generator'].values()):
        raise ValueError('invalid Glyph generator')
    fields(data['conversion'], ('name', 'version', 'fill_rule'), path='conversion')
    if (data['conversion']['name'] != 'skia-pathops' or data['conversion']['fill_rule'] != 'nonzero' or
            not isinstance(data['conversion']['version'], str) or not data['conversion']['version']):
        raise ValueError('invalid nonzero path conversion')
    occ = data['occurrence']
    fields(occ, ('occurrence_id', 'character', 'cue_id', 'line', 'column', 'glyph_variant_id'), path='occurrence')
    if (not isinstance(occ['character'], str) or len(occ['character']) != 1 or
            any(type(occ[k]) is not int or occ[k] < 1 for k in ('line', 'column')) or
            not isinstance(occ['occurrence_id'], str) or not re.fullmatch(r'cue\d{4,}-char\d{4,}', occ['occurrence_id']) or
            occ['glyph_variant_id'] != data['variant_id'] or not isinstance(data['variant_id'], str) or
            not re.fullmatch('g[0-9a-f]{24}', data['variant_id'])):
        raise ValueError('invalid occurrence/variant identity')
    cue = data['cue']
    fields(cue, ('id', 'text', 'start_ms', 'end_ms'), path='cue')
    if (not isinstance(cue['id'], str) or not re.fullmatch(r'cue\d{4,}', cue['id']) or
            cue['id'] != occ['cue_id'] or not occ['occurrence_id'].startswith(cue['id']+'-char') or
            not isinstance(cue['text'], str)):
        raise ValueError('invalid cue link')
    start, end = cue['start_ms'], cue['end_ms']
    if (start is None) != (end is None) or (start is not None and
            (type(start) is not int or type(end) is not int or not 0 <= start < end)):
        raise ValueError('invalid cue interval')
    lines = cue['text'].split('\n')
    if occ['line'] > len(lines) or occ['column'] > len(lines[occ['line']-1]) or lines[occ['line']-1][occ['column']-1] != occ['character']:
        raise ValueError('occurrence does not match cue text')
    metrics = data['metrics']
    fields(metrics, ('view_box', 'bounds', 'anchor', 'advance'), path='metrics')
    bounds = metrics['bounds']
    if metrics['view_box'] != [0, 0, 1000, 1000] or metrics['anchor'] != [500, 500] or not isinstance(bounds, list) or len(bounds) != 4:
        raise ValueError('invalid Glyph metrics')
    for v in bounds:
        number(v, 0, 1000, 'bounds')
    if not (bounds[0] < bounds[2] and bounds[1] < bounds[3]):
        raise ValueError('empty Glyph bounds')
    number(metrics['advance'], 0.0001, 100000, 'advance')
    if data['stroke_model'] not in ('authored', 'outline'):
        raise ValueError('invalid stroke model')
    paths = data['paths']
    if not isinstance(paths, list) or not 1 <= len(paths) <= 64:
        raise ValueError('invalid Glyph path count')
    ids, total = set(), 0
    for path in paths:
        fields(path, ('element_id', 'source_id', 'terminal', 'commands'), path='glyph path')
        pid = path['element_id']
        if not isinstance(pid, str) or not re.fullmatch('stroke[0-9]{3}', pid) or pid in ids:
            raise ValueError('duplicate/invalid stroke ID')
        ids.add(pid)
        if not isinstance(path['source_id'], str) or not 1 <= len(path['source_id']) <= 100:
            raise ValueError('invalid source stroke ID')
        if path['terminal'] not in (('tome', 'hane', 'harai') if data['stroke_model'] == 'authored' else (None,)):
            raise ValueError('invalid terminal metadata')
        commands = path['commands']
        if not isinstance(commands, list):
            raise ValueError('invalid commands')
        total += len(commands)
        if total > MAX_COMMANDS:
            raise ValueError('Glyph exceeds command budget')
        opened, edges = False, 0
        for cmd in commands:
            if not isinstance(cmd, list) or not cmd or not isinstance(cmd[0], str) or cmd[0] not in ('M', 'L', 'C', 'Z'):
                raise ValueError('unsupported glyph command')
            op = cmd[0]
            if len(cmd) != {'M': 3, 'L': 3, 'C': 7, 'Z': 1}[op]:
                raise ValueError('invalid command arity')
            # Controls may lie outside the design box even when the curve does not.
            for v in cmd[1:]:
                number(v, -10000, 10000, 'path coordinate')
            if op == 'M':
                if opened:
                    raise ValueError('open contour')
                opened, edges = True, 0
            elif op == 'Z':
                if not opened or edges < 2:
                    raise ValueError('empty contour')
                opened = False
            else:
                if not opened:
                    raise ValueError('path command outside contour')
                edges += 1
        if not commands or opened or commands[-1] != ['Z']:
            raise ValueError('open or empty Glyph path')
    if asset['sha256'] != digest(data):
        raise ValueError('Glyph snapshot checksum mismatch')
    return asset


def local_bounds(geometry):
    b = geometry['asset']['data']['metrics']['bounds']
    s, d = geometry['metres_per_unit'], geometry['depth'] / 2
    return [(b[0]-500)*s, -d, (500-b[3])*s], [(b[2]-500)*s, d, (500-b[1])*s]


def srgb_color(hex_color):
    channels = [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
