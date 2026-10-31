# Rejected weight-repair review

**All repair attempts were rejected. Keep the original authored/runtime GLBs. AAA art approval remains pending.**

Full original sampling found Lyra's worst edge at `heavy` 0.63s: 5.820mm →
27.414mm (4.710×, +21.594mm), and Sentinel's at `enemy_attack` 0.68s:
6.180mm → 44.226mm (7.156×, +38.046mm). The JSON reports include exact vertex
IDs, world coordinates and named bone weights. Earlier sparse pose checks
underestimated these maxima.

The last restricted repair reduced these target defects and global ratios, but
created worse strain on other torso boundaries. Lyra's largest newly increased
edge extension was +22.635mm; Sentinel's was +49.450mm. Sentinel's global maximum
absolute extension worsened from 58.660mm to 64.200mm. The source/runtime assets
were therefore retained. Improved percentiles or an improved selected closeup
are insufficient evidence of a safe repair.

The four PNGs use identical source/candidate cameras, materials and lights.
They show the **original worst-ratio target**, not the newly worsened region;
their local improvement must not be mistaken for a passing whole-body review.
The full checks sampled every exported timestamp and every interval midpoint
across all 20/10 clips. Per-edge envelope changes compare the maximum over that
schedule, while the largest increases also include both skins at the same peak
pose. Finite sampling is not a continuous deformation proof.

`validation.json` records the exact tool SHA and confirms that the authored
source copies, archived source GLBs and runtime GLBs retain their original
hashes. The rejected candidates changed only `JOINTS_0` and `WEIGHTS_0`; geometry,
UVs, normals, textures, materials, rest/inverse-bind matrices and every motion
key remained byte exact. Hands/finger weight rows were also byte exact in the
last candidate. None of these structural proofs constitute art approval.

Blender 4.3.2 and Python/NumPy 2.3.5 were used. Reproduce in a new directory:

```bash
character=lyra
input_glb="art_source/production/candidates/${character}-gameplay-001/source.glb"
review_dir="build/art-candidates/weight-review-reproduction/${character}"
python tools/repair_character_weights.py --input "$input_glb" --output "$review_dir/before" --keys-only
python tools/repair_character_weights.py --input "$input_glb" --output "$review_dir/rejected" --repair-from "$review_dir/before/before.npz" --radius .045 --iterations 24
python tools/repair_character_weights.py --input "$input_glb" --output "$review_dir/full-before" --report-name audit
python tools/repair_character_weights.py --input "$review_dir/rejected/source-weights.glb" --output "$review_dir/full-after" --report-name audit
python tools/repair_character_weights.py --input "$review_dir/rejected/source-weights.glb" --output "$review_dir" --compare-before "$review_dir/full-before/audit.json" --compare-after "$review_dir/full-after/audit.json" --report-name comparison
blender -b --factory-startup --python tools/repair_character_weights.py -- --input "$review_dir/rejected/source-weights.glb" --output "$review_dir/rejected-render" --render-cases "art_source/production/character_actions/deformation_review/${character}-render-cases.json"
```

Repeat with `character=sentinel`. The repair uses source key-only diagnostic
seeds (ratio >2 and extension >8mm), then a 45mm geodesic radius/24 iterations
within spine-dominant thorax skin. The four-slot named-chain fold, smoothing and
normalization are deliberately documented as a **failed automatic repair**.
The 0.1mm rest-edge analysis floor is unchanged between source and candidate.

Before writing, the tool verifies the companion audit JSON's source SHA and
topology counts, NPZ measured-edge identities/order, clip/time schedule, finite
array shapes and extrema distributions. New audits also embed source SHA and
counts in NPZ. Wrong-character evidence and a deliberately reversed NPZ edge
array were both rejected without writing a GLB. No full frame arrays, NPZ files
or rejected GLBs are included here; those remain under ignored build outputs.

Both original meshes have zero boundary/nonmanifold edges after position welding
at one micrometre. A rendered dark tabard opening must still be checked against
the intended leg split and self-intersection; this test does not justify filling
it. No geometry was cut, filled or moved. Further correction needs explicit
region/garment ownership and artist-reviewed weights, plus the remaining hand,
sculpt, texture, transition and platform-performance quality gates.
