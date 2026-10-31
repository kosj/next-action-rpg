# 모바일 Web 입력과 화면 좌표 검수 절차

대상 프로젝트의 실행 검증 상태는 `pending`에서 시작한다. 이 절차는 다른 프로젝트의 엔진 판본·브라우저 지원표·버튼 크기·감도·전투 값·성공 결과를 이전하지 않는다. 공식 문서와 실제 실행 엔진의 고정 소스를 대조한 뒤 적용한다.


[프로젝트 설정](project-profile.json)의 입력·화면 계약을 실제 값으로 채우고 [모바일 검수 양식](mobile-input-report.json)에 입력·좌표·브라우저·기기 증거를 나눠 기록한다. 저장·배포 검증은 [웹 검수 보고서](web-qa-report.json)와 연결한다.

## 입력 계약

1. 실제 게임이 polling으로 읽는 action과 이벤트로 읽는 action, 연속 축·hold·단발 edge를 구분한다. 터치는 기존 이동·피해·공격 시간의 권한 앞에 입력을 제공하고 별도의 전투 실행 경로를 만들지 않는다.
2. pointer index는 생존 기간 동안의 식별자로 취급한다. 순서·개수·연속 배열 위치로 추정하지 않는다. 시작할 때 이동/look/버튼 소유권을 정하고 같은 ID의 이전 위치를 보관한다. release·cancel·영역 밖 해제·알 수 없는 ID·재사용 ID를 검사한다.
3. 해당 Web backend가 browser cancel을 어떤 엔진 이벤트로 변환하는지 읽는다. cancel flag만 기다리지 않고 실제 release 경로도 정리한다. pause·modal·타이틀·복귀·초점 손실·비활성화·resize 때 소유권/hold/잔여 look를 정리하되 다른 입력 장치의 상태는 보존한다.
4. 터치와 에뮬레이션 마우스 중 어느 이벤트가 먼저 전역 상태와 GUI에 전달되는지 확인한다. handled가 polling 상태까지 취소한다고 가정하지 않는다. 에뮬레이션 setter의 자동 해제 여부와 Button의 press/release activation 조건은 실제 판본의 소스로 확인한다.
5. GUI 콜백이 원래 touch 이벤트보다 먼저 재진입할 수 있으면 활성화 전환을 안전한 deferred 경계에서 commit한다. 모든 GUI pointer가 끝났는지 확인하고 시작 버튼 터치가 플레이의 이동·공격으로 승계되지 않게 한다. 기본 release 버튼, press-mode, 키보드로 메뉴 닫기, 다른 손가락 hold를 따로 검사한다.
6. 입력 장치별 action 소유권을 나눈다. 터치가 만든 alias만 해제하고 실제 키/패드가 쓰는 canonical 상태를 지우지 않는다. 상태 주입 API와 이벤트 전달 API의 차이를 확인하고 이벤트 handler에도 alias 의미를 연결한다.
7. merged pressed 상태가 실제로 바뀐 때에만 edge를 만든다. 현재 process/physics loop의 공식 frame stamp 규칙과 호환 설정을 확인한다. 짧은 tap·같은 frame의 press/release·장치가 겹친 hold/release에서 실제 gameplay 효과까지 검증한다.
8. 방향별 strength·원형 deadzone·대각선 제한과 장치 병합 정책을 명시한다. deadzone을 중복 적용하거나 최종 이동 벡터를 항상 normalize해 아날로그 속도를 잃지 않게 한다. 방향을 구하는 정규화와 이동 크기는 구분한다.

## 화면 계약

- CSS client 좌표, canvas backing pixels, 엔진 논리 viewport, 개별 Control 로컬 좌표의 각 변환을 추적한다. 이미 변환된 엔진 이벤트에 DPR을 다시 곱하지 않는다.
- 화면 UI의 논리 크기와 렌더 해상도/픽셀 예산을 나눠 정한다. 런타임에는 실제 Window/Viewport 속성을 변경하고 anchors·containers·resize 신호로 재배치한다.
- drag의 relative/screen_relative가 stretch에 영향을 받는지, Web backend가 그 전에 어떤 배율을 적용했는지 확인한다. look 감도의 단위를 CSS 거리·논리 거리·화면 분율 중 하나로 명시한다. 포인터별 이전 position으로 delta를 계산하면 다른 손가락의 전달 순서에 의존하지 않는다.
- native safe-area API가 Web에서도 구현됐는지 확인한다. Web은 CSS safe-area 환경 값과 실제 canvas rect를 교차해 필요한 inset만 논리 좌표로 한 번 변환한다. canvas padding을 중복 적용하지 않는다. viewport meta, 주소창 변화·회전·fullscreen 전후를 검사한다.
- Pointer Lock·fullscreen은 실제 브라우저의 사용자 gesture/권한·실패를 다룬다. 터치 이동/look와 인라인 플레이가 선택 API에 의존하지 않게 한다. 기능 존재·요청 성공·실제 게임 동작은 각각 확인한다.

## 근거와 승인 범위

엔진 소스는 정확한 리비전, 브라우저 지원은 조회일과 고정 compatibility-data 리비전으로 남긴다. 공개 스킬은 필요한 원칙만 선택하고 원문·참조·LICENSE/NOTICE·리비전·해시를 보존한다. 설치/스크립트 실행 권한을 스킬을 읽었다는 사실에서 추론하지 않는다. 원래 프로젝트의 계정·기기 접근·비용/업로드 권한도 이전되지 않는다. 이미 위임된 현재 작업에 새 승인 절차를 만들지는 않는다.

자동 입력 fixture, desktop touch emulation, 실제 모바일 OS/브라우저, 목표 GPU 성능의 결과를 분리한다. 테스트는 기존 gameplay/UI를 통해 진행하며 입력 상태나 저장을 강제로 고쳐 통과시키지 않는다. console 오류·소유 pointer·action/axis·viewport/CSS/backing·남은 hold와 실제 행동 결과를 기록한다. 과거 지원표나 한 브라우저의 성공을 다른 기기의 승인으로 복사하지 않는다.
