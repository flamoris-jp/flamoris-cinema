# FLAMORIS Cinema

**Portable scene, sampled animation and cinematic rendering infrastructure for FLAMORIS.**

シーンと演技データを保持し、同じ演技を複数のカメラから撮影するための基盤です。
Glyphは文字の形、Cinemaは空間と演技、Blenderはネイティブ編集と描画、Kachincoは編集と音を担当します。

**Status: development prototype, 0.1.0.** Implemented: validated scene/take contracts,
camera-independent sphere/floor simulation and Blender subset importer/exporter.
Portable tests pass locally; Blender 5.2.3 CPU/HIP previews, subset roundtrips and
two full five-second HIP camera sequences have passed. A read-only Glyph adapter,
immutable 赤 fixture and v2 staging/Blender mapping are implemented; native Glyph
acceptance remains pending. See [Glyph actors](docs/glyph-actors.md).
This is not a full rigid-body engine, character animation system or AI film director.

## Identity and ownership

Cinema owns portable scene definitions, sampled performances, the reference
simulation and renderer adapters. Glyph owns letterforms, vector shapes and Style
DNA. Kachinco/KineticTypo own timeline editing, subtitles, audio and final export.
Generation owns generated assets/model inference. Blender owns native projects,
shaders, modifiers and renderer features beyond the supported interchange subset.

Start at the [FLAMORIS organization map](https://github.com/flamoris-jp/.github).
開発の道筋と各段階の完成条件は [ロードマップ](docs/roadmap.md) を参照。

See [architecture and next slices](docs/architecture.md),
[scene/time contract](docs/scene-contract.md), and [Blender bridge](docs/blender-bridge.md).

## Install and test

Python 3.11+; runtime uses the standard library. Core is portable across Windows
and Linux; Blender is optional and installed separately.

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
python -m flamoris_cinema.core examples/red_falls.scene.json --out red.anim.json
python -m flamoris_cinema.core examples/red_falls.scene.json --animation red.anim.json --validate-only
```

Installed CLI `flamoris-cinema` accepts the same arguments. Output paths must be
new. `--animation FILE --out NEW_FILE` reuses an existing sampled performance
without simulation. `--validate-only` validates inputs without writing.

The sample has a red **sphere proxy**, two cameras and two point lights; it is not
yet the actual 赤 Glyph. A separate `examples/red_glyph.take.json` contains the
actual authored Glyph as a static stage take; it is not a sphere simulation.
Physics uses 120 Hz gravity, sphere/floor contact, normal
restitution and constant horizontal velocity. No actor collisions, rotation,
friction, obstacle trip, walking or recovery are implemented.

## Optional Blender workflow

Target: Blender 5.2.3 LTS; minimum API version 4.5. Sphere preview/full-sequence
acceptance is recorded in [acceptance evidence](docs/acceptance.md). Run from the checkout:

```sh
blender -b --python-exit-code 1 --python blender/import_scene.py -- examples/red_falls.scene.json red.anim.json red-wide.blend --camera wide
blender -b --python-exit-code 1 --python blender/import_scene.py -- examples/red_falls.scene.json red.anim.json red-close.blend --camera close
```

Add `--render-dir renders/wide` to render a CPU PNG sequence into a new directory.
Both commands use the same motion. The importer creates a new Blender scene and
retains existing scenes. It does not need Cinema installed inside Blender's Python.

After supported edits in Blender, save the project as `red-edited.blend`:

```sh
blender -b red-edited.blend --python-exit-code 1 --python blender/export_scene.py -- edited.take.json
blender -b --python-exit-code 1 --python blender/import_scene.py -- edited.take.json roundtrip.blend --camera close
```

Round trip covers sampled actor translation, flat RGB, static perspective cameras
and point lights. Geometry changes, rigs, modifiers and other listed structural
features are rejected. Native renderer cosmetics remain in `.blend`. See the
[precise supported-subset table and acceptance procedure](docs/blender-bridge.md).
No installation, live service, MCP endpoint or GPU setup is included.

### Collected CPU acceptance job

From a checkout, run one fixed, repository-owned Blender job (no pip install needed):

```sh
python tools/run_blender_smoke.py --blender /path/to/blender --out /path/to/new-job
```

It runs edited-subset acceptance, saves/reloads native projects, compares sampled
motion and renders frames 1/76/150 from each camera at 720p. The new job directory
contains native projects, PNGs, returned takes, a versioned execution result, log,
receipt, checksums and `cinema-smoke.zip`. A failed run returns nonzero and retains
its logs/receipt; it never counts as accepted. Existing outputs can be rechecked without rendering or changing their receipt using `--check-only --out /path/to/existing-job`. Add `--full --timeout 7200` in a NEW
job directory for all 150 frames per camera. Add `--encode` to also produce and
verify `wide.mp4` and `close.mp4` (5 seconds, 720p, 30 fps). FFmpeg with libx264 and
ffprobe must already be on PATH; the runner checks before rendering. This defaults to CPU; HIP is explicitly selectable as described below. Installation GPU
smoke results do not by themselves verify Cinema rendering.

Before any sample rendering, geometric preflight checks the whole sphere at all
150 samples, reserving 5% of screen width/height along each edge; results are saved
in `framing.json`. The close sample camera was reframed after the first real preview.
This checks perspective clipping, not occlusion or final image appearance.

### Explicit HIP preview

```sh
python tools/run_blender_smoke.py --blender /path/to/blender --device HIP --gpu-name "RX 9060 XT" --threads 2 --out /path/to/new-hip-preview
```

This renders the same six preview images. A single HIP GPU must match the name/id
fragment. CPU and other render devices are disabled; missing/ambiguous GPUs fail
instead of selecting CPU. Device selection is reapplied after native-file reload,
checked before frames and recorded for each camera, including the effective HIP RT
preference. Host validation rejects a CPU result when HIP was requested. A real HIP preview has passed; see [acceptance evidence](docs/acceptance.md).
The full five-second HIP sphere run has also passed. Performance research is
deferred until an actual production need; preview timings are not a controlled benchmark.

The default render/helper thread setting is now 2 (`--threads 1..64`), also passed
to Blender and common CPU math-library environment settings. MP4 encoding uses two
threads. These are configuration limits, not an OS CPU quota or temperature limit;
scene preparation/driver compilation and encoding can still use CPU resources.
No runtime/service is started or stopped and user preferences are not saved.
After reviewing the short HIP preview and temperatures, add `--full --encode` in a
NEW directory to render complete videos. No resumed-frame mixing is implemented.

### Glyph stage preview (native acceptance pending)

```sh
python tools/run_blender_smoke.py --blender /path/to/blender --device HIP --gpu-name "RX 9060 XT" --threads 2 --glyph --out /path/to/new-glyph-preview
```

This uses the prepared, font-free actual 赤 fixture, runs Glyph-specific native
checks and renders six stills from two cameras. It needs no Glyph/fontTools/PathOps
installation in Blender. `--full` is unnecessary for this static stage. Geometry,
unit conversion, IDs, source licensing and optional source preparation are documented
in [Glyph actors](docs/glyph-actors.md). Walking/collision/recovery are later work.

## Development checks

CI defines Python 3.11–3.13 on Windows/Linux. The real-Blender test is skipped when
Blender is absent; set `BLENDER` to its executable path to enable it. A skipped test
is not runtime acceptance. Core sampling, validation, camera independence, take
compatibility and CLI overwrite protection have automated tests.

## License

Code is [Apache 2.0](LICENSE). Third-party tools, models and produced assets retain
their own applicable terms. Commercial use of the code is welcome; individual
support is not guaranteed.
