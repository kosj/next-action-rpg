# 완충 강타 접촉·모션·피드백 제작 단위

기록일: **2026-10-31 UTC**. v0.1.8의 완충 강타·일반 근접 수호병 강피격 **기능 프로토타입**이다. [로컬 검증 자료](validation/v0.1.8/README.md)는 native **439개·실패0**, Python **51개·실패0**, 실제 모바일 집중 검사 **282.938초·오류0**, Web 원본 **146,279,323B/150MB** 예산과 Windows 내보내기·ZIP 검증의 통과 범위를 기록한다. 손잡이 접촉과 recoil 초과로 기각한 이전 통과·실패는 아래에 보존했다. 이번 근거는 source HEAD `b6af5a5118bd3dd8a6d8f70a056a5568bfc7bbe8` 이후 변경을 포함한 **dirty preview**이며, 최종 커밋 CI·전체 브라우저 여정·공개 주소·릴리스는 **pending**이다. 정상1배속 AV·목표 하드웨어·최종 AAA 품질도 **pending**이다.

최종 CI·공개/릴리스의 pending은 이 로컬 기록 작성 시점의 상태다. 이후 확정한 커밋·Actions·공개 주소·다운로드 파일의 결과는 [PR #9](https://github.com/kosj/next-action-rpg/pull/9)에서 확인한다. 이 기록을 배포 완료나 AAA 승인 근거로 대신하지 않는다.

이전 [전투 품질 평가](COMBAT_QUALITY_REVIEW.md)는 v0.1.7의 기존 기능·촘촘한 bake·80ms 전환 보간과 의미 있는 강타 안무를 구분했다. 이번 범위는 완충 강타 하나와 일반 근접 수호병의 접촉 반응을 함께 제작하는 것이다. 무기 길이·피해량·테스트 수를 늘려 타격감 개선으로 대신하지 않는다. 반복 검수에는 [공통 전투 품질 절차](../reusable/game-production-kit/skills/godot-web-production/references/combat-quality-review.md)를 사용한다.

## 합의한 설정과 원본

| 항목 | 현재 구현 계약/설정 | 검증 범위 |
| --- | --- | --- |
| 입력 | 기존 완충 기준과 hold/release·취소·TouchControls 액션 경계 유지 | 실제 키/패드/터치와 정지 중 edge 버퍼 확인 필요 |
| 전용 공격 | `charged_heavy`, startup/active/recovery **.34/.18/.54초**, 합계 **1.06초** | [공격 리소스](../game/data/charged_heavy.tres)와 실제 선택 상태·새 clip/import 연결을 대조 |
| 완충 전용 판정 | 표시 Grip/Tip **1.19m**, 근위18%를 제외한 **.9758m 피해 구간·반경.12m 캡슐** | 기존3.3m 수평 대리 범위에서 축소. 일반 공격 판정과 완충 피해69.3 유지 |
| 루트 이동 | 준비0 / active3.2 / 회복0 m/s, 막힘 없는 active 이론 이동 **.576m** | 충돌·phase 경계·hitstop 후 실제 CharacterBody 이동과 비교; 실측 접지 값이 아님 |
| 피해 | 업그레이드0에서 기본42×완충1.65 = **69.3**, 강인도48×1.65 = **79.2** | v0.1.7의 완충 수치 유지. 일반 근접 적 HP95를 항상 한 번에 처치하는 계약이 아님 |
| 피격 표현 | 강한 반응 `heavy_hit` **.48초**, 기존 방패/보스 강인도 규칙 유지 | 실제 모델 반응·중단·death 우선순위와 벽 앞 이동 검수 필요 |
| 완충 접촉 정지 | 공격자·피격자 **.075초** | 같은 접촉으로 요청되며 실제 두 actor의 시계·포즈·이동 정지를 확인해야 함 |

설정 원본은 [AttackData](../game/scripts/core/attack_data.gd), [Player](../game/scripts/actors/player.gd), [Enemy](../game/scripts/actors/enemy.gd)다. phase 이동은 `lunge_between()`처럼 틱이 겹친 구간만 적분하고, 물리 틱 전체에 active 속도를 부여하지 않는다. 이론 이동과 벽·중단으로 줄어든 실제 이동을 구분한다. 문서에 값을 적었다는 이유로 변경 중인 코드·새 자산의 통과를 보증하지 않는다.

## 확정 접촉 문맥과 실제 위치의 한계

[CombatStrike](../game/scripts/core/strike.gd)는 공격창의 sweep overlap·벽 가림·한 swing의 target 중복 제외를 거쳐 피해 대상을 확정한다. `intersect_shape()` 결과는 collider/shape 식별 정보이며 검/표면의 실제 접촉점은 아니다. 현재 문맥의 `hurtbox_ray`는 확정 대상 hurtbox에 추가 ray를 보낸 표면 위치/법선이고, ray가 다른 대상을 만나거나 유효한 법선을 얻지 못하면 `hurtbox_proxy`를 명시한다. 이를 실제 칼 메시와 피부 삼각형의 충돌점이라고 표시하지 않는다.

공통 문맥에는 공격 종류/강도·공격 인스턴스와 target 식별자, point/normal/direction·접촉 근거, 재질 분류와 피해·방어·강인도 파괴·사망 결과를 연결한다. point는 유한 값, normal/direction은 유효한 정규 방향이어야 한다. 현재 수호병의 `metal`은 대상용 분류값이며 ray가 PBR 표면 재질을 자동 검출한 결과가 아니다. 결과는 receiver가 방어/체력/강인도를 적용한 뒤 확정하고, 공격자·피격자·카메라·VFX·오디오가 같은 결과를 읽는다. presentation 관찰은 scalar/벡터 복사이며 게임 상태를 쓰는 명령 통로로 만들지 않는다.

[Game의 impact 전달](../game/scripts/game.gd), [Camera](../game/scripts/world/camera_rig.gd), [Audio](../game/scripts/core/audio.gd)의 시작 시점을 대조한다. 준비 중 swing과 접촉 feedback을 나누고 miss는 명중 결과를 만들지 않게 한다. 여러 sweep 표본·여러 대상·방패·처치에서도 중복 피해와 중복 피드백의 정책을 확인한다. 효과의 양·수명·동시 개수와 quality별 예산을 제한하되 그 존재를 성능 승인으로 바꾸지 않는다.

완충 전용 경로는 `smooth(f²)=3f⁴−2f⁶`의 가속률로 그립·방위각·높이를 함께 진행한다. 그림의 방위각만 가속하고 판정은 선형으로 움직이던 중간 불일치를 제거한다. 칼날 캡슐은 렌더러나 GLB를 조회하지 않는 게임 데이터에서 계산하고 실제 최종 본의 Grip/Tip과 독립 비교한다. 표시 구간에서 손잡이에 가까운18%(.2142m)를 제외하며, 피해 캡슐의 총높이는 남은.9758m에 반구를 포함한다. 반구 중심축은 양끝에서 각각.12m 안쪽이며, 접촉 ray도 이 축을 기준으로 한다. 전체 Grip/Tip과의 거리만으로 손잡이 접촉을 승인하지 않는다. 짧은 물리 틱과 전체 active를 한 번에 넘는 큰 delta 모두 같은 경로를 세분화한다. `contact_blade_grip/tip`과 `contact_phase`는 실제 질의 표본이며 surface point와의 거리를 별도로 검사한다.

## 공통 시계와 양쪽 hitstop

- actor의 hitstop을 줄이는 실시간 delta와 실제 gameplay/presentation을 진행할 delta를 구분한다. 정지 중 공격창/strike elapsed·이동·타이머·차지/버퍼의 유효시간이 서로 다른 시계로 앞서가지 않는지 확인한다. 정지 중 입력 edge를 잃지 않게 버퍼링하되 새 gameplay 효과를 먼저 실행하지 않는 정책을 검사한다.
- 명중을 만든 틱의 순서가 중요하다. 접촉 뒤 같은 틱의 나머지 이동·포즈 갱신이 정지 목표를 밀지 않는지, 공격자/피격자가 실제로 같은 접촉 상태를 유지하는지 검사한다. 두 actor의 manual pose는 정지 delta로 표본화하고 최종 손 본/검 소켓·world marker·trail age도 고정돼야 한다.
- 피해자 정지 중 AI가 수평 속도를 다시 지정하지 않게 하고 recoil·중단·death를 명시적인 상태로 처리한다. 복귀/새 공격/epoch에서는 이전 contact·hitstop·recoil·표현 이력을 정리한다. 방패/보스의 저항과 다른 actor의 독립 진행은 유지한다.
- camera/VFX의 age와 오디오 시작·지속의 시계도 명시한다. 같은 접촉으로 시작했다는 사실과 각 매체가 정지 중 어떻게 진행하는지는 별도 검증이다. 애니메이션 재생 속도나 전역 time scale만 바꿔 판정과 표현의 불일치를 숨기지 않는다.

이는 완료 판정이 아니라 실행 시 확인할 계약이다. 중간 코드에서 clock guard가 보인다는 사실만으로 모든 타이머·입력·이동·동시 actor의 동등성을 승인하지 않는다.

## 저작 모션·검·발 보정

[강타 저작 도구](../tools/author_impact_actions.py)와 source/파생 manifest에 전용 강타·강피격의 recipe·도구/입력 해시를 기록한다. 준비·지지발/골반 선행·검의 가속·접촉·팔로스루·회수를 구분하고, 같은 수평 공식을 촘촘히 bake한 것과 의미 있는 안무를 나눈다. 기존 보간을 보존하되 보간이 안무를 만들어 준다고 가정하지 않는다.

[production 상태 매핑](../game/scripts/actors/production_character_art.gd)과 [skeletal bridge](../game/scripts/actors/skeletal_visual_bridge.gd)에서 `charged_heavy`/`heavy_hit`가 실제 새 clip으로 연결됐는지, 이동 중 차지가 locomotion 선택에 가려지지 않는지 확인한다. source skin/rest/기존 이미지 보존과 새 clip의 완전한 PRS/RESET·import 채널 검사는 별도다.

검과 지지발의 보정은 물리 단위·rig normalization·외부 actor scale을 구분한다. 실제 최종 본 포즈 뒤 같은 프레임의 grip/tip·양손/발 world 위치를 대조하고 루트 이동을 이중 적용하지 않는다. 지지 구간의 발 보정과 swing/다음 발디딤을 구분한다. .576m의 막힘 없는 이론 경로를 bake했다는 이유로 벽에 막힌 실제 이동·중단·hitstop·yaw 전환에서도 발이 고정된다고 주장하지 않는다. terrain IK·연속 접지·최종 양손 접촉은 별도 검수다.

### 중간프레임 실패

2026-10-31의 중간 native 실행은 **기능424개 통과와 별도로 전체429개 중1개 실패**를 보존한다. 관찰용 공격 식별자를 RefCounted ObjectID 대신 양의 JS-safe serial로 고친 뒤 기능424개가 통과한 것은 관찰 프로토콜/기능 경로의 확인이며, 아래 실제 검 정렬의 통과가 아니다.

| 검사 | 당시 관찰 | 판정 범위 |
| --- | --- | --- |
| 실제 imported Grip/Tip | active phase.75, t≈.475초에서 grip 최대오차 **.264342m**, tip **1.767758m** | RunePlayer capsule/시각 바닥 보정과 외부 actor scale을 포함한 실제 frame에서도 실패 |
| 명목 지지발 | drift **1.893mm** | 해당 지지 구간의 gate는 통과했지만 검·팔 연속성이나 terrain IK·전체 안무 승인은 아님 |
| 초기 Node3D fixture | 실제 RunePlayer의 **+.025m** 시각 바닥 차이를 누락해 별도25mm bias | fixture를 실제 actor frame으로 정정했으며 게임/리그 보정이나 허용오차를 바꾼 수정이 아님 |

당시 실제 body SHA는 `b6bc88d72ad1605a70f3b00ffedda21e67064f012a1c5700d0b96e9ad4216bf7`이다. 작업 증거의 `native-actor-frame.log`와 `alignment-fps100-actor-fixture.json`은 이 입력과 정정된 fixture를 구분한다. import fps를30에서100으로 올린 뒤에도 실패했다. raw GLB의 .47→.48초에서 RightArm/RightHand의 shortest 회전 차이는 각각 약174.04°/174.83°, 팔꿈치는10ms에 약.53m 튀었다. 고정 IK pole이 해 방향과 거의 일직선이 되는 구간에서 key의 손 목표는 맞아도 팔·손의 counter-rotation을 보간한 중간 포즈가 깨지는 문제다.

따라서 끝점/저작 key의 grip 수치·촘촘한 bake만으로 채택하지 않는다. raw와 실제 imported 모델의 모든 key와 midpoint에서 최종 Grip/Tip·발을 같은 actor frame으로 대조하고, 인접 quaternion의 shortest 회전과 팔꿈치 world 이동에도 연속성 상한을 둔다. quaternion 부호/Euler wrapping과 실제 관절 뒤집힘도 구분한다. 수정본은 impact 팔에 연속 elbow-plane frame을 사용한다. 새 두 동작만500Hz로 저작하고 실제 GLB의188개 key/midpoint 감사에서 그립.320mm·칼끝1.280mm·최대관절차9.574도를 확인했다. 실제 반입에서도531개의 새 손 회전 키와3mm 정합 기준을 확인했다. 허용오차 확대·실패 구간 제외로 통과시키지 않는다.

Godot4.7.2 [scene importer의 설정 원본](https://github.com/godotengine/godot/blob/4.7.2-stable/editor/import/3d/resource_importer_scene.cpp#L2328)은 optimizer enabled=true, max_velocity_error=.01, max_angular_error=.01, max_precision_error=3이며 animation/fps 기본값은30이다. source IK·bake·import resampling·optimizer를 별도 변수로 A/B하고 raw source에 이미 있는 관절 점프를 importer 탓으로 단정하지 않는다. 새 GLB에만 optimizer/compression을 끄고 실제 반입 키를 검사한다. 이는 원본 IK 반전의 원인을 optimizer로 바꿔 설명하는 것이 아니다. 전 씬500Hz 내보내기가152,592,309B로 예산을 넘자 [선택 반입](../game/import/impact_animation_sampling.gd)으로 새 두 동작을 보존하고 기존 동작의 원본100Hz 표본·끝점·채널을 복원했다. 이 단계의435검사와 Web146,275,179B/150MB 예산 통과는 당시 반입·예산 이력이며, 이후 발견한 손잡이 접촉을 승인하지 않는다. **1배속 AV·실기기·AAA는 pending**이다.

## 재현·검증 순서와 완료 판정

1. source commit/dirty 파일·툴체인, 새/기존 GLB와 저작 recipe의 SHA를 고정한다. 새 자산은 원본을 보존한 별도 출력으로 생성하고 실제 import·상태 매핑·channel 보존을 확인한다.
2. 통합 Node runner에서 실제 전용 공격 선택, half-open active·phase 이동 적분, 벽 가림/중복 target, miss/block/kill 결과, 같은 context의 양쪽 정지·타이머/입력 버퍼·socket/trail·death/restore를 확인한다. 코드의 계산식을 그대로 복제한 수치 검사만으로 물리·표현을 승인하지 않는다.
3. 실제 production 모델에서 charge hold/이동/release, 무기와 지지발, 강피격과 recoil·벽 충돌을 검사한다. 모든 exported key/midpoint와 실제 동작 화면의 범위를 나누고 장전 끝·중단·복귀도 포함한다.
4. [공통 비교 행렬](../reusable/game-production-kit/skills/godot-web-production/references/combat-quality-review.md)의 약/강/차지×명중/빗맞힘/방어/처치를 같은 거리·카메라에서 실제1배속 영상/음향으로 검수한다. 데이터 시각과 관찰한 영상 시각을 구분한다. 소프트웨어 저FPS·정지 캡처를 정상1배속이나 기기 성능의 근거로 사용하지 않는다.
5. 통합 검사 후 Web/Windows export, 기존 데스크톱·모바일 입력/저장/재시작·공개 주소 gate를 유지한다. QA 관찰은 읽기 전용이며 성공 상태나 저장을 주입하지 않는다. 실행 로그·종료 코드·stderr·실제 빌드/자산과 남은 항목을 함께 기록한다.

재현 명령은 다음과 같다. 정확한 실행 범위와 관측값은 [로컬 검증 기록](validation/v0.1.8/README.md)을 확인한다. 엔진은 실제 `tools/toolchain.json`과 맞는 binary를 사용한다.

```bash
python tools/knowledge.py check
python tools/build.py --test-only
python tools/build.py --windows
python tools/check_web.py
python tools/check_mobile_web.py
```

현재 자료의 확인 범위는 **로컬 native·실제 모바일 집중 기능 검사와 Web/Windows 패키지 통과**다. 최종 커밋 CI·전체 브라우저 여정·공개 주소·릴리스는 pending이다. 기능·구조 통과, 시각/음향 개선, 실기기 성능과 [대표 구간 AAA 승인](AAA_ART_QUALITY.md)은 각각 판정한다. 이전 버전의 검사 수·배포 성공을 새 구현의 통과로 승계하지 않는다.

## 참고 대상·공식 자료·적용 스킬

레퍼런스는 사용자가 확인한 **제우스: 오만의 신 / 버서커 / 대검·강한 한방**이다. [공식 클래스](https://zeus.com2us.com/gameinfo/class)와 [공식 변경 안내](https://zeus.com2us.com/p/137fc870-5481-44dd-9ca4-205dcaab2f9e)는 대상/설명을 확인하는 근거다. 이전 리뷰에서 확인한 무음 홍보 배경 프레임은 gameplay·접촉 시간·오디오 기준이 아니다. 공식 YouTube 전투 프레임은 환경의 proxy403으로 관찰하지 못했으므로 hitstop/공격 프레임·음향을 직접 측정했다고 쓰지 않는다. MMORPG 연출 스타일과 이 게임의 입력 반응은 별도로 평가한다.

공식 기술 자료 조회일은 **2026-10-31 UTC**다. [PhysicsDirectSpaceState3D](https://docs.godotengine.org/en/stable/classes/class_physicsdirectspacestate3d.html)의 overlap 식별 결과, ray의 표면 정보, `collide_shape()`의 접촉점 쌍과 motion 미반영을 구분한다. 현재 구현이 쓰지 않은 query를 이미 사용한 것으로 표시하지 않는다. [렌더러 비교](https://docs.godotengine.org/en/stable/tutorials/rendering/renderers.html)와 [CPUParticles3D](https://docs.godotengine.org/en/stable/classes/class_cpuparticles3d.html)는 Web Compatibility와 CPU 표현 후보의 근거이며 현재 효과의 외관·성능 통과 증명이 아니다. stable URL은 바뀔 수 있으므로 엔진 갱신 시 실제 버전과 다시 대조한다.

프로젝트 [개발](../.agents/skills/runefall-development/SKILL.md)·[아트](../.agents/skills/runefall-art/SKILL.md)·[릴리스](../.agents/skills/runefall-release/SKILL.md) 절차와 공개 [godot-animation](../.agents/skills/godot-animation/SKILL.md)을 적용한다. 공개 스킬의 upstream HEAD는 2026-10-31 API 재확인에서 기존 pin `19d93f97c9c1ea0f8b306e77aa81e0d3e352d3e9`와 같았으며 새 설치가 필요하지 않았다. 원문·Apache LICENSE/NOTICE·[provenance](../.agents/skills/upstream.json)는 수정하지 않는다. AnimationPlayer는 clip 데이터, AnimationTree는 표현 표본/전환을 맡으며 gameplay 시간·피해 권한을 애니메이션 이벤트로 이중 실행하지 않는다.

### 손잡이 접촉을 놓친 통과 기록

초기 로컬435검사·터치299.510초와 첫 PR CI는 전체 Grip/Tip 선분을 감싼 캡슐 기준으로 통과했다. 이후 실제 clean CI 기록을 독립 검토하자 첫접촉이.375556초/phase.19753이며 날 구간 거리.265814m·전체날 투영−.021113으로 손잡이 뒤였다. 기존 로컬 기록도 날 구간 거리.170316m·투영.077705로 탈락했다. 이 통과를 현재의 날 접촉 승인으로 승계하지 않는다. [기각한 접촉 기록](validation/v0.1.8/rejected-contact-summary.json)은 이전 green CI와 아래 recoil 실패의 입력·관측값을 보존한다.

수정본은 표시용 소켓과 날 피해 구간을 분리하고 양 반구가 실제 날 바깥으로 연장되지 않도록 한다. [CapsuleShape3D 공식 정의](https://docs.godotengine.org/en/stable/classes/class_capsuleshape3d.html)의 height는 반구를 포함한 총높이, mid_height는 반구 중심 사이 거리다(2026-10-31 조회). 끝점을 무엇으로 정의했는지에 따라 사용하며, 과거의L+2r 자체를 보편적인 산술 오류로 설명하지 않는다. 근접.725m 회귀에서는.38초까지HP95 유지·이후 실제 베기에서69.3한번을 검사한다. 중간 native438/0은 아래의 최종 실패한 모바일 실행과 구분한다.

### 날 구간 통과와 recoil 실패

중간 모바일253.900초 실행의 실제 접촉은 phase **.49382716**, 질의 시각 **.428888889초**다. 전체 Grip/Tip 기준 투영 **.254513 > .18**, 독립적으로 계산한 날 피해 구간 **.975800053m**, 반구 중심축까지 거리 **.119670002m ≤ .125m**로 날 위치 gate를 통과했다. 이 수치는 표시 소켓·내부 축·실제 surface point를 별도로 비교한 결과이며 과거 전체 Grip/Tip 캡슐 통과와 구분한다.

그러나 같은 집중 실행은 recoil **.365348910m**가 요청 **.35m**, 허용 상한 **.355m**를 넘어 최종 실패했다. 브라우저 오류0이나 날 접촉 통과를 전체 성공으로 바꾸지 않는다. 이 실패를 보존한 뒤 수정본을 아래 최종 집중 검사로 다시 확인했다. 허용오차를 넓히거나 검증 경로를 건너뛰어 통과시키지 않았다.

수정은 [Enemy의 recoil motor](../game/scripts/actors/enemy.gd)가 `move_and_slide()`로 실제 이동한 수평 경로를 매 틱 예산에서 차감한다. 접촉 직전 겹친 capsule을 물리가 밀어내는 이동도 실제 변위이므로 별도 회복량 위에 다시 온전한.35m를 더하지 않는다. 요청 속도×시간, 최종 순변위, 누적 수평 경로를 구분하고 벽 앞에서는 실제 충돌이 이동을 줄이도록 유지한다.

실제 Godot4.7.2 native439/0의 새 겹침 회귀는 capsule 반경 합 **.76m**에 초기 수평 간격 **.744995117m**를 사용했다. 첫 실제 이동 **.039993286m**를 포함해 최종 순변위·누적 경로가 각각 **.349990845m**였고 공격자 root는 움직이지 않았다. 열린 바닥은 **.349975586m**, 벽 앞은 **.197509766m**였다. 이 추적은 겹침 복구를 예산에 포함한 native 결과이며 실제 모바일 결과와 독립된 근거다.

입력 보고도 정정했다. [현재 native 접촉 기록](validation/v0.1.8/contact.json)은 실제 runtime hero `0aa78c46c0453f8286785ee937ef9388324dc4312bb076f5179934f08e44d57d`와 reference hero `4cc9ae5b9340263b824d549ad59a7955705c927859bf35949d66984cd647ed0c`를 분리하고, fixture `0351c54bfd0ef4e8bbe98a08826508061272656555cd7332e692bceae56159ad`를 기록한다. 이전 `hero_body`의 잘못된 경로 표기를 실제 모델 변경으로 설명하지 않는다.

### 현재 로컬 집중 검증의 통과 범위

[최종 모바일 요약](validation/v0.1.8/mobile-focused-summary.json)과 [실제 터치 원문](validation/v0.1.8/mobile-focused-proof.json)은 수정 후 **282.938초·오류0**을 확인한다. 신뢰된 CDP 다중 터치를 사용했고 빗맞힘의 contact/spawn0, 실제 피해 **69.3(HP95→25.7)**, impact와 effect spawn 각각1회, `heavy_hit .48초`, 양측 `.075초` 정지 요청, 실제 수평 recoil **.349998474m**를 관찰했다. 마지막 실제 일시정지는 **HP72·소유 포인터0**다.

이 실행의 접촉 질의 시각은 **.432222222초**이며 전체 Grip/Tip 투영 **.263749193 > .18**, 독립 날 피해 길이 **.975799985m**, 내부 축 거리 **.118551338m ≤ .125m**로 날 구간을 확인했다. release→관찰 일치 **5.787초**는15초 응답 제한 안의 검사 지연이며, 정상1배속 영상의 공격 시간 측정이 아니다. [입력/상태 타임라인](validation/v0.1.8/mobile-release-timeline.json)과 [export 문맥](validation/v0.1.8/mobile-export-context.json)은 source HEAD 이후 dirty 변경과 실행한 파일 해시를 연결한다.

브라우저에서는 짧은 양측 frozen pair를 관찰하지 못했다. 별도 native 접촉은 질의/권한 시각 **.46초**, 표시 **.459999975초**에서 시작해3개 물리 프레임 동안 두 root·전체 skeleton·공격/피격 시계와8개 trail 표본·mesh·age를 유지했다. 따라서 브라우저의 정지 요청 관찰과 native의 실제 동결 증거를 구분한다. [현재 실행/패키지 기록](validation/v0.1.8/local-preview.json)은 native439/0·Python51/0, Web146,279,323B·Windows export·ZIP 검증을 담는다. **확인 범위는 로컬 기능·집중 검사이며 최종 커밋 CI·전체 브라우저 여정·공개/릴리스·정상1배속 AV·실기기·AAA는 pending**이다.
