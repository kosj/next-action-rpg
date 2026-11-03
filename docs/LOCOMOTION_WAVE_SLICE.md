# 이동 공격과 진행하는 검기: 제작·검수 계약

2026-11-03 UTC. 사용자 지적은 “이동 공격이 애니메이션 없이 밀리고, 검기 범위와 액션성이 없다”이다. 작업 기준은 `feat/stride-and-sword-waves`의 전달받은 시작점 `e7c9ee3c`다. 이 문서는 코드 읽기와 공식 자료 대조, 앞으로 실행할 실제 Game 캡처 명세를 기록한다. **검사 통과 ≠ 질감 승인**이다. 이 문서 작성자는 엔진·GPU·Blender·브라우저를 실행하지 않았다. 새 native·실제 캡처·연속 1배속 시청·직접 청취·실기기·AAA 결과는 모두 `pending`이다.

## 관찰 범위와 이전 증거의 경계

프로젝트 [개발 스킬](../.agents/skills/runefall-development/SKILL.md), [아트 스킬](../.agents/skills/runefall-art/SKILL.md), [Godot 애니메이션](../.agents/skills/godot-animation/SKILL.md)과 [물리](../.agents/skills/godot-physics/SKILL.md), [아트 반입 지침](ART_REVIEW.md)을 읽었다. 공개 스킬의 프로젝트 pin은 `19d93f97c9c1ea0f8b306e77aa81e0d3e352d3e9`이며 [원장](../.agents/skills/upstream.json)을 보존한다. 아래 공식 자료를 현재 4.7 계열과 직접 대조했다. 엔진 설정 원본 [toolchain](../tools/toolchain.json)은 Godot 4.7.2다.

[v0.1.15 제작 기록](DECISIVE_SWORD_SLICE.md)과 [검증 원장](validation/v0.1.15/README.md)은 일반 heavy의 양손 머리 위 준비·내려베기와 fan의 제한된 prototype 개선을 다뤘다. 기존 light 세 클립은 보존했고, 이전 14.4초 trace에는 skill 행이 없었다. 새 독립 skill factory의 735/0 결과도 이동 공격의 연속 질감·새 검기 증거는 아니다. 명목 sole/marker 오차와 프레임 안 좌표는 terrain footplant나 전체 skin 승인이 아니다. 이력의 유한 승인 범위를 이번 작업으로 승계하지 않는다.

동시 구현 중인 공유 작업 트리에서 읽었으므로 모든 읽기 결과가 시작 커밋과 byte 동일하다고 주장하지 않는다. 특히 bridge에는 이미 새 combat layer 작성분이 보였다. 아래 원인 관찰은 아직 연결되지 않은 player 흐름과 기존 공격 선택 우선순위를 대상으로 하며, 최종 통합 source freeze는 루트 담당자가 별도로 기록해야 한다.

| 읽은 소스와 관찰 | 사용자 불만과의 관계 |
| --- | --- |
| [player](../game/scripts/actors/player.gd)의 공격 motor는 `strike != null`이면 일반 방향 이동을 `facing * lunge_speed`로 치환했다. 실제 이동은 `move_and_slide()`가 해결한다. | 버튼을 누르는 동안에도 몸체는 이동한다. 입력 방향과 공격 전진은 같은 권한이 아니며, 다리 모션만 추가해 자유로운 공격 조향까지 구현됐다고 할 수 없다. |
| [bridge](../game/scripts/actors/skeletal_visual_bridge.gd)의 상태 선택은 피격·회피·패링 다음 attack을 locomotion보다 먼저 선택했다. 기존 이동 charge만 Spine 분기 위에 별도 시간으로 얹었다. | 공격 전신 포즈와 controller 전진이 결합되어 발이 붙은 채 미끄러져 보일 수 있다. charge 레이어의 존재가 light 공격 레이어의 존재를 뜻하지 않는다. |
| [strike](../game/scripts/core/strike.gd)의 light는 actor 주변의 capsule/arc 표본과 벽 ray를 사용한다. physical heavy/charged는 별도 blade LUT를 사용한다. | light `reach`를 올리면 보이지 않는 근접 proxy가 커질 뿐, 앞으로 이동하는 검기는 생기지 않는다. |
| [skill factory](../game/scripts/actors/player.gd)는 독립 `AttackData.new()`이며 첫 스킬 lunge 13, `.16/.35/.28` 시간을 명시한다. | heavy Resource 상속을 되살리면 이전 물리 곡선/phase motor 회귀가 재발한다. 검기 추가도 독립 계약으로 연결해야 한다. |

