# 3D 아트 검수 기록 양식

새 기록을 복사해 채운다. 모든 초기 상태는 `pending`이다. 확인한 결과는 `verified`, 기각한 후보는 `rejected`로 표시하고 판본·근거·검증 범위를 함께 적는다. 검사 사실의 확인과 최종 아트 채택은 별도다. [자산 기록 양식](asset-record.json)의 비용·권한·라이선스와 연결한다.

## 대상과 조건

| 항목 | 입력 |
|---|---|
| 자산/검수 목적 | 미입력 |
| 원본 및 후보 SHA-256·bytes | 미입력 |
| recipe·도구/엔진/importer 버전·판본 | 미입력 |
| 현재 프로젝트 작업·비용 사용 근거 | 미입력 |
| 목표 품질·플랫폼·GPU/CPU·렌더러·해상도 | 미입력 |
| 실행 결과·로그·검수 날짜 | 미입력 |
| 구조 / 시각 / 실기기 성능 / 최종 채택 | pending / pending / pending / pending |

## 원본·반입·모션

- 출처·제작자·생성 당시 라이선스/플랜·귀속·실제 비용: 미입력.
- 완료 task 재사용과 실제 downstream 실행 범위, 유료 재실행 여부: 미입력.
- 원본 불변 SHA, 파생 변경 범위, geometry/UV/재질/rest/모션의 보존 증거: 미입력.
- source mesh와 실제 bone custom-shape helper 제외 목록, evaluated rest bounds·축·단위: 미입력.
- 본 이름·부모·rest basis/roll·inverse bind·named weights·정규화 검증: 미입력.
- 원점/scale 정규화의 공통 변환 증거와 재반입 정점 오차: 미입력.
- 클립별 저작/stock/생성 provenance, 중복 timestamp 및 원본 보존 처리: 미입력.
- 실제 imported Animation 채널·RESET·수동 보간 시 빠진 채널 정책: 미입력.

## 소켓·게임 권한

그립 basis/offset·marker 치수·import scale·actor scale을 따로 기록한다. 최종 본 포즈 뒤 같은 프레임의 무기 world transform과 끝점을 확인한다. modifier 적용 순서와 source 발바닥/실제 capsule bottom도 적는다.

이동·공격창·피해·HP·충돌·게임 RNG의 전후 동등성, 시각 난수 분리, 여러 actor의 독립 재생·hit pause·취소·hold·복귀 근거: **미입력**.

## 눈 소켓이나 국소 형상을 수정한 경우

[국소 수정 절차](local-character-polish.md)에 따라 해당 항목만 채운다.

- 실제 결함과 flat overlay의 시각 판정, 동일 source/candidate 카메라: 미입력.
- 의도된 절단 triangle·새 lid/inner rim·곡면 안구·경계 속성/weights 유도·topology 검증: 미입력.
- 원본 이미지/재질·rest/skin/모션 및 수정 밖 geometry 보존, 의도된 차이: 미입력.
- source Head-local rigid basis·물리 단위·identity root·import/actor scale 분리·동일 프레임 socket: 미입력.
- 정면/사선/측면·skin을 따르는 rim/rigid Head globe의 상대 drift·모든 key/midpoint fit·실제 head pose와 표본 한계: 미입력.
- 독립 REST 재구성 일치·주변 body 전체와의 실제 triangle 교차/clearance·실패 후보 대체 및 재검수: 미입력.
- 고밀도 studio / 경량 파생 shape / 실제 Web·Windows·게임 카메라 / 최종 아트 판정 각각: pending.

## 전체 변형 비교

표본은 모든 exported key와 interval midpoint를 포함한다. 추가 표본·클립 전환·렌더 표본을 구분한다. 같은 topology/edge ID와 시점임을 확인하며 분석에서 제외한 작은 rest edge 기준을 명시한다.

| 측정 조건 | 입력 |
|---|---|
| 클립 목록·exported key 수·총 표본 수 | 미입력 |
| 시점 schedule·topology/edge identity 검증 | 미입력 |
| rest-edge 분석 하한·측정 단위 | 미입력 |
| envelope 비교인지 같은 시점 비교인지 | 미입력 |
| finite sampling 및 표면/충돌 측정 한계 | 미입력 |

