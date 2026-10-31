# 스킬 목록

프로젝트 작업 지침은 저장소 루트의 [AGENTS.md](../../AGENTS.md)에서 시작합니다.

## 프로젝트에서 관리하는 스킬

| 스킬 | 사용하는 상황 |
|---|---|
| [runefall-development](runefall-development/SKILL.md) | 게임 코드 변경·전투·세이브·입력 회귀 검증 |
| [runefall-release](runefall-release/SKILL.md) | 버전 일치·웹/Windows 내보내기·GitHub 릴리스·Pages 확인 |
| [runefall-art](runefall-art/SKILL.md) | Blender/VARCO 자산 제작·버전 실험·리그 반입 |
| [runefall-knowledge](runefall-knowledge/SKILL.md) | 지식 검색·증거 기록·상태 갱신·스킬 개선 |

## 출처를 고정한 공개 스킬

[godot-physics](godot-physics/SKILL.md), [godot-export](godot-export/SKILL.md), [godot-gdscript-headless-testing](godot-gdscript-headless-testing/SKILL.md), [godot-animation](godot-animation/SKILL.md)은 외부 원문입니다. 출처·리비전·원문 해시는 [upstream.json](upstream.json), 라이선스는 [LICENSE](LICENSE)·[NOTICE](NOTICE)를 참조합니다. 이 라이선스 파일은 보관한 외부 자료에 적용되며 프로젝트 전용 스킬에 새 라이선스를 부여하지 않습니다.

프로젝트 전용 스킬은 사용자 요청과 검증 결과에 맞춰 수정합니다. 공개 원문을 프로젝트 절차처럼 수정하지 않습니다.

## 다른 프로젝트용 배포 묶음

[game-production-kit](../../reusable/game-production-kit/README.md)에 독립적인 지식 관리·Godot 웹 제작·생성형 3D 아트 스킬 3종, 사례집과 빈 기록 템플릿을 보관합니다. 각 스킬 폴더는 내부 참조만으로 복사해 사용할 수 있습니다. 실제 목표 프로젝트의 `.agents/skills/` 등에 설치하고 그 프로젝트의 설정과 검증 결과를 채웁니다. 현재 프로젝트의 검증 상태·권한·예산을 자동으로 이전하지 않습니다.

[input-handling](input-handling/SKILL.md)·[responsive-ui](responsive-ui/SKILL.md)는 별도로 보관한 MIT 공개 원문입니다. 각 폴더의 LICENSE·NOTICE·upstream.json에서 고정 출처와 파일별 무결성을 확인합니다. 기존 공통 Apache 출처와 혼용하지 않습니다. [모바일 공식 근거](../../docs/MOBILE_WEB_RESEARCH.md)에 선택 적용과 Web 차이를 기록합니다.