## 선택한 수정과 충분성의 범위

light 1/2/3와 첫 스킬의 **실제 수평 이동**에 기존 보행을 연결하고 Spine 및 자손에는 해당 공격을 표본화한다. 루트의 통합 결정은 light 입력 방향 이동을 4.2m/s로 허용하고, 무입력 공격은 active 구간의 작은 전진만 적용하는 것이다. 구체 속도·phase 값의 원본은 최종 player/AttackData 설정이며, 첫 스킬의 고유 돌진과 구분한다. Root·Hips·다리/발은 locomotion이 소유한다. `movement_distance`는 같은 presentation 구간의 collision-resolved 수평 변위이며, 원한 속도×시간이 아니다. 실제 이동 방향의 local x/z로 전후좌우 gait를 선택한다. 이동 phase는 콤보가 바뀌어도 이어지고 공격 시간은 gameplay snapshot을 따른다. heavy/charged와 해당 blade LUT는 기존 fullbody를 유지한다.

이는 “움직이는데 다리는 공격 자세에 고정”인 직접 원인에 맞는 수정이다. Spine 경계의 허리 비틀림, 기존 보행의 보폭, 급격한 감속/정지 후 전신 회수, skill1의 높은 전진 속도에서 자연스러운 달림은 별도 시각 위험이다. 실제 이동량과 cycle을 동기화해도 각 발의 접촉 구간을 잠그는 IK/stride warping은 구현된 것이 아니다. 발이 지면에 닿는 높이, 발바닥 world drift, 피부 변형·발뒤꿈치 들림을 보지 않고 “footplant 해결”이라고 표시하지 않는다.

검기는 실제 world 위치와 폭을 가진 별도 진행체로 발사한다. 루트가 고정한 4.5m/7.5m는 **발사 시 source origin에서 전방 leading edge까지의 최대 거리**다. 앞 `.6m`에서 발사하고 crescent 전면이 중심의 z=0이면 중심 travel은 각각 `3.9m/6.9m`다. 발사 후 이동한 source를 기준으로 사거리를 다시 늘리지 않는다. 발사점 오프셋·곡면의 뒤로 굽은 깊이·폭·target hurtbox 반경을 따로 기록한다. 끝점에서 hurtbox가 겹쳐 피해가 난 target의 노드 중심이 더 멀 수 있으므로 노드 중심 거리와 geometry 도달 거리를 혼동하지 않는다. 최종 매핑은 L3/일반 heavy/charged 순서로 사거리 4.5/4.5/7.5m, 폭 1.6/2.0/2.4m, 속도 16/16/18m/s, 원래 strike 피해 계수 .7/.7/.65다. 검기는 startup 직후가 아니라 `startup + active * wave_release_fraction`에 발사하며 현재 저작 기본 fraction은 .65다. 루트의 첫 native 관찰에서 너무 이른 검기가 가까운 charged의 물리 칼날 접촉을 먼저 소비했으므로, 접촉 가드를 완화하지 않고 앞으로 베는 release phase 뒤로 발사를 옮긴다. 재실행 전 성공을 주장하지 않는다. 검기 부착과 heavy/charged의 fullbody 유지 여부는 서로 다른 계약이다.

VFX는 실제 진행 위치에 붙은 crescent여야 하며, 물리 폭·전면 위치와 같은 계약을 사용한다. travel 도중에만 닿는 적, 폭 가장자리의 적, 벽 앞/뒤의 적을 구분한다. 큰 기존 `reach`, actor 중심 disk, 화면 전용 fan을 원거리 판정의 대용으로 사용하지 않는다. 손·검·상체의 의미 있는 공격은 실제 클립에서 가져오며 무작위 bone jiggle·추가 카메라 흔들림으로 보행 부재를 숨기지 않는다.

## 구현을 읽고 확인할 기능 기준

다음은 합격을 아직 관측하지 않은 수용 기준이다. 수치 허용오차는 각 회귀의 좌표계·부동소수 오차·물리 margin과 함께 명시하고, 실패 후 범위를 늘려 통과시키지 않는다.

