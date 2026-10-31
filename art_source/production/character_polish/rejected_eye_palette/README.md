# One controlled eye-color alternative

Status: **pending actual Web comparison / no runtime adoption**.

Input geometry: final socket Web eye `d7d984fb10637be102a740e91e89316580b33c53d4b6a2cd1055108675ef3ef4`.
Candidate: `eyes-palette.glb`, SHA-256
`9f2c513f7efaeb54741645ebe9b2ee99c66c66c5711c1c55678b1c482fd7064c`.
Both are 112,488 bytes, with the same 3,840 triangles and 2,176 vertices.

Only existing `COLOR_0` RGB float values are patched. The GLB JSON and all
headers are byte exact, as are **all bytes outside those changed RGB fields**.
Position, normal, index, material, node, root transform and topology bytes stay
exact; existing geometry/fit evidence is unaffected. Alpha, 1,152 original
sclera rows and 384 back rows are unchanged. The patch changes 896 RGB rows /
9,443 individual bytes. `palette-audit.json` records every changed vertex index,
input/output/tool hashes and the exact byte-mask checks.

The iris palette changes from sRGB `(0.20,0.27,0.24)` to `(0.32,0.40,0.36)`,
converted to linear vertex color. Existing iris angular variation, limbal ring
and upper shadow are retained; newly revealed iris inside the old dark pupil
uses the same procedural factors. The color pupil target changes from 2.4mm to
1.5mm radius with a 0.6mm smoothstep half-width, interpolated on the existing
vertex grid. These are color boundaries, not new geometric dimensions.

Primitive/material groups are deliberately unchanged. In particular, some
newly lighter iris color still uses the original `Pupil` material group/PBR
response. No image is painted, baked or generated. No material is edited.

The purpose is a single actual courtyard-light comparison: front and three
quarter at quality 0/1. The original accepted d7d geometry remains the reference;
this palette has no visual, gameplay, GPU or AAA approval until reviewed.

Reproduce in a new directory, without Blender/browser/authentication:

```bash
python tools/derive_eye_palette.py --input-glb build/art-candidates/character-polish/eye-sockets/socket-001/surface-refit/eyes-web.glb --refit build/art-candidates/character-polish/eye-sockets/socket-001/surface-refit/refit.json --output build/art-candidates/character-polish/eye-palette/reproduction-001
```
