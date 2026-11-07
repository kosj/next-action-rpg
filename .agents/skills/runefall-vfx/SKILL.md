---
name: runefall-vfx
description: >
  Author or improve RUNEFALL combat VFX with Blender and Godot: sword waves,
  impacts, rune skills, smoke/fire, particles, flipbooks, and Web/Windows quality.
  Use for effect design, gameplay integration, visual review, and VFX budgeting.
---

# RUNEFALL VFX 제작

[재사용 VFX 스킬](../../../reusable/game-production-kit/skills/realtime-combat-vfx/SKILL.md)을 기본 절차로 사용한다. [출처·열람 범위](../../../reusable/game-production-kit/skills/realtime-combat-vfx/references/source-notes.md)는 공개 강좌 소개와 공식 문서 대조이며 전체 강의 이수나 새 VFX 제작 승인이 아니다. 런타임 선택은 [공식 기능 조사](../../../docs/research/VFX_RUNTIME_CAPABILITY_NOTES.md)로 다시 확인한다.

## 현재 프로젝트에 적용

1. [개발 스킬](../runefall-development/SKILL.md)·[아트 스킬](../runefall-art/SKILL.md)과 지식 DB의 `resolved-stride-upper-attack-and-traveling-wave`, `mixed-delivery-contact-oracles-and-same-strike-ledger`를 읽는다. 엔진 버전은 `tools/toolchain.json`, 렌더러/품질은 실제 프로젝트 설정을 원본으로 삼는다.
2. [현재 검기](../../../game/scripts/world/sword_wave.gd)·[셰이더](../../../game/assets/shaders/sword_wave.gdshader)·[확정 타격](../../../game/scripts/world/impact_effect.gd)·[플레이어 연결](../../../game/scripts/actors/player.gd)을 읽는다. 실제 파일명/이벤트·marker·clock·공유 ledger와 source/target identity를 확인한다. 시각 수정이 피해/거리·blade curve·이동/입력 계약을 바꾸지 않게 한다.
3. 현재 보이는 결함의 근거는 [이동 공격·검기 기록](../../../docs/validation/v0.1.16/README.md)이다. 근거리의 흰 띠, 보행/상체 연결과 전체 모션은 서로 다른 개선 대상이다. 검기 형상·밀도/끝 감쇠·잔향을 먼저 작은 후보로 비교하고 밝기로 동작을 가리지 않는다. 앞선 프로토타입 채택을 새 후보나 AAA 승인으로 승계하지 않는다.
4. 주 검기·보조 입자·확정 접촉을 각각 시험한다. `RuneSwordWave`의 벽 차단/거리·원래 `CombatStrike` ledger, 다른 strike에 늦은 hitpause를 적용하지 않는 계약, encounter/title/restore epoch 정리를 보존한다. 전달 수단별 타격 자료를 임의 blade 접촉으로 위장하지 않는다.
5. Web Compatibility를 기본 경로로 검수한다. q0/q1의 실제 이름과 그림자/render scale 설정은 기존 코드에서 읽고 뒤집지 않는다. GPU 파티클 자체와 지원되지 않는 built-in trail/SDF 기능을 구분한다. 소켓 기반 trail은 최종 marker로 만든 현재 방식과 별도로 비교한다.
6. 새 atlas/효과를 넣기 전 실제 raw Web 용량과 목표를 확인한다. 기존 공개판의 여유가 작으므로 큰 베이크 자산을 무조건 추가하지 않는다. 텍스처 import 후 전송/메모리·첫 사용 hitch를 측정하고 시각 채택과 별개로 기록한다.

## 제작·검증·기록

[제작 양식](../../../reusable/game-production-kit/skills/realtime-combat-vfx/references/vfx-brief.json)을 작업 후보에 복사한다. 확정 접촉·실제 화면/그림자/오버드로·취소/복귀·웹/모바일·정상1배속 AV를 검수하고, 미실행 항목은 `pending`이다. 게임 코드를 바꾸면 기존 native 회귀와 해당 export/browser 검사를 적용한다. 문서·스킬만 바꿨다면 엔진/게임 배포를 반복하지 않는다.

새 원칙은 [지식 관리 스킬](../runefall-knowledge/SKILL.md)에 따라 DB와 재사용 묶음에 남긴다. 공개 강의 원본이나 제공 자산을 새 스킬의 배포 파일에 넣지 않는다. 실제 게임 배포가 요청 범위일 때만 [배포 스킬](../runefall-release/SKILL.md)로 이어간다.