| 대상 | 독립 확인과 실패 조건 |
| --- | --- |
| 실제 이동 입력 | 일반 Game 입력으로 light 1/2/3와 skill1이 발생한다. 요청 lunge, 최종 순변위, 틱별 수평 경로와 layer에 전달한 거리의 뜻을 구분한다. 벽에 막힌 positive-delta 이동을 요청 속도로 재구성하면 실패다. |
| 보행/공격 소유권 | 같은 시각의 실제 Hips·좌우 다리/발은 선택 gait와, Spine 자손·Grip/Tip은 공격 layer와 비교한다. flag 이름/본 수가 맞는 것만 확인하지 않는다. heavy/charged에 gait가 섞이거나 LUT/socket/피해 시간이 달라지면 실패다. |
| 연속 콤보 | L1→L2→L3에서 실제 공격 인스턴스는 바뀌고 gait phase는 이어진다. active 이전의 전환과 active 정확 표본을 구분한다. 매 타격마다 같은 발로 리셋되거나, 마지막 회수에서 발이 튀면 시각 실패다. |
| 접촉 hitpause | 접촉 직전 양의 delta에서 해결된 이동을 한 번 소비한 뒤 동일 상태의 delta0은 attack/gait/블렌드/소켓을 고정한다. delta0의 `movement_distance=0`을 새 정지로 오인해 layer를 끄거나, 보관된 거리를 반복 소비하면 실패다. |
| 정지·벽 | 양의 delta에서 실제 이동이 멎는 경우와 delta0 pause를 구분한다. 벽에 계속 걷거나 발을 바꾸며 압박하지 않는지, 전신 회수로 돌아갈 때 하체가 튀지 않는지 본다. 실제 벽 slide가 있다면 그 해결 방향으로 gait를 고른다. |
| 우선 중단 | hit/death/dodge/parry, epoch 복귀·순간이동에서 공격 layer와 과거 trail을 정리한다. 이미 발사된 검기의 존속 정책은 별도로 고정한다. 후속 버퍼가 중단된 공격을 되살리면 실패다. |
| 검기 발생/시간 | 지정 trigger당 발사 1회, 저작 release 시각 전 발사/검기 피해 0, startup 중 근접 피해 0, 동일 strike id 연결, 이동 후 접촉과 명확한 수명 종료를 확인한다. 준비 중 직접 HP 감소나 도달 전 피해가 있으면 실패다. 큰 delta에서도 전체 경로를 검사한다. |
| 실제 폭과 sweep | 전후 위치 사이를 실제 폭이 있는 hull로 검사한다. `intersect_shape.motion`만 설정한 overlap은 sweep 증거가 아니다. 초기 겹침과 낮은/높은 target, 중심 밖 가장자리, 폭 밖, 끝점 밖을 함께 확인한다. 한 질의의 max-results 포화가 전체 적 검출 보증은 아니므로 혼잡도/예산 조건도 적는다. |
| 벽 차폐 | 중심선만이 아니라 곡면 폭의 가장자리가 닿는 얇은 벽·모서리를 본다. 초기 wall overlap과 첫 blocker 시각을 먼저 해결하고 적 query를 거기까지 자른다. 같은 시각의 blocker/target은 blocker 우선이다. 벽 너머 적 피해·계속 보이는 통과 VFX는 실패다. |
| 공유 피해 ledger | 근접/검기가 같은 원본 `CombatStrike`의 target ledger를 사용한다. 근접→검기 및 검기→근접 순서의 동일 target 총 피해는 계약상 1회이며, 서로 다른 적은 각각 맞을 수 있어야 한다. 별도 attack id로 중복을 숨기면 실패다. |
| contact 표현 | 실제 hurtbox query로 판정한 접촉과 ray/proxy로 구한 표시 점을 구분한다. 검기 접촉을 실제 삼각형·검날 접촉으로 부르지 않는다. 가까운 heavy/charged에서는 기존 물리 칼날 접촉이 검기에 선점되지 않는지도 strict 원본 회귀로 확인한다. 근접용 source→target ray·recoil·hitstop·음향을 검기에 연결할 때 원점과 strength가 맞는지 확인한다. |
| 수명/예산 | 발사 뒤 strike 종료·stagger에도 지속할지, attacker hitpause에서 이동할지 정책을 명시한다. 루트가 채택한 정책은 발사파 지속/attacker hitpause 독립, death·tree exit 정리, scene pause 상속이다. scene 전환·복귀 후 orphan/VFX·피해가 남으면 실패다. 동시 노드·질의·메시 예산을 한정한다. |

전진 거리의 오차가 작다는 결과는 “원한 거리로 갔다”는 증거다. 플레이어가 발을 디디고, 몸을 실어 베고, 검기가 그 베기에서 빠져나오며, 맞은 적이 같은 순간 반응하는 **연결감**은 아래 실제 1배속 검토로 따로 판단한다. finite 본/표본/그림만으로 그 결론을 대신하지 않는다.