| 부위·재질/의상 소유 | clip·시간·edge/vertex ID | world 좌표·named weights | rest→posed mm·비율 | 후보의 절대 증감 mm | 근접 화면·판정 |
|---|---|---|---|---|---|
| 원래 최악 부위: 미입력 | 미입력 | 미입력 | 미입력 | 미입력 | pending |
| 새로 악화된 부위: 미입력 | 미입력 | 미입력 | 미입력 | 미입력 | pending |

원본/후보의 최대·분포와 edge별 악화 개수를 함께 남긴다. 같은 카메라·조명의 전후 렌더를 원래 최악 부위와 **새 악화 부위 모두**에 제공한다. 후보 채택 여부와 원본 유지/복구 결과를 적는다. 불변 bytes·정규화 weights·좋아진 p99만으로 채택하지 않는다. weld의 boundary 유무, 의도된 옷 트임, 실제 self-intersection은 별도 판단이다.

### 고정 영역의 제약 solver를 사용한 경우

- source anchor·geodesic 영역·고정 boundary·변화 envelope·원래 joint 슬롯/support: 미입력.
- 물리 단위의 edge 늘어짐/압축·triangle 면적/반전 제약: 미입력.
- raw/normalized 변수·목적·제약 단위, 같은 물리 문제임을 확인한 근거: 미입력.
- 독립 finite-difference gradient 오차·step·검사 pose·검사하지 않은 Jacobian 범위: 미입력.
- solver 종료 / 근사 feasibility / 실제 저장 dtype의 반올림 전 strict gate: pending / pending / pending.
- 원래 결함 감소량·새 악화·추가 압축의 절대 물리값과 시각적으로 충분한 수선인지: 미입력.
- 메모리 평가·export·렌더 각각의 실행 여부, 원본 runtime 유지/교체: 미입력.

## 시각 검 궤적을 추가한 경우

- 같은 프레임 최종 socket의 실제 grip/tip marker·world 이력·actor 이동/scale: 미입력.
- 권한 snapshot의 반열린 active 경계·presentation clock·zero-delta freeze: 미입력.
- 우선 중단·새 공격/재시작·역행/seek·epoch·순간이동·invalid 입력 clear와 표본/수명 제한: 미입력.
- 피해·reach·충돌·공격 시간 불변 근거: 미입력.
- 동일 화면 ribbon on/off·blend 비교·깊이 설정·밝은 배경/edge-on/장애물 가림: 미입력.
- 정지 fixture / 실시간 교전·중단 / 품질·플랫폼 / 목표 GPU 성능 범위 각각: pending.

## 품질 모드와 조명 비교

숫자가 클수록 높은 품질이라고 가정하지 않는다. UI label·저장값 의미·실제 렌더 scale/DPR·주광 shadow flag를 함께 읽고 기준표를 만든다. 기존 성능 모드 화면에 그림자가 없다는 사실을 고품질 설정의 결함으로 확정하지 않는다. 모드의 의미를 확인한 뒤 source 전후와 품질별 비교를 나눈다.

- 같은 실제 장면·몸체·재질·포즈·카메라·해상도·UI에서 원본/후보 × 각 품질 모드의 원본 raster를 확보한다. source/입력 해시·renderer/adapter·실효 scale·env/light·종료 상태를 남긴다. native 화면을 Web/DPR 화면으로, controlled scene-view를 정상 입력·기기 FPS로 바꾸어 해석하지 않는다.
- 현재 엔진 판본의 공식 지원표와 고정 renderer source를 함께 확인한다. UI에 property가 보이거나 값이 읽히는 사실은 그 renderer에서의 구현·실제 픽셀·비용·품질 채택을 모두 증명하지 않는다. 오래된 지원표로 새 판본의 tone mapper·fog·postprocess를 일괄 배제하거나, 지원된다는 이유만으로 무거운 기능을 켜지 않는다.
- sky/ambient/reflection의 실제 혼합 경로를 확인한다. 완전한 sky contribution이 explicit ambient color/energy 항을 대체하는 구현에서는 energy 하나만으로 전체 diffuse 대비를 제어한다고 가정하지 않는다. source의 입력 구성과 shader 식·runtime 설정·같은 조건의 화면을 연결한다.
- 광원의 품질 권한은 밝기보다 역할로 연결한다. 아트의 key intensity를 조정해도 성능 모드의 real shadow 정책이 바뀌지 않도록 실제 전환과 반환을 검사한다. 저장된 품질 index의 의미를 임의로 뒤집지 않는다.
- 저비용 ellipse/blob가 필요한 경우 실제 support ray·normal/높이/no-hit·깊이 검사·모드별 중복 방지·노드/질의/수명 한도를 선언한다. 예측·캐시·평면/경사·ledge·teleport·정지/이동을 구분한다. 이는 근사 grounding이며 정확한 접촉 그림자·지형 IK·물리·AAA 승인과 다르다. 그림을 위해 collider·RNG·actor transform을 바꾸지 않는다.

