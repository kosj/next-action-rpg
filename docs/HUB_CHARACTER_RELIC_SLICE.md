# v0.1.13 허브 NPC와 룬 성소

2026-11-02 UTC. 공개 v0.1.12의 `cb038edf487f9a0ad7c7ed1c7c7606e6df5b3578`에서 기록관 Erin·대장장이 Roen의 고유 몸체와 idle, 석재/bronze relic, 성능 모드의 두 NPC 근사 접지를 추가했다. 실제 Game 원본에서 **허브 인물·기능 오브젝트의 프로토타입 개선을 채택**했다. 최종 native601/0·Web/Windows export·raw Web149,705,279B를 확인했다. 실제 local Web desktop506.152초를 통과했고 full mobile·clean CI·공개/릴리스는 이 source snapshot에서 pending이며 AAA·전체 의상/skin·연속 AV·실기기 성능은 승인하지 않았다.

## 실제 이야기와 사용 권한을 먼저 확인한다

[게임의 대사·상호작용](../game/scripts/game.gd)은 NPC0를 기록관 에린, NPC1을 룬을 강화하는 대장장이 로엔으로 지정한다. 초기 generic elderly Keeper/기사 guard 제안은 생성 전에 폐기했다. Erin은 성인 여성·ash ivory/teal 로브·보이는 얼굴/손/boots, Roen은 건장한 성인 남성·leather apron/workclothes로 구성했다. 둘 다 몸에 든 소품 없이 idle을 사용한다. Enemy source/clip을 덮어쓰지 않는다.

[VARCO 연결 절차](VARCO_MCP.md)는 공식 client의 실제16tools/readonly·helper catalog/call과 선택 runtime DB 설정을 확인했다. 일반 client state 쓰기 권한은 별도이며 auth/config를 복사·우회하지 않았다. 두 신규 mesh scope만 단발 실행하고 rig/idle에는 완료 task를 고정했다. [provider chain](../art_source/production/hub_npcs/README.md)의 두 mesh/rig/idle SUCCESS와 reported400/0/0은 실제 응답이다. balance/final debit을 독립 확인했다는 뜻은 아니며 추가 구매/upstream 재실행은 없다.1024×1536 원본2D참조는 runtime 몸체가 아니다.

[공식 rights 근거](validation/v0.1.13/rights-evidence/review.json)는 자신의 PRIVATE 생성물의 commercial use·Private 파생/라이선스 유지와 게임용 loop를 자신의 rig에 적용하는 workflow를 확인한다. 자신의 animated character GLB에 대한 제한적 판단이며 모든 stock/raw library 재배포 권리로 확대하지 않는다. terms root403은 fullterms를 읽었다는 증거도 금지라는 증거도 아니다. Erin/Roen의 `standing_idle_1_looping`은 provider motion이고 Hero/일반 근접 Sentinel의 프로젝트 저작 모션과 [출처 고지](../THIRD_PARTY_NOTICES.md)에서 구분한다.

## 원본·수선·실제 게임 채택을 나눈다

[Erin001](../art_source/production/candidates/erin-001/manifest.json)·[Roen001](../art_source/production/candidates/roen-001/manifest.json)의 원본·rig·정규화 구조/해시를 보존했다. runtime은 각각53본/16ktriangle,10.1667s idle+RESET·모든 map1k다. raw normal은 요청1k와 달리2k였으며 runtime 파생에서 조정했다. 원본 idle의21개 sampler는 마지막 timestamp가 중복이었다. 원본과 strict 실패를 남기고 최종 loop closure를 유지하며 앞선 equal-time row만 canonicalize했다. 모호한 원본과의 전체 fidelity나 새 모션 저작으로 표기하지 않는다.

Erin001 검은 lowerrobe patch는 clay/no-normal/flat에도 남는 닫힌 concavity였다. 잘못된 mesh-node-only 좌표의111mm dryrun은 GLB 생성 전에 기각했다. 실제 weighted joint/inverse-bind LBS와 wrapper, 같은 triangle의 barycentric REST 매핑으로6개 ray 지점을 .996µm 안에서 대조했다. [Erin002](../art_source/production/candidates/erin-002/visual-review.json)의 제한적 수선은 gray triangle/tail/slit이 남아 미채택했다.

선택 [Erin003](../art_source/production/candidates/erin-003/manifest.json)은 combined POSITION25/NORMAL98행과 one-ring normal을 수정했다. 실제 UV clone은383allowed mask 안에서 albedo378/normal369pixel만 바꾸고 outside·얼굴/손0delta·ORM encoded byte를 보존했다. 실제 Game에서 큰 결함 개선을 확인했지만 작은 teal tip/검은 ragged hem·깊은 slit은 남는다. one-ring/유한6pose 수치·222foot row 불변을 전체 skin/의상·footIK/AAA로 바꾸지 않는다.8,903,772B GLB에는 old image prefix와 새 PNG가 함께 있으므로 raw 크기를 PCK 증분으로 사용하지 않는다. [별도 postimport chain](../art_source/production/candidates/erin-003/postimport-image-audit.json)이 선택 embedded map과 실제 외부PNG·MD5/CTEX header를 연결하며 새 map의 전체 mip decode는 별도다.

## 기능 권한과 표시 접지를 분리한다

