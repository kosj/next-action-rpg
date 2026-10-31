# v0.1.5 최종 로컬 Web 일반 플레이 검증

**PASS — 471.812초, exit0, browser errors0.** 실제 실행 빌드는 `0.1.5 · c6be1dce`이며 `RUNEFALL_EXPECTED_COMMIT=c6be1dce6cc6d5a6c41e3728d377a0a0bc5ee174`로 확인했습니다. Godot4.7.2의 최종 `build/web`을 대상으로 원본 `tools/check_web.py`를 실행했습니다. 고정 아트 fixture가 아닌 실제 Game/UI/입력/물리/저장 흐름입니다.

| 검증 | 실제 결과 |
| --- | --- |
| 새 프로필·새 여정·프롤로그·일시정지/설정 UI | 통과 |
| 안전 접근 구역 품질1→0→1 | HP120 유지, encounter−1, 같은 위치 유지 |
| 실제 좌클릭 공격 | `light_1`·실제 RightHand 변화·idle 복귀 확인 |
| 리라·무기·눈 | 모든 관찰에서 skeletal/hero, eyes_attached=true, Grip→Tip1.19m 허용범위 통과 |
| 실제 Tab·좌클릭10회·Space 전투 | 일반 근접 수호병3명 모두 skeletal/sentinel_melee, HP120, hits4 |
| 실제 영구 저장 | primary quality0·1 커밋 확인; readonly8회, 최장14.027초 |
| 브라우저 완전 종료 후 같은 프로필 재실행 | quality1, checkpoint0, z6, HP120, skeletal hero·눈·무기 복원 |
| 실행 파일/입력 고정 | 시작/종료의 source·asset9개 및 실제 Web 파일 SHA 동일 |

UI 조건15초·readonly 저장/커밋30초 한도와 기존 assertion을 유지했습니다. 실제 입력으로만 게임을 진행했고 QA 상태 쓰기, 강제 파일 동기화, 고정 sleep으로 저장 통과를 만들지 않았습니다. IndexedDB는 발견 시 key34개를 조회하고 primary payload1개만 읽었으며, 같은 페이지의 후속 읽기는 발견된 primary 경로를 직접 조회했습니다. 브라우저 재시작 시 경로를 다시 발견했습니다.

공격 상태 표본은 늦은 recovery인 sampled_time .516667초입니다. RightHand 변화는 Skeleton-local 이동 .000913·회전 .009022rad이며, 이때 ribbon은 이미0samples/hidden입니다. [08-skeletal-attack.png](08-skeletal-attack.png)를 active trail 가시성 승인으로 해석하지 않습니다. 트레일의 active-window/수명 검사와 고정 아트 비교는 별도 근거입니다. [실제 전투](04-gameplay.png)와 [재시작 이어하기](05-continue.png) 원본도 보존했습니다.

[character-qa-summary.json](character-qa-summary.json)에 결과·소스 SHA·모드·손뼈 변화·저장·재시작 수치가 있습니다. [run-context.json](run-context.json)은 시작 시점 manifest와 실제 Web 파일/입력 해시를 고정합니다. [browser-progress.json](browser-progress.json)과 [run.log](run.log)는 단계별 시간, [browser-storage-diagnostics.json](browser-storage-diagnostics.json)은 실제 readonly 요청 추적, [browser-errors.json](browser-errors.json)은 오류0을 기록합니다. [evidence-manifest.json](evidence-manifest.json)은 이 폴더 증거의 byte/SHA를 검증합니다.

단일 Chromium SwiftShader로 실행했으며 다른 무거운 작업과 겹치지 않았습니다. 로딩을 포함한 rAF 최대 간격은 첫 브라우저25,482.3ms, 재시작16,882.7ms였습니다. 이는 소프트웨어 렌더러에서의 기능 검증이며 목표 GPU/60fps 성능 승인이 아닙니다. Windows 실제 실행·공개 Pages/CI·최종 AAA 아트 승인도 이 실행의 범위 밖입니다. d7d 눈의 어두운 주변부/강한 응시는 별도 아트 제한으로 남아 있습니다.

재현 명령은 `RUNEFALL_EXPECTED_COMMIT=c6be1dce6cc6d5a6c41e3728d377a0a0bc5ee174 python tools/check_web.py`입니다. 시작·종료 측정 wrapper는 source를 수정하지 않고 원본 도구를 `runpy`로 호출했습니다. 최종 출력 후 두 Chromium·로컬 HTTP 서버/thread가 종료됐고 live Chromium0을 확인했습니다. 추가 export·게임 소스 변경은 하지 않았습니다.
