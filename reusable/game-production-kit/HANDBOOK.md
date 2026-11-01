# 재사용 가능한 실패 사례와 제작 원칙

이 문서는 특정 게임의 설정을 복사하기 위한 문서가 아닙니다. **관찰 → 원인/한계 → 재사용할 원칙 → 목표 프로젝트에서 다시 확인할 값**을 연결합니다. 판본 **1.4.2**의 원본 항목 수·ID·상태·날짜·고정 커밋 근거는 [provenance.json](provenance.json)에 있습니다. 아래 ID는 그 출처를 찾는 키입니다.

주요 원관찰 환경은 Godot4.7.2·Blender4.3.2·Playwright1.62입니다. Blender 새 판본 실험이나 클라우드 브라우저의 상태는 해당 실험의 결과입니다. 새 프로젝트·다른 버전에서도 동일하다는 보장은 아니며, 과거 `verified`나 비용/치수를 목표 프로젝트의 현재 값으로 가져오지 않습니다.

## 프로젝트 기억과 실험

| 사례/출처 ID | 재사용할 원칙 | 목표 프로젝트에서 확인할 것 |
| --- | --- | --- |
| `toolchain-version-pin`, `blender-lts-batch-exit` | binary·템플릿 버전을 명시한다. 출력 파일 생성과 배치 정상 종료를 각각 검사한다. | 실제 실행 binary, export templates, 앱 버전, 프로세스 exit/timeout. 새 Blender가 출력했다고 바로 제작 기준을 바꾸지 않음 |
| `public-skills-provenance` | 공개 스킬의 원문·리비전·해시·LICENSE/NOTICE를 보존하고 프로젝트 판단을 분리한다. | 현재 공식 문서, 원문 변경, 적용할 부분과 적용하지 않을 부분 |
| `workspace-resume-checkpoints` | 비용이 큰 작업의 재개 정보를 지속되는 작업 위치에 기록한다. | 환경 교체 시 유지되는 경로, 완료 task ID·상태·원본 해시·실제 비용 |
| `headless-integration-lifecycle` | autoload/전체 씬이 필요한 테스트는 실제 노드 수명과 종료까지 다룬다. | runner 구조, 예약 coroutine, 노드/리소스 해제, stderr |
| `portable-production-knowledge-kit` | 프로젝트 사례·일반 절차·빈 템플릿을 분리하고 독립 경로의 ZIP 무결성과 source 일치를 검증한다. | 고정 출처·판본·파일별 manifest·복사한 스킬의 독립성. 원본 검증 상태를 대상에 승계하지 않음 |
| `headless-input-injection-boundary` | 입력 주입 시각과 게임의 실제 just-pressed 처리 경계를 함께 확인한다. | process/physics 신호 순서, 실제 행동 발생과 입력 해제 |

비용·권한·상태를 추측으로 채우지 않습니다. 외부 목록이 비거나 CLI가 실패하면 실제 도구 발견·읽기 호출·지원 API의 실패 범위를 확인합니다. 한 도구의 인증 오류가 다른 연결 경로까지 사용할 수 없다는 뜻은 아닙니다.

## 전투·복귀·저장·입력

| 사례/출처 ID | 재사용할 원칙 | 목표 프로젝트에서 확인할 것 |
| --- | --- | --- |
| `combat-swept-hit-query` | 베기 궤적의 연속 구간과 원형 범위 내부를 실제 물리 query로 검사한다. | 공격 거리/각도, sampling 간격, 안쪽 대상·대형 collider·한 공격의 중복 적중 |
| `parry-and-restore-state` | 성공·실패·복귀는 관련 타이머·버퍼·예약 효과를 함께 취소한다. | 경직·무적·콤보·쿨다운·지연 이벤트·새 생명/표현 epoch |
| `save-validated-backup` | 검증된 정상 primary만 backup으로 회전하고 실패 시 정상 상태를 보존한다. | 스키마/자료형/유한 값/범위, 쓰기·rename 실패와 롤백 |
| `save-settings-vs-journey` | 설정 저장과 실제 플레이 여정 시작은 서로 다른 상태다. | 타이틀 이어하기 조건, 새 게임/설정만 저장/복귀 시나리오 |
| `web-input-after-ui` | UI 클릭이 곧바로 공격으로 누수될 수 있다. 이벤트 소비와 fresh-press 경계를 둔다. | 마우스/패드/키보드별 재개 입력, 실제 공격 효과 |
| `touch-input-alias-lifecycle` | pointer 소유권과 장치별 action 해제 범위를 나누고 merged edge·GUI 전환을 검사한다. | cancel/release·초점/복귀·에뮬레이션 재진입, 동시 물리 입력·process/physics 경계. native fixture 통과와 실제 Web을 구분 |
| `mobile-driver-feedback-and-transient-observation` | 실제 입력 전에 짧은 상태의 읽기 전용 관찰을 시작하고, 같은 gesture의 geometry를 반복 조회하며 이전 입력을 오래 유지하지 않는다. | 입력 응답 지연·미래 frame snapshot·최종 실제 위치·pointer 종료·유한 시간. driver 실패와 앱 결함, 집중/전체 통과를 구분 |
| `charge-held-end-pose-regression` | 상태명이나 손가락 변화만으로 차지/장전 동작을 승인하지 않는다. | 끝 시점의 실제 몸/무기 이동, 임계 이후 hold, 취소와 release 타이밍 |