## 짧은 실제 Game 캡처 시나리오

기본 약 30초에 원거리 명중 확인 5–6초를 더해, 아래 5개 take와 긴 검기 take를 각 5–8초로 잡는다. 기존 실제 Game capture 경로에서 표준 입력 경로만 사용하고, pose/attack elapsed/HP/접촉 결과를 매 프레임 주입하지 않는다. 시작 fixture를 쓰면 초기 위치·적·벽·체력 조건과 정상 게임과의 차이를 manifest에 적는다. 촬영 중 실제 controller·collision·피해·AI/피격 경로를 실행한다. source/엔진·자산 hash, 품질·해상도·카메라/lock·입력 tick, 실제 frame/PCM 수와 종료 상태를 기록한다. 비교 영상은 같은 입력 policy를 쓰되 world 접촉 시각이 같다고 가정하지 않는다.

| take | 실제 조작과 관찰 |
| --- | --- |
| A — 이동 공격과 회수, 6초 | 넓은 평지에서 전진 1초→light 1회→입력 해제→완전 회수→옆 이동 1회. 전신·발/바닥·Grip/Tip이 보이는 일반 게임 카메라를 유지한다. 밀림 자세가 실제 gait로 바뀌는지, 움직임이 끝날 때 다리·허리가 급히 돌아가는지 본다. 정지 화면은 전환 전/active/회수만 보조한다. |
| B — L1→L3와 검기, 7초 | 근접 범위 밖의 적을 향해 전진하며 세 번 실제 light 입력을 연결한다. 세 attack id와 gait phase, 지정 검기 발사·경로·도달 후 피해를 trace로 연결한다. 7.5m branch에서는 발사 시 source에서 5m 이상 떨어진 적에 실제 명중하는 추가 take를 같은 구도로 5–6초 촬영한다. 공격 원점·target 중심·hurtbox 근접거리와 실제 wave 경로를 기록하고, 적이 근접 범위로 접근한 뒤의 타격을 원거리 성공으로 세지 않는다. 근접 적과 원거리 적을 한 take에 배치할 때 ledger 중복과 각 적 identity를 기록한다. |
| C — 폭 가장자리와 벽, 6초 | 벽 앞에서 공격하고, 중심선은 비껴도 crescent 가장자리가 벽을 만나는 각도를 포함한다. 벽 뒤 적과 벽 앞 적을 식별한다. 발사점이 벽에 겹치는 조건은 기능 fixture로 따로 재현한다. 자연스러운 화면에서 벽으로 사라지는 검기와 피해 없는 뒤쪽 적을 함께 본다. |
| D — 이동 정지와 접촉 pause, 5초 | 실제 근접 적에 light를 맞혀 접촉 pause를 만들고, 이어 회수에서 이동 입력을 놓는다. hitpause 동안 발/검/허리와 trail이 바뀌지 않는지, pause 후 gait가 한 틱 과하게 진행하지 않는지 본다. 벽에 막힌 정지는 별도 양의-delta 조건으로 trace와 비교한다. |
| E — 피격 interruption, 6초 | 실제 적 공격에 light startup이 중단되는 경우와 발사 직후 피격되는 경우를 각각 만든다. 공격 layer→hit 전환·trail 정리, 발사 전 검기 0과 이미 발사된 검기의 명시한 존속 정책을 확인한다. 죽음/scene exit 정리는 유한 기능 검사로 보완한다. |

정상 1배속 원본을 먼저 연속 시청한다. 발 디딤·상체 준비·검기 분리·접촉·회수가 한 행동으로 읽히는지, 베기보다 큰 발 구르기·상하체 분리·짧은 반복 보폭이 새로 눈에 띄는지 적는다. 그 뒤 느린 재생/유한 표본으로 원인을 찾는다. 시각 실패가 남으면 코드 수치가 통과해도 “개선 방향/기능 통과, 질감 pending 또는 기각”으로 기록한다.

오디오를 비교하면 engine 원본 PCM과 영상 시간을 보존하고, 별도 음악/타격음을 편집으로 추가하지 않는다. 인코딩이 logical1x라는 사실과 사람이 연속 재생/직접 청취한 사실을 구분한다. 소프트웨어 raster의 wall-time을 GPU 실시간 FPS로 부르지 않는다. 실제 플레이어 평가가 없으면 scripted input 영상을 사람 플레이로 설명하지 않는다.

