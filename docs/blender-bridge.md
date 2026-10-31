# Blender bridge: supported-subset prototype

Cinema owns portable scene revisions and sampled performances. Blender owns native
projects, geometry, shaders and rendering. Glyph owns letterforms and Style DNA;
Kachinco owns timelines, sound, compositing and final video export.

**Implemented:** offline importer, sampled-motion exporter, static camera/light
mapping, optional CPU PNG rendering and a real-Blender acceptance script.
**Verified:** portable tests and reviewed external Blender 5.2.3 CPU/HIP previews and subset roundtrips.
See [acceptance evidence](acceptance.md): full HIP sphere sequences have passed.
The fixed Glyph native HIP preview has passed; performance research is deferred. Target: Blender 5.2.3 LTS.
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
| Shape | V1 UV sphere proxies; v2 immutable Glyph snapshots tessellated/extruded with stroke face IDs. Edited geometry/shape keys rejected. See [Glyph actors](glyph-actors.md); fixed native HIP preview accepted |
| Actor animation | Translation sampled at every integer output frame; original source conditions retained separately; rotation/scale edits rejected at samples |
| Material | One opaque static Diffuse BSDF → Material Output graph; export reads shader RGB, not viewport diffuse_color |
| Camera | Static perspective, horizontal FOV, position, target direction; original target distance retained; roll, shift, DOF, non-unit scale and animation rejected |
| Lights | Static point position, RGB and energy; neutral Emission → Light Output graph (or legacy no-tree light); custom light graphs rejected |
| Floor | Fixed Z=0 collision plane; finite 20m render helper; topology/transform edits rejected |
| Timeline | Original fps and duration; altered frame range or fps rejected; zero-based Cinema to one-based Blender mapping |
| Resolution | Square pixels, 100% dimensions; width and height returned |
| Rig/modifiers | Parents, constraints, modifiers and rigid bodies rejected; not silently baked |

The additive [v3 part-performance contract](glyph-performance.md) permits one exact
Glyph EMPTY/child-mesh hierarchy and sampled child local-Y rotation/translation.
The parent/rotation rejection above continues to apply to v1/v2 and to arbitrary
rigs; v3 does not promise general Blender skeleton/constraint interoperability.

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

## Blender 5.x compatibility

Blender 5.x always uses material nodes: setting `Material.use_nodes=False` no
longer disables them. The adapter creates one Diffuse BSDF connected to Material
Output and round-trips its Color input. Change that shader input to edit actor RGB;
viewport `diffuse_color` is not the portable rendered colour. Additional nodes,
links, material animation and nonzero diffuse roughness are rejected.

5.x also deprecates the light `use_nodes` flag. The bridge checks the node graph
itself. Where a light tree exists it contains neutral white Emission of strength 1
connected to Light Output; the portable Color/Power live on the light data.
Texture/animated light trees, exposure and temperature are outside the subset.
API fixes do not substitute for running the installed-version acceptance job.

References: [Material API](https://docs.blender.org/api/5.0/bpy.types.Material.html),
[Light API](https://docs.blender.org/api/5.2/bpy.types.Light.html),
[Cycles light nodes](https://docs.blender.org/manual/en/5.2/render/cycles/light_settings.html).

## Acceptance after separate Blender setup

For a collected, CPU-only test from a checkout (no pip install required):

```sh
python tools/run_blender_smoke.py --blender /path/to/blender --out /path/to/new-job
```

Default: two cameras × three PNG frames (1/76/150), both saved/reloaded native
projects, returned take JSON, actual Blender version/build hash, logs, failure or
success receipt, source/output SHA-256 manifests and a ZIP for inspection. Existing
job directories are refused. The child has a 900-second timeout; a timeout/nonzero
exit/missing result/missing output is failure. Failed logs remain available.
The host recognizes raw/gzip/Zstandard native containers and checks PNG headers/dimensions.
Actual native structural validation happens in Blender on reopen. New jobs also
verify the reopened-project hashes; visual appearance still requires inspection.
`--check-only --out /path/to/existing-job` revalidates existing results without
Blender, rendering or modifying any existing receipt or ZIP. This command is not a remote execution endpoint.

Use `--full --timeout 7200` with another NEW output directory to render all 150
frames per camera. Add `--encode` to create `wide.mp4` and `close.mp4` with
FFmpeg/libx264. The runner requires ffmpeg/ffprobe on PATH before starting the
expensive render, then verifies both streams are 1280×720, 30 fps, 150 frames and
five seconds. Encoder logs and source PNGs remain available if encoding fails.
This makes silent review clips; Kachinco still owns sound and final editing.
The ZIP is a local collection artifact, not automatically uploaded. For review,
the two MP4s can be transferred instead of the complete PNG archive.

The sample now performs whole-sphere framing preflight across all 150 samples
before rendering. It reserves 5% at each image edge, uses the bridge's explicit
0.1..1000 m clip range and records `framing.json`. A failed preflight stops the
job. The test is renderer-independent geometry; inspect actual renders for
occlusion, lighting and staging. See `framing.check_framing` and its tests.

For only the roundtrip test, set `BLENDER` to the executable's path if it is not on PATH, then run:

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

## Explicit CPU/HIP selection

Both `blender/import_scene.py` and the collected smoke runner accept `--device
CPU|HIP`, `--gpu-name NAME_OR_ID_FRAGMENT` and `--threads N` (1..64, default 2).
CPU remains the backwards-compatible default, now with a two-thread render setting.
For an initial six-image GPU preview:

```sh
python tools/run_blender_smoke.py --blender /path/to/blender --device HIP --gpu-name "RX 9060 XT" --threads 2 --out /path/to/new-hip-preview
```

In the Blender process, the adapter selects the HIP compute backend, discovers
available devices, requires exactly one matching GPU, disables CPU and all other
render devices and sets Cycles to GPU. It reapplies selection after reopening each
native project and verifies the selected flags before frames. Discovery/selection
failure stops the job; this code has no CPU fallback path. Process-local preferences
are not written to the user's preference file. HIP RT uses the installed Blender
default and its effective flag is recorded rather than inferred from an earlier run.

`result.json.render_devices` records each camera's selected name/id/type, backend,
Cycles mode, CPU render flag, thread setting and HIP RT flag. The host rejects HIP
results without explicit GPU-only selection evidence, and rejects CPU output when
HIP was requested. These settings do not independently prove GPU utilisation or
kernel execution: inspect actual Blender logs and live telemetry during acceptance.
No GPU reservation, runtime activation or service control is implemented here.

Blender render threads and OMP/OpenBLAS/MKL thread environment settings default to 2;
video encoding uses two threads as well. This reduces requested CPU parallelism,
but is not an OS CPU quota or a guarantee of a maximum temperature. GPU rendering
still needs CPU-side scene preparation, data transfers and potentially driver/kernel
compilation. Confirm temperatures and device use on the short preview before a full
sequence. Existing completed CPU images remain in their original job directory;
GPU jobs use fresh output directories, not implicit CPU/GPU mixed resumption.

Design references: [GPU render configuration](https://docs.blender.org/manual/en/5.2/editors/preferences/system.html)
and [Cycles preferences source](https://github.com/blender/blender/blob/main/intern/cycles/blender/addon/properties.py).