[relic module](../game/scripts/world/checkpoint_relic.gd)은 기존 FLOOR_STONE world-triplanar1.4m plinth·bronze/patina·opaque core·convex alpha shell을5mesh/2068triangle로 구성한다. [공식 spatial shader 원문](validation/v0.1.13/relic-shader-source-evidence.json)의 ALPHA transparent pipeline/sorting 제약은 실제 compile/raster와 구분한다. [정적 감사](validation/v0.1.13/relic-static-audit/review.json)에서 upper-rim winding과10mm claw gap을 첫 raster 전에 수정했다.

static foundation을−.30으로 recess해 높은 장애물처럼 보이던 표시를 낮추고 core/shell pivotY1.35를 유지했다. art origin은 logical checkpoint+(2,0,0)이며 음수AABB는 매립 의도다. 실제 interaction/ring/checkpoint/heal/save·collision/support를 art에 따라 옮기지 않는다. 새 light/collider/timer/particle/process/RNG가 없는 표시 모듈이다.

첫 실제16장에서는 q1 NPC boots가 떠 보여 최종 표현으로 채택하지 않았다. 후속 [두 static NPC grounding](../game/scripts/world/hub_grounding_shadow.gd)은 실제 바닥을 읽는 ray와 기존 shader의 연한 ellipse를 사용한다. q0는 실제 key shadow와 중복하지 않게 숨기고 q1만 표시한다. static NPC2 budget은 Hero/Enemy8 budget과 독립이며 게임 물리 권한을 갖지 않는다. 최종 원본에서 부유 인상을 줄였지만 per-foot/light-derived shadow가 아니다.

## 남은 Web 예산은 실제 export로 판단한다

v0.1.12 실제 raw Web146,600,803B의3.4MB 여유와 신규 GLB bytes를 직접 비교하지 않는다. 원본 texture·Godot import/mipmap·PCK·raw Web·ZIP·GPU memory는 다르다. 옛 미사용 GLB는 이미 package에서 제외돼 있었으므로 삭제 예상량을 절감에 더하지 않았다.

완전한 static RunefallKR430은 FontTools4.61.1로 원본 전체glyph/cmap을 유지하고 OFL/RFN에 맞게 이름을 바꿨다. [isolated 실제font 비교](validation/v0.1.13/ui-font/README.md)는15쌍 중16/18/24/36px12쌍 layout/pixel exact,12px3쌍은 extraAVrow1/64px·213pixel 차이로 전체 strict equality false다.3660owned shape의 fallback/누락0을 확인했다. 실제 touch10/14px는 이 corpus 밖이며 브라우저에서 확인해야 한다. rawTTF4,190,416B와 privatefontdata2,868,608B 절감은 각각의 측정이다.

[lossless import 근거](validation/v0.1.13/lossless-webp/README.md)는6/100 cold866.85초·cache fingerprint/성공marker/warm0과 pixel 검증을 분리한다. 원래 frozen-local31CTEX strict 실패(icon80RGB/max1)는 유지한다. 별도30bitmap/346mip·same-input icon·actualpublic v12icon equality를 혼합해 단일347mip PASS로 쓰지 않는다. 승인된 HubNPC script delta로 전체input guard가 실패했던 원본도 유지한다. import 비용은 runtime FPS가 아니다.

최종 [post-grounding package](validation/v0.1.13/local-runtime-package-grounding-002.json)는 raw149,705,279B/14files·150MB 미만/여유294,721B, PCK109,745,420B·entry MD5를 실제 확인했다. WebZIP119,076,424B·WindowsZIP146,917,780B는 [preview manifest](validation/v0.1.13/local-preview-build-grounding-002.json)에 고정했다. 실제 export가 예전 forecast를 대체하며 Windows OS 실행·hardware/AAA 승인은 별도다.

## 원본과 검증 단계

[hubwide/Erin/Roen/relic×q0/q1 원본](validation/v0.1.13/hub-review/README.md)은 baseline8·pre-grounding8·최종8의24장이다. 최종 after8은99.948초/exit0/오류0·source 불변·audio release·프로세스 종료를 확인했다. q0네 장은 이전 후보와 SHA 동일하고 q1만 접지 pixel이 바뀌었다. camera/FOV/scale·논리 origins·static160body/178shape/RNG는 baseline과 같다. 새 NPC의 production yaw±.7→±1.815는 의도된 변경으로 기록했다. paused idle0의 통제된 native still이며 정상 입력·live idle/AV·spawn 물리·기기FPS 증거가 아니다. 양쪽 warm6/100 cache와 baseline source2/25의 경계도 보존한다.

[최종 native601/0](validation/v0.1.13/native-grounding-002-checkpoint.json) 전에 있었던 첫 import 실패·001580·pre-grounding580/export를 덮어쓰지 않는다. tools80/0skip은 그때의 별도 단계이고 canonical5와 통합 숫자로 합치지 않는다. [검증 현황](validation/v0.1.13/README.md)의 새 근거로만 상태를 갱신한다. 이전 공개/523검사·모바일 시간의 성공을 현재 입력으로 승계하지 않는다.

[실제 desktop Web 후속 검증](validation/v0.1.13/local-desktop/README.md)은 q1→q0→q1·live idle/실제53본 source·바닥/shader/relic/font와 완전 재시작을 확인했다. 실제IDB8read는 최대14.928초로 완료됐고 재시작HP120/CP0/z6/q1/input-ready,88source·14Web·두ZIP/manifest 사후 byte 불변을 확인했다. page errors[]와 nonfatal server client-close reset은 다른 근거다. desktop06/07 원본의 검수는 실제 mobile Touch10/14px를 승인하지 않는다.
