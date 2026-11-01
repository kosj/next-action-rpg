# 다른 프로젝트에 가져가는 제작 지식 묶음

버전 **1.4.4** · 정리일 **2026-11-01**.

기존 프로젝트에서 축적한 지식을 **재사용 절차·실패 사례·작성 템플릿**으로 정리했습니다. 원본 항목 수·ID·상태·고정 커밋은 [출처 스냅샷](provenance.json)을 원본으로 확인합니다. 프로젝트 주소, 캐릭터 치수, Flow ID, 공격 시간, 비용과 용량 목표를 새 프로젝트의 설정으로 강제하지 않습니다. 원래 검증 결과는 출처 사례이며, 가져간 프로젝트의 검증 상태는 새로 기록합니다.

## 필요한 것부터 사용하기

| 구성 | 사용하는 상황 |
| --- | --- |
| [evidence-led-project-memory](skills/evidence-led-project-memory/SKILL.md) | 어떤 프로젝트에서든 결정·실패·근거·검증 상태를 관리할 때 |
| [godot-web-production](skills/godot-web-production/SKILL.md) | Godot 웹/Windows 빌드, 모바일 터치·화면 좌표, 실제 브라우저 입력·저장, 공개 배포를 검증할 때 |
| [모바일 Web 절차](skills/godot-web-production/references/mobile-web-input.md)·[검수 양식](skills/godot-web-production/references/mobile-input-report.json) | 포인터 수명·에뮬레이션·동시 물리 입력과 CSS/viewport·safe area를 함께 검수할 때 |
| [generated-3d-game-art](skills/generated-3d-game-art/SKILL.md) | 생성형 3D·Blender·리그·모션·PBR·아트 품질을 검수할 때 |
| [사례집](HANDBOOK.md) | 문제의 원인, 재사용할 원칙, 다시 확인할 조건을 빠르게 찾을 때 |
| [출처 스냅샷](provenance.json) | 원래 항목의 상태·날짜·고정 커밋 근거를 추적할 때 |

각 스킬 폴더의 `references/`에 해당 템플릿을 함께 넣었습니다. 선택한 **스킬 폴더 전체**만 복사해도 로컬 참조가 유지됩니다. 일반 소프트웨어 프로젝트라면 첫 번째 스킬만 가져가면 됩니다.

## 새 프로젝트에 적용하는 순서

1. 새 프로젝트의 기존 지침과 스킬을 먼저 확인합니다. Codex의 프로젝트 스킬 경로를 쓰는 경우, 원하는 `skills/<이름>/` 폴더를 새 프로젝트의 `.agents/skills/<이름>/`으로 복사합니다. 같은 이름이 있으면 내용을 비교해 합치며 덮어쓰지 않습니다. 다른 클라이언트는 그 클라이언트의 스킬 검색 경로를 사용합니다.
2. 스킬의 `name`·`description`은 유지하고, 프로젝트 `AGENTS.md` 또는 작업 지침에서 사용할 스킬을 연결합니다. 참고용으로 이 묶음을 보관하는 것만으로 모든 클라이언트에 자동 등록되지는 않습니다.
3. 웹/게임 작업에는 [프로젝트 설정 템플릿](skills/godot-web-production/references/project-profile.json)의 빈 값을 채웁니다. 엔진·템플릿·Blender 버전, 프로젝트 경로, 이동/무기 축, 저장 식별자, 배포 주소, 성능·용량 목표를 실제 프로젝트에서 결정합니다.
4. 지식 기록은 [항목 템플릿](skills/evidence-led-project-memory/references/knowledge-entry.json)으로 시작합니다. 템플릿의 자리표시자를 실제 값으로 바꾸고 로컬 근거를 연결하기 전까지 `pending`을 유지합니다. 원래 프로젝트의 `verified`를 새 프로젝트에 복사하지 않습니다.
5. 관련 공식 문서와 실제 코드/도구 스키마를 다시 확인하고, 필요한 작은 실험·실제 화면·플랫폼 검사로 적용을 검증합니다. 완료한 범위와 남은 범위를 따로 기록합니다.

