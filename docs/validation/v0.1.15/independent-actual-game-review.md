# Independent actual-Game decisive-sword review

**Verdict: ACCEPT as a bounded prototype improvement to strong-attack preparation and visible sword trajectory in the actual Game.** This is not approval of the complete perceived impact, continuous motion/audio, every deformation, hardware performance or AAA quality.

I directly viewed the before/after native originals `10-ordinary-heavy-first-active.png` and `04-actual-confirmed-contact.png`, plus all twelve actual raw-MJPEG decoded frames from the provenance below: ordinary first-active+6, charged-whiff active mid, and charged contact+1/+2/+4/+6 on both sides. No newly generated render, crop or edited still was substituted.

## What is visibly improved

Ordinary first-active now raises both arms and the sword over the head. The older actual sample is a small horizontal sword/arm silhouette much like the earlier light3 sample. This change is recognisable in the actual gameplay camera, not just the neutral studio. The blade tip, body and feet stay in frame in the reviewed samples.

At ordinary active+6 and charged-whiff mid, the new trail forms a much larger visible cutting plane than the older thin pale/orange trace. At confirmed contact and +1/+2/+4/+6, that cutting plane is also clearly visible around the target while the hero, feet and the surrounding opponents remain readable. It does not become a full-screen flash that erases all actor context in these selected frames. This addresses the user's request for a more decisive visual gesture to a limited, visible extent.

## What is not yet resolved or proven

The new trail still reads as a bright, fairly flat geometric fan with a hard-looking outer shape. Larger coverage is visible progress, but not proof of polished layered impact or AAA VFX. Consider a refined taper/edge/brightness breakup in a later controlled candidate if normal-speed review confirms a cardboard-like impression; do not assume a longer/bigger trail is automatically stronger.

The closest hero/target/weapon silhouettes remain overlapped, and the chapter text still occupies background action space. Fingers, wrist skin, extreme shoulder deformation and precise hand/blade clearance cannot be certified at this gameplay distance. Preparation looks different and more emphatic, but whole-body weight transfer, hit reaction, recovery rhythm and perceived punch need a continuous logical1x review.

The contact samples are near one another and show similar poses. This alone does not prove excessive freezing or insufficient reaction; no full-duration timing diagnosis is made from these stills. I did not listen to the audio or watch a continuous take. PCM/encoding/pipeline pass would not constitute either activity.

## Pairing and source attribution

The ordinary and charged-whiff mid frames share ticks209/308 respectively. Contact was actually recorded at before tick610 and after tick621. Therefore +1/+2/+4/+6 pairs are relative to each actual contact, not the same absolute playback time. Event timing, body/trajectory, root travel and presentation intentionally differ; this is not a one-variable VFX-only comparison. The capture agent reports q1 Performance/native.65/960×600 and unchanged policy, with intentional new heavy travel about.704m versus baseline about2.09m. Those are producer-reported capture contracts, not independently rerun by me.

The after source manifest binds the viewed take to the following actual source bytes. I read and hash-bound the manifest; I did not rerun import, gameplay or audio.

| After source | SHA-256 |
| --- | --- |
| `assets/models/production/lyra_fury_gameplay.glb` | `9bb9025621c7aec3690c47a35e0d6946b322f9b4f73f736a10696d1170071a9f` |
| `scripts/actors/blade_trail.gd` | `4c5d42f8dfc97ad8d3b3c9dd05949817f1da097183e55adba110887c8c181c86` |
| `scripts/world/impact_effect.gd` | `eaa82edb2b6c03822165b01ad537c10bae8a64c64b10cb63623a217608f21bc3` |
| `scripts/world/camera_rig.gd` | `a8461c35466950a34543878d6f089b9ddb274a3e1aecc18537182b7f6681de60` |
| `scripts/core/audio.gd` | `25bf3fe30a21415ffdece1543aafafc26680aa435acb3313f75951880f8fe4ee` |