원본의 밝은 돌/머리·어두운 갑옷·발·검·적 예고·출구가 후보에서 분리되는지 UI를 켠 화면으로 판정한다. 후보만 노출/색을 후처리하거나 숫자·그림자 유무·자동 검사 수만으로 채택하지 않는다. 같은 원본 PNG·기각한 후보·새 악화와 한계를 보존한다. 목표 하드웨어·브라우저·Windows 렌더 경로와 최종 AAA 판정은 별도다.

조명 변경 뒤 규칙적인 바닥 줄무늬가 생기면 실제 그림자가 있는 모드와 생략한 모드의 같은 화면을 먼저 대조한다. shadow bias나 cascade를 원인으로 추정한 단계와 단일 변수 복구 후 실제 원본에서 결함이 사라진 단계를 구분한다. 기각한 원본/환경/해시를 남기고 runtime source inventory로 수정 범위를 확인한다. 그림자가 없는 모드의 원본 해시가 그대로라는 사실은 그 모드의 새로운 품질 검수를 대신하지 않는다.

촬영 뒤 관측용 getter·HUD telemetry만 추가했더라도 촬영 source와 최종 source가 정확히 같다고 기록하지 않는다. 변경된 파일의 양쪽 해시와 변경 목적을 기록하고, 조명·재질·배우 배치 source의 일치 범위와 최종 native/브라우저 검증을 나눈다. 같은 픽셀이라고 추정할 수 있는 변경과 실제 재촬영한 원본을 구분한다.

## 분위기·원경·시각 바닥과 충돌 권한

공간의 첫 화면이 평평하다면 하늘/horizon band, 주인공 전면의 재질, 원경 실루엣, 진입/연결 바닥을 실제 카메라에서 함께 비교한다. source의 sky gradient나 에너지 값은 픽셀 결과가 아니다. 고정 renderer의 실제 수식·runtime 값·같은 구도의 원본을 연결하고, 하늘색을 늘리면서 밝은 돌이나 갑옷 세부를 잃는 악화도 기록한다.

정적인 sky shader라면 cubemap bake와 보이는 배경 fragment를 구분한다. 공식 recipe와 고정 renderer의 실제 분기에서 계산/샘플링 경로를 확인하고, TIME·카메라 위치·변경되는 uniform에 의한 갱신 조건을 조사한다. bake 뒤 단순 샘플링을 사용해도 최초 bake/filter와 radiance 해상도·세부·메모리 비용은 남는다. source에 분기가 있다는 사실과 실제 compile/renderer/raster·시작 시간·목표 GPU 비용을 각각 검증한다.

표시 전용 원경이나 PBR floor skin이 필요하면 노드·표면·vertex/triangle·재질/텍스처·그림자·AABB와 카메라 가림을 원장으로 남긴다. collision/navigation/light·processing·RNG 권한 유무를 실제 tree와 physics/source로 확인한다. 시각 전용은 비용이 없다는 뜻이 아니다. 먼 배경이 실제 동선 밖에 있어도 화면과 그림자를 가릴 수 있다.

전체 transformed triangle 경계 감사와 자주 갱신하는 HUD/browser telemetry의 비용을 구분한다. 정밀 geometry 검사는 별도 fixture나 일회성 report로 수행하고, 반복 관측은 이미 확인한 mesh의 값싼 surface/index count·flag·해시처럼 제한한다. 검증용 getter가 플레이 중 매번 전체 삼각형을 순회해 새 부하를 만들지 않았는지도 확인한다. 값싼 report라는 설계 설명과 목표 GPU 성능 측정은 별개다.

