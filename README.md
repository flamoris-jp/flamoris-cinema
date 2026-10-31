# FLAMORIS Cinema

**AI-directed scene, animation and cinematic rendering infrastructure for the FLAMORIS ecosystem.**

**Status: prototype bootstrap (0.1, unmerged).** This repository contains a portable scene JSON v1, a bounded fixed-step vertical-gravity simulation, a Blender one-way importer, and unit tests. It does **not** contain a full 3D/rigid-body engine, a live AI director, an MCP service, or a verified LIME Blender installation.

## Repository identity / 何者か

FLAMORIS Cinema represents editable scenes and animation independently of a particular rendering backend. The first experiment is a red actor proxy falling onto the ground, with motions calculated independently from the camera or renderer.

### Owns
- Versioned scene/actor/motion contracts, physics and camera abstraction (future)
- Scene simulation and render-adapter interfaces
- Explicitly supported Blender data interchange

### Does not own
- **Glyph** owns letterforms, vector shapes, Style DNA and glyph bundle provenance.
- **Kachinco / KineticTypo** own timeline editing, compositing, subtitles and final video export.
- **FLAMORIS Generation** owns generated images, video, audio and model inference.
- **Blender** owns its editable project files and native scene/render features.

See [Blender bridge design](docs/blender-bridge.md). See [Glyph](https://github.com/flamoris-jp/flamoris-glyph) and [Kachinco](https://github.com/flamoris-jp/flamoris-kachinco).

## Install and first test

Python 3.11+ on Windows/Linux. Standard-library-only Cinema prototype; Blender is optional.

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
flamoris-cinema examples/red_falls.scene.json --out red.anim.json
```

The output is explicit per-frame positions at 30 fps. It refuses to overwrite existing output. The physics is deliberately elementary: 120 Hz fixed integration, vertical gravity, floor contact for spherical proxy actors, no rotation, actor collisions, bounce, or walking animation.

### Optional Blender import

```sh
blender -b --python blender/import_scene.py -- examples/red_falls.scene.json red.anim.json red.blend
```

This writes an editable Blender scene with sphere proxies and transform keyframes. Blender must be installed and accessible on PATH. Import does not prove a render or LIME deployment has occurred. It also does not import SVG Glyph geometry yet.

## Roadmap

1. Define authoritative scene schema (transforms, cameras, lights, material subsets, stable actor IDs).
2. Add proper rigid-body physics, 2.5D glyph geometry import and collision shapes.
3. Blender bidirectional **supported-subset** bridge with clear conflict resolution and round-trip tests.
4. Camera renders and Kachinco asset/timeline integration.
5. AI director planning scenes under bounded declarative APIs, never arbitrary remote Blender Python.

## Safety and portability

Scene inputs must be validated. Prefer explicit local asset roots, predictable IDs, bounded simulations and isolated render jobs. Never expose raw Blender scripting as a public AI-execution API. Do not install Blender in ComfyUI's virtual environment or assume AMD ROCm support for PyTorch guarantees compatible Blender GPU rendering.

## License

Code is Apache 2.0 (see [LICENSE](LICENSE)). Third-party tools and produced assets retain their own licensing terms.

FLAMORIS is open-source creative software. Commercial use is welcome under applicable licenses; no individual support is guaranteed.
