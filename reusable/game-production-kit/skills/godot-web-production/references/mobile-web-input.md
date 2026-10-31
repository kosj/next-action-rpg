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

## canvas inline CSS와 viewport 피드백

1. 화면을 줄였다가 키우는 연속 resize와 회전을 실제 DOM 환경에서 재현한다. screen/outer 크기, document client 크기, window inner 크기, document scroll 크기, canvas client/bounding rect·inline style·computed style, visualViewport 크기/scale, 엔진 논리 viewport와 bitmap 크기를 같은 시점에 기록한다. 하나의 viewport 지표만 정상이라고 화면 배율을 승인하지 않는다.
2. 엔진의 adaptive canvas sizing이 inline CSS 크기를 쓰는지, 페이지의 CSS 규칙과 어떤 cascade/우선순위로 경쟁하는지 대상 판본의 source와 실제 DOM에서 확인한다. canvas 표시가 페이지보다 커지고 다시 window inner/scroll·자동 축소에 영향을 주는 피드백이 있는지 비교한다. 초기 desktop 또는 landscape 크기가 모바일 표시 크기로 남는지도 검사한다.
3. 페이지가 소유할 CSS 표시 영역과 엔진이 소유할 bitmap/DPR·렌더 해상도를 명시적으로 분리한다. CSS 수정이 필요한 경우 해당 엔진의 sizing/cascade와 호스팅 구조에 맞춰 적용하고 고정 크기나 `!important`를 모든 프로젝트의 영구 기본값으로 강제하지 않는다. 논리 viewport·입력 좌표·safe area도 새 표시 영역과 맞는지 다시 확인한다.
4. 원인 분리는 같은 PCK/데이터·WASM·JS·QA·모델을 유지한 HTML/CSS-only A/B처럼 변경 범위를 고정해 수행한다. 실제 배포 파일 해시와 원본 DOM/이미지를 남기고 다른 엔진 코드·자산 변경이 섞인 비교를 CSS 단독 근거로 쓰지 않는다. DOM 지표를 clamp하거나 DPR을 없애서 기대값만 맞추지 않는다.
5. 수정 후 새 frame에서 DOM 표시 영역·visualViewport scale·논리 viewport·bitmap의 관계를 재측정한다. 실제 PNG가 화면 폭을 채우는지, UI 열/버튼 크기·hit rect와 터치 행동이 일치하는지도 확인한다. 특정 장면의 픽셀 guard나 한 기기의 성공을 다른 화면·엔진·실기기 승인으로 확대하지 않는다. 원래 실패·집중 A/B·최종 브라우저/실기기 검증은 각각 기록하고 미실행 범위는 `pending`으로 둔다.

## 버튼에서 시작하는 스크롤과 이벤트 전달

1. 긴 설정/메뉴의 실제 Button·CheckButton 위에서 시작한 손가락 drag 경로를 유지해 재현한다. 빈 여백으로 시작점을 옮겨 QA를 통과시키거나 scroll 값을 직접 쓰지 않는다. 동일 gesture의 시작 control·좌표·move/end·실제 소유 pointer와 화면을 기록한다. native fixture·브라우저 trusted gesture·실제 휴대기기에서 관찰한 범위는 구분한다.
2. 대상 엔진의 child control `mouse_filter`, Container의 부모 전달, Viewport의 consume/propagation 예외와 ScrollContainer의 drag 경로를 함께 읽는다. wheel만 부모로 강제 전달되는 경로가 있다면 mouse-wheel 성공이 touch drag 성공을 입증하지 않는다. 터치가 emulated MouseDown/Motion으로 부모 drag를 시작하는지도 확인한다. Button에서 이벤트가 멈춰 부모에 닿지 않으면 실제 스크롤이 시작되지 않을 수 있다.
3. 수정은 스크롤 안에서 부모 전달이 필요한 버튼 계층에 한정해 검토한다. Slider처럼 자기 drag를 소유하는 control과 구분하고 모든 control을 일괄 PASS로 바꾸지 않는다. drag 시작/SCROLL_BEGIN 경로가 Button의 pending click을 취소하는지 확인한다. 짧은 tap은 callback이 한 번 발생하고, 스크롤 drag 후 release는 우발적인 클릭·설정 변경·메뉴 닫기를 만들지 않아야 한다.
4. 실제 gesture 후 새 frame에서 scroll value·maximum·page 크기와 콘텐츠 이동, pointer 해제, 실제 control/callback 상태를 함께 관찰한다. 레이아웃 값이나 Done 버튼의 bounding box만으로 스크롤 성공을 판단하지 않는다. 화면 밖 완료 버튼이 화면 안으로 이동했는지 실제 화면과 hit rect를 대조한다.
5. 설정을 바꾼 뒤 같은 실제 스크롤 경로로 완료 버튼에 도달하고 그 버튼을 눌러 설정 반영·저장을 확인한다. callback 직접 호출·빈 여백 gesture·테스트 측 상태/저장 쓰기로 대체하지 않는다. 실패 재현·수정 후 집중 검사·최종 전체 브라우저 검증을 각각 기록한다. native 검사나 export 성공만 확인했다면 수정 후 브라우저·실기기 판정은 `pending`으로 유지한다.

## 로딩 UI 제거 뒤의 비동기 콜백