ArrayMesh surface가 항상 indexed라고 가정하지 않는다. 유효한 unindexed triangle mesh의 `ARRAY_INDEX`는 null일 수 있으므로 typed array에 바로 대입하지 않고 존재/형식을 먼저 확인한다. indexed는 index 수, unindexed는 vertex 수와 primitive 형식으로 triangle을 계산한다. 검수기 자체가 잘못된 가정으로 중단됐다면 실패 원본을 보존하고 검수기/report만 수정한 뒤 같은 geometry로 전체 검사를 다시 실행한다. mesh를 불필요하게 재저작하거나 실패를 통과 수치에 포함하지 않는다.

바닥 skin의 시각 높이·깊이 겹침과 실제 support surface를 나누고 ray·actor transform이 보존되는지 검사한다. PBR 채널·OpenGL normal·roughness와 물리적 타일 반복 크기, 영역 사이 연결을 확인한다. 장면을 예쁘게 보이게 하려고 collider나 게임 판정을 옮기지 않는다.

PBR 채널·라이선스·타일 크기가 맞아도 재질이 형상과 거리의 의미에 맞는지 실제 화면으로 본다. 가까운 건축의 규칙적인 밝은 벽돌을 큰 원경 절벽에 반복하면 거대한 벽이나 커튼처럼 읽힐 수 있다. geometry와 권한을 보존한 채 기존의 불규칙한 stone 재질·색·반복 크기만 바꾸는 후보로 원인을 좁히고 같은 카메라/품질에서 다시 검수한다. 새 텍스처가 없다는 사실이나 기존 native geometry 통과는 수정 재질의 화면·최종 source 검증을 대신하지 않는다.

형상 보존 근거의 종류도 구분한다. construction 함수 source 해시, 실제 count/AABB·shadow flag, collision canonical rows와 실제 vertex-buffer payload 해시는 같은 검사가 아니다. 앞 후보가 vertex payload 해시를 수집하지 않았다면 뒤에서 측정된 해시 일치라고 소급해 쓰지 않는다. 확보한 source/메트릭·재현 조건과 수집하지 않은 증거를 명시한다.

같은 source의 진입·교전·overview 구도와 각 품질 모드 원본을 확보한다. 하늘/원경을 잘 보여 주는 구도와 실제 전투 카메라의 가독성은 다른 gate다. baseline/candidate의 body/pose/camera/HUD·source/renderer/scale을 맞추고 기각 후보와 수정 이유를 보존한다. 정지 fixture·소프트웨어 raster·export 성공은 실제 입력·목표 GPU·모션/연속 AV·AAA 최종 판정과 구분한다. 가져간 프로젝트는 자신의 source·budget·camera·검증 상태를 새로 기록한다.

## 생성 NPC·공유 리그와 기능 오브젝트

생성이나 자산 재사용 전에 실제 script/dialogue/interaction의 이름·역할·기능을 대조한다. 의상·나이·성별 같은 새 art brief는 코드에서 확인한 사실과 프로젝트의 현재 방향을 구분해 기록한다. 기존 generic keeper/guard 가정이 기록관/대장장이 같은 실제 이야기 역할과 어긋나면 비용을 쓰기 전에 고치고, 재사용이 쉽다는 이유로 잘못된 역할을 완성안으로 삼지 않는다.

현재 provider의 연결·발견된 도구·입력/출력 schema·비용과 사용 조건을 읽기 전용으로 확인한다. 필요한 생성의 사용자 위임과 추가 구매를 구분하고, 오래된 action 기본값이나 과거 실행 비용을 새 모델/rig 작업에 고정하지 않는다. 실제 호출·청구·결과·raw bytes/SHA·파생 manifest·권리/공개 조건을 기록하며 인증이나 signed 일회성 URL은 제외한다. 생성 성공·preview와 실제 반입·피부/얼굴/손/옷·idle/발·게임 채택은 각각의 gate다.

