> Public archive: three selected original PNGs are retained here (game .24s and detail on/off .18s). Other named screenshots remain in the original ignored build review; their hashes are preserved, but the files are not part of this archive. All text reports, fixture/capture sources and logs are retained. MIX screenshots are omitted; its report records the decision. Reproduction paths below describe the original workspace and need relocation in another checkout. This review predates the eye-socket body adoption.

# Blade-trail fixed Web art review

Capture completed 2026-10-31 with Godot 4.7.2 Web GL Compatibility, Chromium SwiftShader, 1440×900, quality0. Six original screenshots completed in 160.515 seconds; console/page errors0. These are fixed paused art fixtures, not live gameplay/timing QA, target-GPU performance evidence, or AAA approval.

The isolated project is `/workspace/.runefall-task/character-polish/trail-lookdev/game`. It copied the actual Game first room and production A89/214 bodies before the pending eye candidate. `source-manifest.json` records the source commit and all154 original source-file hashes; uncommitted trail source is pinned by those hashes. Shared game files and `build/web` were not modified.

The hero stands at the actual floor top .005m minus capsule sole offset .025m. The fixture samples actual `ActorVisual.pose` continuously at60Hz with `light_1` AttackData (startup .13s, active .17s, total .52s), then freezes .24s or .18s. It uses the actual blade-marker history and never fabricates sweep geometry. The no-trail counterpart hides only the ribbon; camera, body pose, material, light, and quality match within each pair.

| Comparison | Ribbon visible | Ribbon hidden |
| --- | --- | --- |
| Actual RuneCamera, .24s | 01-game-trail-024.png | 02-game-no-trail-024.png |
| Deliberately closer camera, .24s | 04-detail-trail-024.png | 03-detail-no-trail-024.png |
| Same detail camera, .18s | 05-detail-trail-018.png | 06-detail-no-trail-018.png |

The ribbon is translucent and restrained. It does not blanket the body or ground in these poses. The .18s detail clearly shows the trailing wedge. Additive mint becomes pale/near-white against bright stone; the default gameplay-distance .24s shot is subtle and more edge-on. Depth testing is enabled; depth writes/shadows are disabled. The inspected poses do not show body-through glow, but dedicated world-obstacle occlusion remains untested.

This is a usable restrained preview baseline. Final readability needs real-speed attacks with UI/enemy telegraphs, multiple actions and interruptions, quality1/Windows and target hardware. If more contrast is needed, evaluate the distal mint edge while keeping physical blade markers and authoritative active-window timing unchanged.

`capture-states.json` stores camera transforms, attack scalars and actual renderer reports; `review.json` stores findings and image SHA256; `capture-provenance.json` pins fixture/export hashes. Fixture sources and all console/export/import logs are included. The first restricted editor import reported local TCP-listen permission errors; the subsequent Web export with authorized network access exited0 without errors/warnings. Those permission diagnostics were not suppressed or treated as app defects.

Reproduce with the preserved isolated project and matching toolchain (preserve these outputs before rerunning):

```bash
env XDG_CONFIG_HOME=/workspace/.runefall-toolchain/config XDG_DATA_HOME=/workspace/.runefall-toolchain/data XDG_CACHE_HOME=/workspace/.runefall-toolchain/cache /workspace/.runefall-toolchain/godot --headless --path /workspace/.runefall-task/character-polish/trail-lookdev/game --export-release Web /workspace/.runefall-task/character-polish/trail-lookdev/web/index.html
python /workspace/.runefall-task/character-polish/trail-lookdev/capture_web.py
```

Only one Chromium was used. Browser and local server were closed after capture, and the CPU/GPU slot was explicitly released to the eye-socket reviewer.

## Bounded MIX comparison

The separate `mix/` output preserves two follow-up screenshots from a fresh isolated copy. Only the actual trail material blend mode changed from ADD1 to MIX0; alpha .34/.035, tint, marker history, pose, camera and quality match. The exported fixture and Chromium completed without errors; the two captures took62.54 seconds. The renderer was closed and the slot released again.

MIX is **rejected for this iteration**: it does not produce an opaque fan, but its pale mint blends into the sunlit stone and reduces visibility relative to ADD. The default rear .24s view is also partly edge-on; changing blend mode cannot fix that geometric limit. Retain ADD as the restrained preview baseline, with real-speed combat readability still pending. See `mix/review.json` for exact comparisons, hashes and remaining scope.
