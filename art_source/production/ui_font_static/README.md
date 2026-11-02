# RunefallKR430 complete static font candidate

This candidate freezes the existing UI font at its actual `wght=430` setting.
The original `game/assets/fonts/NotoSansKR.ttf` remains unmodified. The new
`game/assets/fonts/runefall_kr430.ttf` is a **modified font**, renamed
**RunefallKR430** (PostScript `RunefallKR430-Regular`) and licensed under SIL
Open Font License 1.1. Original copyright and license records remain embedded;
the original license is copied byte for byte to [OFL.txt](OFL.txt). Adobe is not
represented as endorsing this modification. The Reserved Font Name `Source`
is retained in the copyright notice and is not used as the derivative family.

Source provenance: the repository's existing Noto Sans KR from
<https://github.com/google/fonts/tree/main/ofl/notosanskr>, as recorded in
`THIRD_PARTY_NOTICES.md`. The exact retained local source is pinned by SHA-256
in [audit.json](audit.json); this experiment does not claim to have downloaded
a new upstream font.

The production derivation uses FontTools **4.61.1** and its official
[`instantiateVariableFont`](https://github.com/fonttools/fonttools/blob/4.61.1/Lib/fontTools/varLib/instancer/__init__.py)
with `wght=430`, `static=True`, `optimize=True`,
`OverlapMode.KEEP_AND_DONT_SET_FLAGS`, and `updateFontNames=False`. Primary
family, style, full, unique, PostScript and variation-prefix name records are
then replaced. No glyph/character subsetting, contour simplification or overlap
removal is performed. Source timestamps are retained for reproducibility.

From the repository root, install the pinned tooling in your isolated Python
environment, then generate a **new output path**:

```sh
python -m pip install -r art_source/production/ui_font_static/requirements.txt
python tools/derive_ui_font.py game/assets/fonts/NotoSansKR.ttf NEW.ttf \
  --license art_source/production/ui_font_static/OFL.txt --report NEW-audit.json
```

Audit the existing candidate without replacing it:

```sh
python tools/derive_ui_font.py game/assets/fonts/NotoSansKR.ttf \
  game/assets/fonts/runefall_kr430.ttf --check \
  --license art_source/production/ui_font_static/OFL.txt --report NEW-check.json
python -m unittest discover -s tools/tests -p 'test_derive_ui_font.py' -v
```

The optional installed system `libharfbuzz` audit shapes every best-cmap
character separately plus seven multilingual/ligature probes, comparing glyph
IDs, UTF-8 clusters, advances and offsets at the font's UPEM scale. It does not
cover all combinations of language/features or pixels. All cmap subtables,
all glyphs (including unencoded glyphs), and GSUB/GPOS script, language and
feature coverage are checked separately. Byte comparison with a freshly
generated complete official instance also covers all resolved layout and
horizontal/vertical metric tables. GPOS numeric lookup indices can change
when variable positioning is resolved; language/feature coverage is compared
without requiring those implementation indices to remain equal.

Source variable outlines are floating point; static TrueType outlines are
integer coordinates. The all-glyph report therefore records the measured
rounding differences rather than claiming raw-outline equality. The early
[lookup-index check](preflight/lookup-index-check-rejected.json) was rejected
because it incorrectly treated renumbered GPOS lookup indices as lost language
coverage. [audit.json](audit.json) uses semantic script/language/feature checks
and retains complete-instance byte verification.

The candidate TTF is 6,224,172 bytes versus the original 10,414,588 bytes.
This is **4,190,416 bytes of raw TTF saving only**. Godot's imported fontdata,
PCK, exported raw Web total and ZIP bytes are distinct measurements.

The later [scoped Godot raster comparison](../../../docs/validation/v0.1.13/ui-font/README.md)
was accepted for reference-only integration. Its fifteen pairs cover
12/16/18/24/36px at three logical viewport profiles. Twelve pairs at
16/18/24/36px match exactly; the three 12px pairs retain a small `AV` edge-case
advance/raster difference. Strict overall pixel/layout equality is false.
Actual touch action14px/helper10px are outside that isolated raster corpus.

`game/scripts/ui/hud.gd` and `game/scripts/ui/touch_controls.gd` now use the
static FontFile directly with the original import parameters. Both export
presets exclude the retained original variable font. Native production/UI
regressions, final PCK/raw Web/Windows byte measurements and actual Game
desktop/mobile browser reviews remain **pending**. The source derivation
report and isolated raster experiment do not approve those later stages.
