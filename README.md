# FLAMORIS Cinema

**Portable scene, sampled animation and cinematic rendering infrastructure for FLAMORIS.**

シーンと演技データを保持し、同じ演技を複数のカメラから撮影するための基盤です。
Glyphは文字の形、Cinemaは空間と演技、Blenderはネイティブ編集と描画、Kachincoは編集と音を担当します。

**Status: development prototype, 0.1.0.** Implemented: validated scene/take contracts,
camera-independent sphere/floor simulation and Blender subset importer/exporter.
Portable core tests pass locally; real Blender roundtrip/render acceptance is pending.
This is not a full rigid-body engine, character animation system or AI film director.

## Identity and ownership

Cinema owns portable scene definitions, sampled performances, the reference
simulation and renderer adapters. Glyph owns letterforms, vector shapes and Style
DNA. Kachinco/KineticTypo own timeline editing, subtitles, audio and final export.
Generation owns generated assets/model inference. Blender owns native projects,
shaders, modifiers and renderer features beyond the supported interchange subset.

Start at the [FLAMORIS organization map](https://github.com/flamoris-jp/.github).
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
yet the actual 赤 Glyph. Physics uses 120 Hz gravity, sphere/floor contact, normal
restitution and constant horizontal velocity. No actor collisions, rotation,
friction, obstacle trip, walking or recovery are implemented.

## Optional Blender workflow

Target: Blender 4.5 LTS; actual version acceptance pending. Run from the checkout:

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

## Development checks

CI defines Python 3.11–3.13 on Windows/Linux. The real-Blender test is skipped when
Blender is absent; set `BLENDER` to its executable path to enable it. A skipped test
is not runtime acceptance. Core sampling, validation, camera independence, take
compatibility and CLI overwrite protection have automated tests.

## License

Code is [Apache 2.0](LICENSE). Third-party tools, models and produced assets retain
their own applicable terms. Commercial use of the code is welcome; individual
support is not guaranteed.
