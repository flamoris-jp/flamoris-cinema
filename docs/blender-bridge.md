# Blender bridge: supported-subset prototype

Cinema owns portable scene revisions and sampled performances. Blender owns native
projects, geometry, shaders and rendering. Glyph owns letterforms and Style DNA;
Kachinco owns timelines, sound, compositing and final video export.

**Implemented:** offline importer, sampled-motion exporter, static camera/light
mapping, optional CPU PNG rendering and a real-Blender acceptance script.
**Verified here:** portable Python tests only. Blender execution, visual quality,
GPU rendering and live deployment remain unverified. Target: Blender 4.5 LTS.
The adapter rejects versions older than 4.5; later versions require acceptance.

## Workflow

From the repository root, after installing Cinema (`python -m pip install -e .`):

```sh
python -m flamoris_cinema.core examples/red_falls.scene.json --out red.anim.json
python -m flamoris_cinema.core examples/red_falls.scene.json --animation red.anim.json --validate-only
blender -b --python-exit-code 1 --python blender/import_scene.py -- examples/red_falls.scene.json red.anim.json red-wide.blend --camera wide
blender -b --python-exit-code 1 --python blender/import_scene.py -- examples/red_falls.scene.json red.anim.json red-close.blend --camera close
```

Both projects receive the **same** `red.anim.json`; no second simulation or AI
video generation occurs. All declared cameras are imported; the chosen camera is
active. With `--render-dir renders/wide` (a new directory), import also renders a
CPU Cycles PNG sequence. Rendering requires at least one declared camera.
This is an offline adapter, not a production render scheduler or MP4 encoder.

Open a generated project in Blender, edit supported properties and save under a
new name, e.g. `red-edited.blend`. Export and reimport:

```sh
blender -b red-edited.blend --python-exit-code 1 --python blender/export_scene.py -- edited.take.json
blender -b --python-exit-code 1 --python blender/import_scene.py -- edited.take.json roundtrip.blend --camera close
```

The scripts load Cinema from the checkout's `src` directory, so Cinema does not
need to be installed into Blender's Python. Import builds a **new Blender scene**,
retaining existing scenes and objects. The new scene becomes active and the saved
project includes the existing scenes too; use `-b` from a clean startup for isolated
projects. Exports sample the active Cinema scene and restore its current frame.
Existing output files and render directories are refused.

## Supported subset

| Data | Import/export semantics |
| --- | --- |
| Actor identity | `cinema_id`/`cinema_kind` custom properties; display-name edits allowed; new/deleted/duplicated/retagged entities rejected |
| Shape | Import creates UV sphere proxies; edited vertex/topology data and shape keys rejected on export; Glyph outlines not imported |
| Actor animation | Translation sampled at every integer output frame; original source conditions retained separately; rotation/scale edits rejected at samples |
| Material | One opaque non-node static diffuse RGB per actor; export reads its colour |
| Camera | Static perspective, horizontal FOV, position, target direction; original target distance retained; roll, shift, DOF, non-unit scale and animation rejected |
| Lights | Static non-node point position, RGB and energy; animation/non-unit scale rejected |
| Floor | Fixed Z=0 collision plane; finite 20m render helper; topology/transform edits rejected |
| Timeline | Original fps and duration; altered frame range or fps rejected; zero-based Cinema to one-based Blender mapping |
| Resolution | Square pixels, 100% dimensions; width and height returned |
| Rig/modifiers | Parents, constraints, modifiers and rigid bodies rejected; not silently baked |

Export is a **performance and basic scene exchange**, not a complete appearance
round trip. Native render engine settings, world/background, shadows, surface
roughness/specularity, light softness, floor material, collections and editor state
remain only in `.blend`; these cosmetic settings are intentionally not serialized
or exhaustively diagnosed. RGB alone does not guarantee pixel-identical rendering.
Subframe curves/motion blur, renderer compositing and interpolation are also outside
the contract. The importer keys every output frame and disables motion blur.

Exporter validation rejects the listed unsupported structural edits before writing
a take. There is no automatic merge or write back to an existing source file.
Cinema does not claim arbitrary `.blend` files are portable or safe; only open
trusted native projects in a local Blender process.

## Acceptance after separate Blender setup

Set `BLENDER` to the executable's path if it is not on PATH, then run:

```sh
python -m unittest discover -s tests -v
```

`test_blender_integration` launches real Blender, checks import → edits → export →
reimport, stable IDs after renaming, sampled translation preservation, current-frame
restoration and refusal of geometry edits. It is explicitly skipped when Blender
is absent; a skip is not Blender acceptance. Then use the two camera commands above
with fresh render directories and inspect floor contact and framing at 720p.

No server installation, runtime restart, port, remote scripting service or GPU
configuration is performed by this repository. The separate setup workflow owns
Blender installation. Future remote jobs should accept validated data and bounded
render options, with isolated work directories and time/resource limits, rather
than caller-supplied Python.

## References

The adapter uses Blender's public [keyframe insertion API](https://docs.blender.org/api/4.5/bpy.types.bpy_struct.html),
[scene frame evaluation](https://docs.blender.org/api/4.5/bpy.types.Scene.html)
and [camera properties](https://docs.blender.org/api/4.5/bpy.types.Camera.html).
API compatibility and live rendering must be verified with the installed version.
