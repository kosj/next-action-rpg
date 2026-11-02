# Lossless WebP storage experiment

The actual cold import and bounded pixel checks are recorded in
[summary.json](summary.json). This is storage/input evidence before the 003
paint update, separate from the final Game, browser and export gates.

Pinned Godot 4.7.2 used WebP `compression_method=6` and
`lossless_compression_factor=100`. Its official defaults are 2/25. The
[WebP implementation](https://github.com/godotengine/godot/blob/4.7.2-stable/modules/webp/webp_common.cpp#L45)
uses `lossless=1` and `exact=1`; this effort setting preserves pixels and is
different from lossy quality or the VRAM-only `compress/high_quality` option.
Source resolutions, image files, mip policies and material channels were not
changed in this experiment.

The **single guarded cold import** regenerated 46 CTEX files and their 46
paired MD5 files in **866.849889 seconds**. The cache included excluded
historical assets in addition to the 31 runtime textures. The actual editor
exited 0 with no engine errors. The original whole-game input gate **failed**
because root explicitly changed `hub_npc.gd` during that operation. That
failure remains recorded; it was not relabeled as success. A separate gate
verified the approved exact script SHA change and all other game
assets/sidecars/import hooks/project settings unchanged. Only then was the
completed profile marker recorded. The next actual warm guard invalidated
zero files. A separately declared `build.py` timeout change is also recorded;
there is no claim that all tools or all game files remained byte-identical.

The original local 31-texture comparison also **failed strictly** at the SVG
icon. Its result remains failed. Diagnostic continuation used the unchanged
exact criterion on the remaining 21 textures:

- **30 bitmap CTEX files from PNG/JPEG imports, 346 mips:** dimensions, decoded
  format, headers and complete RGBA bytes match, including RGB beneath alpha0.
  Per-texture bytes and all mip hashes are in [bitmap-corpus.json](bitmap-corpus.json).
- **Local-only frozen SVG icon:** 80 pixels differ in RGB by at most 1/255;
  46 have nonzero alpha and 34 have alpha0. Alpha is identical. No transparent
  pixels were excluded from the strict gate.
- **Same frozen icon bitmap directly reencoded by Godot at 6/100:** complete
  RGBA bytes match, in a separate 0.236-second codec check.
- **Actual published v0.1.12 icon versus the new cold import:** complete
  Godot-decoded RGBA, header, dimensions and format match. The cached public
  ZIP's size/SHA matched the release manifest. No asset was downloaded again.

All 25 actual published CTEX payload MD5s were verified and compared with the
local freeze in [public-v12-payload-bindings.json](public-v12-payload-bindings.json).
The 24 bitmap payloads match byte for byte; the icon is the only difference.
Thus those published bitmap inputs connect directly to the bitmap mip proof,
while the public icon has its own actual Godot pixel check. The six new NPC
bitmap inputs use their first-import frozen local baseline. This **does not
make the original single local 31-case test a pass**. The historical cause of
the local icon cache difference has not been established.

The unedited decoded icon images are [local freeze](local-frozen.png),
[actual public v0.1.12](public-v0.1.12.png), and [new cold import](new-cold.png).
The public and new-cold PNGs have identical bytes and RGBA hashes. These are
texture decode images, not screenshots of Game UI.

The current 31 CTEX payloads measured **100,028,252 → 95,792,014 B**, saving
**4,236,238 B**. Applying measured payload deltas to the local Web tree projects
149,614,973 B. Using the stronger actual public v0.1.12 ZIP/PCK/font baseline
projects **149,616,472 B**, with **383,528 B** under the unchanged 150,000,000 B
cap. These are forecasts, **not a final new export measurement**; subsequent
003 paint, scripts and export metadata remain outside this snapshot.

The reusable [freeze/decode helper](../../../../tools/compare_ctex_storage.py)
prepares without launching Godot. `--decode` needs the exclusive CPU slot and
uses a minimal private SceneTree, private XDG directories and bounded pinned
Godot subprocesses. It never encodes, changes a runtime cache or masks pixels.
The [package audit](../../../../tools/audit_runtime_package.py) checks the
actual final PCK/font presence, imported texture bytes/mips and raw Web cap.
The stock texture importer's settings hash omits these WebP effort settings;
the build guard therefore invalidates only generated CTEX and paired MD5
files when the profile changes, preserving source files and sidecars.