자신의 generated model에 적용한 provider idle과 프로젝트가 새로 저작한 모션의 출처를 구분해 notice/manifest에 남긴다. 현재 공식 source의 commercial/derivative/workflow 근거와 자신의 제한적 사용 판단을 연결하되 full terms를 못 읽었으면 읽었다고 하지 않는다. 공개 terms 접근 실패는 금지의 증거가 아니며, 자신의 animated output 사용 근거를 모든 raw stock library의 무제한 재배포 허가로 확대하지 않는다. 추가 제한/승인 요구가 실제로 확인되지 않았다면 추측으로 새 승인 절차를 만들지 않는다.

공식 client의 startup/local state 초기화, authentication, 도구 발견, 실제 provider 호출의 실패 단계를 나눈다. client가 시작되기 전에 멈췄다면 provider/네트워크가 불가능하다고 단정하지 않는다. 공식 client의 문서화된 runtime 설정과 승인된 상태 저장 경로를 사용하며 인증/토큰을 복사하거나 수동 OAuth로 대체해 해결했다고 쓰지 않는다. 미호출된 생성의 실제 비용이나 결과를 만들어 기록하지 않는다.

용량 여유는 실제 해당 export에서 계산한다. 원본 GLB·texture와 Godot import/mipmap·PCK/raw Web·ZIP·GPU 메모리는 같은 양이 아니다. 저장소의 큰 옛 GLB가 이미 export dependency에서 제외됐다면 지워도 게임 패키지가 그만큼 줄지 않는다. 실제 dependency/pack 원장을 먼저 확인하고 local preview와 published/clean artifact의 source identity·bytes를 나눈다. 새 후보의 전체 최종 export 증분과 얼굴/손/실루엣을 함께 확인한다.

요청한 texture resolution과 출력의 모든 map 해상도를 동일하다고 가정하지 않는다. 실제 embedded/external image 각각의 크기·PBR slot/채널·색 공간과 원본 해시를 검사한다. 낮은 해상도를 요청해도 normal만 더 크게 출력되는 경우처럼 예상과 다른 import 비용이 생길 수 있다. 파생본을 줄였다면 원본·변환과 실제 게임 표면/얼굴/손·최종 export를 다시 검수한다.

실제 engine import가 GLB image를 외부 PNG와 sidecar로 추출해 참조한다면 최종 source/provenance roster에 그 dependency도 포함한다. GLB 해시만 같아도 외부 atlas나 import policy가 달라질 수 있다. importer가 만든 실제 dependency와 최종 PCK를 조사하고 node의 요청값·원본 embedded 구조만으로 runtime 입력을 고정했다고 주장하지 않는다.

lossless encoder effort를 바꿔도 고정 엔진의 importer cache key가 이를 반영하는지 확인한다. 반영하지 않으면 warm cache로 새 설정의 절감/동등성을 측정했다고 하지 않는다. effective setting fingerprint와 성공한 import marker를 사용해 변경/누락 시 generated texture cache와 대응 checksum만 갱신하고 원본은 보존한다. marker는 성공 후에만 남기며 중단·설정 복귀·symlink·warm 무변경을 검사한다. 같은 pixel/mip를 확인해도 최종 PCK/raw Web·실제 입력은 별도다. 느린 offline encoding의 한도를 바꿀 필요가 있으면 import 단계에만 적용하고 native/runtime/watchdog·브라우저 검증 한도와 구분한다.

단일 frozen baseline 검사가 실패하면 그 실패를 새 PASS로 덮지 않는다. 같은 bitmap의 encoder round trip, 실제 배포 artifact와 local cache의 identity, 나머지 texture/mip 비교를 각각 분리해 원인을 좁힌다. 공개 baseline과 local cache가 다르다면 버전·플랫폼 원인을 추측하지 않고 확인한 bytes/decoded 내용과 출처를 기록한다. 여러 기준을 쓴 scoped 증거의 합계를 하나의 동일-baseline 전체 픽셀 검사 성공이라고 쓰지 않는다.

게임이 variable font의 한 weight만 사용한다면 공식 complete static instancing을 별도 후보로 검토할 수 있다. glyph subset/윤곽 단순화와 구분하고 원본·전체 glyph/cmap·layout 의미 범위·실제 사용 weight·라이선스와 reserved family name 처리를 보존한다. 유한 HarfBuzz 결과가 같아도 모든 language/feature 조합이나 픽셀을 증명하지 않으며 고정 소수점/정수 윤곽 차이가 남을 수 있다. 같은 driver에서 원본 variation과 파생 font의 실제 engine raster·UI layout을 비교하고 PCK/export 증분을 측정한다. raw TTF 절감액을 곧바로 새 3D 애셋 여유로 계산하지 않는다.