게임 코드의 초 단위를 클립 제작의 원본으로 씁니다. 클립이 부족하다고 피해 창을 임의로 늘리거나 검을 길게 만들어 접촉 문제를 숨기지 않습니다. 표현과 판정의 불일치는 실제 영상·marker·게임 데이터를 함께 보며 해결합니다.

## 웹 검증과 배포

| 사례/출처 ID | 재사용할 원칙 | 목표 프로젝트에서 확인할 것 |
| --- | --- | --- |
| `web-persistence-test`, `web-idbfs-async-commit` | 메모리/UI 상태와 durable commit을 분리하고 완전 종료·같은 프로필 재시작까지 검사한다. | 실제 저장 backend/primary key, 동기화 시점, 재시작 후 설정·진행 |
| `web-unsupported-shader-cache-userfs-directories` | 저장 대기 변경 전에 userfs 키와 cache 기능의 플랫폼별 실제 지원을 조사하고, 미지원 cache의 디렉터리 생성과 유효한 load/save를 구분한다. | 읽기 전용 metadata·고정 source, fresh/기존 프로필과 남는 디렉터리, shader compilation·품질·다른 플랫폼 보존. 키 변화와 primary 커밋·재시작·공개 QA는 별도 판정 |
| `browser-quality-before-combat` | 설정/저장 대기를 안전 구역에 배치하고 전투 검증을 별도로 유지한다. | 정상 입력으로 접근할 수 있는 구역, 검사 중 실제 HP/진행 보존 |
| `pages-public-deployment`, `pages-enablement-blocker` | repo 공개, 호스팅 최초 활성화, 배포, 공개 URL 실행은 별개 상태다. 해결된 과거 제약을 다시 현재 제약으로 쓰지 않는다. | 현재 Pages 설정과 token scope, 실제 실패 작업, 공개 빌드 식별자 |
| `release-assets-ci-token` | 릴리스 첨부는 해당 작업에 맞는 현재 인증 경로로 처리한다. | CLI·연결 앱·CI token 각각의 실제 권한과 만료 상태 |
| `public-browser-ca-trust` | 클라우드의 CA 신뢰 문제와 배포 장애를 구분하고 TLS 검증을 유지한다. | 정상 trust 환경/hosted runner의 실제 결과, URL·source commit |
| `web-loader-progress-after-dom-removal` | 로딩 UI 제거 뒤 도착하는 비동기 callback의 현재 element·작업 수명을 확인하고 cleanup/abort와 늦은 호출을 함께 다룬다. | 실제 DOM의 초기 표시·제거·late callback·cleanup, 기능 상태와 page error의 별도 판정. 집중 fixture 성공을 최종 브라우저 QA로 승계하지 않음 |
| `mobile-css-viewport-and-evidence` | CSS client·canvas backing·논리 viewport를 한 번씩 변환하고 native/Web safe area와 선택 API를 구분한다. | resize/회전·DPR·버튼 hit rect·UI 넘침·fullscreen 거부·브라우저 기능. 에뮬레이션과 실제 기기 증거를 분리 |
| `web-canvas-inline-css-viewport-feedback` | adaptive canvas의 inline CSS와 페이지 cascade가 viewport에 만드는 피드백을 확인하고 CSS 표시 영역과 bitmap/DPR 소유권을 분리한다. | 축소→확대·회전의 client/inline/computed/inner/outer/scroll·visualViewport scale·논리/bitmap 대조, 동일 산출물의 CSS-only A/B와 실제 PNG·터치 행동. 지표 clamp나 DPR 제거로 통과시키지 않음 |
| `touch-scroll-button-event-propagation` | 실제 버튼 위에서 시작한 scroll gesture를 보존하고 child consume·부모 전달·drag 시작 시 pending click 취소를 함께 검사한다. | wheel/touch 경로와 Slider 소유권 구분, 새 frame의 scroll value·콘텐츠 이동·pointer 해제·callback/우발 클릭, 실제 완료 버튼을 통한 설정 저장. 수정 후 브라우저 검증은 별도 |
| `godot-window-resize-reentrant-screen-attach` | 크기 변경 signal 안의 content-scale setter 재진입을 피한다. 입력은 즉시 종료하고 화면 설정은 외부 처리 후 deferred로 모은다. | CPU/public transform이 정상이어도 최종 screen attach가 오래될 수 있다. 동일 조건 원본 raster A/B와 대상 장면 이미지 guard를 사용 |

