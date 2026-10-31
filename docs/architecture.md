# Cinema architecture and next implementation slices

> **Historical implementation architecture / PAUSED 2026-10-31.** The contracts and bridges below describe the existing prototype and its then-proposed next steps, **not** the agreed future product architecture or an instruction to continue work. Current conceptual direction: [vision and pause](vision-and-pause.md). No active engineering slices are authorized while paused.

## Authority and dependency direction

Cinema is a renderer-independent scene/performance library. It can run on Linux
and Windows without Blender. No service is started by importing or installing it.
Core/prepared-take consumption uses only Python's standard library. Optional
Glyph preparation reuses Glyph, fontTools and PathOps; none is required inside
Blender. See [Glyph actors](glyph-actors.md).

| Component | Authority | Current connection |
| --- | --- | --- |
| Glyph | Letterform geometry, occurrence identity, style/provenance | Read-only bundle adapter; fixed native actor HIP preview accepted |
| Cinema contracts | Scene entities, clock, limits and sampled performance | Implemented Python validators and take bundles |
| Cinema simulation | Reference sphere/floor trajectory | Implemented 120 Hz gravity, normal restitution, linear velocity |
| Blender adapter | Mapping portable subset into/from native projects | Sphere CPU/HIP/full sequence and Glyph native preview accepted |
| Blender | Native scene editing and offline rendering | Optional local process; install handled separately |
| Kachinco | Clips, audio, editorial timing, compositing, final export | Actual silent-walk MP4 uploaded/inserted/previewed/saved through guarded CLI MCP; no direct project mutation |
| AI director | Bounded scene/take proposals | Future client of the same validators, no execution service yet |

The adapter imports the core, never the reverse. No second timeline, document
history store, Hub/MCP stack or runtime manager is introduced. FLAMORIS Commons
currently provides policies/foundations rather than an existing scene/physics
package; no shared scene implementation is duplicated.

## Portable revision model

A scene contains initial conditions and static staging. A take adds a sampled
performance. A renderer consumes that take plus a camera choice. Camera/lighting
edits can create another scene revision using unchanged sampled motion. Blender
export returns a new take; it never silently overwrites or merges the source.
Do not run simulation again to render an edited take.

Multiple cameras are separate shots of the same performance, not alternate
physics histories. Native Blender extras stay in the native project. The supported
subset is documented in [the bridge contract](blender-bridge.md), with strict
structural rejection where data would otherwise be misrepresented.

## Roadmap and immediate engineering slices

The user-facing milestones and acceptance gates are authoritative in
[the Cinema roadmap](roadmap.md). The list below expands engineering dependencies;
character performance, the first short and later AI direction are tracked there.

### Historical proposed engineering slices (on hold)

1. **Real Blender acceptance:** run the included roundtrip test and inspect the
   two-camera render. CPU/HIP previews and the full HIP sequence are accepted;
   see acceptance.md. GPU setup belongs to the separate runtime workflow.
2. **Glyph 2.5D actor:** inspect the actual Glyph bundle contract; preserve source
   checksum, occurrence/stroke IDs, holes and fill rules. Specify pixel-to-metre
   conversion, origin/pivot, read-only asset roots and collision proxy separately
   from visible geometry. This needs a new geometry contract, not extra ad hoc
   properties accepted by the existing sphere validator.
3. **Rigid-body backend:** choose an existing maintained solver with explicit
   license/portability review, collision events and a fixed clock; provide rotations
   and collision shapes under a new contract version. The reference simulator is
   retained for simple fixtures, not expanded into a home-grown general solver.
4. **Kachinco handoff:** render PNG/RGBA or encoded media plus shot fps/frame range
   and source-take identity. Kachinco decides timeline placement; Cinema does not
   modify Kachinco projects behind its editor.
5. **AI authoring:** allowlisted declarative actor/camera operations with validation
   and revision selection. No raw remote Blender Python or autonomous installation.

The prototype is not yet the walk → trip → fall → recover film. Sphere/floor
contact, fixed letter geometry and an initial authored v3 walk are accepted.
Physical trip/fall/recovery remains future
work. See [Glyph performance](glyph-performance.md). Track the larger film in
[Kachinco #124](https://github.com/flamoris-jp/flamoris-kachinco/issues/124)
and the Glyph boundary in [Glyph #3](https://github.com/flamoris-jp/flamoris-glyph/issues/3).
