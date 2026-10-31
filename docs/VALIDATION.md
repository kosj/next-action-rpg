# 검증 결과

## v0.1.4 · 실제 스킨·동작 전환·첫 방 PBR 프리뷰

- [반입 기록](CHARACTER_INTEGRATION.md)의 리라32k·53본·19상태+RESET과 일반 melee 수호병22k·53본·9상태+RESET을 runtime에 설치했습니다. 다른 적·보스는 기존 표현을 유지합니다. 모든 runtime 이동·행동 키는 프로젝트 Bpy 저작이며 stock FCurve·수치 포즈를 복사하지 않았습니다.
- 최신 Godot4.7.2 전체 runner **305개·실패0**, 오류·경고0과 Web·Windows 내보내기 정상 종료를 확인했습니다. [실제 로그·source SHA·manifest](validation/v0.1.4/README.md)를 보관합니다. 이전268개 통합 및 독립43개 반입 결과는 당시 판본으로 보존하며 최신305개에 중복 합산하지 않습니다.
- Production 전용 최대80ms 포즈 보간과 이동 정규화 phase 보존을 추가했습니다. [집중27개 검사](validation/v0.1.4/transition-polish-runtime.log)는 실제 손/발/칼끝의 첫프레임 튐 감소, hitpause·epoch·즉시 우선 상태·공격 active의 정확한 목표 포즈와 같은 프레임 socket을 확인합니다. runtime foot IK와 최종 접촉/발디딤 승인은 아닙니다.
- 종료 시 AudioServer가 아직 보유한 WAV playback 참조 때문에 발견한 누수는 고정timer 대신 실제 WeakRef·player 해제 조건으로 수정했습니다. [실제9개 집중검사와 종료 자료](validation/v0.1.4/audio-lifecycle.json)는 stale callback·반복 중지·명시적 재개·최종 참조0을 확인합니다. 전체305개 검사도 오류 없이 종료했습니다.
- 첫 방에 [CC0 PBR3종](../art_source/production/courtyard_materials/README.md), 실제 크기의UV·밉맵, sky 반사·키/필 조명과 주변/배경 석재를 반입했습니다. [실제 Web 고정 카메라 검사](validation/v0.1.4/courtyard/README.md)와 기존178개 충돌체·공유RNG 일치 근거를 기록합니다. 별도 fixture의 정지 화면으로 이동·접지·공격 품질을 승인하지 않습니다.
- 원본의 전체 저작key+midpoint 리라2,358·수호병1,608표본에서 흉갑/손목 등 [실제 변형 불량](../art_source/production/character_actions/deformation_review/README.md)을 찾았습니다. 자동 수선은 새 경계 악화22.635/49.450mm로 **모두 기각**했습니다. 원본 runtime A89/214를 유지하며 수작업 웨이트·의상 소유/메시 분리가 남습니다. 선택 렌더나 최대비율 개선만으로 합격 처리하지 않았습니다.
- 새 전체 웹 원시합계는 **141,912,072bytes**로150,000,000bytes 예산 이내입니다. [로컬 manifest](validation/v0.1.4/art-quality-build-summary.json)의 ZIP크기/SHA와 원시크기를 구분합니다. 수호병 경량화·리깅·개발 샘플의 이번 실제 비용은 **0포인트**, 추가 구매는 없으며 이전1,250포인트 배치와 구분합니다.
- Python 도구 **41개**와 지식 DB46항목·제작/후보11개 무결성·CC0 원본9장 검증을 통과했습니다. [재사용 가능한 readonly reader fixture](validation/v0.1.4/readonly-storage/README.md)는 실제 source를 추출해 별도 payload를 읽거나 스키마를 변경하지 않는지 검사합니다.
- 최신 export의 [전체 로컬 Web 검사](validation/v0.1.4/local-web-final/README.md)는 **316.961초·오류0·exit0**입니다. 실제 베기/손 변화·수호병3명·전투·품질1→0→1·실제 저장·완전종료/재시작을 통과했습니다. 기존15/30초 assertion은 유지했습니다. 초기294.774초 결과와 구분하며 로컬 빌드번호 `0.1.4 · 1b8d95b9`에는 커밋 전 변경이 포함됩니다. 공개 커밋의 CI·Pages 실행은 [PR#6](https://github.com/kosj/next-action-rpg/pull/6)과 [main/tag Actions](https://github.com/kosj/next-action-rpg/actions/workflows/build.yml)에서 해당 SHA의 실제 결과로 확인합니다.
- **AAA 최종 승인 미완료:** [검수 기준](AAA_ART_QUALITY.md)의 얼굴·손·갑옷/천·머리카락·동적 접촉·공격 발디딤·최종 표면/장면과 실제 목표 GPU60fps·Windows 실기기 실행은 남아 있습니다. 현재 두 플랫폼의 렌더 경로는 Compatibility이며 Windows Forward+는 별도 계획입니다.

## v0.1.3 · 생성 소품 반입과 배치 검수

- Godot 4.7.2 회귀 **179개·실패 0개**, Python 검사 **36개**, 제작 입력 계약과 원본/파생 무결성 검사를 통과했습니다.

- 첫 전투 구역의 기둥 8개·출구 문틀과 리라의 룬검을 VARCO 원본에서 Blender로 가공한 소품으로 교체했습니다. 기존 진행 문·바닥·생성 위치를 유지하며 새 기둥·문틀의 충돌, 12×6m 통로와 무기 피벗을 회귀 검사합니다.
- 이번 생성 배치는 실제 실행 9건, 합계 **1,250포인트**이며 추가 포인트 구매는 없습니다. 이미지·원본·파생 모델·설정·task ID·SHA를 [배치 기록](ART_BATCH_2026_10_31.md)과 [manifest](../art_source/production/batches/2026-10-31/manifest.json)에 보관합니다. 수호병은 두 후보를 비교하며 기본 캐릭터를 완성형으로 교체하지 않았습니다.
- 웹 검사는 실제 UI에서 성능→균형→성능 설정을 바꾸고, 읽기 전용 IndexedDB 조회로 실제 저장 완료를 확인한 뒤 브라우저를 완전히 닫고 같은 프로필에서 이어하기를 검사합니다. Godot 4.7.2의 정상 비동기 저장을 강제 동기화하거나 테스트에서 값을 쓰지 않습니다.
- [로컬 실행 근거](validation/v0.1.3/README.md)에서 두 품질 설정의 실제 게임 화면·primary 커밋·브라우저 완전 종료 후 품질1·이어하기 복원과 오류0을 확인했습니다.
- Windows 실기기 실행, 목표 하드웨어 FPS, 최종 전투 모션·의상·접지 품질은 후속 검수입니다. 구조 검사·생성 완료를 AAA 아트 완성으로 표시하지 않습니다.

## v0.1.2 · 아트 제작과 스킨 연결 기반

- Godot 4.7.2 회귀 **163개, 실패 0개**, 오류·경고 없이 통과했습니다. 기존 131개에 실제 합성 스킨·bone pose 시간 동기화·장착/해제·필수 클립·루프·트랙 권한·fallback 검사를 추가했습니다.
- Python 도구 검사 **36개**가 통과했습니다. GLB 손상/참조/스킨/애니메이션 구조 13개, 제작 명세·참조 무결성·실제 공격 데이터·후보 원본/파생 무결성 계약 11개, 공식 Codex 클라이언트 stdio 연동 6개와 기존 지식 도구 6개입니다.
- 웹·Windows x86_64 release 내보내기를 통과했습니다. 이미지 참조는 `art_source/production/references/`에 보관하며 게임 패키지에 넣지 않습니다.
- 새 웹 내보내기의 실제 Chromium 검사에서 WebGL·모달·입력·첫 전투·브라우저 종료 후 저장 복원까지 통과했습니다. 이 결과는 로컬 하위 URL에서의 검증이며 아래 공개 URL의 클라우드 인증서 문제와 구분합니다.
- 실제 생성한 2D 참조 3장과 입력 명세·9클립 계약을 보관했습니다. 참조 해시와 약공격의 기본값/Resource override·판정 구간은 CI에서 검사합니다. 이 검사는 시각 품질 합격이나 VARCO 모델 생성 결과가 아닙니다.
- 공식 Codex 클라이언트에 VARCO 서버를 등록하고 OAuth와 실제 도구 발견·계정/가격/노드/Flow 목록 조회, 프로젝트 클라이언트 도구의 실서비스 읽기 호출을 확인했습니다. 인증 정보와 계정/Flow 원문은 저장소에 보관하지 않습니다.
- 명시적으로 승인된 리라 1건을 사용자가 지정한 빈 Flow에서 실제 생성했습니다. 메시 200포인트·리깅0·대기/조깅/달리기0으로 총200포인트이며 추가 구매는 없습니다. 기존 Flow는 수정하지 않았습니다. [원본·후보·3면 렌더](../art_source/production/candidates/lyra-001/manifest.json)와 SHA를 보관합니다.
- Blender 4.3.2의 실제 후처리와 정상 종료를 확인했습니다. 동일한53본·메시/웨이트/원점 관계를 입증하고 3시점 포즈 오차를 확인한 뒤 키1.82m·REST 바닥0으로 정규화했습니다. 최대 표본 오차는7.1e-7m이며 원본4파일은 불변입니다. 파생 GLB는 skin1·idle/walk/run/RESET 구조 요구를 통과했습니다. [후처리 근거](../art_source/production/candidates/lyra-001/preparation.json)를 참조합니다.
- [실제 Godot 후보 반입 감사](validation/lyra-001/README.md)에서 53본·skin53binds·4클립, CPU 스킨 REST 높이1.82000023m·바닥Y 약0과 AnimationTree 수동 샘플링의 실제 bone 변화를 확인했습니다. 이동3클립은 현재 loop mode `NONE`이며 최종 루프/변형 품질 승인이 아닙니다.
- 실제 후보는8만 폴리곤으로 Windows6.5만·웹3.2만 목표를 초과합니다. 리토폴로지/LOD·전투6클립·BoneMap·크로스페이드·발 접지·루프·재질/장면 품질 검수는 남아 있습니다. 런타임 기본 자산은 기존 피벗 모델이며 후보를 완성 아바타로 장착하지 않았습니다.
- [v0.1.2 태그 CI](https://github.com/kosj/next-action-rpg/actions/runs/41123131649)가 build/release를 통과해 웹·Windows ZIP과 매니페스트 3개를 게시했습니다. 실제 첨부를 다시 내려받아 버전·커밋·파일 크기·SHA-256·ZIP CRC를 [검증](validation/v0.1.2/release-verification.json)했습니다.
- [main CI](https://github.com/kosj/next-action-rpg/actions/runs/41123086701)의 build·Pages deploy·`verify_public_web`이 모두 통과했습니다. 공개 HTTPS 주소의 HTTP200과 실제 실행 중인 `0.1.2 · 7162bd25`, WebGL·모달·이동·첫 전투/공격/회피·브라우저 종료/재시작 저장 복원을 확인했습니다. [실제 상태·오류0·캡처 근거](validation/v0.1.2/README.md)를 보관합니다. TLS 검증은 유지했습니다.

## v0.1.1 · 기존 플레이 루프와 최초 배포 검증

검증일: 2026-10-30. Linux 클라우드 환경의 Godot **4.7.2 stable**, Blender **4.3.2**, Chromium **154**, Playwright **1.62.0**을 사용합니다. v0.1.0의 Godot 4.6.3 결과와 분리해 검증했습니다.

## 통과한 검사

- Godot 4.7.2의 캐시 없는 별도 체크아웃에서 프로젝트 반입·스크립트 컴파일과 통합 검사를 통과했습니다. 동일 버전 에디터·웹/Windows 템플릿을 사용합니다.
- **회귀 검사 131개, 실패 0개.** 기존 62개 외에 원형·안쪽·큰 delta 공격 판정, 패링의 공격 취소, 복귀 상태 초기화, 반복 백업 복구, 쓰기·교체 실패, 데이터 검증·롤백, 설정만 저장한 파일의 구분, UI 클릭의 공격 누수와 게임·HUD 실패 처리를 보강했습니다.
- 7개 전투의 적 생성, 충돌이 있는 문 잠금·해제, 완료 보상과 진행 저장, 보스 2단계 전환과 챕터 완료 저장을 통합 검사했습니다. 이 검사는 진행 상태를 직접 제어하는 자동 검사이며, 사람이 전체 챕터를 플레이한 결과가 아닙니다.
- 대화창과 HUD의 화면 내 배치, 설정 창의 제어 계층을 회귀 검사했습니다.
- 실제 Chromium에서 타이틀 → 새 게임 → 도입 대화 → 일시정지 → 복귀 → 이동 → 첫 전투 진입·공격·회피를 통과했습니다. 별도 persistent 프로필과 960×600 소프트웨어 렌더링에서 성능 설정을 UI로 선택한 뒤, 브라우저를 완전히 닫고 같은 프로필로 다시 열어 이어하기·체크포인트·설정 복원을 확인했습니다. 하위 URL `/web/`에서 실행하여 Pages 경로도 검증했습니다. 하드웨어 성능 측정 결과가 아닙니다.
- Web release와 Windows x86_64 release 내보내기, ZIP 구성, 라이선스 포함, 웹 용량 예산과 SHA-256 매니페스트 생성.
- Python 문법, 셸 스크립트 문법과 GitHub Actions YAML 구문.

브라우저 검사는 `?qa=1`일 때만 제공하는 읽기 전용 상태를 사용합니다. 게임 상태를 변경하거나 전투를 건너뛰는 API는 제공하지 않습니다. 캡처와 오류·재접속 기록은 `build/verification/`에 생성됩니다. CI도 headless 회귀·내보내기 후 실제 Playwright 검사를 실행하고 성공한 빌드만 배포 대상으로 올립니다.

## 배포 확인

- 사용자가 2026-10-30 소스 저장소를 공개로 전환했고 API에서도 public을 확인했습니다.
- 소유자가 Pages Source를 GitHub Actions로 활성화한 뒤 [run 41076834637의 2번째 시도](https://github.com/kosj/next-action-rpg/actions/runs/41076834637/attempts/2)에서 기존 성공 build를 유지하고 deploy를 재실행해 성공했습니다.
- 실제 공개 URL https://kosj.github.io/next-action-rpg/ 의 HTTPS HTTP 200 응답을 확인했습니다. 최초 배포 소스는 `4b182802e6138e66b42fc91f15b0dadd5c97acc1`이며 이후 검증된 main 변경이 자동 게시됩니다.

최초 배포 당시 이 관리형 클라우드의 Chromium 추가 검사는 초기 접속에서 `ERR_CERT_AUTHORITY_INVALID`가 발생해 게임 조작 단계에 도달하지 못했습니다. 같은 환경의 curl·Python HTTPS 요청은 인증서 검증을 유지한 채 HTTP 200을 받았습니다. 관리형 프록시 CA를 기존 브라우저 NSS 신뢰 DB에 추가한 뒤에도 Chromium 오류가 남아 있어, 이 클라우드 브라우저의 조작 성공으로 기록하지 않습니다. 이후 v0.1.2의 GitHub hosted runner에서 공개 주소의 실제 브라우저 조작·실행 커밋·재시작 저장 검사를 통과했고 위 기록에 근거를 보관했습니다. 로컬 클라우드 CA 문제 자체가 해결된 것은 아닙니다. 이는 CI의 로컬 웹·브라우저 재시작 검사 성공과 Pages 배포 성공을 취소하는 결과가 아니며, TLS 검증을 끄지 않았습니다.

## 미검증·후속 작업

- Windows 실기기 실행과 Forward+ 화면, Xbox 패드의 실제 입력, Edge.
- Ryzen 5 5600급·RTX 3060·RAM 16GB에서 Windows 1080p·웹 720p 60fps와 메모리 장시간 안정성.
- 신규 테스터 3명 이상의 길 찾기·난이도·30~60분 완료 시간.
- 최종 캐릭터 전투 모션·변형·재질·환경·음향 품질과 경량화. VARCO 연결 및 첫 리라 3D/리깅/locomotion 후보 생성은 완료했습니다.

현재 기본 게임 아트는 프로토타입이며 별도 VARCO 후보도 검수 중입니다. AAA급 완성 아트나 최종 성능 검증 결과로 안내하지 않습니다.