비동기 저장 관찰은 읽기 전용으로 수행합니다. 키 발견과 primary 읽기를 분리하고 관련 없는 payload를 전부 읽지 않습니다. async 결과는 실제로 await하고 그 값으로 제한된 반복을 합니다. 실패 시 단계별 저장/프레임 진단을 남기며 테스트가 저장을 쓰거나 강제 동기화하지 않습니다.

로컬 dirty export·PR용 합성 merge·main·태그는 서로 다른 source 식별자일 수 있습니다. 각각의 실제 빌드 번호를 기록하고 공개 주소가 기대한 commit을 실행하는지 확인합니다. 릴리스 파일은 실제 첨부를 다시 내려받아 bytes·SHA256·ZIP CRC·필수 실행 파일·의존 notices를 대조합니다.

[모바일 Web 절차](skills/godot-web-production/references/mobile-web-input.md)는 터치 소유권·해제·GUI 활성화와 화면 좌표를 함께 확인합니다. 재사용할 것은 경계와 검수 방법이며 특정 브라우저 지원표·감도·버튼 위치가 아닙니다. 이전의 native 회귀나 desktop touch fixture 통과를 실제 휴대기기의 실행·가독성·성능 승인으로 승계하지 않습니다. 현재 권한·계정·기기 접근 범위도 대상 프로젝트에서 확인합니다.

## 생성형 3D·Blender·애니메이션

