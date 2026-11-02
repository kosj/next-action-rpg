# Independent final 006 actual-broad still review

**Verdict: ACCEPT candidate 006 for scoped prototype adoption on the directly viewed stills below.** This is not approval of all skin deformation, full-clip motion, gameplay/continuous AV, hardware performance or AAA quality.

Viewed the four originals under `studio-006-actual-broad/`: old/new `armpit033` at light_2 .330, and old/new `front025` at light_2 .250. At .330 the new lower counterguard gives the shoulder, upper arm, elbow and wrist a more natural relationship than the old pose. The pauldron reads as armour over the shoulder rather than the raised folded wing that led to rejection of 004. The free hand sits in a plausible compact guard near the torso. I do not see an obvious open background hole or needle-like spike in the newly exposed underarm/side image.

The underarm still contains dark fabric and shadow. That limits surface reading; absence of an obvious hole in this still is not evidence that the reported worst edge/vertices or every skin sample are clean. This review does not overrule the separate deformation measurements.

At front .250 the fist remains close beneath the blade/guard. I see no clear blade-through-hand defect in this projection sufficient to reject this prototype, but proximity in one still neither proves contact nor establishes 3D clearance. These finite views support scoped adoption; they do not certify every arm/weapon crossing through the full action.

Composition reports identify old character source `f2edbd37...`, new character source `14e5069a...`, retained base hilt/PBR `68dfaca4...`, production broad geometry `4fd76a77...`, and runtime grip `6d04ad12...`. I independently checked that each actual PNG SHA matches its composition report, and that old/new captured camera matrices are exactly equal within each pair. Raw marker checks are reported as passing by the producing tool; I did not rerun that tool or independently recompute mesh composition/markers.

The prior `studio-006-first` images used the old slim blade. Their wrist/body assessment and explicit weapon-source qualification remain in `independent006-review.md`; those images are not retroactively relabelled as broad-blade evidence. Likewise, the prior wrong-file camera assessment and its correction remain preserved there. The current four studio stills do not resolve the separate post-take camera framing failures.

| Pair / file relative to `studio-006-actual-broad/` | Actual PNG SHA-256 | `continuity-composition.json` SHA-256 |
| --- | --- | --- |
| `armpit033-old/light_2-0330.png` | `e70a6cc7e4aa74a14feb41c11873a9724906c2eb4e57aca98064325c20030d35` | `bd259e00e131e74a875a17bbb7d6055c37ab3933b8fd65bf3f4626fad3965e15` |
| `armpit033-new/light_2-0330.png` | `f54a65055e8ac673d2fd7f868d833e7665f8332abec93329f897346741ccc14e` | `ceb6d165fabf4ac349a30704dbeec3a66d38358d48a1eec54f5297ec7ca258d2` |
| `front025-old/light_2-0250.png` | `d4369564cf46781f4476f69784c93f0badd5d0e0c6c0ef625d072bf71243b76f` | `d2e05391e2e30052390255388585507b1cf3200b5a585c5cd7f5b5c7ed3397b0` |
| `front025-new/light_2-0250.png` | `90b34b46a00586c79a7342bfab76c14f7b2ba30cddf897d968f760cb8a7f6141` | `2a7ec459a254ac07699dd9464219d4eb56de8f87914254a62683c10bb8ad8bc7` |

No engine, browser, network, source/Git mutation or generation was used. Read-only image views, report reads, SHA calculations and the single private review file were the scope of this task.
