# Blender acceptance evidence

**Latest status:** stage 1's full two-camera HIP sphere sequence and stage 2's fixed
Glyph native HIP preview are accepted. See the corresponding sections below.
Earlier pending statements describe historical runs.
The v3 authored walk/native roundtrip, Flamenco movie and Kachinco CLI handoff
are also accepted as a partial stage 3 / early media-handoff slice.

## 2026-10-31: Blender 5.2.3 CPU preview

**Accepted scope:** the fixed two-camera CPU preview and the edited-subset roundtrip.
Evidence is the user-supplied `cinema-smoke.zip` from an actual external Blender run,
not a Blender execution in the development container. Large/native artifacts are
not committed. Submitted scripts correspond to the 5.x adapter change in
`77808c4621ebf8747dc22baef54f5cd4c29d3af9`.

| Check | Result |
| --- | --- |
| Blender | 5.2.3 LTS, build `e13b728c6880` |
| Renderer | CPU, fixed sample scene |
| Edited-subset acceptance | Passed (translation, RGB, identity and rejection cases) |
| Native save/reload and sampled motion comparison | Passed for wide and close |
| PNG output | 6 images, 1280×720, frames 1/76/150 per camera; decoded successfully |
| Uploaded manifest integrity | All 15 listed files matched byte lengths and SHA-256 |
| Native project container | Both Zstandard-compressed; independently decompressed and confirmed `BLENDER17-01v0502` prefix during review |
| Job timing | Blender result reports 27.64 s; original host receipt 29.14 s including process overhead |

### False failure and correction

The original host receipt reported `missing native Blender project` after Blender
completed successfully and printed `CINEMA_SMOKE_OK`. The checker required the
literal `BLENDER` prefix at byte zero, incorrectly excluding compressed projects.
It now recognizes raw/gzip/Zstandard containers. Structural validation remains the
actual Blender save/reopen step, not a claim that a magic-byte test parses a scene.
New jobs also report hashes of the reopened projects and the host checks them.
The fix adds signature regression tests and read-only `--check-only` revalidation.
The submitted existing output passes the corrected checker without re-rendering.
Historical receipt/ZIP files are preserved unchanged, including their original
false result; revalidation does not rewrite them.

### Visual review and remaining scope

Wide framing shows the ball above the floor at frame 1 and on the floor later.
Close framing loses the ball above the image at frame 1 and clips it near the lower
edge later. Adjust the close camera before considering framing accepted for a
finished shot. Three sampled frames cannot verify continuous motion or visible
bouncing across a complete sequence.

Still pending: full 150-frame sequences, camera framing refinement, Cinema GPU
rendering, Windows Blender native acceptance, Glyph geometry, and character acting.
This evidence establishes a CPU preview integration, not completion of roadmap
stage 1's full five-second two-camera acceptance or the film engine.

## Follow-up preparation: full sequence (execution pending)

The close sample camera was moved from `[3.5,-5,2.6]` toward `[0.7,0,1.2]` at 45°
to `[3.5,-7,4.5]` toward `[0.85,0,2.1]` at 60° horizontal FOV. Simulation inputs and
sampled motion are unchanged. Static sphere/frustum preflight passes all 150 frames
for both cameras with a 5% margin along each screen edge. The original close camera
fails a regression test as expected; new framing has not yet been visually accepted
in Blender. `framing.json` is collected by new jobs.

`--full --encode` renders 150 PNGs per camera and encodes the sequences as two
silent MP4s. Encoding and ffprobe validation were exercised locally with generated
solid-colour test frames; this is **not** evidence of rendering the actual complete
Cinema scene. The real five-second two-camera render and visual review remain pending.

## HIP preview preparation (actual Cinema GPU execution pending)

Following the interrupted full CPU render, explicit HIP selection and two-thread
render/helper defaults were added. Device-policy tests check exact GPU selection,
CPU exclusion, ambiguous/missing-device failures and host refusal of CPU fallback
reports. API-configuration test doubles are not real Blender/HIP acceptance.

The next acceptance step is six actual 720p images using `--device HIP`, with
Blender device logs, result metadata, elapsed time and live CPU/GPU telemetry.
Only then proceed to the full sequence. A separately successful GPU installation
smoke test does not complete this Cinema-specific acceptance step. Prior CPU preview
evidence above remains valid and separate from HIP rendering.

## 2026-10-31: HIP preview accepted

