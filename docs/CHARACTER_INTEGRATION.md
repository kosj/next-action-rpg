# 캐릭터 스켈레톤 프리뷰 계약

확인일: **2026-10-31**. 목표는 실제 리라·근접 수호병 메시를 현재 게임 시간에 맞춰 움직이는 웹 프리뷰입니다. 최종 AAA 캐릭터, 모션 캡처 품질, 전체 적/보스 교체나 목표 기기 60fps 달성을 뜻하지 않습니다. 정적 소품의 기존 반입 결과는 [아트 배치 기록](ART_BATCH_2026_10_31.md), 전체 검수 단계는 [대표 아트 구간](ART_SLICE.md)을 따릅니다.

v0.1.5에는 [국소 눈 소켓·곡면 안구와 검 잔상](CHARACTER_POLISH.md)을 추가했습니다. [최종 native 근거](validation/v0.1.5/character-eyes.json)는 통합345개·실패0, 독립 좌표·색상·Head 부착을 확인합니다. 아래의 v0.1.4 검증 수치·이력은 당시 범위로 보존하며 현재 Web·공개 배포의 실행 근거로 대신하지 않습니다.

## 입력과 현재 증거

| 대상 | 확인한 입력·상태 | 검증 범위와 남은 조건 |
|---|---|---|
| 리라 runtime | [lyra_gameplay.glb](../game/assets/models/production/lyra_gameplay.glb), [저작 recipe](../art_source/production/character_actions/lyra.json). 몸체32,288삼각형·19,438,644바이트와 안구3,840삼각형·112,488바이트. 53본·스킨1·19상태+RESET | 실제 hero profile에 설치. 독립 Godot 반입·포즈·무기·시간 검증 통과. 최종 얼굴/손·의상 변형·교차 전환과 타격감은 후속 아트 검수 |
| 일반 melee 수호병 runtime | [sentinel_gameplay.glb](../game/assets/models/production/sentinel_gameplay.glb), [저작 recipe](../art_source/production/character_actions/sentinel.json). 22,000삼각형·53본·스킨1·9상태+RESET, 17,146,728바이트 | 실제 일반 melee profile에 설치. ranged·shield·elite·boss는 기존 표현을 사용하며 이 프리뷰 승인을 상속하지 않음 |
| 보존한 제작 입력 | [리라 웹 원본](../art_source/production/candidates/lyra-web-001/manifest.json), [수호병 웹 정규화 후보](../art_source/production/candidates/sentinel-web-001/manifest.json). 리라1.82m·수호병1.95m의 rest skeleton·메시·웨이트를 입력으로 재사용 | 개발용 stock 라이브러리와 raw timestamp 문제는 원본 기록대로 보존. runtime은 source actions를 삭제하고 새 프로젝트 키만 저작함 |
| 게임 표현·검증 | [ActorVisual](../game/scripts/actors/actor_visual.gd), [ProductionCharacterArt](../game/scripts/actors/production_character_art.gd), [SkeletalVisualBridge](../game/scripts/actors/skeletal_visual_bridge.gd), [실제 모델 검사](../game/tests/production_character_regressions.gd) | v0.1.5 실제 데이터로 통합345개·실패0. 눈·블레이드의 전용 회귀를 포함하며, 정상 Web 입력·저장·공개 주소 및 Windows 실행은 각각의 검증 기록을 참조 |

runtime 모션은 [author_character_actions.py](../tools/author_character_actions.py)와 [character_gait.py](../tools/character_gait.py)의 순수 프로젝트 저작 Bpy 키입니다. 기존 stock FCurve·샘플 수치 포즈를 복사하거나 긴 stock slash를 단순 재명명/압축하지 않았습니다. 원본의 중복 timestamp와 Blender 해석 파생의 승인 범위도 그대로 구분합니다.

