# Independent 006 wrist and baseline framing review

**Scoped wrist verdict: accept the orientation correction for continued candidate evaluation. This does not approve the complete clip, runtime adoption, skin deformation or AAA quality.**

Directly viewed all six original stills in `studio-006-first/{front,opposite}/light_2-{0130,0250,0330}.png`.

At .130 the free hand now follows the forearm more naturally in both views; the conspicuous hanging wrist fold seen in 005 is reduced. The lower elbow and layered shoulder silhouette remain substantially better than rejected 004. At front .250 the free fist still crowds the underside of the blade/guard. Changing wrist orientation does not resolve that positional concern. The opposite view obscures it, so these images do not establish 3D intersection or clearance. At .330 the affected left thorax/axilla is substantially obscured by the arm and torso; these views **do not clear the reported worst thorax skin sample**. No continuous-motion judgment is made.

**Weapon-source qualification added after root's fixture audit:** The six 006 studio images above use the old slim `rune_sword_web` asset (root-verified SHA prefix `68df`), whereas production `ActorVisual` replaces `visualBladeSurface` with `rune_greatsword_geometry` (SHA prefix `4fd`). The body/wrist pose observations remain applicable to the pictured candidate, but the blade-adjacent hand observation describes only the slim sword actually pictured. It does **not** assess the current broad production blade, establish its hand clearance/interference, or approve its grip/contact. A dedicated studio comparison using the actual retained hilt, broad blade geometry and production grip is being prepared separately. The original viewed images and their source boundary remain unchanged; do not relabel them as current-weapon evidence.

**Camera correction:** My first message mistakenly assessed `before/original-png/01-normal-gameplay.png`, `02-charge-near-real-enemy.png`, and `03-native-heavy-release.png`. Those are not the requested post-take frames. The earlier statement that the full hero was readable without clipping is invalid for the requested samples and is withdrawn.

I subsequently directly viewed and SHA-checked these exact requested originals under `/workspace/next-action-rpg/build/art-review/combat-continuity-before-14-002/post-take-framing/`:

| File | SHA-256 | Visible framing assessment |
| --- | --- | --- |
| `decoded-01.png` | `f879b3a92e2b98fb436355729e37644845229f572ace26186e9a9826aff30200` | Severely unreadable combat framing: oversized partial hero against the right edge, most of the image showing floor, no foes visible. Hero silhouette, weapon action and encounter relationships cannot be judged. |
| `decoded-02.png` | `d104ee2aae538461a4f7cf00ee43ea0a7ac1bc50dbc696b1031db52228f2e0dc` | Large over-shoulder hero with lower body cut off. Distant foes and exit are visible, but hero feet and full action silhouette are not. |
| `decoded-03.png` | `30fc0b27c060a3873745e588bae4d034c7f93c8fcc50f2ae2302bba582c6554e` | Hero is low/right with legs and feet outside the frame; enemies remain readable. This sample cannot show hero grounding or footwork and loses part of the action silhouette behind the edge/UI. |

These exact post-take samples fail complete-character combat readability. The stills alone do not identify why their framing occurs, whether the problem persists through the entire take, or which camera code/fixture state caused it. They are not evidence against the isolated 006 wrist change either. Cause and full-take behavior require the separate capture/provenance investigation.

No engine, browser, network, source edit, Git operation or mutation outside this private report was used. Read-only path discovery and SHA checks accompanied the direct image views.
