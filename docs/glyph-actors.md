# Glyph actors: stage 2 prototype

**Implemented; fixed native HIP preview accepted.** A read-only adapter snapshots one real
Glyph schema-2 occurrence into a self-contained Cinema v2 take. The fixed 赤 fixture
has seven authored stroke IDs. `--glyph` passed native save/reload, hole-cap area,
edited placement and rendered appearance on Blender 5.2.3 LTS. Stage 2 is accepted;
see [execution evidence](acceptance.md).
This is static staging and sampled translation, not walking, rotation or physics.
The additive v3 [part-performance slice](glyph-performance.md) now provides an
authored walk, while this document retains the accepted v2 static contract.

## Authority and compatibility

Glyph owns letterforms, occurrence/variant/stroke identity, licensing and Style DNA.
Cinema owns unit conversion, placement, thickness and sampled translation. Blender
tessellates/extrudes normalized paths. Source bundles are never rewritten.

V1 sphere scenes/takes remain supported. V2 is deliberately Glyph-only: actor
fields are `id`, `position`, `color`, `geometry`. Radius/velocity/restitution fail;
the reference simulator rejects v2. Mixed geometry, rotation, per-part acting,
collision proxies and recovery are future work. Floor placement is geometric.

## Read-only preparation

Core/Blender consumption needs no new package. Preparing new shapes needs a
separately installed Glyph 0.2 checkout plus optional fontTools and PathOps:

```sh
python -m pip install -e ".[glyph-prepare]" -e ../flamoris-glyph
python tools/prepare_glyph_actor.py /path/to/glyph-bundle --occurrence cue0002-char0001 --out new-red.take.json
```

Preparation calls Glyph's actual `validate_bundle`, verifies unchanged source,
and resolves an explicit occurrence. Invalid hashes/paths/SVG, missing identity
and multiple colours fail. Output is exclusive; no machine path is embedded.

SVG uses **nonzero** fill. BSD-3-Clause
[skia-pathops](https://github.com/fonttools/skia-pathops) 0.9 simplifies overlaps
and self-intersections within each original path under that rule. The actual 赤
has self-intersections in its hooks; direct extrusion can change its filled shape.
Separate strokes are never unioned. fontTools reads M/L/Q/C/H/V/Z; quadratics
become cubic segments. Skia float storage means converted curves are not byte-
identical to source curves. Original SVG checksum/metrics and converter version
are retained. Native meshes approximate curved paths at resolution 12.

Normalized contours must be simple, disjoint or nested with opposite-winding holes.
Remaining self-intersections, contour touches/overlap and same-winding nesting fail.
A topology guard samples at native resolution 12 and caps each path at 4096 points;
pathological finer curve features are outside this first slice. No fallback shape,
font substitution or texture-plane replacement is performed.

## Shape and coordinates

| Property | Meaning |
| --- | --- |
| Source | viewBox `[0,0,1000,1000]`, Y down, anchor `[500,500]` |
| Actor origin | Source anchor, not an inferred foot rig or visible bounds centre |
| `metres_per_unit` | .000001..0.1 m/unit; default .003, design box height = 3 m |
| Mapping | local X = `(u-500)*scale`, local Z = `(500-v)*scale` |
| `depth` | .0001..10 m, centred on local Y; default .12 m |
| Floor placement | Actor Z = `(ymax-500)*scale`; actual outline bottom at Z=0 |
| Colour | One opaque flat RGB, converted from SVG sRGB hex to linear RGB |
| Cue times | Retained provenance; not stage playback scheduling |
| Collision proxy | None; reference physics refuses Glyph actors |

`geometry = {kind:"glyph", asset, metres_per_unit, depth}`.
Asset: `{format:"flamoris-cinema-glyph",version:1,sha256,data}`. SHA-256 covers sorted
compact UTF-8 JSON `data`: source manifest/SVG checksums, provenance/license note,
Glyph generator and PathOps conversion versions, selected occurrence/cue/variant,
original metrics/stroke model and ordered paths. Paths retain `element_id`,
`source_id`, `terminal`, and numeric absolute M/L/C/Z command arrays. All contours
close; at most 64 paths and 20000 commands per asset. Controls are finite within
±10000 source units. JSON retains the 64 MiB limit. Hashes are consistency checks,
not proof of authenticity.

Take/scene/animation versions all equal 2. The compatibility hash includes timing,
actor IDs, initial positions, asset checksum, scale and depth. Camera/light/RGB
edits reuse motion; geometry/unit edits need a new compatible take. Samples remain
authoritative translations; native edits never trigger implicit simulation.

## Native mapping and acceptance

Each actor is one MESH; authored paths remain separate components. FACE integer
attribute `cinema_part` indexes `cinema_parts` metadata containing original IDs and
terminals. All contours of a path are tessellated together. Export verifies mesh/
part digests and metadata, then returns the original snapshot with edited placement.
Geometry edits, parents, rigs, modifiers, rotation and scale are rejected.

```sh
blender -b --factory-startup --python-exit-code 1 --python blender/import_scene.py -- examples/red_glyph.take.json red-glyph.blend --camera wide
blender -b red-glyph.blend --python-exit-code 1 --python blender/export_scene.py -- returned-red.take.json
python tools/run_blender_smoke.py --blender /path/to/blender --device HIP --gpu-name "RX 9060 XT" --threads 2 --glyph --out /path/to/new-glyph-preview
```

The fixed job runs sphere regression plus Glyph native checks: seven face-part IDs,
floor/thickness, rename/translation edit, save/reload/reimport, geometry rejection,
and synthetic compound-hole front-cap area of 2.88 m². The actual 赤 then goes through
two native camera projects with snapshot/motion checks. Framing preflight tests all
eight corners of its extruded-outline AABB. The host requires a Glyph success marker
and exact returned snapshot; sphere-only success cannot pass. Logs/projects/takes/
six PNGs/device reports/checksums use the existing receipt/ZIP failure flow.
No full render is needed for this static placement milestone.

## Fixture provenance

`examples/red_glyph.take.json` comes from FLAMORIS Glyph commit
`d10909b88d109df9a11587449484112e285fdfdd`, Apache-2.0 original authored shapes.
Regenerate using fontTools 4.61.1, PathOps 0.9.2 and that pinned Glyph checkout:

```sh
python -m flamoris_glyph.cli generate ../flamoris-glyph/examples/demo.srt --song "Cinema Glyph source fixture" --skeletons ../flamoris-glyph/examples/skeletons.json --style ../flamoris-glyph/examples/tango.style.json --seed 42 --out new-source-bundle
python tools/prepare_glyph_actor.py new-source-bundle --occurrence cue0002-char0001 --out new-red.take.json
```

Selected original SVG SHA-256:
`7eb51f6adf0bd7c7dc97c49473f970b2dc41f9c891a34becd227d8ab88b22f30`.
Optional Windows/Linux CI pins Glyph source and tests its real reader, immutable
inputs, converted fixture and tamper rejection. Core tests cover units, identity,
v2 contracts, camera independence, framing and nonzero-fill normalization.
Native tests are separate and skipped when Blender is absent.
