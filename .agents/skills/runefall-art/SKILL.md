---
name: runefall-art
description: Create and import RUNEFALL Blender or VARCO assets, evaluate Blender upgrades, and migrate prototype pivots to skeletal animation. Use for model generation, rigging, animation, or art-pipeline changes.
---

# RUNEFALL 아트 제작과 반입

[아트 파이프라인](../../../docs/ART_PIPELINE.md)과 [재검증 기록](../../../docs/ART_REVIEW.md)을 먼저 확인합니다. `python tools/knowledge.py search --tag art`로 실험 결과와 라이선스 조건을 찾습니다. 리그·애니메이션 변경에는 [godot-animation](../godot-animation/SKILL.md)을 적용합니다.

## 원본과 생성

- 현재 검증된 Blender 버전은 아트 가이드에서 확인합니다. 새 버전은 별도 디렉터리·체크아웃에서 먼저 시험합니다.
- `art_source/generate_assets.py`는 기존 원본과 GLB를 덮어씁니다. 수작업 자산을 보존하고 임시 출력에서 비교한 뒤 적용합니다. `.blend`는 LFS, 런타임 GLB는 일반 Git으로 관리합니다.
- 고유 주인공·룬도 VARCO 생성 후보와 Blender 후처리를 조합합니다. 생성 사용 범위를 소품으로 제한하지 않습니다. VARCO 사용 전 생성 당시 플랜·라이선스·공개 범위를 공식 정책과 대조하고 자산 URL·제작자·귀속 표기를 기록합니다.
- [공식 MCP 연결 가이드](../../../docs/VARCO_MCP.md)에 따라 서버 존재·현재 클라이언트 등록·OAuth·도구 발견·실제 호출을 구분합니다. 사용 가능한 도구와 플러그인을 검색하기 전에 연결 불가로 단정하지 않습니다. 클라이언트의 OAuth를 사용하고 MCP 엔드포인트나 토큰 교환을 수동 호출하지 않습니다.
- 현재 환경은 `tools/varco_mcp.py`를 통해 공식 Codex app-server의 도구 발견·호출 API를 사용할 수 있습니다. 새 세션에서는 `catalog`와 실제 읽기 호출로 상태를 확인합니다. Flow 목록이 비어 있으면 대상 Flow를 준비하고, 실제 스키마의 `flowId`를 명시합니다. 임의 ID나 오래된 workflow 이름을 만들지 않습니다.
- `art_source/production/`의 입력 명세와 실제 생성 후보는 분리합니다. `tools/check_art_production.py`는 입력·참조 해시·게임 공격 값의 일치만, `tools/inspect_glb.py`는 바이너리 구조와 명시 요구 조건만 검사합니다. 최종 반입은 두 검사와 실제 화면·변형·성능 검수까지 확인합니다.
- 현재 도형 블록아웃은 최종 제작 방식이 아닙니다. 주인공 1명·적 1종·전투 공간 1개부터 형태·재질·리그·모션·조명·VFX를 함께 검수한 뒤 확장합니다. 상세 범위는 아트 가이드에서 확인합니다.

## 버전 실험의 완료 기준

프로세스 정상 종료, GLB 구조·재질·변환·메시 비교, Godot의 오류 없는 반입, 실제 씬의 시각·모션 확인을 분리해 기록합니다. 출력 파일이 존재한다고 배치 성공으로 처리하지 않습니다. 현재 보관한 LTS 실험은 구조·반입 비교를 통과했어도 배치 종료 실패가 남아 있으므로 제작 버전을 자동 교체하지 않습니다.

## 반입 계약

1. 단위 1m·발바닥 높이·무기 위치를 확인합니다. 게임 이동 -Z와 Humanoid 리타겟 +Z를 구분하고 180도 보정을 중복 적용하지 않습니다.
2. 현재 GLB의 임시 피벗과 최종 `Skeleton3D`·스킨 웨이트를 구분합니다. 최종 자산은 BoneMap, RESET 포즈, 클립 트랙, 루프·발 접지를 검사합니다.
3. `AnimationPlayer`는 클립, `AnimationTree`는 블렌딩·표현을 담당합니다. 실제 이동·공격 타이밍·피해 판정은 게임 코드가 소유합니다.
4. 웹 Compatibility의 재질·조명 대체와 Windows 화면을 확인합니다. LOD 설정만으로 성능을 합격 처리하지 않고 드로콜·프레임 시간을 측정합니다.

## 완료

변경한 자산의 원본·수정 이력·사용 조건과 실제 검증 범위를 기록합니다. 최종 리그·성능이 미검증이면 지식 상태를 `pending`으로 유지합니다. 반입 후 게임 검사가 필요하면 [개발 스킬](../runefall-development/SKILL.md)을 따릅니다.
