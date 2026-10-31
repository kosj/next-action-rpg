> Root decision: **rejected for runtime** after independently viewing neutral front/side polygon seams. Original4cc remains installed. Actual Game A/B was not run after this failed visual gate. The19.6MB trial GLB stays in ignored build; its exact SHA/recipe/mask/proofs are retained. The following is the original candidate-stage report.

# Read-only atlas evidence and one isolated skin trial

Source: Lyra socket body **4cc9ae5b9340263b824d549ad59a7955705c927859bf35949d66984cd647ed0c**.
Original archive A89 remains unchanged. The actual Web reference is
`docs/validation/v0.1.5/eyes-web-reference/02-face-front-neutral-q1.png`.

`audit-001/material-audit.json` samples the original embedded2048px RGB PNGs
through actual GLB UVs at seven barycentric points per triangle. Images are
decoded/read only; no image is edited, resized, baked or generated.

The source material omits metallic/roughness factors, so both default to1.
Face ORM-B median metallic values are forehead0.234, nose0.240, cheeks0.285/
0.259 and chin0.235; chest armor0.537. Skin is thus actually nonzero metallic,
not merely described as shiny. Face roughness medians0.475–0.531 are already
plausible and are preserved. Median tangent normal-map tilts are about5° on
forehead/cheeks,10.9°nose and15.5°chin: those measurements do not justify
blindly changing normal strength. Crown hair metallic median is0.373, but its
solid sculpted silhouette is also a separate quality problem.

`geometry-texture-diagnostic.json` records selected face-core texel density
median821px/m and coincident vertex-normal differences max0.0323°. The large
UV bounding box includes separate islands and is not a facial pixel-count
certificate. These diagnostics do not prove the source of all Web faceting.

## Ownership and candidate

The conservative proposed mask selected287 front/warm face triangles and left
51 uncertain border triangles unchanged. `ownership-001/` renders the selected
triangles with a diagnostic3D green material in isolated Blender memory.
Source triangle→Blender polygon positions agree within0.252µm. Front/side
inspection found no observed scalp/hair/armor selection. The mask is an inset
face region, with visibly stepped internal boundaries and small nostril/lip
islands; it is not a complete semantic skin/hair segmentation.

The explicit reviewed mask is `reviewed-face-mask.json`. ONE trial partitions
original primitive0 indices into old and selected-face groups, keeps the136
new inner-lid triangles/primitive unchanged, and duplicates the original PBR
material with **metallicFactor0 ONLY**. Albedo, normal, roughness, AO, maps,
samplers and existing materials stay unchanged. Original BIN prefix,
attributes/UVs/weights, animations/rest, images and oriented triangle multiset
are exact. It adds one material/draw group, not textures or geometry.

Candidate: `dielectric-001/lyra-skin-dielectric.glb`, SHA-256
**35ea57e7fde492ce52bbf2fc921535e3ccdd1f0926729b1162d54d40a3a22f9f**,
19,632,192 bytes, **32,288 triangles /3 surfaces**.

The actual reimported ordinary-material source/candidate neutral captures are
`neutral-reference/` and `neutral-candidate/`: front, close threequarter, side,
same camera transforms and neutral lights, unchanged accepted d7d eyes.
The candidate is less specular centrally, but a faint stepped transition is
visible on cheek/side boundaries. **Runtime adoption remains pending actual
Game A/B and boundary review.** Do not promote the trial based on studio alone
or silently include uncertain hairline/edge triangles. Full face ownership may
need explicit manual segmentation rather than a spatial/color heuristic.

## Reproduction and limits

```bash
python tools/audit_character_skin_materials.py --input-body game/assets/models/production/lyra_gameplay.glb --original art_source/production/candidates/lyra-gameplay-001/source.glb --output build/art-candidates/skin-material-review/new-audit
python tools/audit_character_skin_materials.py --input-body game/assets/models/production/lyra_gameplay.glb --original art_source/production/candidates/lyra-gameplay-001/source.glb --review-mask build/art-candidates/skin-material-review/reviewed-face-mask.json --derive-candidate --output build/art-candidates/skin-material-review/new-trial
```

The second command requires an explicit reviewed mask with the correct source
SHA. Do not set that state merely to bypass review. The exact trial tool is
preserved as `dielectric-001/audit_tool_at_build.py`.

`texture-import-observations.json` records current generic GST2 containers,
lossless import mode0, mipmaps and `vram_texture=false`, with no local
S3TC/ETC2 variants observed. It does not inspect actual engine/GPU image formats
or establish mobile compatibility; that is the root engine audit's scope.

No runtime/source originals were changed. No paid service, full game build,
browser, target-GPU test or final AAA approval is part of this trial.
