# Lyra eye-socket geometry candidate · frozen review

Original archive: `art_source/production/candidates/lyra-gameplay-001/source.glb`,
SHA-256 `a89ced80a24f93685b35bf52e5fedb689e25b0f7ead6188c009d4405c0dfa4a1`.
The old runtime source path in `../derivation.json` is historical; runtime may
now contain the accepted derivative. Check the archived A89 when reproducing.

Frozen body: `../lyra-eye-sockets.glb`, SHA-256
`4cc9ae5b9340263b824d549ad59a7955705c927859bf35949d66984cd647ed0c`.
Frozen Web eyes: `eyes-web.glb`, SHA-256
`d7d984fb10637be102a740e91e89316580b33c53d4b6a2cd1055108675ef3ef4`.
High eyes: `eyes.glb`, SHA-256
`87172646dbc3acba0070b574b6d8e38209b438a5a03a85498cb3b18f0fd9ac4c`.

This is an **incremental studio candidate**. Independent native attachment,
actual Web material/gameplay review and final AAA acceptance are separate.

## Intentional geometry and preserved source

The tool removes painted-eye interiors by convex polygon triangle difference
limited to front-facing source triangles within a 20mm front depth band.
Nine original triangles are clipped; 11 neighboring original triangles are
refined to propagate source-edge splits without T-junctions. New boundary
position, normal, UV and named weights are interpolated, with no dropped weight.
Original attribute rows remain byte exact. A three-ring 1.6mm inward lid wall
creates real depth. Body is **32,288 triangles**, including 136 wall triangles;
its only welded boundaries are the two intentional inner-socket loops.

The original BIN prefix, all animations, skin/rest/inverse binds, nodes, images,
textures and original materials are preserved. New geometry/accessors and one
inner-lid material are appended. No original bitmap is edited. Source model
preservation does not mean that this derivative has unchanged topology.

The two 12mm-radius globes use procedural mesh/vertex colors/PBR and an 0.8mm
maximum anterior corneal crown. They have an identity GLB root in the ORIGINAL
glTF Head REST-local orthonormal basis, in physical meters. Runtime attaches
under Head and cancels only the uniform imported rig scale; external actor
scale is retained. The full/rigid source Head matrices and exact sample
vertices are in `refit.json` and `anchor-samples.json`. No Blender axis rotation
is silently added to the socket.

## Failure retained and corrected fit

The original inner-rim-only fit missed surrounding surface intersections.
`../bvh-pose-check-failed-identity.json` retains the failed REST/yaw/pitch pairs.
`failed-intersection-map.json` maps body triangle 15556, 13916 and lid 32271 to
source-world positions. `../pose-space-check.json` independently compared
Blender REST/identity and RESET with CPU glTF defaults: the micrometre errors
did not explain away the collision. The wrong limited fit was superseded.

Refit moves the globe centers inward 2.192mm and 1.050mm. It solves exact minimum
point-to-triangle distance over **all body triangles**, requiring default-pose
sphere gap >=1.6mm, then audits 484 nearby body triangles over every exported
key and interval midpoint: **2,358 samples / 20 clips**, minimum gap **0.551mm**
to the conservative 12.8mm sphere including the whole corneal crown. This is
finite sampling, not a continuous collision proof. Original animation data
and body 4cc9 remain unchanged by refitting.

Actual reimported Web/body BVHs have **zero overlapping triangle pairs** in
canonical RESET, yaw ±15° and pitch ±10°. Canonical pose fixtures sample the
complete imported RESET before clearing playback. They do not assume a retained
first animation or a guessed BoneAttachment basis is the intended pose.

## Web geometry and actual images

Web eyes are **3,840 triangles / 112,488 bytes / no texture images**; total body
plus Web eyes is **36,128 triangles**. Front 60° uses 5° polar steps plus the
exact pupil boundary and 64 azimuth segments; the occluded back is coarser.
Actual reimported Web-to-high samples (vertices, edge midpoints, centroids):
17,792 samples, visible front max **0.017623mm**, mean **0.005324mm**; whole globe
max **0.722444mm** on the occluded back. This is one-way finite sampled distance,
not a continuous Hausdorff bound or hardware performance approval.

`translation-proof.json` verifies the refit is a per-eye rigid translation
within float32 rounding, with unchanged index/color buffers and materials.
`surface-error.json` also recomputes the final actual GLB reimport distances.

Reviewed final Web captures: `rest/face_front.png`, `rest/head_three_quarter.png`,
`close/head_three_quarter.png`, `close/face_side.png`, `yaw/face_front.png`, and
`pitch/face_front.png`. Original same-camera captures are in `../before-close/`
and the original `build/art-review/character-polish/lyra-regions-001/`.
These are neutral Blender studio images, not actual game screenshots.

## Reproduce in new directories

Use Python 3.12.14/NumPy 2.3.5 and Blender 4.3.2 as recorded in `FINAL_REVIEW.json`;
CPU rendering uses one thread. No account, API, upload or paid run is involved.

```bash
python tools/derive_character_eye_sockets.py --input art_source/production/candidates/lyra-gameplay-001/source.glb --reference-review build/art-review/character-polish/lyra-regions-001/review.json --output build/art-candidates/character-polish/eye-sockets/reproduction-001 --audit-animation
python tools/derive_character_eye_sockets.py --refit-eyes-from build/art-candidates/character-polish/eye-sockets/reproduction-001/derivation.json --output build/art-candidates/character-polish/eye-sockets/reproduction-001/surface-refit
```

The reference camera JSON carries immutable source SHA and manual aperture
pixel coordinates are recorded in derivation/refit reports. The exact final
tool snapshot is `derive_tool_at_final.py`; the body build-time snapshot is
`../derive_tool_at_build.py`. Helper tool hashes are recorded in the final JSON.

Reimport review/checker recipes are `../bvh_pose_check_final.py`,
`canonical_region_fixture.py` and `web_surface_error_final.py`; their paths are
fixed to this frozen review directory and must be parameterized for a new copy.
Keep the failed diagnostic and final reports together when archiving. Do not
turn the technical or studio results into final gameplay/GPU/AAA approval.