| 사례/출처 ID | 재사용할 원칙 | 목표 프로젝트에서 확인할 것 |
| --- | --- | --- |
| `varco-official-mcp`, `varco-client-connection`, `varco-first-candidate` | 도구 존재·현재 연결·OAuth·실제 도구 호출을 구분한다. 완료 task를 입력으로 고정하고 명시 scope를 사용한다. | 현재 공식 MCP 스키마, 실제 Flow/노드/task, 완료 상태와 실행 범위 |
| `varco-generation-license` | 생성 당시 공개 범위·라이선스·원본·파생 권리와 실제 비용을 자산별로 기록한다. | 현재 정책, 입력 이미지/모션 권리, 상업 사용과 원본 재배포의 구분 |
| `varco-stock-duplicate-endpoints` | 원본의 중복 timestamp를 보존하고 별도 파생 재샘플을 검사한다. | 엄격한 구조 검사, motion fidelity, 전체 타이밍·loop |
| `varco-remesh-measured-budgets` | 삼각형 감소와 파일/텍스처 크기·리그·재질·프레임 비용은 별개다. | 실제 출력 수치, 이미지 재베이크, 메모리·실행 화면 |
| `skeletal-candidate-origin-normalization`, `armature-translation-roll-precision` | 공통 원점 이동을 먼저 증명하고 rest/topology/named weights를 보존한다. 변환 API의 roll/basis 오차를 검사한다. | 같은 리그인지, 허용오차, 전체 본/메시 관계와 표본 포즈. 실패를 허용오차 확대로 통과시키지 않음 |
| `importer-bone-display-helpers` | importer가 추가한 bone custom-shape helper와 실제 메시를 구분한다. | source 메시/삼각형, 실제 custom_shape 참조, skinned bounds. 이름/크기로 임의 제거하지 않음 |
| `generated-static-prop-axis-contract`, `skeletal-socket-scale-and-frame` | 실제 marker로 무기 축·길이를 대조하고 수입 리그 스케일만 보정한다. 수동 pose와 같은 프레임의 socket을 검사한다. | 리그 스케일/actor 외부 스케일, 최종 modifier 순서, grip·blade tip과 해부학적 접촉 |
| `character-capsule-visual-floor` | source 발바닥과 capsule bottom은 다른 좌표다. 필요한 시각 자식 offset만 계산한다. | 실제 collider 중심/높이·REST sole. 원래 프로젝트의 보정치를 복사하지 않음 |
| `skeletal-presentation-bridge`, `production-art-contract-checks` | 구조·클립/본 매핑·권한 경계와 실제 시간/화면 검증을 분리한다. | bind/정규화 weights/RESET/track 대상/필수 상태, 누락 시 명시 fallback |
| `project-authored-runtime-gaits` | stock 참고·프로젝트 저작·복제/리타겟의 provenance를 구분한다. 이동 속도와 보폭·stance를 함께 측정한다. | 저작 키·출처 권리, loop seam·reach·발 위치와 실제 이동/방향 |
| `production-phase-bounded-pose-blend`, `immutable-import-tracks-and-pose-feedback` | 수동 local pose 보간에는 다음 target이 모든 필요한 채널을 덮어써야 한다. phase/hold/취소와 판정 시간을 보존한다. | importer의 상수 트랙 제거, 전체 본 position/rotation/scale. 이 조건이 필요한 경로에만 적용 |
| `local-weight-solver-units-and-rejection` | solver의 단위/gradient와 기하학적 가능성을 구분하고 엄밀한 물리 상한을 반올림하지 않는다. | 고정 ROI·support, 독립 목적 미분, 정규화 후 실제 효과·새 압축/늘어짐·시각 판정 |
| `eye-socket-topology-and-whole-surface-fit` | 평면 삽입 대신 실제 눈꺼풀·소켓을 검토하고 주변 전체 표면과 rigid 안구/혼합 skin 경계를 함께 측정한다. | 원본 보존, 전체 주변 면·최대 cornea·동작 drift·좌표 독립 대조. 표본 교차0은 연속 증명이 아님 |
| `gltf-first-primitive-color-material-flag` | source 색상·imported array·실효 재질 flag를 각각 대조하고 자산 범위를 검증한 import 보정을 사용한다. | 현재 엔진에서 독립 재현·양자화 오차·공유 재질 불변·실제 반입/화면. 다른 판본에 버그를 가정하지 않음 |
| `blade-trail-world-markers-and-action-clock` | 실제 world marker 이력과 권한 있는 반열린 공격창을 읽고 표현 clock·중단 이력을 분리한다. | 외부 이동/scale·정지·취소·복귀·seek와 실제 on/off 가독성; VFX가 reach/피해를 소유하지 않음 |
| `weight-repair-per-edge-worsening` | 글로벌 최대/p99가 개선돼도 새 국소 악화를 찾는다. 전 프레임 표본과 실제 렌더로 채택 여부를 정한다. | 모든 key/중간 포즈의 edge별 변화, 부위 소유, 손/옷/갑옷 접촉과 같은 카메라 전후 |

원래 사례의 리깅·모션이 다른 자산에서도 맞는다고 가정하지 않습니다. source SHA·rest·named weight·모션 키를 대조하고 각 자산의 실제 골격과 의상 소유 영역을 확인합니다. 거부한 수선도 원인·근거·재현 절차를 보존하며 성공한 파생으로 표시하지 않습니다.

## 재질·환경·품질·성능

