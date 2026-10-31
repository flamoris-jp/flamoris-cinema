# Glyph part performance — v3 walk slice

**Accepted prototype:** a three-second authored 赤 walk, real Blender subset
roundtrip, Flamenco render and Kachinco CLI media/timeline/save handoff.
This is partial roadmap stage 3. Obstacle collision, physical falling and recovery
are not implemented. Earlier v1 sphere/v2 static Glyph takes remain unchanged.

## Portable v3 contract

Scene, animation and take versions are all 3. Like v2, actors contain `id`,
`position`, `color`, immutable `geometry`. Each adds `pivots`, an exact map of
every source `element_id` to an actor-local metre-space `[x,y,z]` pivot.
All IDs must match the Glyph snapshot; unknown/missing parts fail. Pivots are
bounded to ±100 m. Glyph owns the source geometry; Cinema owns these acting pivots.

Each frame contains the usual root `positions` plus `parts`:

```json
{
  "frame": 0,
  "positions": {"red_glyph": [-0.9, 0, 1]},
  "parts": {
    "red_glyph": {
      "stroke001": {"translation": [0, 0, 0], "angle_degrees": 0}
    }
  }
}
```

This abbreviated example needs all seven parts in an actual take. Part positions
are translation offsets, not absolute world coordinates. A point is transformed
by `root_position + pivot + RotY(angle) * (point - pivot) + translation`.
Only local Y rotation is supported; root rotation, arbitrary 3D rotations, scale,
mesh deformation and per-part colours are outside this slice. Translation is
bounded to ±100 m, angles to ±3600 degrees, and total part samples to 250000.
Every actor/part is required at every integer frame. Subframe interpolation is
Blender-owned; motion blur remains off. The compatibility hash includes immutable
shape/units/depth, root initial conditions and normalized pivot maps. It is not
a trajectory checksum. Camera/light/shared-RGB edits can reuse the exact motion.

## The fixed walk

The sample explicitly binds authored `s1/s2/s3` to the body, `s4/s5` to legs,
and `s6/s7` to arms. It does not infer anatomy from arbitrary characters.
Source geometry and the seven element/source IDs remain unchanged.

- 24 fps, 72 frames, three seconds, 640×360 review resolution.
- Four alternating half-second steps cover 1.8 m over two seconds, then a one-second hold.
- Swing feet follow smooth horizontal progress and an 18 cm lift; arms counter-swing.
- The lowest support point is pinned during stance; foot roll is deliberate.
- Feet are placed from the source control hull. For this polygonal authored fixture
  those extrema are exact; this is not general curved-foot collision or inverse kinematics.

The root follows a deterministic eased translation with a small body bob. Rigid
stroke limbs may separate at joints: the result is a cartoon letter performance,
not an anatomical rig. There is no actor/actor contact or physical simulation.

## Blender mapping and editable subset

A v3 root is an EMPTY with seven child meshes. Each child preserves its source
stroke geometry, shifted around its pivot; identity is an internal composite
`actor_id::element_id` tag, independent of display names. FACE part indices and
metadata remain attached. Only this exact parent hierarchy is supported.

Importer keys root location and each child's location/local-Y rotation at every
sample. Export samples edited poses without re-running the gait. Source geometry
and pivots remain immutable. Geometry changes, reparenting, parent inverses, rigs,
constraints, modifiers, delta transforms, scale and other rotation axes fail.
All parts must retain the same opaque RGB shader colour.

## Repeatable file workflow

Run from a checkout; prepared-take consumption has no optional dependencies:

```sh
python tools/build_glyph_walk.py --out red-walk.take.json
blender -b --factory-startup --python-exit-code 1 --python blender/import_scene.py -- red-walk.take.json red-walk.blend --camera wide --device HIP --gpu-name "RX 9060 XT" --threads 2
blender -b red-walk.blend --python-exit-code 1 --python blender/export_scene.py -- returned-walk.take.json
```

The two camera definitions consume the same performance. Framing checks every
transformed source control-hull point including extrusion thickness, at every
sample, with the existing screen-edge margin. It does not check occlusion.

`tools/prepare_flamenco_job.py` creates a **data-only** proposal for the Manager's
built-in `simple-blender-render`. It derives fps/frame range from the validated
take, requires an existing native file and a new output directory within the
explicit shared root, and requires the actual native scene name and current
Manager job-type etag. It does not submit, retry, manage Workers or alter services.

```sh
python tools/prepare_flamenco_job.py --take red-walk.take.json --shared-root /path/to/shared --blend-file /path/to/shared/red-walk.blend --render-output /path/to/shared/new-renders --scene-name Cinema --name Red-Walk --type-etag ACTUAL_MANAGER_ETAG --out new-job.json
```

The controller/operator must read the actual Manager API/job-type schema, validate
with its job-check endpoint and submit once. On uncertain submission, resolve the
unique job name/receipt before any retry. Worker HIP preferences, shared-path
translation and queue/resource ownership belong to deployment operations.
No installation, credentials, GPU runtime switching or external scripts are part
of the job proposal. Native motion is baked in `.blend`; rendering needs no Cinema
package installed in the Worker. Kachinco import uses its normal guarded upload
and timeline commands, never direct project-file edits.

See [acceptance evidence](acceptance.md) for the external execution and limitations.