기존 전투 캐릭터를 guard NPC에 재사용하면 원본 model·clip·게임 판정과 NPC의 표시 instance/재생 상태를 분리한다. immutable resource 공유와 mutable playback/material override를 구분하고, 한 NPC의 idle 조작이 원래 적이나 다른 actor의 재생을 바꾸지 않는지 실제로 검사한다. 재사용으로 용량을 줄였다는 사실은 NPC 역할의 외관·변형 품질 인증이 아니다.

기능 오브젝트의 장식 module은 시각 origin/pivot·geometry/material/light/processing과 interaction/checkpoint/heal/save의 논리 위치/반경·collision/ray를 원장에 나눠 기록한다. 장식을 이동/회전해도 기능 권한을 몰래 바꾸지 않고 정상 입력으로 접근·효과·저장·재시작을 확인한다. 투명 shell은 renderer의 실제 ALPHA 경로와 정렬/깊이/가림을 actual camera·품질·밝고 어두운 배경에서 검사한다. opaque core나 단순한 convex shell이라는 설계만으로 투명 정렬·모바일 비용을 통과시키지 않는다.

정적 profile의 winding·구간 접합 두께를 실제 source 수학으로 확인하고 원본/수정 해시와 의도한 좌표 차이를 보존한다. material의 normal-map tangent 경로도 고정 renderer source에서 확인한다. world-triplanar가 tangent frame을 재생성하는 경우와 일반 UV tangent가 필요한 경우를 구분해 빈 tangent array만으로 결함을 확정하지 않는다. source/math 감사의 성공은 실제 engine 반입·빛/깊이·raster 채택을 대신하지 않는다.

기존 바닥이 walkable인데 장식만 큰 단차/장애물처럼 보이는 불일치도 검수한다. 권한을 보존하는 범위에서 recessed/floor-bound 표현을 비교하고, 실제 동선을 바꾸는 collider 추가와 시각 마감을 구분한다. 매립 foundation의 음수 AABB는 의도일 수 있지만 support/접지 증명이 아니다. count/topology가 같아도 mesh transform이나 authored vertex 위치가 바뀌면 그 범위를 기록하고 실제 ray·화면·정상 이동으로 다시 확인한다.

## 원본 모션과 실제 스킨 표면을 수선할 때

provider task 성공을 raw glTF animation의 strict validity로 간주하지 않는다. sampler의 시간·count·interpolation과 loop closure를 먼저 검사한다. 알려진 terminal timestamp 중복을 고칠 때도 원본/strict failure를 보존하고, 실제 마지막 loop-closure row와 earlier equal-time row를 구분해 검증한 한 경우만 canonicalize한다. 임의로 전체 key를 sort/merge하거나 endpoint를 지워 통과시키지 않는다. 원본의 malformed 중복은 의미가 모호할 수 있으므로 수정 전후를 수학적으로 완전히 같은 유효 clip이라고 쓰지 않는다. strict 재검사·거부해야 하는 합성 사례·실제 loop/pose 검수는 별도이며 이 처리로 provider motion이 프로젝트 독자 저작이 되지 않는다.

skinned glTF의 raw `POSITION`과 mesh-node transform만으로 실제 world 표면을 식별하지 않는다. joint global·inverse bind·weight를 실제 REST/idle 공간과 wrapper에 맞춰 평가한다. posed ray가 맞은 triangle의 barycentric 좌표를 같은 triangle의 실제 REST skin 표면으로 옮겨 수선 mask를 설계하고, 독립적인 Blender/engine 표면과 몇 점을 대조한 범위를 명시한다. 잘못된 좌표 해석으로 큰 변위가 나오면 GLB를 쓰기 전 dry run을 기각한다. 선택한 점의 작은 오차는 전체 mesh·전체 시간·의도한 시각 수선 성공을 증명하지 않는다.