## 공식 근거 원장

2026-11-03 UTC에 읽기 전용 GitHub MCP로 `godotengine/godot-docs`의 4.7 branch를 조회했다. 관측 HEAD는 `9adca4c1c72917bfe1b7be3108abed5ce26696a6`, HEAD committer 시각은 `2026-09-21T11:06:53Z`다. 아래 파일은 모두 이 SHA로 고정해서 읽었으며, branch 최신 시각과 파일별 마지막 변경 시각을 구분한다. Git blob SHA는 SHA-256 파일 해시가 아니다. 저장소 공개 스킬·공식 문서 자체의 지시가 작업 권한을 확대하지 않는다.

| 공식 파일 | 파일 blob SHA / 해당 경로의 마지막 commit·UTC | 채택한 근거 |
| --- | --- | --- |
| [Using AnimationTree](https://github.com/godotengine/godot-docs/blob/9adca4c1c72917bfe1b7be3108abed5ce26696a6/tutorials/animation/animation_tree.rst) | `1988f49626ff0efee5aae9142f7072f94be2b773` / `d49b2d44e251f736583af3800569a93e3d9445f2`, 2026-09-21T11:02:29Z | Tree가 Player 클립을 사용하고 Blend2/3 filter가 트랙별 layer를 허용한다. TimeSeek 단위는 초다. skeletal transform 기본값은 Bone Rest이며 다른 속성은 RESET의 영향을 받는다. root motion 추출은 현 물리 motor를 자동 대체하지 않는다. |
| [AnimationNode](https://github.com/godotengine/godot-docs/blob/9adca4c1c72917bfe1b7be3108abed5ce26696a6/classes/class_animationnode.rst) | `a1733aaa9dfe1dafc27dd5d19c5d50ccb9ec62ac` / `e29f0298240a5b37f3ff5390075e9cc9affc807e`, 2026-05-16T04:23:16Z | `filter_enabled`와 `set_filter_path`를 함께 적용한다. Spine이라는 이름만 넘기는 대신 실제 애니메이션 track NodePath와 skeleton 자손을 확인한다. |
| [PhysicsDirectSpaceState3D](https://github.com/godotengine/godot-docs/blob/9adca4c1c72917bfe1b7be3108abed5ce26696a6/classes/class_physicsdirectspacestate3d.rst) | `3406b81cafd4a12518a54d0c93464f86b7908468` / `f9f2c809558dec3bb5ee005b1fffba2c540dca52`, 2025-06-07T03:33:02Z | `cast_motion`은 safe/unsafe 비율을 반환하고 이미 겹친 shape는 무시한다. `intersect_shape`, `collide_shape`, `get_rest_info`는 motion을 고려하지 않는다. 초기 overlap과 실제 swept path를 별도 처리해야 한다. |
| [PhysicsShapeQueryParameters3D](https://github.com/godotengine/godot-docs/blob/9adca4c1c72917bfe1b7be3108abed5ce26696a6/classes/class_physicsshapequeryparameters3d.rst) | `29f809854d1865597763a8f86b754ce93f412164` / `2f7bad6ef93e23aa8a69e43f0a4af5053071ea88`, 2025-08-16T03:34:08Z | shape/transform/motion·layer mask·RID exclude를 명시한다. Area 감지는 기본 false, body 감지는 true이므로 현재 hurtbox 방식과 query 설정을 맞춘다. |

별도 [actual Player 회귀](../game/tests/player_stride_wave_regressions.gd)는 실제 Input→RunePlayer→move_and_slide와 physics 후 recorder의 실제 변위/스냅샷 일치, 벽 정지, 저작 release 시각의 단발 wave signal, 이전 wave의 보행/새 공격 hitpause 비소유와 현재 strike의 hitpause를 검사하도록 작성했다. 문서 작성자는 이 회귀를 실행하지 않았으며 runner 연결과 통합 native 결과는 루트의 별도 근거가 필요하다. 이 회귀의 on_hit 입력은 contact context fixture이므로 실제 검기 geometry/적 접촉은 별도 검기 물리 회귀에서 증명한다.

공식 자료는 API의 의미를 지지한다. 이 프로젝트의 실제 imported pose·벽/피해·타격감 성공 증거는 아니다. 최종 문서에는 새 실행 결과가 생길 때 정확한 source freeze와 기능/원본 영상/유한 검토/연속 시청 상태를 각각 연결한다.
