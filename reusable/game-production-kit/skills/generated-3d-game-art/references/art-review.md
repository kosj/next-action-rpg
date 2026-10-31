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

## 재질·장면·실기기

| 검토 항목 | 근거/결함 | 상태 |
|---|---|---|
| albedo 색 공간·normal 규약·packed map 채널 | 미입력 | pending |
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