| Actual decoded original relative to `paired-action-frames/` | Event | Tick/movie frame | Independently checked PNG SHA-256 |
| --- | --- | --- | --- |
| `before/decoded-01.png` | ordinary-heavy-active-mid | 209/208 | `0bf62233da81e4d3c2343e3e6172c1c1bddd252b67b4a11ea2814641fe77f10a` |
| `before/decoded-02.png` | charged-whiff-active-mid | 308/307 | `37621be6fecb74998174caa0716e2df8b94e03891220c298ba76b884e1010b11` |
| `before/contact-details/decoded-01.png` | charged-contact-plus1 | 611/610 | `9e2ade0306b965b26d87b13f03084b03ffe214679e8f5020fc9974c6bc78312a` |
| `before/decoded-03.png` | charged-contact-plus2 | 612/611 | `86b7d94aeea38ce985dcf1ddf83f0424ee09a6de4671c3f8ff0184d8888c6376` |
| `before/contact-details/decoded-02.png` | charged-contact-plus4 | 614/613 | `5d96273ff2dbaf1e3c975c75aa34e75436c1282b3157ebffcdd6aab84122a1d2` |
| `before/decoded-04.png` | charged-contact-plus6 | 616/615 | `ae644220d167af8c21620e4dc3fa1566bccba1d2b9c624a8516ba0e20b48c694` |
| `after/decoded-01.png` | ordinary-heavy-active-mid | 209/208 | `bb12c7a7e72bdb1a7e25b5dd0c8c941d09d655645b3931df91a33f4cd100c186` |
| `after/decoded-02.png` | charged-whiff-active-mid | 308/307 | `69eb445f99b30853b5113dd6bd81febd5393012c4b3b25cfc72378dfbc4c3a7a` |
| `after/contact-details/decoded-01.png` | charged-contact-plus1 | 622/621 | `b83c1df2a84f0c838fdb8a95e3099e99c8f1878467f495e3a40f96a21687c9a0` |
| `after/decoded-03.png` | charged-contact-plus2 | 623/622 | `f4e440a1f61381978b76208714e7c396c6d0aad68530c3fc83cad1f20132331e` |
| `after/contact-details/decoded-02.png` | charged-contact-plus4 | 625/624 | `dc9c547e0c703c5d22d387af117a9f336c10502327c7e13844ef70345e8db533` |
| `after/decoded-04.png` | charged-contact-plus6 | 627/626 | `6115edb8f0a5b12d57ba468c00b2d77299386a691d63e7c6f920417f66127a45` |

Native originals directly viewed and SHA-checked:
- `build/art-review/decisive-sword-before-14-001/before/original-png/10-ordinary-heavy-first-active.png`: `0726c1335283f0e1a3fa03d1841882a558ab16e10854e3ce7661d1bc1080a687`
- `build/art-review/decisive-sword-before-14-001/before/original-png/04-actual-confirmed-contact.png`: `eb04b4f8fdafb7ddf40936ac426ddcee7daf135febf38312d5dce9ef2dcf7b9d`
- `build/art-review/decisive-sword-after-14-001/after/original-png/10-ordinary-heavy-first-active.png`: `a7d19ef1968ca5dcde09f3561df48e3cc1c7d600f5478e25660e52a535dd9e05`
- `build/art-review/decisive-sword-after-14-001/after/original-png/04-actual-confirmed-contact.png`: `dfea56c90dadfdf120e638ce81e4cbd1149501cb3c1dea37d9c33dbe4de5aa11`

Paired provenance: `build/art-review/decisive-sword-after-14-001/paired-action-frames/provenance.json`, SHA-256 `7876fd794ffcb60837355b70379e481aa0dc726fe49f18f00a4cf84174b67698`. Each decoded PNG SHA was independently calculated and matched against it. Source manifest SHA-256: `4420e8e744f6a496fa2c5c4a03f46070148571a99cae63e7ee1e4331fa6cd272`.
- before retained AVI, attributed by provenance: `d2ee97d98fd4d3826949f06e44c105fa5a127cb4ad957c7b93b98ac70d9567f6`. I did not rehash the large AVI or re-decode it.
- after retained AVI, attributed by provenance: `1470b34d1265a082d6c56cb35a95243dc34872bf593e427f528c536d706269bf`. I did not rehash the large AVI or re-decode it.

Only this private report was written. No engine/browser/network, game/document/source/Git edit or capture-original mutation was performed. Prototype adoption here does not imply full continuous AV/hearing/hardware/AAA approval.
