---
name: godot-web-production
description: Build and validate Godot Web/Windows projects with reproducible toolchains, mobile touch and responsive viewport mapping, real input and durable browser saves, exact-commit publishing and clean asynchronous shutdown. Use for game integration tests, mobile web controls, web exports, release automation or deployment failures.
---

# Godot 웹 제작과 배포 검증

## 시작 조건

[프로젝트 설정](references/project-profile.json)을 실제 값으로 채웁니다. 엔진 binary와 export templates의 버전, 앱 버전, 렌더 경로, 프로젝트 경로, 저장 파일/스키마, 입력 규칙, 배포 서비스와 목표 기기를 확인합니다. 기존 프로젝트 도구를 우선하고 시스템 `godot`가 원하는 버전이라고 가정하지 않습니다.

아래 엔진 내부 구현 사례는 **Godot4.7.2에서 확인한 사례**입니다. 대상 버전의 공식 문서·소스·실제 실행과 다시 대조합니다. 특정 버전, 호스팅 서비스, 용량이나 timeout을 모든 프로젝트의 기본값으로 고정하지 않습니다.

## 게임 상태·입력·저장 계약

1. 공격의 준비/판정/회복과 무적·경직·이동은 게임 코드의 실제 시간을 원본으로 삼습니다. 프레임 정수로 반올림하거나 표현용 클립 이벤트로 피해를 중복 실행하지 않습니다. 베기 궤적과 원형 범위의 안쪽 대상도 실제 collision query로 검사합니다.
2. 패링 성공/실패, 사망·복귀·체크포인트 재개는 콤보·버퍼·무적·경직·예약 효과와 표현 epoch를 함께 정리합니다. 상태명뿐 아니라 남은 타이머와 실제 행동 효과를 검사합니다.
3. UI 재개/이어하기 클릭과 게임 공격 입력이 같은 이벤트를 공유할 수 있습니다. UI가 소비한 입력을 구분하고 필요한 release/fresh-press 경계를 사용합니다. 임의 긴 cooldown으로 입력 누수를 숨기지 않습니다.
4. 저장은 스키마·자료형·유한 값·범위를 검증합니다. 검증된 primary만 backup으로 회전하고 실패 시 기존 정상 파일을 보존합니다. 설정 저장과 실제 여정 시작을 구분합니다. 대상 파일시스템의 실제 rename/write 실패를 검사합니다.
5. headless fixture에서 autoload·전체 씬이 필요하면 실제 Node/SceneTree 수명을 유지합니다. 입력 주입은 process/physics 신호 경계와 `just_pressed`·실제 행동을 함께 확인합니다. fixture 오류를 게임 판정 완화로 해결하지 않습니다.

## 모바일 Web 입력과 반응형 화면

터치·작은 화면을 지원할 때는 [모바일 입력·좌표 절차](references/mobile-web-input.md)를 읽고 [모바일 검수 양식](references/mobile-input-report.json)을 현재 프로젝트의 근거로 채웁니다. pointer ID별 이동/look/버튼 소유권과 모든 terminal 경로, 에뮬레이션 마우스의 전달 순서·GUI 재진입, 장치별 action 해제 범위와 merged edge를 함께 검사합니다. 터치 cleanup이 실제 키/패드 hold를 지우거나 메뉴를 닫은 손가락이 공격으로 이어지지 않게 합니다. 상태 주입과 이벤트 전달 API를 구분하고 해당 엔진의 process/physics frame 규칙을 확인합니다.

CSS client·canvas backing·논리 viewport·Control 로컬 좌표와 렌더 픽셀 예산을 나눠 기록합니다. 이미 변환한 이벤트에 DPR을 다시 적용하지 않습니다. runtime Window/Viewport 크기와 UI anchors/containers, native/Web safe area 차이·실제 CSS/canvas 변환, resize/회전·주소창 변화를 검수합니다. fullscreen·Pointer Lock은 실제 지원·gesture·거부를 확인하는 선택 기능으로 두고 인라인 touch 조작을 보존합니다.

desktop touch emulation·native 입력 fixture·실제 Android/iOS 브라우저·목표 GPU 성능의 결과를 각각 남깁니다. 원래 프로젝트의 기기 접근 권한·계정·QA 상태는 승계하지 않습니다. 이미 위임한 현재 작업에 별도 승인 절차를 새로 만들지는 않습니다. 휴대기기를 실제로 검사하지 못했으면 해당 검증은 `pending`입니다.

## 웹에서 실제 저장을 확인하는 방법

UI/메모리에 설정이 바뀐 것과 IndexedDB에 저장된 것은 서로 다른 관찰입니다. 다음 절차를 실제 대상 Godot 버전의 저장 경로/구조에 맞춥니다.

