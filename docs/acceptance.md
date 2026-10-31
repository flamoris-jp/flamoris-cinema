# Blender acceptance evidence

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
