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
