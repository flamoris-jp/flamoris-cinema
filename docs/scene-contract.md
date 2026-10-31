# Scene and sampled performance contract v1

**Status:** implemented Python contract, prototype physics. The executable authority is
`flamoris_cinema.contracts.validate_scene/validate_animation`; this document explains its semantics.
No external JSON Schema dependency is required. Unknown properties fail validation.

## Coordinates and time

- Right-handed world, metres, Z up, floor at Z=0. Sphere `position` is its centre.
- RGB is linear, three numbers in 0..1. No textures, alpha, external files or executable fields.
- `fps` is an integer in 1..120. Duration is at most 120 seconds and must produce a
  positive integral frame count. Frame `n` samples time `n/fps`.
- A five-second 30 fps take contains **150** samples, indices 0..149. Blender maps
  these to frames 1..150. No duplicate terminal sample at five seconds.
- Simulation uses 120 Hz semi-implicit Euler, interpolating between adjacent physics
  states for output rates such as 29 fps. Only output-rate sampling changes.
  Floating-point comparisons across platforms use absolute tolerance 1e-8 metres;
  Blender's float storage uses 1e-5 metres. Bit-identical files across Python/Blender
  versions are not promised. CI exercises Windows and Linux; remote results must be
  checked before claiming platform acceptance.

## Scene fields

| Field | Contract |
| --- | --- |
| `schema_version` | Integer 1 |
| `fps`, `duration_seconds` | Clock described above |
| `actors` | 1..100 sphere proxy actors |
| `cameras` | Optional list, up to 16 static cameras |
| `lights` | Optional list, up to 32 static point lights |
| `render` | Optional `{width, height}`; integer dimensions 16..4096; default 1280×720 |

IDs are globally unique across actors, cameras and lights, match
`[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}`, and cannot equal reserved helper ID `__floor__`.
They identify entities independently from Blender display names or list order.

| Entity | Required fields | Optional fields |
| --- | --- | --- |
| Actor | `id`, `position: [x,y,z]`, `radius`, `color: [r,g,b]` | `velocity: [vx,vy,vz]` (default zero), `restitution` (default zero) |
| Camera | `id`, `position`, `target`, `fov_degrees` | None |
| Light | `id`, `position`, `color`, `energy` (Blender point-light watts) | None |

Positions/samples are bounded to ±10000 metres, velocity to ±100 m/s, radius to
0.0001..100 metres, restitution to 0..1, light energy to 0..1000000 watts.
Actors cannot start intersecting the floor. Cameras use horizontal perspective FOV
1..170 degrees, zero roll, and Z-up orientation; their view direction cannot be
parallel to Z. Actor samples are capped at 250000 per take; input/output JSON is
capped at 64 MiB. Booleans, NaN, infinity, duplicate JSON properties and fractional
frame counts are rejected. The validator does not silently clamp inputs.

## Animation fields and authority

```json
{
  "schema_version": 1,
  "fps": 30,
  "motion_id": "sha256-of-normalized-initial-conditions",
  "frames": [
    {"frame": 0, "positions": {"actor_id": [0, 0, 3]}}
  ]
}
```

The illustration shows one sample; a real take must contain exactly the scene's
frame count and every actor on every sample. Indices must be contiguous from zero.
`motion_id` hashes timing and sorted actor initial positions/radii/velocities/
restitution; changing camera, light or actor colour leaves it unchanged. It is an
**initial-condition compatibility key**, not a checksum of the sampled trajectory
or a claim about which physics engine generated it. Bootstrap animations without
this field remain readable; new simulations and take bundles add it.

A sampled animation is authoritative for playback. Blender-edited translations
may differ from physical simulation or pass below the floor; no re-simulation or
floor correction occurs on import/export. Initial conditions remain in `scene`.
Calling `simulate(scene)` explicitly creates a new physically generated performance
and discards those edited samples. Do not call it during camera changes.

## Portable take bundle

`interchange.make_take(scene, animation)` creates a deep copy:

```json
{
  "format": "flamoris-cinema-take",
  "version": 1,
  "scene": {"...": "validated scene"},
  "animation": {"...": "validated sampled performance"}
}
```

A single `.take.json` is the Blender return artifact and can be reimported directly.
It does not reference mutable external files. Cinema's JSON file is a revision
snapshot, not an automatic merge target: export creates a new file; a human or a
future editor chooses the accepted revision. Automatic concurrent merge, native
`.blend` feature round trip, camera animation, meshes, rotations and scale require
future contracts.

## Physics limits

Each sphere independently experiences gravity -9.81 m/s² on Z and an infinite flat
floor. Floor penetration clamps the centre to the radius; normal velocity reflects
by restitution, with tiny rebounds settled. Horizontal velocity is constant.
There are no actor collisions, friction, torque, rotation, sleeping islands,
continuous collision solver, skeletons or walking/recovery. This is an inexpensive
reference simulator, not the final rigid-body backend. No random seed is needed.
