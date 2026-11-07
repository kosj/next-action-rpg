---
name: runefall-unreal-vfx
description: >
  Use when the user requests Unreal Engine or Niagara VFX guidance, authoring,
  baking, caching, Blueprint integration, or profiling. Routes to the standalone
  Unreal skill without changing RUNEFALL's Godot engine or deployment settings.
---

# Unreal VFX 작업 진입점

사용자가 언리얼 VFX를 요청하면 [독립 Niagara 제작 스킬](../../../reusable/game-production-kit/skills/unreal-niagara-vfx/SKILL.md)을 적용한다. 실제 Unreal 프로젝트에서 쓰려면 해당 폴더 전체를 그 프로젝트의 스킬 경로에 복사한다. [출처와 확인 범위](../../../reusable/game-production-kit/skills/unreal-niagara-vfx/references/source-notes.md)·[제작 양식](../../../reusable/game-production-kit/skills/unreal-niagara-vfx/references/unreal-vfx-brief.json)을 함께 사용한다.

현재 RUNEFALL의 Godot 코드·버전·웹 배포 설정과 별도의 문서/제작 경로다. 이 스킬 추가를 엔진 전환·Unreal 설치·프로젝트 생성·새 효과 실행으로 해석하지 않는다. 실제 제작 요청에는 지정한 `.uproject`와 설치 버전·대상 플랫폼을 확인한 뒤 그 프로젝트의 지침을 따른다. 제공된 맥락으로 실행 가능한 준비를 진행하고 새로운 외부 도구 권한을 임의로 만들지 않는다.

기술 조사·문서 검증과 Unreal 실습·cook/package·게임 화면/성능 승인을 구분해 기록한다. 재사용 원칙은 [지식 관리 스킬](../runefall-knowledge/SKILL.md)에 따라 축적한다.