Reviewed the user-supplied `cinema-smoke(1).zip` from the explicit-HIP runner,
corresponding to adapter commit `2ea4fff1fed0d65471c71e28d26436a1c2c9f582`.
The existing-output checker passes with the submitted artifacts unchanged.

| Check | Result |
| --- | --- |
| Blender | 5.2.3 LTS, build `e13b728c6880` |
| Device in both camera reports | AMD Radeon RX 9060 XT, HIP, Cycles GPU |
| CPU render device | Disabled |
| HIP RT | Enabled |
| Thread setting | 2 |
| Images | 6 decoded 1280×720 PNGs, frames 1/76/150 per camera |
| Framing | 150-sample sphere/frustum check passed; revised close camera shows the whole ball in all three rendered samples |
| Native save/reload, motion and edited-subset roundtrip | Passed |
| Uploaded manifest | All 16 listed entries matched size/SHA-256; native project hashes matched result metadata |
| Motion versus previous CPU preview | `motion.anim.json` bytes identical |

The unchanged wide-camera images are nearly identical to the CPU preview: per
channel mean absolute 8-bit RGB differences are below 0.0002 across all three images.
The close-camera images are not directly compared pixel-wise because framing changed.

### Timing comparison and limits

| Preview run | Blender-script elapsed | Host-process elapsed |
| --- | --- | --- |
| Original CPU preview | 27.64 s | 29.14 s |
| Explicit HIP preview | 48.12 s | 49.66 s |

These times include acceptance checks, scene creation, native save/reload, sampled
motion export and PNG writes. They are **not isolated GPU kernel/render times**.
The HIP run is slower end to end in these samples. CPU thread configuration and
the close camera also changed, so this is not a controlled CPU/GPU benchmark.
No stage timings were collected to attribute the delay to rendering, CPU-side
processing, denoising, PNG output or device initialization. Do not claim a GPU
speedup or name a bottleneck without further measurements.

Live observations during the HIP run sampled CPU at 62.8°C, GPU edge/junction at
27/28°C and GPU memory at about 1 GiB. A GPU utilization snapshot was only 2%; the
busy peak was not captured. These are snapshots, not run-wide maxima. The earlier
CPU full-render observation near 85°C was from a longer run with different thread
settings, not an otherwise identical thermal comparison. No temperature ceiling
or guaranteed thermal benefit is established by the short preview.

The corrected close framing and CPU/HIP subset connections now pass preview
acceptance. A complete five-second movie, continuous motion and sustained-load
measurements remain pending. `videos: {}` is expected for preview mode.

## 2026-10-31: full HIP sphere sequence accepted — stage 1

Reviewed the user-supplied `cinema-smoke(2).zip` from the fixed full/encode job.
Its recorded source hashes match the accepted HIP implementation. This is external
execution evidence, not a Blender run in the development container.

| Check | Result |
| --- | --- |
| Blender | 5.2.3 LTS, build `e13b728c6880` |
| Both camera device reports | RX 9060 XT, HIP/Cycles GPU, CPU rendering disabled, HIP RT on, two threads |
| PNG sequences | Exact frames 1..150 per camera; all 300 PNGs decoded as 1280×720 |
| Videos | Both H.264 MP4s: 1280×720, 30 fps, 150 frames, exactly 5.000 seconds; full decode passed |
| Native save/reopen, edited subset, sampled-motion comparison | Passed in the recorded Blender job; unchanged-output checker passed during review |
| Integrity | All 314 manifest entries matched byte lengths and SHA-256; native hashes verified |
| Framing | Whole-sphere preflight passed; sampled visual inspection shows complete sphere in both camera views |
| Elapsed | Blender script 2373.46 s; host process 2377.58 s (about 39 min 38 s) |

Samples show the same red sphere dropping, bouncing and moving horizontally from
wide/close perspectives. These are silent geometric prototype clips, not the
walking Glyph film. Stage 1's two-camera five-second render and subset roundtrip
gate is met. User-requested performance investigation is deferred; no speedup,
bottleneck or run-wide thermal maximum is inferred from elapsed time.

## Glyph stage 2 preparation — native execution pending

The actual authored 赤 is snapshotted read-only from pinned Glyph source, retaining
seven stroke IDs, occurrence/cue/variant/source hashes and license provenance.
Portable v2 placement, nonzero normalization, framing and input-integrity checks
pass locally. `--glyph` adds a native identity/placement/save-reload gate and a
synthetic hole-area check before two-camera stills. The development container
has no Blender; the two native integration tests are skipped. No Glyph native
success or completed stage 2 is claimed until that actual job passes and is reviewed.

