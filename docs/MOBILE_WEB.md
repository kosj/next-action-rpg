# 모바일 웹 조작과 검증

v0.1.6 작업 범위는 키보드 없이 메뉴·이동·시점·전투·상호작용을 조작하는 것이다. 기존 키보드/마우스·패드 입력과 저장 형식은 유지한다. 터치 지원은 자동 감지하며 세로·가로 화면을 지원한다. 실제 기기의 GPU 성능과 iOS Safari 실행은 별도 검수 대상이다.

v0.1.7은 Web에서 미지원인 바이너리 shader cache의 빈 하위 디렉터리 생성을 막는다. [실제33→5키 A/B와 저장·재시작 집중 검사](WEB_USERFS_CACHE.md)는 전체 모바일·공개 주소 승인과 구분한다. 기존 프로필의 저장이나 디렉터리를 삭제하지 않는다.

## 조작

| 동작 | 터치 |
| --- | --- |
| 이동 | 왼쪽 원형 패드. 중심에서 멀수록 빠르게 이동 |
| 시점 | 오른쪽 화면 빈 영역을 드래그 |
| 연속 공격 | `공격` |
| 강공격/차지 | `강공`을 누른 채 유지한 뒤 놓기 |
| 회피/패링 | `회피` / `패링` |
| 달리기 | 이동하면서 `질주`를 누른 채 유지 |
| 룬 스킬 | `룬 1/2/3`. 기존 룬 비용과 판정을 사용 |
| 회복 | `회복`. 회복약·체력 조건은 기존 규칙과 같음 |
| 대화/휴식/기록 | 대상 가까이에서 `대화` |
| 대상 고정/교체 | `조준` / `전환` |
| 일시정지 | 오른쪽 위 일시정지 버튼 |

이동·시점·동작은 각각 다른 손가락을 소유한다. 동작 버튼 밖으로 손가락이 이동해도 해당 버튼의 소유권을 유지하고 놓을 때 해제한다. 화면 회전·초점 상실·취소·메뉴 전환에서는 잔여 입력을 지우며, 필요한 경우 일시정지 화면에서 계속하기로 복귀한다. 이전에 누르던 손가락이 복귀 직후 공격을 시작하지 않도록 처리한다.

## 화면과 입력 계약

[TouchControls](../game/scripts/ui/touch_controls.gd)는 전용 `touch_*` action만 소유한다. 실제 키/패드의 canonical action을 해제하지 않으며, 이벤트와 polling 입력을 기존 게임 동작에 합친다. 짧은 탭·동시 hold·해제는 process/physics frame 경계를 보존한다. 전투 타이밍·피해·캐릭터 속도를 터치 UI가 별도로 소유하지 않는다.

메뉴 터치가 남아 있으면 게임 조작 활성화를 deferred 경계에서 기다린다. GUI 마우스 에뮬레이션과 터치의 전달 순서도 구분해 이동/시점 터치가 공격으로 중복되지 않게 한다. Web의 cancel이 `canceled=false`인 release로 전달되는 경우와 손가락 ID가 연속하지 않은 경우도 처리한다. [공식 근거와 선택적 공개 스킬 적용](MOBILE_WEB_RESEARCH.md)을 참조한다.

UI 논리 크기는 canvas의 실제 CSS client 크기다. DPR을 터치 좌표에 다시 곱하지 않는다. CSS safe-area inset을 읽어 버튼을 배치하고, 작은 화면의 제목·대화·설정·상점은 스크롤할 수 있게 한다. 터치 대상의 폭·높이는 최소44 CSS px, 주요 메뉴는48 CSS px이다. UI 선명도와 3D 렌더 픽셀 수를 분리하고 높은 DPR의 휴대폰에서 3D 해상도를 제한한다. 이것만으로 실제 기기의 프레임 성능을 합격 처리하지 않는다.

## 검증 범위

- [실제 native 입력 fixture](../game/tests/mobile_input_regressions.gd)는 서로 다른 ID17/59/83, 이동·look·공격, 독립 해제, 충전, 키보드 경합, 대화/고정, 메뉴·회전·초점 복귀와 상태 복원을 검사한다. 기존345에터치·종료복원30개가 추가된 [통합375검사·실패0](validation/v0.1.6/native-final.json)을 확인했다.
- [모바일 브라우저 검사](../tools/mobile_browser_smoke.py)는 CDP의 실제 trusted touch 이벤트를 사용한다. 클릭/키보드로 대체하거나 게임 상태·저장을 강제로 수정하지 않는다. 390×844/DPR2·844×390·360×640, 동시 손가락, 실제 저장과 브라우저 완전 재시작을 검사하는 절차다. 실행 결과는 [판본 기록](validation/v0.1.6/README.md)과 [PR #8](https://github.com/kosj/next-action-rpg/pull/8)의 해당 빌드·공개 URL 근거로 확인한다.
- 최초 preview는 제목·프롤로그·휴식·실제 이동/상점을 통과했지만 QA 조향의 feedback/RPC 지연으로 navigation 단계가 실패했다. 전체 통과로 기록하지 않으며 실제 원인과 재실행을 구분한다. 기존15초 UI·30초 IDB 한도는 유지한다.
- Chromium의 모바일 에뮬레이션, 실제 Android/iPhone, Windows 실행, AAA 아트·목표 GPU 성능은 각각 다른 검증 범위다.

```bash
python tools/build.py
python tools/check_mobile_web.py
python tools/check_web.py
```

소프트웨어 GPU 검사는 브라우저 한 개씩 실행한다. 고정 sleep·강제 파일 동기화·QA 상태 쓰기로 검사를 통과시키지 않는다. 같은 입력 기기·viewport·export를 기록하고 실패 화면·실제 pointer trace·저장 관찰을 보관한다.

[회전 후 최종 screen-attach 재진입 오류](validation/v0.1.6/rotation/README.md)는 즉시 입력 정리와 deferred content 설정으로 수정했다. 동일조건 원본 PNG에서360px strip→1688px 전체폭으로 복구됐고, 단일 공식 Playwright 회전 경로에서도 확인했다. 숫자 좌표뿐 아니라 해당 daylight 장면의 실제 raster를 검사한다.

[가로 설정의 Button-start 스크롤](validation/v0.1.6/scroll/README.md)은 모바일 Button/CheckButton의 부모 이벤트 전달로 수정했다. 실제 같은 드래그의0→91·Done·게임복귀·primary값을 확인했으며 Slider 처리는 유지했다. 최종 native375는 [수정후 근거](validation/v0.1.6/native-after-scroll.json)를 참조한다.

[작은 화면으로 복귀할 때 canvas inline 폭 feedback](validation/v0.1.6/canvas-css/README.md)을 CSS 소유권으로 수정했고 [로딩창 제거 후 늦은 callback](validation/v0.1.6/loader/README.md)도 실제 DOM 재현으로 수정했다. 실제 restart 기능과 pageerror 실패를 별도로 보존하며 최종 전체·공개 URL 승인은 PR #8에서 확인한다.
