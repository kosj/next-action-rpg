# Static UI font native comparison

The complete static **RunefallKR430** candidate was accepted for reference-only
HUD/touch integration with the small 12px change below recorded explicitly.
The original Noto Sans KR variable font and OFL remain in the repository. The
original is excluded from Web and Windows exports after the two runtime
consumers switch to the static font.

[summary.json](summary.json) pins the actual font/fixture inputs, Godot binary,
renderer, palette, coordinates, import sizes, comparisons and raw PNG hashes.
The full [source derivation audit](../../../../art_source/production/ui_font_static/audit.json)
retains all 24,964 glyphs and all cmap subtables. Static instancing is separate
from this finite raster experiment.

Pinned Godot 4.7.2, Compatibility/OpenGL3 on local Xorg/llvmpipe and the actual
Godot TextServer rendered Label/Button controls. The baseline uses the original
FontFile inside a FontVariation at `wght=430`; the candidate uses the derived
FontFile directly. Fifteen pairs cover logical 390×844, 360×800 and 844×390 at
12/16/18/24/36px. All content fits. All 3,660 shaped glyph records use the
requested font; fallback and missing glyphs are zero.

The twelve pairs at 16/18/24/36px have exact layout and pixels. Each 12px pair
has **213 changed pixels**, limited to the additional `AV`/ligature/multilingual
row. The first shaped `A` advance changes from 7.125 to 7.109375px, propagating
1/64px character offsets. The maximum RGB channel difference is 88/255 and
whole-frame mean absolute channel difference is 0.019565/255 (0.022361/255 at
360×800). **Strict overall layout and pixel equality are false.** Actual
HUD/touch/dialog rows in this finite corpus, widget rectangles, minimum sizes
and wrapping/line counts are unchanged. This does not establish raster
equivalence for every glyph or every real game UI state.

Actual touch action text uses14px and helper text10px, which are outside this
isolated 12/16/18/24/36px corpus. No pixel/layout equivalence is claimed for
10/14px; final real-game portrait/landscape browser review remains necessary.

The unedited 390×844, 12px originals are
[variable430](variable430-390x844-12.png) and
[static430](static430-390x844-12.png). The whole PNG was compared with no
registration, scaling, masking or tolerance. The full 30 original PNGs and
shaped/Control metrics remain in the local ignored capture directory recorded
in the summary.

Real isolated compressed fontdata imports measured **6,732,809 → 3,864,201 B**.
The 2,868,608 B difference is an importer measurement. Final PCK, raw Web and
ZIP savings require the production build. Native/software rendering does not
approve target hardware or the actual desktop/mobile browser UI.

Reproduce only while holding the exclusive local render slot:

```sh
python tools/render_ui_font_review.py --capture --output NEW_CAPTURE_DIRECTORY
```

The helper refuses existing outputs, mirrors the original font import
parameters, creates a minimal private project and private XDG directories, and
closes the engine and local TCP-disabled Xorg. It copies neither the complete
Game nor production import caches. Final native/game/browser regressions and
production export budget validation remain separate.
