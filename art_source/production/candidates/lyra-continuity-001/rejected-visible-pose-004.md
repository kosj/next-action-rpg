# Independent candidate 004 still-image review

Verdict: **Reject candidate 004 for runtime art adoption; redesign the free left-arm elbow/pole target.** This is a judgment of the supplied original stills, not a motion, gameplay, hardware or AAA approval.

I directly viewed these eight original PNGs under `studio-004/`:

- `old-light_2-front/light_2-0250.png`
- `new-light_2-front/light_2-0250.png`
- `old-light_2-opposite/light_2-0250.png`
- `new-light_2-opposite/light_2-0250.png`
- `old-light_1-opposite/light_1-0115.png`
- `new-light_1-opposite/light_1-0115.png`
- `old-light_3-opposite/light_3-0155.png`
- `new-light_3-opposite/light_3-0155.png`

At light_2 .250, the new elbow rises toward the head/shoulder line while the forearm hangs almost vertically. The upper arm no longer reads as a relaxed counterweight to the sword-bearing right arm. In the opposite view, the shoulder armour is pulled into a raised wedge close to the neck, with an awkward fold and a strained exposed underside at the shoulder/armpit. There need not be a visible open hole or an extremely thin triangle for this to look wrong: the broad pose and the armour articulation themselves are unconvincing.

The new light_1 .115 and light_3 .155 opposite views repeat a very similar high-elbow, hanging-hand silhouette. These sampled poses read as a persistent wing-like shrug rather than a purposeful free-arm counterbalance. This is visible in normal full-body framing without relying on a deformation heat map. I cannot infer from these stills whether the entire clip holds that pose or how it moves between samples.

The old poses are not approved as final motion or deformation. Their lower elbow and less elevated shoulder nevertheless read more naturally at these particular samples. The new arm branch should not be adopted simply because it removes the old numerical rotation spike. Reported rate/edge metrics explain technical progress and risk; I did not independently recompute them in this review.

Recommended next direction: keep the dense continuity work, but redesign the elbow/pole path so the free elbow can sit lower and slightly outside/behind the torso instead of being driven toward the head. Treat shoulder/clavicle and humeral roll as part of that pose choice; do not force the old wrist target through a high-elbow branch. Recheck the same front/opposite samples and affected shoulder skin/pauldron before another runtime candidate. Do not restore the old abrupt branch flip as the solution, and do not relax the existing numeric continuity gate to hide the pose problem.

No engine, browser, network, asset generation, source edit or Git operation was used for this review. Continuous movement, weight transfer, combat readability, actual native import and final art acceptance require their own evidence.
