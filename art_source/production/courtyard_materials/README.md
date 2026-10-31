# First courtyard PBR surfaces

These are real photogrammetry surfaces for the first sanctuary courtyard. The
material response and dimensions are shared by Web and Windows builds; the Web
package uses nine JPEGs totaling **9,785,368 bytes**. The floor color map is 2K;
all other maps are 1K. Higher resolution and displacement maps remain available
from the recorded source URLs but are not required by the Web slice.

| Material resource | Surface | One UV repeat |
| --- | --- | --- |
| `game/assets/materials/courtyard/floor_stone.tres` | Weathered stone flagstones | 1.8 × 1.8 m |
| `game/assets/materials/courtyard/wall_limestone.tres` | Pale sandstone masonry | 2.0 × 2.0 m |
| `game/assets/materials/courtyard/ground_detail.tres` | Compact forest soil, leaves and grit | 2.0 × 2.0 m |

The historical `wall_limestone` filename is retained for scene integration; its
actual source is **white sandstone**, as the manifest and material name state.

The `StandardMaterial3D` resources wire color, tangent-space OpenGL (+Y) normals,
and the official packed ARM texture. Albedo uses Godot's color-texture semantics;
normal and ARM are linear data. ARM **R = ambient occlusion**, **G = roughness**;
the metallic channel is intentionally unused and each surface has metallic = 0.
The two scalar maps share one texture and its mip chain. Materials use mipmapped
anisotropic filtering for ground viewed at grazing angles. No baked displacement
geometry or parallax approximation is required.

The checked-in `.jpg.import` sidecars explicitly generate mipmaps and flag the
three normal maps. Automatic 3D compression changes are disabled so a headless
CI import has the same policy as the editor. The textures use lossless runtime
import; their imported `.ctex` size differs from the source JPEG byte budget and
the complete Web export must pass the project's existing build-size gate.

Use **surface dimensions / physical tile dimensions** for mesh UV repeats. A
40 m square floor therefore uses `uv1_scale = Vector3(40.0 / 1.8, 40.0 / 1.8, 1)`.
For walls, map UV axes consistently along the masonry courses. The shared
resources retain unit UV scale: duplicate a material only when a mesh needs its
own scale or vertex-alpha ground blending. Ground edge patches should feather
their opacity through vertex color; a hard rectangular decal is not the intended
presentation. Materials do not change collision or fight-space navigation.

`manifest.json` is the authoritative source, license, resolution, channel, scale,
byte-budget and checksum record. `source_metadata.json` and the three `.files.json`
files preserve the selected official API responses. Poly Haven's official API
schema specifies texture dimensions **in millimeters**; the measured values are
converted to the meter units above. See [LICENSE.md](LICENSE.md) for credits and
the official CC0 statement.

From the repository root:

```sh
python art_source/production/courtyard_materials/sync_materials.py
```

Pass `--download` only to restore missing maps from the pinned official public
URLs. Both modes verify published MD5, recorded SHA-256 and the byte budget;
they also check the mipmap and normal-import policy. Existing files are never
silently replaced. Refreshing a texture requires a
deliberate manifest update and visual review. No token, login, paid generation,
or secret is used by this pipeline.

`render_materials.py` produces a neutral-light Blender material review image
using the exact runtime bitmaps; it is an asset review, not a gameplay screenshot:

```sh
blender --background --factory-startup --python art_source/production/courtyard_materials/render_materials.py -- --output build/art-review/courtyard-materials/material-review.png
```

The photogrammetry foundation improves surface scale, weathering and light
response. It does not establish an AAA release gate by itself: composition,
close camera inspection, character animation, environment detail and Web
performance still require review in the integrated game.