| 사례/출처 ID | 재사용할 원칙 | 목표 프로젝트에서 확인할 것 |
| --- | --- | --- |
| `courtyard-cc0-pbr-materials`, `godot-texture-import-budget-and-mips` | 색/데이터 채널·물리적 반복 크기·밉맵을 실제로 확인한다. 원본 JPEG와 runtime import/메모리는 다르다. | 공식 자산/작가/라이선스, sRGB albedo·linear normal/ARM, normal 방향·packed 채널·단위·실제 mips |
| `skin-material-semantics-rejection` | 피부 metallic의 실제 비정상 값을 확인해도 국소 hard material 경계가 새 seam을 만들면 기각한다. | 원본 UV/map·기본 factor·semantic mask와 불확실 경계, 동일 정면/측면의 일반 재질 비교. 구조 보존과 Game A/B·최종 채택은 별도 |
| `v013-generated-art-validation`, `v014-skeletal-preview` | 각 판본의 구조·실행 성공은 그 코드/자산의 범위에서 보존한다. | 실제 code/asset SHA·검사 범위·당시 화면, 현재 판본과의 차이 |
| `art-skeleton-contract`, `character-preview-final-art-review` | 과거 피벗/스킨 상태나 일부 pose 통과를 현재 최종 아트 승인으로 일반화하지 않는다. | 실제 runtime 종류, 전체 변형·전환·얼굴/손·머리/천·접촉 |
| `combat-quality-function-versus-heavy-impact` | [전투 기능과 타격감](skills/godot-web-production/references/combat-quality-review.md)을 나누고 dense key/기존 blend의 존재와 동작의 의미·접촉 표현을 별도로 검수한다. | 사용자/코드/정지 화면/정상1배속 영상·음향/기기 근거 구분, 참고 대상 동일성·관찰 범위, 약/강/차지의 명중·빗나감·방어·처치와 공통 접촉 피드백. 미관찰 영상의 타이밍·AAA 달성률을 만들지 않음 |
| `combat-reference-source-versus-provider-summary` | [참고 영상의 실제 미디어와 제공자 요약·preview](skills/godot-web-production/references/combat-quality-review.md)를 대조하고 원본 판본·편집 cut·직접 시각/청각·제공자 보고를 구분한다. | 공식 ID·실측 길이/해시·preview와 원본 해상도, 같은 shot의 접촉 전후, 기존 부유 대상·편집의 인과 한계, 오디오 존재와 직접 청취 구분. 공개 조사/계정 권한·기능 가격/승인 예산·정상 TLS 경로를 확인하고 비공개 식별자/서명 URL/raw 자산을 공개하지 않음. 현재 게임/새 프로젝트의 AV·기기·AAA 승인은 별도 |
| `charged-impact-confirmed-contact-clock` | 확정 접촉과 최종 표시 포즈의 시계·원본과 반입 곡선의 key/midpoint·양쪽 hitstop을 함께 비교한다. | 실제 actor frame/바닥 offset, IK pole과 관절 연속성, 씬 전체 재표본화·선택 보존·배포 바이트, 날 구간/반구 중심축·접촉 투영, query와 멈춘 검/잔상의 동일 시점, 충돌 복구를 포함한 실제 밀려남 예산, JS 안전 식별자와 실제 입력 관찰. 정상1배속 AV·실기기·AAA는 별도 |
| `aaa-representative-slice-acceptance`, `target-hardware-validation` | 대표 캐릭터·적·환경을 같은 판본으로 검수하고 최종 품질·실기기 성능은 별도 승인한다. | 전신/근접/플레이 영상, 조명/VFX 가독성, 목표 GPU·해상도·frame time·draw call·메모리 |
| `audio-server-deferred-playback-shutdown` | stop 요청과 mixer 최종 해제를 구분한다. 실제 참조 해제와 callback 재생 차단을 유한 조건으로 검사한다. | 대상 엔진의 audio 수명 모델, WeakRef/노드 해제, 반복 stop·명시 start |

환경 장식을 추가할 때는 공유 RNG의 호출 순서와 기존 충돌·카메라 경계를 보존합니다. 별도 시각용 RNG와 baseline 비교를 사용하고 collider 개수만 같다는 이유로 동일하다고 판단하지 않습니다. 동일 카메라의 실제 게임 화면으로 구도·표면·가독성을 검토합니다.

[국소 캐릭터 수정 절차](skills/generated-3d-game-art/references/local-character-polish.md)는 재질 수치·소유 mask·실제 경계의 시각 판정을 분리합니다. 보수적인 얼굴 내부 mask도 완전한 피부/머리 경계 분할을 뜻하지 않습니다. 중립 렌더의 seam gate에서 기각했다면 미실행 Game A/B나 실기기 검수를 통과로 적지 않습니다.

삼각형·본/클립 개수·텍스처 해상도·자동 검사 통과는 AAA 품질 인증서가 아닙니다. 얼굴·양손·갑옷·머리/천·전체 전환·공격 발디딤과 접촉, 재질·조명·VFX, 목표 기기 성능을 실제로 확인합니다. 소프트웨어 WebGL의 FPS를 목표 GPU 결과로 사용하지 않습니다.

## 새 프로젝트의 첫 적용 기록

1. 해당되는 스킬과 사례 ID를 선택합니다.
2. 원인 가설·현재 버전·적용할 조건·사용자 권한 범위를 기록합니다.
3. 가장 작은 실제 재현/확인 절차를 실행하고 원본과 결과 SHA를 남깁니다.
4. 결과를 `pending`/`verified`/`superseded`의 정확한 범위로 기록합니다.
5. 반복할 절차를 해당 프로젝트의 스킬에 반영합니다. 공통 원칙이 바뀌면 이 묶음의 판본·출처도 함께 갱신합니다.