현재 runtime GLB SHA-256은 리라 몸체 `4cc9ae5b9340263b824d549ad59a7955705c927859bf35949d66984cd647ed0c`, 안구 `d7d984fb10637be102a740e91e89316580b33c53d4b6a2cd1055108675ef3ef4`, 수호병 `214bab372dfce2552b1f97fd2fd88a160fa593cb2450c6ffbc66c1547974e721`입니다. 원본 리라 A89는 별도 보존하고 현재 파생은 [눈 소켓 manifest](../art_source/production/candidates/lyra-eye-sockets-001/manifest.json)와 대조합니다. v0.1.4 제작 입력과 사본 해시는 [리라 gameplay manifest](../art_source/production/candidates/lyra-gameplay-001/manifest.json)·[수호병 gameplay manifest](../art_source/production/candidates/sentinel-gameplay-001/manifest.json)와 대조합니다. 초기 데이터 revision에서는 별도 실제 모델41개와 fresh 로컬 Web294.774초 검사(오류0)가 통과했고, 이후 charge 종료·손 그립 데이터를 보정한 최신 파일로 통합268개를 다시 통과했습니다. 최신 파일의 [독립43개·통합268개 검사와 내보내기 근거](validation/v0.1.4/README.md)를 보관합니다. 최신 Web·공개 CI 결과를 초기 revision 결과로 대신하지 않습니다.

## 공식 API와 최신 공개 스킬 재검증

엔진 기준은 [toolchain.json](../tools/toolchain.json)의 **Godot 4.7.2**입니다. 2026-10-31에 GitHub 연결 도구로 공식 `4.7.2-stable` 소스와 4.7 문서를 직접 대조했습니다.