모바일 작업이면 [입력·화면 절차](skills/godot-web-production/references/mobile-web-input.md)를 선택하고 새 프로젝트의 포인터/action 소유권과 좌표 변환을 검수 양식에 기록합니다. desktop touch emulation·소프트웨어 WebGL·실제 Android/iOS와 목표 GPU의 결과를 분리하며, 원래 프로젝트의 권한·기기 접근·QA 통과를 승계하지 않습니다.

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

판본1.1.0은 국소 눈 소켓의 전체 표면 fit, solver 단위/엄밀한 제약, 실제 marker 기반 잔상, imported COLOR_0 사용 flag의 검수 절차를 보완합니다. 원본 엔진의 특정 버그·치수·표본 통과를 대상 프로젝트에 고정하지 않습니다.

판본1.2.0은 모바일 Web의 입력 소유권·GUI 전환·동시 장치 해제·CSS/backing/논리 좌표·safe area·선택적 브라우저 기능과 기기별 증거를 기록하는 절차를 추가합니다. 아트 절차에는 국소 피부 metallic 수정으로 새 경계 이음새가 생긴 실패를 반영합니다. 원래 사례의 자동 검사 통과나 재질 수치 교정을 최종 화면·실기기·아트 승인으로 바꾸지 않습니다.

판본1.2.1은 Web의 미지원 바이너리 캐시가 만드는 저장소 디렉터리와 비동기 순회를 실제 메타데이터·플랫폼 소스·한정 A/B로 확인하는 절차를 추가합니다. 새 프로필의 키 감소, 기존 프로필, 전체 재시작·공개 주소·기기 성능의 승인 범위를 구분합니다.

판본1.3.0은 [전투 기능과 타격감 검수](skills/godot-web-production/references/combat-quality-review.md)를 추가합니다. 사용자 평가·코드/자산·정지 화면·실제1배속 영상/음향·기기 측정과 참고 자료의 종류를 구분하고, 공격자·피격자·카메라·VFX·음향을 같은 접촉 결과에서 비교합니다. 원본의 큰 피해량·클립 수·기능 검사 통과를 최종 AAA 승인으로 승계하지 않습니다.

판본1.4.0은 실제 본의 key 사이 뒤집힘, 반입 후 정밀도·씬 전체 재표본화의 용량 증가, 확정 접촉의 세부 시각과 멈춘 검/잔상의 시계를 함께 검사하는 절차를 보완합니다. 원본 관측과 새 프로젝트의 재검증을 나누며, 표본율이나 허용오차를 그대로 복사하지 않습니다.

판본1.4.1은 전체 검 소켓과 실제 날 구간·캡슐 반구 중심축을 분리하고, 근접 겹침의 충돌 복구까지 실제 밀려남 예산에서 소비하는 검수 절차를 보완합니다. 이전 CI 통과에서 뒤늦게 발견한 손잡이 접촉·과도한 밀림을 기각한 근거를 보존합니다.

판본1.4.2는 참고 영상의 공개 판본·제공자 요약·저품질 미리보기와 실제 프레임/청취의 근거를 구분하는 절차를 추가합니다. 편집된 영상의 시간과 인코딩FPS를 게임 내부 시간·성능으로 바꾸지 않으며, 검증한 기존 기능과 새 시청각·기기·AAA 승인을 분리합니다.

판본1.4.3은 표시용 손·검 정합과 본의 local/global 회전·속도를 따로 검사하는 절차, 실제 idle와 반열린 마지막 프레임의 복귀 비교, 충돌 root와 시각 발 보정의 경계, 정확한 actor/visual 바닥 배치와 오프라인 논리1배속 자료의 검증 범위를 보완합니다. 새64번째 사례는 실패 후보와 수정한 로컬 기능·표본 근거를 보존하며 전체 AV·실기기·AAA 승인을 부여하지 않습니다.

판본1.4.4는 재저작한 active 동작과 게임용 칼날 곡선의 출처·좌표·표본·pin을 함께 검증하고, 준비 자세의 이른 겹침 예측과 실제 접촉을 구분하는 절차를 보완합니다. 무기 profile의 같은 atlas/PBR 재사용·raw 보존과 native 반입 양자화/triangle 대응, 전체 팔 수치와 새 국소 피부 악화, zero-point provider 참고 후보와 실제 채택의 경계를 기록합니다.65번째 원본 사례는 pending이며 묶음 무결성·기능 검증을 새 프로젝트의 실행·시각·실기기·AAA 승인으로 승계하지 않습니다.
