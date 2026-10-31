# Blender bridge (prototype)

Cinema owns the portable scene contract and physics results. Blender owns its own editable .blend project, shaders, modifiers, and rendering. Kachinco owns editing and export. Glyph owns vector shapes and style.

## Currently implemented
- Versioned JSON scene with sphere proxies.
- Deterministic vertical fixed-step gravity / floor contact, no rigid-body rotation or actor collisions.
- One-way scene + motion import into Blender as animated objects.
- No Blender installation, server service, remote access, MCP endpoint, or automatic export configured.

## Local experiment

```sh
python -m pip install -e .
flamoris-cinema examples/red_falls.scene.json --out red.anim.json
blender -b --python blender/import_scene.py -- examples/red_falls.scene.json red.anim.json red.blend
```

Blender invocation requires Blender to be installed separately and discoverable on PATH. Generated .blend contains editable sphere proxy objects with location keyframes, not the Glyph outline.

## Planned round trip
Forbid silently treating arbitrary .blend content as a Cinema scene. A Blender exporter will map a documented supported subset (named actors, transform keyframes, camera, supported meshes/materials) to a new scene revision. Unsupported nodes/constraints/simulations should be reported, not discarded. Design IDs and conflict policy before implementing this.

## LIME deployment plan
1. Check distro/CPU/GPU/driver compatibility and disk budget on the live host.
2. Test Blender headless as a normal user, CPU render first. Blender's AMD GPU support depends on Blender/ROCm combinations; do not assume ROCm PyTorch availability implies Cycles compatibility.
3. Install separately from ComfyUI's Python and GPU runtime; no system service or port initially.
4. Add a narrowly scoped job adapter later, with path allowlists, timeouts, resource ceilings, per-job isolation and no arbitrary Python submissions over MCP.
5. Add Cinema scene export and Kachinco import only after offline acceptance.