1. 로딩 완료 Promise나 화면 전환으로 UI를 제거해도 progress 등 비동기 콜백이 더 도착할 수 있다. 등록 시점의 element와 현재 DOM의 수명을 구분하고, 콜백이 실제로 UI에 접근하는 시점에 대상 element와 해당 작업이 여전히 유효한지 확인한다. 특정 guard 문자열을 모든 프로젝트에 고정하지 말고 사용 API의 완료·취소·unmount 계약에 맞춘다.
2. 가능한 경우 cleanup에서 구독 해제·abort를 수행하고, 취소가 보장하지 못하는 이미 예약된 콜백도 안전하게 종료하도록 한다. 이전 작업이 새 화면을 갱신하지 않도록 작업 세대/수명도 구분한다. 정상적인 초기 progress 표시까지 생략해 오류만 없애지 않는다.
3. 실제 DOM에서 초기 콜백의 정상 업데이트, UI 제거, 제거 뒤 늦은 콜백, cleanup 뒤의 반복 호출을 순서대로 검사한다. 실제 shell과 제한된 Engine stub/Promise를 쓰는 집중 fixture는 그 DOM 수명 계약의 근거이며 전체 게임·최종 배포 검증과 범위를 구분한다. 원래 실패와 수정 후 초기 표시/늦은 콜백 완료·오류 결과를 함께 남긴다.
4. 이어하기·설정/영구 저장·복귀 같은 기능이 모두 성공해도 늦은 page error가 있으면 전체 브라우저 검증 실패를 보존한다. 기능 상태와 console/page error를 별도로 기록하고, 늦은 callback까지 관찰하는 종료 경계를 둔다. 오류를 필터로 숨기거나 성공 단계만 합산하지 않는다. 수정 뒤 최종 빌드의 브라우저 실행을 다시 확인하기 전에는 집중 fixture의 성공을 전체 QA로 승계하지 않는다.

## 근거와 승인 범위

엔진 소스는 정확한 리비전, 브라우저 지원은 조회일과 고정 compatibility-data 리비전으로 남긴다. 공개 스킬은 필요한 원칙만 선택하고 원문·참조·LICENSE/NOTICE·리비전·해시를 보존한다. 설치/스크립트 실행 권한을 스킬을 읽었다는 사실에서 추론하지 않는다. 원래 프로젝트의 계정·기기 접근·비용/업로드 권한도 이전되지 않는다. 이미 위임된 현재 작업에 새 승인 절차를 만들지는 않는다.

자동 입력 fixture, desktop touch emulation, 실제 모바일 OS/브라우저, 목표 GPU 성능의 결과를 분리한다. 테스트는 기존 gameplay/UI를 통해 진행하며 입력 상태나 저장을 강제로 고쳐 통과시키지 않는다. console 오류·소유 pointer·action/axis·viewport/CSS/backing·남은 hold와 실제 행동 결과를 기록한다. 과거 지원표나 한 브라우저의 성공을 다른 기기의 승인으로 복사하지 않는다.

## 자동 조작의 피드백과 짧은 상태

이동을 유지한 채 매 제어 단계에서 bounding box를 새로 읽으면 이전 방향/속도가 RPC 응답 동안 계속 적용될 수 있다. 한 gesture의 geometry를 캐시하고 layout 세대가 바뀌지 않았는지 확인한다. 실제 이동 성공을 확인한 뒤 같은 pointer를 중앙으로 되돌리거나 독립 해제하여 보조 검사의 불필요한 이동을 줄인다. 최종 실제 위치·소유권·행동 효과와 합의한 시간 조건은 그대로 검사한다.

회피·release 공격·짧은 스킬은 입력 응답 뒤의 snapshot에서 이미 끝날 수 있다. 실제 입력 전에 별도의 읽기 전용 관찰을 시작해 이후 frame에서 조건이 참인 snapshot을 복사하고 관찰자 자체도 유한 시간 안에 종료한다. 게임/QA 원본·저장 상태에 값을 쓰거나 이벤트 성공을 주입하지 않는다. 실제 발동과 늦은 조회를 구분하고 원래 실패·집중 검사·최종 전체 검사를 각각 보존한다.

자동화 프레임워크가 focus·visibility·사용자 gesture를 강제로 에뮬레이트하는 기본값도 확인한다. 실제 focus loss 검사는 필요한 override만 해제한 뒤 브라우저의 trusted blur/focus와 document 상태를 관찰하고, foreground 복귀 후 실제 게임의 pause·입력 종료를 대조한다. background snapshot/rAF 중단을 앱 취소 실패로 오인하지 않는다. 설정 복원은 finally에서 수행하며 synthetic 이벤트나 QA 상태 쓰기로 대신하지 않는다.

Window 크기 변경 signal 안에서 content-scale setter를 다시 호출하면 외부 엔진 함수가 계산해 둔 최종 screen rect를 나중에 덮을 수 있다. 정확한 엔진 소스의 signal/외부 적용 순서를 확인하고 입력 정리는 즉시, 최신 화면 설정은 coalesced deferred로 수행한다. public geometry와 offscreen texture가 정상이어도 최종 화면은 틀릴 수 있으므로, 같은 driver·품질·장면·자산의 원본 PNG A/B를 확인한다. 픽셀 guard는 해당 장면의 알려진 배경 조건으로 한정하고 어두운 모든 게임에 일반화하지 않는다.

복원용 snapshot의 Node handle은 저장 후 해제될 수 있다. 다운캐스트 전에 실제 유효성을 확인하고 expired fixture를 포함해 복원이 끝까지 실행됐는지 검사한다. assertion 개수 외에 stderr·종료코드·리소스 정리 결과도 검증한다.