수선한 position 주변 one-ring normal을 원본의 distinct smoothing/UV seam 그룹을 유지하며 갱신하고, 바꾸지 않은 topology·UV·skin/rest·clip·texture·발 영역과 관련 없는 bytes를 추적한다. 원본에 TANGENT가 없다면 새 position/UV/normal에서 target importer가 생성하는 경로를 확인하며, 빈 source attribute를 TBN 전체 보존 증거로 쓰지 않는다. 원래 있던 normal/face 지표와 새 악화를 구분해 확장 경계와 유한 pose를 검사한다. matched 실제 원본에서 재질 삼각형·검은 꼬리·주름/틈이 남으면 수치가 통과했어도 partial/held로 남기고 runtime에 자동 채택하지 않는다.

## 재질·장면·실기기

| 검토 항목 | 근거/결함 | 상태 |
|---|---|---|
| albedo 색 공간·normal 규약·packed map 채널 | 미입력 | pending |
| source COLOR_0 / imported array·양자화 / part별 effective color flag·독립 씬·범위 제한 import 보정/재반입 | 미입력 | pending |
| 실제 UV의 packed channel·생략 factor 실효값·sampling/filter/mip 조건 | 미입력 | pending |
| semantic material 소유 mask·불확실 경계·진단 선택 화면 / 일반 PBR 외관 분리 | 미입력 | pending |
| 국소 물성 변경 전후의 정면/사선/측면 경계 seam·surface 비용·중립 gate / 실제 Game A/B 각각 | 미입력 | pending |
| 물리적 타일 크기·UV 반복·금속/천/피부 구분 | 미입력 | pending |
| 실제 imported mip·압축·필터·LOD | 미입력 | pending |
| 원본/import/build 전송량/상주 메모리 각각 | 미입력 | pending |
| 얼굴·양손/손목·손가락 그립·발 접촉/발디딤 | 미입력 | pending |
| 머리/의상·관절 체적·무기/갑옷 관통 | 미입력 | pending |
| 상태 전환·플레이 카메라·조명·VFX 가독성 | 미입력 | pending |
| 같은 판본의 플랫폼별 화면과 실제 교전 영상 | 미입력 | pending |
| 실제 목표 GPU/CPU의 프레임 시간·로딩·메모리 | 미입력 | pending |

소프트웨어 WebGL/headless 수치에는 목표 GPU 성능 합격을 부여하지 않는다. 생성 성공·삼각형/본/클립 수·해상도는 품질 인증이 아니다.

## 판정

- 확인된 범위: 미입력.
- 새 국소 악화 및 남은 결함: 미입력.
- 채택 또는 기각의 근거와 원본 보존 상태: 미입력.
- 다음 수정의 구체적 부위·검증 조건: 미입력.
- 런타임 채택: **pending**.
- 최종 아트 품질: **pending**.


## 그림자를 끄는 모드의 정적 인물 접지

실제 품질 index·key shadow flag·render scale과 지지면을 먼저 관측한다. 정적 NPC의 제한된 soft ellipse를 추가할 때는 실제 floor read ray·normal/no-hit·불투명도·중복 shadow 방지와 별도 수명/질의 budget을 둔다. 기존 플레이어/적의 budget이나 collision/gameplay 권한을 빼앗지 않는다. 이는 per-foot/light-derived shadow나 animated foot IK가 아니다.

접지 없는 후보를 지우지 말고 원본·기각 이유·source delta를 보존한다. 동일 fixture에서 baseline과 수정 전/후를 비교하고, 실제 shadow 모드의 원본 byte equality와 근사 모드의 pixel 영역 변화를 각각 확인한다. pause된 idle pose의 정지 화면은 live idle/연속 AV·정상 상호작용·목표 기기 성능을 검증하지 않는다. 관측을 위한 source 변경 뒤에는 이전 native/export 숫자를 새 판본에 승계하지 않는다.

실제 Web에서는 resource path/rig/live idle·quality grounding·relic shader·font 경로를 관측하고 저장/완전 재시작 후 같은 계약을 재확인한다. 읽기 검증 뒤 selected source/export byte가 불변인지 비교한다. page error와 server client-close 진단은 구분하고 desktop 검수로 다른 touch 글꼴 크기·모바일 입력·clean 공개판을 승인하지 않는다.
