"""Optional read-only Glyph bundle adapter. Glyph owns source validation."""
from copy import deepcopy
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from .glyph_asset import digest, validate_asset, srgb_color, local_bounds


def path_commands(svg_path):
    # Imported only by the preparation host, never by Blender or the core.
    from fontTools.pens.basePen import BasePen
    from fontTools.svgLib.path import parse_path
    import pathops

    class Pen(BasePen):
        def __init__(self):
            super().__init__(None)
            self.commands = []

        def _moveTo(self, p):
            self.commands.append(['M', *p])

        def _lineTo(self, p):
            self.commands.append(['L', *p])

        def _curveToOne(self, a, b, c):
            self.commands.append(['C', *a, *b, *c])

        def _qCurveToOne(self, q, end):
            start = self._getCurrentPoint()
            a = [p + 2*(v-p)/3 for p, v in zip(start, q)]
            b = [p + 2*(v-p)/3 for p, v in zip(end, q)]
            self._curveToOne(a, b, end)

        def _closePath(self):
            self.commands.append(['Z'])

        def _endPath(self):
            raise ValueError('open Glyph contour')

    pen = Pen()
    source = pathops.Path()
    source.fillType = pathops.FillType.WINDING
    parse_path(svg_path, source.getPen())
    # Resolve self-intersections/overlaps under SVG's default NONZERO rule.
    # Preserve separate authored strokes by simplifying each path separately.
    try:
        pathops.simplify(source, fix_winding=True).draw(pen)
    except pathops.PathOpsError as exc:
        raise ValueError('cannot resolve Glyph nonzero fill') from exc
    return pen.commands


def prepare_asset(directory, occurrence_id):
    try:
        from flamoris_glyph.bundle import validate_bundle
        import pathops
    except ImportError as exc:
        raise ValueError('Preparation requires separately installed flamoris-glyph 0.2 and skia-pathops 0.9') from exc
    directory = Path(directory)
    # Prevent source replacement/symlink ambiguity before invoking Glyph's reader.
    if directory.is_symlink() or (directory / 'manifest.json').is_symlink():
        raise ValueError('bundle and manifest must not be symlinks')
    with (directory / 'manifest.json').open('rb') as stream:
        manifest_bytes = stream.read(20_000_001)
    if len(manifest_bytes) > 20_000_000:
        raise ValueError('Glyph manifest exceeds 20 MB')
    manifest = validate_bundle(directory)
    selected = [o for o in manifest['occurrences'] if o['occurrence_id'] == occurrence_id]
    if len(selected) != 1:
        raise ValueError('select exactly one existing occurrence ID')
    occurrence = selected[0]
    glyph = next(g for g in manifest['glyphs'] if g['variant_id'] == occurrence['glyph_variant_id'])
    svg = (directory / glyph['asset']).read_bytes()
    if hashlib.sha256(svg).hexdigest() != glyph['sha256'] or (directory/'manifest.json').read_bytes() != manifest_bytes:
        raise ValueError('Glyph source changed during import')
    root = ET.fromstring(svg)
    colors = {p.attrib['fill'].upper() for p in root}
    if len(colors) != 1:
        raise ValueError('Cinema currently supports one flat RGB per Glyph actor')
    data = {
        'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(), 'svg_sha256': glyph['sha256'],
        'source': deepcopy(manifest['source']), 'generator': deepcopy(manifest['generator']),
        'conversion': {'name': 'skia-pathops', 'version': pathops.__version__, 'fill_rule': 'nonzero'},
        'occurrence': deepcopy(occurrence), 'cue': deepcopy(next(c for c in manifest['cues'] if c['id'] == occurrence['cue_id'])),
        'variant_id': glyph['variant_id'], 'metrics': deepcopy(glyph['metrics']), 'stroke_model': glyph['stroke_model'],
        'paths': [{**deepcopy(stroke), 'commands': path_commands(p.attrib['d'])}
                  for stroke, p in zip(glyph['strokes'], root)],
    }
    asset = {'format': 'flamoris-cinema-glyph', 'version': 1, 'data': data, 'sha256': digest(data)}
    from .glyph_blender import check_fill_topology
    for path in data['paths']:
        check_fill_topology(path['commands'])
    return validate_asset(asset), srgb_color(next(iter(colors)))


def stage_take(asset, color, *, metres_per_unit=0.003, depth=0.12):
    """A static placement take; this is not a physical Glyph simulation."""
    from .contracts import frame_count, motion_id, validate_scene
    from .interchange import make_take
    geometry = {'kind': 'glyph', 'asset': deepcopy(asset), 'metres_per_unit': metres_per_unit, 'depth': depth}
    low, _ = local_bounds(geometry)
    position = [0, 0, -low[2]]
    scene = {'schema_version': 2, 'fps': 30, 'duration_seconds': 5,
             'actors': [{'id': 'red_glyph', 'position': position, 'color': list(color), 'geometry': geometry}],
             'cameras': [
                 {'id': 'wide', 'position': [5, -9, 4], 'target': [0, 0, 1.05], 'fov_degrees': 50},
                 {'id': 'close', 'position': [2, -6, 2.7], 'target': [0, 0, 1.05], 'fov_degrees': 50}],
             'lights': [
                 {'id': 'key', 'position': [-3, -4, 6], 'color': [1, 1, 1], 'energy': 1400},
                 {'id': 'rim', 'position': [3, 2, 4], 'color': [1, 0.8, 0.65], 'energy': 900}],
             'render': {'width': 1280, 'height': 720}}
    validate_scene(scene)
    animation = {'schema_version': 2, 'fps': 30, 'motion_id': motion_id(scene),
                 'frames': [{'frame': i, 'positions': {'red_glyph': list(position)}} for i in range(frame_count(scene))]}
    return make_take(scene, animation)