1. 테스트 전용 새 브라우저 프로필에서 정상 UI로 여정을 시작하고 설정을 바꿉니다.
2. 비동기 저장을 제한 시간 안에 조건 대기합니다. Godot4.7.2의 IDBFS 사례에서는 다음 프레임의 동기화가 실제 커밋을 진행했습니다. 중복 강제 sync를 넣어 저장 결함을 수정했다고 기록하지 않습니다.
3. 전용 프로필의 실제 저장소를 **읽기 전용**으로 관찰합니다. IDBFS/`FILE_DATA`를 사용하는지 먼저 확인합니다. 키를 발견한 뒤 primary payload만 읽고, 후속 관찰에서는 발견한 키를 직접 읽습니다. 스키마 upgrade는 중단하고 게임 저장을 테스트에서 쓰지 않습니다.
4. `wait_for_function(async ... )`가 비동기 결과를 원하는 방식으로 반복 검사한다고 가정하지 않습니다. Promise 처리와 polling은 사용 버전에서 확인합니다. 브라우저의 async 읽기를 실제로 await한 다음 값으로 조건을 검사하고, 제한된 재시도를 합니다. 진단에는 단계·frame gap·커밋 전후 값을 남깁니다.
5. 품질/저장 대기는 적 없는 실제 접근 구역에서 수행하고 전투는 별도 구간에서 검사합니다. QA 전용 상태 변조로 무적·위치·저장 완료를 만들지 않습니다.
6. 브라우저 프로세스를 완전히 종료한 뒤 **같은 프로필**로 새 프로세스를 시작합니다. 실제 이어하기 UI와 여정·설정·캐릭터/장비 복원, 입력 가능 상태를 확인합니다. 페이지 reload만으로 재시작 검증을 대신하지 않습니다.

[웹 검증 보고서](references/web-qa-report.json)에 코드/빌드 식별자·실제 상태·오류·저장 관찰·재시작을 함께 기록합니다. timeout은 목표 환경과 측정 근거에서 정하고, 실패하면 렌더링/프레임 정지·API 단계·저장 실패를 구분합니다. 한도 증가·고정 sleep·상태 조작만으로 실패를 지우지 않습니다.

## 비동기 오디오와 종료

Godot4.7.2에서는 `AudioPlayer.stop()`이 player의 참조를 비운 후에도 AudioServer가 fade/mix/cleanup까지 playback을 보유할 수 있었습니다. `playing=false`나 짧은 고정 timer는 최종 해제 증명이 아닙니다.

대상 버전에서도 같은 수명 모델이면, 정지·stream 해제·노드 삭제와 지연 callback 차단을 구현하고 WeakRef 등으로 실제 playback/노드 해제를 유한 시간 안에 확인합니다. 대기 중 강한 참조를 보유하지 않습니다. epoch를 구분해 과거 finished callback이 새 player를 재생하지 않도록 하며 반복 중지·명시적 재개도 확인합니다. assertion 성공 뒤의 engine stderr와 종료 코드까지 검사합니다.

## 빌드·공개 배포·릴리스

1. 실제 엔진/템플릿·태그/앱 버전 일치, import/코드 검사와 변경에 맞는 회귀를 완료합니다. 문서만 바꿨다면 불필요한 엔진 검사를 반복하지 않습니다.
2. 호스팅과 같은 하위 URL에서 export를 서빙하고, 실제 브라우저로 입력·전투·품질 모드·저장 재시작을 검사합니다. HTML 파일을 직접 연 결과와 구분합니다.
3. 원시 Web 파일 합계·전송 ZIP·메모리를 따로 측정해 프로젝트 예산과 비교합니다. Windows export 성공과 Windows 실기기 실행/성능을 구분합니다.
4. 빌드에 source commit 식별자를 넣습니다. 로컬 dirty export·PR 합성 merge·병합 main·태그의 식별자를 혼동하지 않습니다. 배포 성공 후 공개 HTTPS 주소가 **예상 commit의 빌드**를 실제 실행하는지 확인합니다.
5. GitHub Pages를 쓴다면 repo 공개와 최초 Pages 활성화는 별개입니다. 이미 설정됐으면 반복 승인/활성화를 요구하지 않습니다. 기본 workflow token의 관리 권한을 추정하지 말고 실패한 API/작업의 실제 scope를 확인합니다.
6. CLI·Git·연결 앱의 인증은 각각 다른 상태일 수 있습니다. 한 경로의401을 서비스 전체 접근 불가로 일반화하지 않습니다. 지원 클라이언트를 사용하고 인증 값을 추출하지 않습니다.
7. 클라우드 Chromium의 CA 문제는 배포 장애와 구분합니다. TLS 검증을 유지한 클라이언트/정상 trust 환경/hosted runner에서 비교하고 인증서 검증을 끄지 않습니다.
8. 릴리스에 실제 첨부된 manifest·ZIP을 다시 받아 버전/commit·byte 수·SHA256·ZIP CRC·실행 파일·의존 notices를 확인합니다. 검증한 source와 배포 대상의 관계를 영구 workflow/release 링크로 남깁니다.

## 공식 근거와 한계

- [Godot 웹 export](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html): 실제 target 버전 문서로 다시 확인합니다.
- [4.7.2 웹 저장 구현](https://github.com/godotengine/godot/blob/4.7.2-stable/platform/web/os_web.cpp).
- [4.7.2 AudioPlayer 내부](https://github.com/godotengine/godot/blob/4.7.2-stable/scene/audio/audio_stream_player_internal.cpp)·[AudioServer](https://github.com/godotengine/godot/blob/4.7.2-stable/servers/audio/audio_server.cpp).
- [configure-pages 입력/권한](https://github.com/actions/configure-pages/blob/v5/action.yml): 사용할 action 판본과 대조합니다.

구조·headless·소프트웨어 WebGL 통과는 실제 목표 GPU의 프레임 시간·컨트롤러·플레이 시간·최종 아트 승인이 아닙니다. 게임 코드의 목표와 실제 측정 결과를 따로 기록합니다.
