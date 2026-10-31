# Third-party notices

- **Godot Engine 4.7.2** — MIT license, https://godotengine.org/license/ . Its complete license is included as `GODOT_LICENSE.txt` in exported distributions. The engine's additional third-party component notices are included as `GODOT_THIRD_PARTY.txt`.
- **Noto Sans KR** — Copyright 2014–2021 Adobe (http://www.adobe.com/), Reserved Font Name 'Source'; SIL Open Font License 1.1. See `game/assets/fonts/OFL.txt` in source and `FONT_LICENSE.txt` in exported distributions. Original file: https://github.com/google/fonts/tree/main/ofl/notosanskr .

The runtime Lyra body, regular melee sentinel body, rune sword, first-courtyard columns and gateway were generated with VARCO 3D and edited in Blender for this project. PRIVATE was selected for the generated 3D sources. The provider documents commercial use of Private assets and their Private derivatives at https://3d.varco.ai/docs/release-notes/2026-10-12-choose-a-license-when-you-generate . Source tasks, references, hashes and edits are recorded in https://github.com/kosj/next-action-rpg/blob/main/docs/ART_BATCH_2026_10_31.md and https://github.com/kosj/next-action-rpg/blob/main/docs/CHARACTER_INTEGRATION.md . The gateway cut caps include project-authored stone material.

The runtime skeletal motion clips are newly authored for this repository in Blender; provider stock FCurves and numerical poses are not copied into those clips. Remaining prototype character models, procedural geometry, shaders, interface and synthesized audio were authored for this repository. VARCO stock motion libraries in `art_source/production/` are development reference sources and are not included in the game runtime/PCK. Blender is a development tool and is not bundled with the game.

The first-courtyard stone, pale sandstone and soil textures in `game/assets/materials/courtyard/` are unmodified Poly Haven assets released under **CC0 1.0 Universal (CC0-1.0)**. The official license permits commercial use and redistribution: https://polyhaven.com/license . Legal code: https://creativecommons.org/publicdomain/zero/1.0/legalcode . Artist credits are preserved although attribution is not required by CC0:

- **Monastery Stone Floor** — Amal Kumar, https://polyhaven.com/a/monastery_stone_floor . Used by `floor_stone.tres`: 2K albedo, 1K OpenGL normal and packed ARM.
- **White Sandstone Blocks 02** — Rob Tuytel, https://polyhaven.com/a/white_sandstone_blocks_02 . Used by `wall_limestone.tres`: 1K albedo, OpenGL normal and packed ARM. The source surface is sandstone; the historical material filename is retained.
- **Forest Ground 05** — Charlotte Baglioni, https://polyhaven.com/a/forest_ground_05 . Used by `ground_detail.tres`: 1K albedo, OpenGL normal and packed ARM.

Permanent asset IDs, original download URLs, selected official API metadata, published MD5 values, verified SHA-256 values and physical tile dimensions are recorded in `art_source/production/courtyard_materials/manifest.json`. The accompanying `LICENSE.md` records the checked license statement. This notice covers the asset bitmaps; Poly Haven website branding and page content are not bundled with the game.

No license for the project's own code or original artwork has been selected by the repository owner; the third-party licenses above apply only to their respective components.

Development-only Agent Skills are vendored under `.agents/skills/` from `gamedev-skills/awesome-gamedev-agent-skills`, revision `19d93f97c9c1ea0f8b306e77aa81e0d3e352d3e9`, under Apache-2.0. Their LICENSE, NOTICE and file provenance are preserved there. They are not included in the game runtime or its PCK.

- **GodotPrompter input-handling and responsive-ui development skills** — MIT, Copyright 2026 GodotPrompter Contributors. Pinned source revision `d7b26cdb5fae14d4ef7b713c5bf259395e75c3c6`; original LICENSE, NOTICE and per-file hashes are preserved in `.agents/skills/input-handling/` and `.agents/skills/responsive-ui/`. These are development documents, not runtime dependencies.