| 근거 | 구현에 적용하는 규칙 |
|---|---|
| [BoneAttachment3D 클래스](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/BoneAttachment3D.xml), [실제 갱신 소스](https://github.com/godotengine/godot/blob/4.7.2-stable/scene/3d/bone_attachment_3d.cpp#L302) | Skeleton3D 자식에 실제 `RightHand` 본을 지정하고 `override_pose=false`로 사용. attachment 변환은 갱신 때 본 포즈로 덮어쓰므로 그립 보정은 자식 `WeaponGrip`에 둠 |
| [Skeleton3D pose API](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/Skeleton3D.xml#L80), [lazy pose 갱신](https://github.com/godotengine/godot/blob/4.7.2-stable/scene/3d/skeleton_3d.cpp#L569), [최종 신호 순서](https://github.com/godotengine/godot/blob/4.7.2-stable/scene/3d/skeleton_3d.cpp#L350) | `get_bone_global_pose()`는 Skeleton 기준이며 world 좌표가 아님. dirty 본은 조회 시 계산하지만 최종 modifier/skin 처리는 별도. 자동 `skeleton_updated`를 수동 Tree 샘플과 같은 시점이라고 가정하지 않음 |
| [AnimationMixer 수동 모드](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/AnimationMixer.xml#L379), [TimeSeek 계약](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/AnimationNodeTimeSeek.xml), [seek 구현](https://github.com/godotengine/godot/blob/4.7.2-stable/scene/animation/animation_blend_tree.cpp#L1084) | `callback_mode_process=ANIMATION_CALLBACK_MODE_PROCESS_MANUAL`, `seek_request=절대 초`, `advance(0.0)`으로 실제 게임 elapsed를 샘플. seek 요청은 처리 후 -1로 돌아가므로 매번 명시 |
| [AnimationTree 재생 소유권](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/AnimationTree.xml#L7) | AnimationPlayer는 클립 저장소. 동일 트랙을 Player 자동 재생과 Tree로 동시에 구동하지 않음 |
| [Humanoid 공식 리타겟 규칙](https://github.com/godotengine/godot-docs/blob/4.7/tutorials/assets_pipeline/retargeting_3d_skeletons.rst#L114), [프로필](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/SkeletonProfileHumanoid.xml) | T-pose·오른손 Y-up·+Z 전방과 실제 bone rest/map을 확인. 게임 -Z 전방으로 가는 wrapper 회전은 한 번만 적용. 프로필 56본을 실제 후보가 반드시 56본이어야 한다는 조건으로 오해하지 않음 |
| [Animation loop·marker API](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/Animation.xml#L37) | runtime 복제 Animation에서 루프/검수 marker를 설정. marker는 피해·이동을 실행하는 method track이 아님 |

modifier가 없는 현재 프리뷰에서는 수동 Tree 샘플 뒤 `BoneAttachment3D.on_skeleton_update()`를 호출하고 **그 프레임의 본·그립·칼끝 world 변환**을 비교합니다. 향후 IK나 SkeletonModifier3D를 추가하면 `skeleton_updated`/`modification_processed` 이후 최종 포즈를 검증합니다. deprecated `force_update_all_bone_transforms()`는 공식 문서가 내부용으로 명시하므로 새 동기화 수단으로 도입하지 않습니다.

공개 스킬도 같은 날 upstream과 고정본을 비교했습니다.

| 공개 스킬 | 최신 확인과 채택 범위 |
|---|---|
| [godot-animation](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/blob/a873f517e5a0f3a2bf5b2414688e811c783b042c/skills/godot/godot-animation/SKILL.md) | 마지막 파일 변경 `a873f517e5a0f3a2bf5b2414688e811c783b042c`(2026-10-24), Apache-2.0. 현재 upstream과 보관본의 본문 및 `references/animation-tree-and-tween.md`가 동일. Player/Tree 분리·파라미터 검수 적용 |
| [scenario-godot-animation](https://github.com/scenario-labs/skills/blob/b8544b9c86e0685844cc6effbb27f3885f744d3a/skills/game-engines/godot/scenario-godot-animation/SKILL.md) | 최신 파일 변경도 기존 고정 `b8544b9c86e0685844cc6effbb27f3885f744d3a`(2026-10-29), MIT이며 본문 동일. controller 소유권·RESET/track 감사·고정 시각 포즈·발 미끄러짐 검수만 선택 적용 |

의미 있는 원문 갱신이 없어 vendored 스킬·라이선스·NOTICE는 변경하지 않습니다. Scenario 전용 MCP/키트 설치, Jolt/Forward+ 전환, method-track 피해 판정, 외부 macOS 성능 수치는 채택하지 않습니다. 이 프로젝트의 웹 Compatibility·GodotPhysics·코드 주도 이동을 유지합니다.

## 상태·시간 수락 기준

현재 [player](../game/scripts/actors/player.gd), [enemy](../game/scripts/actors/enemy.gd), [CombatStrike](../game/scripts/core/strike.gd), [공격 데이터](../game/data/light_1.tres)가 게임 상태와 시간을 소유합니다. 시각 계층은 새 스칼라 snapshot을 읽고 전투 객체·CharacterBody3D·HP·자원을 수정하지 않습니다. 초가 원본이며 60fps 정수 프레임 반올림으로 판정 경계를 바꾸지 않습니다.

| hero 상태 | 실제 시간·입력 | 프리뷰 수락 기준 |
|---|---|---|
| idle | 행동 없는 정지 상태, 표현 locomotion clock | 제자리 cycle·발 접지·같은 포즈의 루프 이음새. stock 원본을 승인 없이 재명명하지 않음 |
| walk / run | 실제 수평 속도 6.4 / 8.5m/s | 측정 속도비로 cycle 샘플. 관절 실루엣·보폭·발 미끄러짐을 플레이 카메라로 확인 |
| walk_back / walk_left / walk_right | velocity를 controller facing 기준 local 방향으로 변환 | 잠금 중 측면/후방을 forward sprint로 오표시하지 않음. 현 프리뷰는 가까운 cardinal 축 선택, 정확한 대각 동률은 전/후방 우선. 측/후방 sprint는 방향 cycle에 실제 속도비를 적용 |
| dodge: 전/후/좌/우·대각 | elapsed 0…0.32초, 이동 17m/s·무적 0.29초·쿨다운 0.48초 | 현 범위는 단일 저작 dodge와 실제 local 회피 방향의 **시각 yaw** 조합. 네 개 전용 클립 완료로 표시하지 않음. controller facing·이동 벡터·락온을 변경하지 않고 종료/취소 시 yaw 복원 |
| light_1 | 준비 0.13 / 판정 0.17 / 회복 0.22 = 0.52초 | 접촉 표현은 [0.13, 0.30), arc 130도·기존 sweep 부호와 일치 |
| light_2 | 0.13 / 0.17 / 0.22 = 0.52초 | [0.13, 0.30), arc 150도·lunge 4.5m/s. 임의의 반대 방향 베기로 교체하지 않음 |
| light_3 | 0.18 / 0.22 / 0.30 = 0.70초 | [0.18, 0.40), reach 3.1m. 수직 연출도 기존 수평 sweep 진행과 타격 시점을 보존 |
| parry | 실제 창 최대 0.22초·쿨다운 0.65초 | 성공 시 controller가 즉시 창을 닫음. 성공 후 무적 0.4초와 별개이며 클립이 창을 연장하지 않음 |
| hit | 실제 stagger 0.15초, 피격 무적 0.70초 | 공격 취소 후 hit elapsed를 따라가고 무적이 끝날 때까지 캐릭터를 고정하지 않음 |
| heavy | 0.32 / 0.22 / 0.32 = 0.86초 | 판정 [0.32, 0.54), arc 170도·reach 3.3m. 차지와 일반 강공격의 피해는 controller가 결정 |
| charge | 실제 heavy hold elapsed / 임계 0.65초 | 정지 hold에서 상한 포즈 유지, release/cancel 즉시 해제. 이동 시 locomotion 우선. 임계 이후 release 배율 1.65를 시각 계층에서 재계산하거나 중복 적용하지 않음 |
| skill_1 | 0.16 / 0.35 / 0.28 = 0.79초 | [0.16, 0.51), reach 4.5m·arc 160도·lunge 13m/s. 코드 invulnerability 0.3초 보존 |
| skill_2 | 동일 0.79초 | 별도 `skill_2` 표현, reach 5.5m·arc 360도·lunge 0·무적 0.3초 보존 |
| skill_3 | 동일 0.79초 | 별도 `skill_3` 표현, reach 7.0m·arc 360도·lunge 0·무적 0.65초 보존 |
| death | controller `death_elapsed`, 새 생명은 `presentation_epoch` 변경 | 단발 뒤 마지막 포즈 유지. 기존 1.3초 후 사망 UI와 충돌/보상 조건을 변경하지 않음. retry/restore에서 이전 포즈·시간·yaw가 남지 않음 |
| heal | HP/포션은 입력 즉시 처리, 표현 gesture 0.35초 | HP 지연·추가 소모·이동 잠금 없음. 정지 gesture만 사용하고 이동/공격/회피/패링/피격/차지 우선. 취소해도 회복을 되돌리거나 중복 지급하지 않음 |

`AttackData.reach`는 원점 기준의 넉넉한 게임 판정이며 물리적 검 길이가 아닙니다. 리라 검을 2.7m로 늘려 간극을 숨기지 않습니다. 세 약공격은 모두 기존 `-arc/2 → +arc/2` sweep을 따릅니다. 피격 VFX·음향은 실제 `landed_hit`에 반응하며 검수 marker마다 무조건 재생하지 않습니다.

hit pause 0.035초에는 공격 elapsed와 이동 처리가 정지하지만 현 controller의 회피·패링·경직 타이머는 early return 전에 감소합니다. 모든 상태의 시간이 동일하게 멎는다고 가정하지 않고 **그 프레임 snapshot 값**을 재생 권한으로 사용합니다. UI 입력 guard와 retry/restore도 같은 원칙을 적용합니다. 동일 상태의 재시작·취소·새 생명에서 과거 이벤트가 재실행되지 않도록 elapsed 초기화와 epoch를 검증합니다.

근접 수호병 프리뷰는 일반 melee의 idle/walk/run·walk_back/left/right·`enemy_attack`·hit·death의 9상태와 RESET을 대상으로 합니다. 적끼리의 separation 이동도 facing과 다를 수 있어 세 방향 cycle을 포함합니다. 일반 접근 속도 3.6m/s, 공격 0.7/0.2/0.6 = 1.5초와 실제 interrupt duration을 사용합니다. 패링/poise 중단 1.4초를 단순한 피격 0.28초로 축소하지 않습니다. ranged·elite·boss·burst는 이 라이브러리 합격에 포함하지 않으며 적합한 모션이 없으면 기존 표현으로 명시적으로 복구합니다.

## 클립·그립·리소스 계약

- source와 파생 GLB는 출처·SHA·저작 recipe로 구분합니다. runtime은 필요한 gameplay 라이브러리만 사용하며 stock 검수 자료를 기본 전투 클립으로 자동 승인하지 않습니다.
- source AnimationLibrary를 공유한 채 변경하지 않습니다. runtime용 Animation을 깊은 복제한 뒤 검수된 cycle만 `LOOP_LINEAR`, action과 RESET은 `LOOP_NONE`으로 설정합니다. 준비한 불변 클립을 공유할 수 있으나 원본 해시·loop mode와 서로 다른 두 actor의 재생 파라미터 독립성을 확인합니다.
- action의 `startup_end`·`active_end`·`recovery_end` 같은 marker는 실제 코드 초에서 정의한 검수 메타데이터입니다. Blender/glTF 보관 방식과 Godot runtime marker를 구분해 provenance에 남깁니다. property/method/audio/게임플레이 객체 트랙은 bridge가 거부합니다.
- 모든 본 트랙은 실제 skeleton 안에서 해석되어야 합니다. BoneMap은 실제 53본 이름과 Humanoid 역할을 대조하고 존재하지 않는 본을 임의 생성하지 않습니다. 스킨 bind·정규화 weights·RESET·rest 일치도 별도로 검사합니다.
- 리라 몸체 1.82m·수호병 1.95m와 바닥 0은 proper skinning된 REST bounds로 확인합니다. raw Mesh AABB에 wrapper scale을 다시 곱한 값으로 스킨 키를 판정하지 않습니다.
- 정규화 wrapper scale은 리라 약1.8189517·수호병 약1.9514694입니다. rigid 검의 attachment에서 수입 리그 scale만 역수로 보정하고 actor 자체 의도 scale은 유지합니다. canonical `GripOrigin=0`, 칼끝 +Y 1.19m·전체 높이 1.35m를 actor unit scale의 world에서도 검사하고 의도적인 actor scale에는 같은 비율로 변하는지 확인합니다. 기존 prototype 검의 Z=PI 보정을 새 손 socket에 중복 적용하지 않습니다.
- [그립 설정](../game/data/character_grips.json)은 실제 오른손 rest/world basis에 맞춥니다. 리라는 손 본 기준 offset `(0.055, 0.10, -0.06)m`, 수호병은 신장비 `1.95/1.82`를 곱한 물리 offset을 사용합니다. 같은 프레임 socket 갱신과 1.19m grip→tip·1.35m 총길이, actor1.25배 scale 보존을 실제 Godot 검사에서 확인했습니다. 손가락의 최종 해부학적 접촉 승인은 별도입니다.
- 실제 오른손 rest/world basis에서 그립을 보정합니다. idle·준비·접촉·회복·회피·패링·사망 표본에서 palm 접촉, 날 방향, 왼손/팔/머리/의상 관통과 같은 프레임 socket 추종을 검수합니다. 리그 실패/누락 상태에는 메시와 검을 함께 기존 피벗 표현으로 복구합니다.

## 접지·스킨·그립의 실제 확인 범위

별도 Blender100Hz gait 검사는 authored leg IK를 실제 목표 속도로 전진시킨 조건에서 reach clamp0·loop endpoint bone matrix 오차≤3e-7·표본 stance drift≤약1.08mm·바닥오차≤약0.93mm를 기록했습니다. 최신 [리라 authoring 보고서](../art_source/production/candidates/lyra-gameplay-001/authoring.json)·[수호병 authoring 보고서](../art_source/production/candidates/sentinel-gameplay-001/authoring.json)에 포함된 이동 cycle10개의 저작 단계 검사도 reach clamp0·endpoint≤3e-7·drift≤약1.08mm·바닥오차≤약0.741mm를 확인합니다. 둘 다100Hz에서 선택한 강한 foot-weight sole vertex의 수치이며, 최종 GPU 변형의 모든 프레임·의상/자기 관통·교차 상태 전환이나 목표 기기 FPS를 승인한 결과가 아닙니다.

최신 source_md5 재반입 대조를 마친 독립43개 검사는 53본/skin binds·필수 상태·Skin CPU REST bounds·수동 포즈 직후 같은 프레임 손 socket·검 길이·3연격 active sweep 방향·발 본 변화·hit pause·복귀와 게임 상태 불변을 확인합니다. charge 끝이 idle 몸/검으로 돌아가던 이전 파일은 추가 검사에서1개 실패했고, 수정한 최신 파일은 골반45.329mm·검그립44.671mm의 장전 변위를 유지하며1.3초 hold가0.65초와 같음을 확인했습니다. [실패 관찰](validation/v0.1.4/production-charge-before-fix.json)·[최종 결과](validation/v0.1.4/production-summary.json)를 구분합니다. 원본32k 후보의 손 socket33표본 감사와 새 runtime의 실제 모델 검사를 혼동하지 않습니다. Production profile에는 아래의 짧은 포즈 전환을 추가했습니다. 공격·회피·경직의 게임 시간은 그대로 유지합니다.

source 모델의 발바닥0과 실제 CharacterBody3D의 capsule bottom은 별도 좌표입니다. 현재 hero capsule은 중심0.95m·높이1.85m여서 바닥이 actor 원점보다0.025m 위에 있습니다. 시각 자식에만 이0.025m를 더하고 수호병은0m를 사용합니다. collider 크기·체력·피해·이동 권한을 변경하지 않고 ground pose를 맞춥니다.

## 사용 조건의 확인 범위

VARCO [2026-10-12 공식 라이선스 변경](https://3d.varco.ai/docs/release-notes/2026-10-12-choose-a-license-when-you-generate)은 Private 자산의 상업 사용을 허용하고, 자신의 Private 자산에서 만든 파생도 Private로 유지한다고 명시합니다. 이번 몸체 후보의 생성 당시 Private 기록과 연결합니다. 0포인트인 리깅/Animate 비용 자체를 권리 근거로 사용하지 않습니다.

공식 [2026-10-07 Looping 설명](https://3d.varco.ai/docs/release-notes/2026-10-07-looping-animations-ready-to-use)은 게임의 반복 모션 용도를, [2026-06-05 Unity 가이드](https://3d.varco.ai/docs/blog/2026-06-05-how-to-apply-varco-3d-fbx-animations-in-unity)는 animated FBX의 외부 엔진 반입을 설명합니다. 다만 stock motion 원본의 독립 재배포·공개 소스 라이브러리 권리를 별도로 명시하지는 않습니다. 공식 footer의 [Terms of Use](https://terms.varco.ai/2b90435c2d75805db85ec940a235c933)(Updated 2026-04-22)에는 기본 비상업/내부 이용 제한과 별도 Pricing·구매 license 예외가 함께 있으므로 제품별 최신 Private 정책과 stock 라이브러리 원본 권리를 동일시하지 않습니다.

확인된 결론은 **Private 생성 자산·그 파생의 일반 상업 사용 근거가 존재한다**는 것입니다. stock motion 자체의 standalone/source 재배포 허락은 이번 공개 자료에서 명문 확인하지 못했습니다. 이에 v0.1.4 runtime 모션은 locomotion을 포함해 프로젝트 Bpy에서 새로 저작하는 방향으로 정했습니다. recipe와 clip provenance로 구분하며, stock 후보 보관 상태를 프로젝트 저작으로 바꾸지 않습니다. 이 구분은 기존 자산 생성 권한 안에서 구현을 계속하기 위한 범위 기록입니다.

## 실행·시각·성능 게이트

1. **구조·출처:** 캐시 없는 Godot 4.7.2 반입, GLB skin/bind/weights/bone/clip 검사, 원본 SHA 불변, runtime loop/marker·트랙 whitelist·BoneMap을 확인합니다. 누락/불량 리그의 기존 피벗 복구도 실제로 실행합니다.
2. **실제 시간:** 합성 clip 존재 검사와 별개로 실제 hero/sentinel scene에서 시작·판정 직전/직후·회복 끝을 샘플링합니다. hit pause·패링 성공/실패·중도 취소·death→restore·UI resume를 비교하고 snapshot을 읽기만 했는지 확인합니다. 무적·판정·HP·자원·문 진행의 기존 회귀를 유지합니다.
3. **실제 메시·검:** Godot skinning된 키/접지와 같은 프레임 RightHand/그립/칼끝 world 관계를 확인합니다. 정면·측면·후면, 손 근접, 현행 플레이 카메라의 이동·3연격·강공격·차지·세 스킬·회피 각 방향·패링·피격·사망·회복을 캡처합니다. 자동 검사 통과와 사람이 본 변형/타격감 승인은 분리합니다.
4. **웹 실행:** GitHub Pages에서 내려받은 동일 빌드의 fresh load·실제 skeletal 표시·quality 0/1 전환·실행 오류·리그 복구를 확인합니다. 브라우저 smoke는 양성 증거가 있는 상태만 합격으로 기록하며 입력을 넣지 않은 모션의 시각 승인을 대신하지 않습니다.
5. **배포 용량:** [build.py](../tools/build.py)의 웹 파일 원시 크기 합계 **150,000,000바이트 이하**를 지킵니다. ZIP 크기나 전송 압축 크기가 기준이 아닙니다. 제작 원본·stock 리뷰 라이브러리는 게임 패키지 밖에 두고 실제 필요한 runtime GLB만 포함합니다.
6. **품질·성능:** 웹 Compatibility 720p·Windows 1080p의 같은 대표 교전을 목표 GPU에서 측정합니다. 목표 60fps/약 16.7ms이며 결과가 아닙니다. frame time·draw calls·메모리·첫 load/셰이더 준비·스킨 관절/LOD/재질을 각각 기록합니다. 소프트웨어 WebGL의 프레임 수나 삼각형 예산 충족만으로 성능을 승인하지 않습니다.

후속 상태를 `verified`로 올릴 때는 파일·SHA·실제 검사 보고서·환경·검수 범위를 함께 갱신합니다. 전체 모션의 교차 전환, 정교한 손가락/얼굴, 머리·천 물리, 보스·나머지 적, 목표 GPU 성능과 최종 아트 방향 승인은 이 프리뷰 이후에도 별도로 남을 수 있습니다.


## AAA 요구에 따른 후속 검토 · 현재 판본

최종 승인 조건은 [AAA 아트 기준](AAA_ART_QUALITY.md)입니다. 첫 방은 [CC0 PBR 원본·반입 기록](../art_source/production/courtyard_materials/README.md)의 바닥·사암·토양, sky 반사와 키/필 조명, 주변 석재와 배경 아치를 사용합니다. [고정 카메라 장면 검사](validation/v0.1.4/courtyard/README.md)에서 실제 Web 화면을 확인했고 기존178개 충돌체와 공유 RNG 상태가 그대로임을 대조했습니다. 큰 아치의 단순한 형태·마모 부족, 먼 방의 블록아웃과 캐릭터 세부는 남은 결함입니다.

Production 전용 `enable_transition_polish()`는 Tree가 실제 elapsed의 목표 포즈를 샘플한 뒤 최대80ms 동안 Skeleton 로컬 포즈를 보간합니다. 방향·속도 변경에서 이동 cycle의 정규화 phase를 보존하고 idle clock을 분리합니다. hit/dodge/parry/death는 즉시 전환하며 공격 블렌드는 남은 startup 안에서 끝나 active에는 원래 목표 포즈와 검 방향을 정확히 사용합니다. hit pause의 delta0은 전환과 phase를 멈추고 epoch 변경은 과거 이력을 비웁니다. 수동 포즈 뒤의 손 socket은 최종 표시 본을 같은 프레임에 따릅니다.

[실제 모델 집중 검사](validation/v0.1.4/transition-polish-runtime.log)는27개·실패0입니다. [측정](validation/v0.1.4/transition-polish.json)의60Hz 첫 전환 프레임에서 Hips·양발·RightHand·BladeTip 중 최대 위치 변화는 시작264→33mm, 정지700→81mm, 방향830→96mm, walk→run307→19mm였습니다. 특정 시나리오의 포즈 튐을 줄인 결과이며 runtime foot IK·발 stance 재고정·속도 연속성·최종 접촉 품질의 합격은 아닙니다.

로컬 pose 후처리에는 다음 Tree 표본이 모든 본 채널을 다시 써야 합니다. Godot 기본 `animation/remove_immutable_tracks=true`가 원본159채널을55트랙으로 줄여 Root 전체와 RightHand position/scale을 없애는 것을 [진단](validation/v0.1.4/transition-import-diagnostic.log)했습니다. 두 runtime `.glb.import`에 해당 옵션을false로 고정하고 재반입했으며, opt-in의 완전한 position/rotation/scale 조건을 유지했습니다. 희소한 합성 리그의 기본 API는 즉시 샘플 계약을 유지합니다.

전체 저작 timestamp와 인접 midpoint의 [변형 검사](../art_source/production/character_actions/deformation_review/README.md)는 리라2,358표본·수호병1,608표본을 평가했습니다. 리라 heavy0.63초의5.820→27.414mm edge와 수호병 enemy_attack0.68초의6.180→44.226mm edge 등 실제 불량을 찾았습니다. 자동 웨이트 보정은 다른 경계를 최대22.635/49.450mm 더 늘려 **모두 불합격** 처리했습니다. 원본/게임GLB의 A89/214 SHA는 유지하며 결함 좌표·본·동일 카메라 전후 렌더와 실패 recipe를 보존합니다. 손·얼굴의 생성 형상, 명확한 갑옷/의상 소유 영역과 수작업 웨이트/메시 분리, 공격 발디딤·머리/천·최종 표면과 실기기 성능이 최종 AAA 승인까지 남습니다.
