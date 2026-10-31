"""Blender-native 2D curve tessellation/extrusion into one tagged actor mesh.

Contours belonging to one SVG path stay in ONE curve, preserving compound holes.
Different authored strokes stay separate mesh components, with a face-part index.
"""
import json


def bezier_contours(commands):
    """Exact M/L/C geometry as Blender cubic knots (point, left, right)."""
    contours, nodes = [], []
    for cmd in commands:
        op = cmd[0]
        if op == 'M':
            p = list(cmd[1:])
            nodes = [[p[:], p[:], p[:]]]
        elif op in ('L', 'C'):
            p = list(cmd[-2:])
            left = list(cmd[3:5]) if op == 'C' else p[:]
            if op == 'C':
                nodes[-1][2] = list(cmd[1:3])
            nodes.append([p[:], left, p[:]])
        elif op == 'Z':
            if nodes[-1][0] == nodes[0][0]:
                nodes[0][1] = nodes.pop()[1]
            contours.append(nodes)
            nodes = []
    return contours


def part_metadata(asset):
    return [{k: p[k] for k in ('element_id', 'source_id', 'terminal')}
            for p in asset['data']['paths']]


def check_fill_topology(commands):
    """Reject compound paths whose SVG nonzero fill differs from nested holes.

The first slice accepts simple disjoint/nested contours, with opposite winding
at holes. Overlap, self-intersection and redundant same-winding inner contours
need a nonzero Boolean solver and must fail rather than change the letterform.
Curves are sampled at the native 12-step tessellation for this topology check.
"""
    rings = []
    for nodes in bezier_contours(commands):
        ring = []
        for a, b in zip(nodes, nodes[1:]+nodes[:1]):
            p, q, r, s = a[0], a[2], b[1], b[0]
            steps = 1 if p == q and r == s else 12
            for i in range(steps):
                t = i / steps
                point = tuple((1-t)**3*p[k]+3*(1-t)**2*t*q[k]+3*(1-t)*t*t*r[k]+t**3*s[k] for k in (0,1))
                if not ring or point != ring[-1]:
                    ring.append(point)
        if len(ring) < 3:
            raise ValueError('degenerate Glyph contour')
        rings.append(ring)
    if sum(map(len, rings)) > 4096:
        raise ValueError('Glyph path exceeds topology sampling budget')

    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])

    def intersects(a, b, c, d):
        if max(a[0],b[0]) < min(c[0],d[0]) or max(c[0],d[0]) < min(a[0],b[0]) or max(a[1],b[1]) < min(c[1],d[1]) or max(c[1],d[1]) < min(a[1],b[1]):
            return False
        return cross(a,b,c)*cross(a,b,d) <= 0 and cross(c,d,a)*cross(c,d,b) <= 0

    edges = [(ri,i,a,b) for ri, ring in enumerate(rings) for i,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1]))]
    for n,(ri,i,a,b) in enumerate(edges):
        for rj,j,c,d in edges[n+1:]:
            if ri == rj and (abs(i-j) == 1 or {i,j} == {0,len(rings[ri])-1}):
                continue
            if intersects(a,b,c,d):
                raise ValueError('overlapping/self-intersecting Glyph contours are not supported')

    def inside(point, ring):
        x,y = point
        count = 0
        for a,b in zip(ring,ring[1:]+ring[:1]):
            if (a[1] > y) != (b[1] > y) and x < a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]):
                count += 1
        return count % 2

    signs = []
    for ring in rings:
        area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))
        if abs(area) < 1e-8:
            raise ValueError('zero-area Glyph contour')
        signs.append(1 if area > 0 else -1)
    for i, ring in enumerate(rings):
        incoming = sum(signs[j] for j, other in enumerate(rings) if j != i and inside(ring[0],other))
        if incoming and incoming + signs[i]:
            raise ValueError('same-winding nested nonzero contours require a Boolean fill solver')


def build_glyph_mesh(target, actor):
    import bpy
    spec = actor['geometry']
    vertices, faces, parts = [], [], []
    for part_index, path in enumerate(spec['asset']['data']['paths']):
        check_fill_topology(path['commands'])
        curve = bpy.data.curves.new('Cinema Glyph stroke', 'CURVE')
        temporary = bpy.data.objects.new('Cinema Glyph tessellation', curve)
        target.collection.objects.link(temporary)
        mesh = None
        try:
            curve.dimensions = '2D'
            curve.resolution_u = 12
            curve.fill_mode = 'BOTH'
            curve.extrude = spec['depth'] / 2
            curve.bevel_depth = 0
            for contour in bezier_contours(path['commands']):
                spline = curve.splines.new('BEZIER')
                spline.bezier_points.add(len(contour) - 1)
                for point, (co, left, right) in zip(spline.bezier_points, contour):
                    point.handle_left_type = point.handle_right_type = 'FREE'
                    for name, xy in (('co', co), ('handle_left', left), ('handle_right', right)):
                        setattr(point, name, ((xy[0]-500)*spec['metres_per_unit'],
                                             (500-xy[1])*spec['metres_per_unit'], 0))
                spline.use_cyclic_u = True
            bpy.context.view_layer.update()
            evaluated = temporary.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = bpy.data.meshes.new_from_object(evaluated)
            if not mesh.polygons:
                raise ValueError('Glyph path produced no filled surface')
            offset = len(vertices)
            vertices.extend((v.co.x, -v.co.z, v.co.y) for v in mesh.vertices)
            faces.extend([offset + i for i in poly.vertices] for poly in mesh.polygons)
            parts.extend([part_index] * len(mesh.polygons))
        finally:
            if mesh is not None:
                bpy.data.meshes.remove(mesh)
            bpy.data.objects.remove(temporary, do_unlink=True)
            bpy.data.curves.remove(curve)
    mesh = bpy.data.meshes.new(actor['id'] + '_glyph')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    attribute = mesh.attributes.new(name='cinema_part', type='INT', domain='FACE')
    for item, part_index in zip(attribute.data, parts):
        item.value = part_index
    obj = bpy.data.objects.new(actor['id'], mesh)
    target.collection.objects.link(obj)
    obj['cinema_parts'] = json.dumps(part_metadata(spec['asset']), ensure_ascii=False, sort_keys=True)
    return obj
