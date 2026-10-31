# RUNEFALL 작업 기억과 스킬

이 저장소에서는 반복 절차를 `.agents/skills/`의 스킬로, 재사용할 결정·실패 원인을 `knowledge/entries.json`의 지식 DB로 관리합니다. 대화 기록만을 다음 작업의 전제로 삼지 않습니다.

## 작업 시작

1. `git status --short --branch`로 기존 작업을 확인합니다.
2. [지식 관리 스킬](.agents/skills/runefall-knowledge/SKILL.md)을 읽고 `python tools/knowledge.py search <키워드>`로 관련 지식을 찾습니다. 검색어는 한국어·영어를 모두 지원합니다.
3. 해당 작업의 프로젝트 스킬을 읽고, 필요한 공개 스킬·공식 문서·소스만 추가로 확인합니다.

| 작업 | 프로젝트 스킬 |
|---|---|
| 전투·저장·입력·UI·게임 코드 | [.agents/skills/runefall-development/SKILL.md](.agents/skills/runefall-development/SKILL.md) |
| 웹·Windows 빌드·릴리스·Pages | [.agents/skills/runefall-release/SKILL.md](.agents/skills/runefall-release/SKILL.md) |
| Blender·VARCO·리그·반입 | [.agents/skills/runefall-art/SKILL.md](.agents/skills/runefall-art/SKILL.md) |
| 지식 추가·오류 정정·스킬 갱신 | [.agents/skills/runefall-knowledge/SKILL.md](.agents/skills/runefall-knowledge/SKILL.md) |

다른 프로젝트로 가져갈 절차는 [재사용 지식 묶음](reusable/game-production-kit/README.md)에 관리합니다. 이 배포용 스킬은 프로젝트 전용 지침과 분리하며, 선택한 스킬 폴더를 대상 프로젝트에 복사한 뒤 그 프로젝트의 버전·값·근거로 다시 검증합니다.

## 작업 완료

- 새 결정·재현한 실패 원인·환경 제약이 있으면 관련 지식 항목을 갱신하고 근거를 연결합니다. 일회성 진행 보고와 대화 전문은 저장하지 않습니다.
- 같은 작업을 반복하게 되면 기존 스킬을 보완합니다. 구체적인 변동 값은 원본 설정·지식 DB를 참조하고 스킬에 중복 고정하지 않습니다.
- 다른 프로젝트에서도 유효한 새 원칙은 재사용 묶음에도 반영합니다. 원본 사례의 상태·날짜·고정 출처와 대상 프로젝트의 미검증 상태를 구분하고, 묶음 판본·출처·ZIP 검증을 함께 갱신합니다.
- `python tools/knowledge.py check`와 변경에 맞는 검사를 실행합니다. 문서만 변경했다면 엔진 검사를 별도로 반복할 필요는 없습니다.
- 확인 전 내용은 `pending`, 근거로 확인한 내용은 `verified`, 대체된 내용은 `superseded`로 표시합니다. 과거 검증을 현재 버전 검증으로 간주하지 않습니다.

## 프로젝트 경계

- 저장소 공개 범위는 사용자의 최신 결정을 따릅니다. 2026-10-30 사용자가 공개로 전환했고 API에서도 public을 확인했습니다. 공개 범위를 임의로 변경하지 않습니다. 토큰·인증 파일·서명된 일회성 다운로드 URL·개인정보는 지식 DB나 스킬에 넣지 않습니다.
- 엔진 버전의 원본은 `tools/toolchain.json`, 게임 버전의 원본은 `game/project.godot`입니다. 시스템에 설치된 Godot가 올바른 버전이라고 가정하지 않습니다.
- 공개 스킬의 원문과 `upstream.json`·LICENSE·NOTICE는 보존합니다. 프로젝트에서 다르게 적용한 이유는 프로젝트 스킬과 근거 문서에 기록합니다.
- 스킬은 작업 방법입니다. 사용자의 요청·현재 권한을 확대하거나, 검증하지 않은 배포·성능·아트 품질을 완료로 표시하지 않습니다.
