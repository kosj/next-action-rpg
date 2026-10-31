# Eye integration: actual Web fixed-art reference

Godot4.7.2, project0.1.5 development source, Web GL Compatibility, Chromium SwiftShader, 1440×900. The actual Game first-room materials and lights were preserved. A private fixture freezes actual idle at.25s, poses only the real Head bone, updates the actual Head attachment in that frame, and reframes the real camera for face inspection.

The d7d984 reference completed12 original screenshots in317.962 seconds, errors0. Six camera/pose cases have exactly matching quality0/1 pairs. All three imported eye PBR surfaces use vertex colors. Head/socket transform error is0 in every captured state and world eye-model basis scales are approximately1. Final body4cc9 and eye d7d984 full SHA values are in `source-manifest.json`.

| Case | Camera | Head local yaw/pitch | Captures |
| --- | --- | --- | --- |
| 01 | Actual RuneCamera facing the hero | 0/0 | quality0, quality1 |
| 02 | Reframed face front | 0/0 | quality0, quality1 |
| 03 | Reframed face three-quarter | 0/0 | quality0, quality1 |
| 04 | Same face-front camera | +15/+10 degrees | quality0, quality1 |
| 05 | Same face-front camera | −15/−10 degrees | quality0, quality1 |
| 06 | Same three-quarter camera | −15/+10 degrees | quality0, quality1 |

The Web images distinguish thin bright sclera, a gray-green iris rim, dark central pupil and small reflection. Eyes are curved and follow the sockets through the sampled rotations; no flat painted overlay or obvious position/scale failure was observed. Large dark pupil regions and heavy eye surrounds still give a stylized/doll-like stare in both qualities. The bounded COLOR_0-only alternative9f was rejected after four actual Web comparisons: its difference is too subtle to claim improved naturalness/readability. Retain d7d as the incremental integration, with this art limitation unresolved.

These captures verify a limited static integration/view sample. They do not approve final face quality, complete animation, blink/gaze behavior, normal gameplay, Windows, target-hardware performance or AAA quality. `review.json` records the limitation and links the rejected color comparison. Original PNG files are unedited.

`capture-states.json` includes actual camera/hero/Head/eye transforms, renderer reports and imported material flags. `capture-provenance.json` pins fixture and exported-file hashes; `source-manifest.json` pins all161 copied original source files and records the root's345-check native pass. `eye_capture.gd`, `capture_web.py` and original console/export/capture logs reproduce the bounded fixture under `/workspace/.runefall-task/character-polish/eyes-web/`. The asset-specific import hook remains the actual source hook; no runtime palette/material/light overrides were introduced.

The reference browser and local server were closed before releasing the CPU/GPU slot. Normal gameplay QA remains deferred until the root freezes the selected final asset/export.

## Color-only alternative and actual export proof

`palette/review.json` records the rejection. Candidate9f kept source JSON, geometry, normals, indices, topology, rest basis and materials byte-identical, changing896 COLOR_0 RGB rows. Its four screenshots match reference front/three-quarter cameras, Head pose and quality exactly. No runtime palette/light/material overrides were used.

`palette/actual-pck-color-proof/verification.json` proves the colors were applied to the actual exported Web PCK. A minimal native inspector project contains no eye assets; it mounts each actual PCK and loads its remapped imported PackedScene. All imported colors match each GLB's source colors after `floor(channel*255)/255` RGBA8 packing, with maximum float error about1.28e−8. Six representative actual imported/source samples are included. The native color rows differ by128/640/384 across the three material surfaces; counts include material-boundary duplicate vertices.

Godot reorders vertex/index arrays when colors change, so raw native array indices are not correspondence IDs. Expanded ordered triangle positions are exact between the two PCKs. Native position compression differs from source floats by at most1.438 micrometers; nearest source positions are used only to associate COLOR_0 values for this audit. This is not a geometric fit tolerance or visual-quality measurement.

The probe source, verifier, import MD5 metadata and logs are preserved with the compact result. Full actual color-array dumps remain in the private `color-probe/` directory. Both inspector runs completed in under one second each; all browsers, servers and inspector processes were closed before releasing the files.
