# 허브 실제 Game 비교·접지 수정과 최종 채택

2026-11-02 UTC. **이 폴더의 candidate001은 NPC 접지 수정 전 기록**이다. 루트는 candidate0018원본 전체를 직접 보고 인물 역할·relic의 prototype 개선을 받아들였지만, 성능 모드에서 그림자/ellipse 없는 NPC boots가 떠 보이는 문제를 최종 표현으로 채택하지 않았다. 후속 source의 native601/0·양쪽 export와 candidate0028원본을 별도로 확인해 두 static NPC의 근사 접지를 제한적으로 채택했다.

| 같은 구도·품질 | 공개 v0.1.12 baseline | pre-grounding candidate001 | 최종 candidate002 |
| --- | --- | --- | --- |
| hubwide q0 | [원본](baseline-001/hubwide-q0.png) | [원본](rejected-001/hubwide-q0.png) | [원본](candidate-002/hubwide-q0.png) |
| Erin full q0 | [원본](baseline-001/erin-q0.png) | [원본](rejected-001/erin-q0.png) | [원본](candidate-002/erin-q0.png) |
| Roen full q0 | [원본](baseline-001/roen-q0.png) | [원본](rejected-001/roen-q0.png) | [원본](candidate-002/roen-q0.png) |
| relic close q0 | [원본](baseline-001/checkpoint-q0.png) | [원본](rejected-001/checkpoint-q0.png) | [원본](candidate-002/checkpoint-q0.png) |
| hubwide q1 | [원본](baseline-001/hubwide-q1.png) | [원본](rejected-001/hubwide-q1.png) | [원본](candidate-002/hubwide-q1.png) |
| Erin full q1 | [원본](baseline-001/erin-q1.png) | [원본](rejected-001/erin-q1.png) | [원본](candidate-002/erin-q1.png) |
| Roen full q1 | [원본](baseline-001/roen-q1.png) | [원본](rejected-001/roen-q1.png) | [원본](candidate-002/roen-q1.png) |
| relic close q1 | [원본](baseline-001/checkpoint-q1.png) | [원본](rejected-001/checkpoint-q1.png) | [원본](candidate-002/checkpoint-q1.png) |

Erin003와 Roen001은 실제 runtime의53본/16ktriangle 몸체다.2D 참조나 Blender studio 이미지를 이16장으로 대체한 것이 아니다. 다만 여전히 Erin의 ragged hem/slit/teal tip과 q1 NPC 접지 문제가 남았고 전체 의상·AAA·모션/연속 AV·목표 기기 성능은 승인하지 않았다. [motivating 판정](rejected-001/review.json)과 [stable case ID·해시 annotation](pre-grounding-review-status.json)을 연결한다.

## 비교 조건과 보존 경계

실제 Game의 prescribed camera/FOV·native scale·Hero/NPC/논리 checkpoint origins를 맞췄고 static collision160body/178shape의 canonical rows/hash와 RNG가 같다. 새 NPC의 **production presentation yaw는±.7→±1.815로 의도적으로 바뀌었다.** 동일한 전체 NPC basis·동일 body/pose·순수 재질 실험이라고 쓰지 않는다. fixture가 model rotation/scale/tilt를 몰래 바꾸어 보여 준 결과도 아니다. relic의 시각 origin/pivot과 논리 checkpoint 위치는 별도다.

fixture는 ordinary idle0을 seek한 뒤 mixer를 pause/inactive로 둔다. live `idle.clip`이 비어 있는 상태와 선택한 idle·이미 샘플된 skin pose를 구분한다. 이 원본들은 정상 대화/강화·checkpoint 입력·실시간 idle·spawn 물리·게임 FPS를 재현한 take가 아니다. 실제 HUD를 표시한1280×720 원본이며 리사이즈·색보정하지 않았다.

전체16장 캡처는165.033초/exit0·엔진 오류0·source 불변·audio release·모든 프로세스 종료를 확인했다. Compatibility/Mesa llvmpipe의 시간은 목표 GPU의 FPS가 아니다. [실제 capture](pre-grounding-capture.json)와 [paired report](pre-grounding-paired-comparison.json)를 보존한다.

[warm cache provenance](pre-grounding-warm-cache-provenance.json)는 양쪽에 method6/100 cache를 복사했고 baseline source는 default2/25를 유지했다고 명시한다. 이를 cold baseline/encoding 성능 실험으로 해석하지 않는다. bitmap346mip·actual public icon의 [서로 다른 scoped 근거](../lossless-webp/README.md)는 pre-paint 경계를 유지하며003새 pixel 승인으로 자동 승계하지 않는다.

공개 `scene-review.json`은 실제 controls·poses·runtime·collision/해시를 유지하고 local cache 경로와 worktree 목록만 생략한 subset이다. 원래 report bytes/SHA는 `curation`에 보존했다. source/capture/runtime input 원장도 각 폴더에 남긴다. 기존580 native·149,687,995B export는 [pre-grounding 입력](../native-selected-003-checkpoint.json)이며 후속 source를 검증하지 않는다.

## 접지 수정 후 candidate002

[최종 판정](candidate-002/review.json)은 프로토타입 범위의 채택이다. 루트는 새 q1네 원본을 모두 직접 보고 부유 인상이 줄었음을 확인했다. q0네 원본은 이미 본001과 byte/SHA가 같다. q0의 두 NPC ellipse는 hidden/opacity0, q1는 실제 바닥[-4,0,5]/[4,0,5]·UP normal·opacity.21·각1회 query/cached/pendingfalse를 보고한다. static NPC2 budget은 기존 Hero/Enemy8과 독립이다. 연한 ellipse를 per-foot/light-derived shadow로 해석하지 않는다.

[after-only 실제 capture](final-capture.json)는99.947558초·exit0·errors[]·source 불변·audio release·프로세스 종료를 확인했다. [baseline 짝 조건](final-paired-comparison.json), [001→002 source/원본 delta](final-grounding-delta-from-001.json)는 camera/origins/static/RNG·body/font/relic SHA와 NPC profile의 새 grounding 외 필드가 같음을 확인한다. q1 pixel 차이는 별도 bbox로 측정했고 q0네 장은 exact다. [warm cache](final-warm-cache-provenance.json)는46CTEX가 root/001과 같음을 연결한다. elapsed time은 FPS가 아니며 새 source88의 [실제 local desktop](../local-desktop/README.md)은 이후 통과했고 full mobile·clean CI·공개/릴리스는 source snapshot에서 pending이다.

공개 archive는 baseline8·수정 동기의0018·최종0028의24원본을 보존한다. [archive manifest](archive-manifest.json)의 bytes/SHA는 raw 원본과 public report subset을 묶는다. Erin의 ragged dark hem/slit/teal tip·전체 의상/skin/연속 AV·실기기/AAA는 미승인이다.