## 2026-10-31: native Glyph HIP preview accepted — stage 2

Reviewed user-supplied `cinema-smoke(3).zip`. All 27 recorded Python source hashes
match implementation commit `da15334b48029873ccb084650afc6a436d06c6b8`.
This is external native execution evidence; no Blender binary is installed in the
development container. Existing-output revalidation passes without changing it.

| Check | Result |
| --- | --- |
| Blender | 5.2.3 LTS, build `e13b728c6880` |
| Both camera reports | RX 9060 XT / HIP / Cycles GPU, CPU render device disabled, HIP RT enabled, 2 threads |
| Native gates | `CINEMA_BLENDER_ACCEPTANCE_OK`, `CINEMA_GLYPH_ACCEPTANCE_OK`, `CINEMA_SMOKE_OK` all present |
| Glyph geometry | Same immutable snapshot after both project save/reloads and exports; original seven `stroke001..007` / `s1..s7` links intact |
| Native checks | Seven face-part indices, floor placement/depth, edited translation and rename, reimport, geometry-edit rejection, synthetic 2.88 m² hole cap all passed |
| Images | Six decoded 1280×720 PNGs, frames 1/76/150 per camera; full letter, visible thickness and floor shadows in both views |
| Framing | Extruded-outline AABB preflight passed |
| Integrity | All 16 manifest entries matched byte lengths/SHA-256; both native-project hashes verified |
| Elapsed | Blender script 49.23 s; host process 50.76 s |

The six images are static by design: this is placement/geometry acceptance, not
walking or an animated performance. Empty `videos` is expected for preview mode.
Stage 2's read-only actual-Glyph shape, identity and placement roundtrip is accepted.
This does not establish actor rotation, per-part motion, collision, walking,
recovery, arbitrary outline support, Windows native Blender rendering, or a remote
MCP/Flamenco render pipeline. Those remain separate integration/acting work.

## 2026-10-31: authored walk → Flamenco → Kachinco CLI accepted

V3 adds explicit per-part pivots, sampled local translation and local-Y rotation.
The authored seven-stroke 赤 walks four alternating steps over two seconds and
holds for one second. This is procedural acting; no collision/falling is claimed.

| Check | Result |
| --- | --- |
| Portable take | v3, 24 fps, 72 samples, three seconds, 1.8 m root travel; source shape/IDs unchanged |
| Pure gait checks | Support-point pinning, nonpenetrating feet, swing lift, deterministic regeneration, exact final hold and camera independence passed |
| Native Blender | 5.2.3 LTS; sphere, static Glyph and walking part-pose tests all executed successfully through a separate background MCP process |
| Native walk subset | All 72 frames compared, edited arm angle/rename/save/reload/reimport passed; mesh edit, reparenting and root delta-transform rejection passed |
| Device preparation | RX 9060 XT / HIP / Cycles GPU selected, CPU render device disabled, HIP RT enabled, two threads, eight samples |
| Shared handoff | Native camera files prepared through connected Blender MCP; existing persistent MCP scene retained |
| Flamenco | Real Manager 3.9.3 job-check returned 204; built-in simple-blender-render completed all three 24-frame render tasks and preview task on the configured HIP Worker |
| Movie | All 72 PNGs present; 640×360, H.264, 24 fps, exactly 3.000 seconds, 72 frames; full decode passed |
| Movie integrity | 83347 bytes; SHA-256 `1ad8904b86f3bda23aeaddd135dcdca25042a0a50b8a2cbeb56afb8eb145a737` |
| Kachinco CLI | Guarded upload verified matching bytes/hash and 105840000 ticks; new three-second sequence inserted, native preview read and project saved at revision 44 |

Visual sampled-frame review confirms alternating leg/arm movement, horizontal
travel and the final hold. Native meshes remain rigid strokes; fine acting and
artistic approval remain human work. Camera geometry passes all samples, but only
the wide camera was rendered as the complete movie in this slice.

The development container's suite reports 56 passed/3 skipped (Blender absent);
the three native tests above are independently executed external evidence.
No authoring-workstation process was needed. No Worker/runtime/service configuration was changed.
This does not certify general articulated characters, physical balance, trip/fall/
recovery, arbitrary rotations/rigs, Kachinco sound/final export, or a production
render scheduler. The data-only Flamenco proposal helper does not submit/retry jobs;
the accepted submission used the actual Manager schema/check/submit API under
operator-authorized orchestration. Private runtime paths/receipts belong in Internal.
