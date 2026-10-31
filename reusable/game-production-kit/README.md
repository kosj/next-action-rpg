# 다른 프로젝트에 가져가는 제작 지식 묶음

버전 **1.0.0** · 정리일 **2026-10-31**.

기존 프로젝트에서 축적한 지식 46항목을 **재사용 절차·실패 사례·작성 템플릿**으로 정리했습니다. 프로젝트 주소, 캐릭터 치수, Flow ID, 공격 시간, 비용과 용량 목표를 새 프로젝트의 설정으로 강제하지 않습니다. 원래 검증 결과는 출처 사례이며, 가져간 프로젝트의 검증 상태는 새로 기록합니다.

## 필요한 것부터 사용하기

| 구성 | 사용하는 상황 |
| --- | --- |
| [evidence-led-project-memory](skills/evidence-led-project-memory/SKILL.md) | 어떤 프로젝트에서든 결정·실패·근거·검증 상태를 관리할 때 |
| [godot-web-production](skills/godot-web-production/SKILL.md) | Godot 웹/Windows 빌드, 실제 브라우저 입력·저장, 공개 배포를 검증할 때 |
| [generated-3d-game-art](skills/generated-3d-game-art/SKILL.md) | 생성형 3D·Blender·리그·모션·PBR·아트 품질을 검수할 때 |
| [사례집](HANDBOOK.md) | 문제의 원인, 재사용할 원칙, 다시 확인할 조건을 빠르게 찾을 때 |
| [출처 스냅샷](provenance.json) | 원래 46항목의 상태·날짜·고정 커밋 근거를 추적할 때 |

각 스킬 폴더의 `references/`에 해당 템플릿을 함께 넣었습니다. 선택한 **스킬 폴더 전체**만 복사해도 로컬 참조가 유지됩니다. 일반 소프트웨어 프로젝트라면 첫 번째 스킬만 가져가면 됩니다.

## 새 프로젝트에 적용하는 순서

1. 새 프로젝트의 기존 지침과 스킬을 먼저 확인합니다. Codex의 프로젝트 스킬 경로를 쓰는 경우, 원하는 `skills/<이름>/` 폴더를 새 프로젝트의 `.agents/skills/<이름>/`으로 복사합니다. 같은 이름이 있으면 내용을 비교해 합치며 덮어쓰지 않습니다. 다른 클라이언트는 그 클라이언트의 스킬 검색 경로를 사용합니다.
2. 스킬의 `name`·`description`은 유지하고, 프로젝트 `AGENTS.md` 또는 작업 지침에서 사용할 스킬을 연결합니다. 참고용으로 이 묶음을 보관하는 것만으로 모든 클라이언트에 자동 등록되지는 않습니다.
3. 웹/게임 작업에는 [프로젝트 설정 템플릿](skills/godot-web-production/references/project-profile.json)의 빈 값을 채웁니다. 엔진·템플릿·Blender 버전, 프로젝트 경로, 이동/무기 축, 저장 식별자, 배포 주소, 성능·용량 목표를 실제 프로젝트에서 결정합니다.
4. 지식 기록은 [항목 템플릿](skills/evidence-led-project-memory/references/knowledge-entry.json)으로 시작합니다. 템플릿의 자리표시자를 실제 값으로 바꾸고 로컬 근거를 연결하기 전까지 `pending`을 유지합니다. 원래 프로젝트의 `verified`를 새 프로젝트에 복사하지 않습니다.
5. 관련 공식 문서와 실제 코드/도구 스키마를 다시 확인하고, 필요한 작은 실험·실제 화면·플랫폼 검사로 적용을 검증합니다. 완료한 범위와 남은 범위를 따로 기록합니다.

예: 새 캐릭터에서 무기가 커진다면 고정 스케일 값을 복사하지 않고, 수입 리그의 정규화 스케일과 actor의 의도 스케일을 나눠 실측합니다. 저장 설정이 바뀌었다면 메모리 값뿐 아니라 영구 저장과 새 브라우저 프로세스의 복원까지 확인합니다.

## 묶음 검증과 ZIP 만들기

Python 3.10 이상과 표준 라이브러리만 사용합니다. 게임 엔진·Blender·인증은 필요하지 않습니다. 저장소 루트 또는 이 묶음을 복사한 위치에서 실행할 수 있습니다.

```bash
python reusable/game-production-kit/scripts/package.py --check
python reusable/game-production-kit/scripts/package.py --output build/knowledge/game-production-kit.zip
python reusable/game-production-kit/scripts/package.py --verify build/knowledge/game-production-kit.zip
python reusable/game-production-kit/scripts/package.py --verify-source build/knowledge/game-production-kit.zip
```

묶음을 독립 폴더로 옮겼다면 `python scripts/package.py --check`처럼 실행합니다. ZIP에는 파일별 SHA-256을 기록한 `MANIFEST.json`을 생성합니다. `--verify`는 ZIP 자체, `--verify-source`는 배포 ZIP의 내용이 현재 source 파일과도 일치하는지 확인합니다. 압축 라이브러리 차이로 ZIP byte가 달라질 수 있어 source 일치는 내부 파일별 byte/SHA로 비교합니다. 이 검사는 템플릿 JSON·스킬 메타데이터·로컬 링크·패키지 무결성을 확인하며, 외부 정책의 최신성·아트 품질·대상 프로젝트 실행 성공은 확인하지 않습니다.

## 이후 지식을 추가할 때

- 새 프로젝트에서 검증한 원본 기록은 그 프로젝트에 둡니다. 재현 가능한 공통 원칙만 이 묶음에 반영하고, 프로젝트 전용 치수·주소·성공 수치는 사례로 분리합니다.
- 원인·적용 조건·예외·실패한 시도와 근거를 함께 남깁니다. 미검증 가설은 `pending`, 재현한 실패는 실패 사실의 범위에서 `verified`로 기록합니다.
- 새 판본은 이 문서와 `provenance.json`의 버전·출처 스냅샷을 함께 갱신하고 ZIP을 다시 검증합니다. 기존 소비 프로젝트에는 변경점을 비교한 뒤 적용합니다.
- 권한·비용 승인 범위는 해당 프로젝트의 사용자 지시에서 확인합니다. 인증, 유료 실행 권한, 생성된 게임 애셋의 사용 조건은 방법 지식을 복사한다고 이전되지 않습니다. 기존 승인을 이미 충족한 작업에 불필요한 재승인을 요구하지 않습니다.
- 공개 스킬 원문을 별도로 가져올 때는 그 자료의 리비전·LICENSE·NOTICE를 보존합니다. 이 묶음의 출처 링크는 원문과 적용 판단을 구분하기 위한 것입니다.
