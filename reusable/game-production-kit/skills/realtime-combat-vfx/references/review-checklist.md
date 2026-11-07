# VFX 검수 기록

상태: **pending**. 요청/대상 버전과 실제 증거를 채운 뒤 항목별로 판정한다. 체크박스는 실행 이력이 아니다.

## 대상

- 효과/목적, source commit·자산/recipe SHA:
- 엔진/Blender·실제 렌더러/브라우저·기기/해상도/품질:
- 변경 전후의 차이, 보존한 gameplay 규칙:
- 현재 채택/기각, 가장 크게 남은 결함:

| 확인 항목 | 결과: pending / pass / fail | 근거 파일·관측 범위 |
| --- | --- | --- |
| 원본/recipe/베이크 정상 종료·반입 결과 | pending | |
| 실제 renderer의 주 형태/alpha/색·깊이/atlas 경계 | pending | |
| 정상 1배속 연속 준비→방출→접촉/빗나감→회수 | pending | |
| 정면·측면·근거리/원거리·밝고 어두운 배경 | pending | |
| 실제 피격점/법선·원점/거리·공유 ledger·벽 차단 | pending | |
| 중단·hitpause·scene pause·restore·동시 인스턴스 | pending | |
| 캐릭터/상대 동작·공격 예고·HUD 가독성 | pending | |
| PC 웹·모바일 크기에서 입력·실제 표시 | pending | |
| 효과 OFF/ON 동조건 CPU/GPU frame time·메모리/전송 | pending | |
| 직접 청취·명중/빗나감 음향 동기·원본 AV | pending | |
| 목표 기기 성능·최종 아트/AAA 승인 | pending | |

카메라/노출/AI 위치 등 비교 중 변동한 조건을 적는다. 정지 화면만 보았으면 연속 시청을, PCM이 존재하면 직접 청취를, 녹화60fps이면 실기기60fps를 승인하지 않는다. 구조/기능 검사와 화면의 채택 이유를 별도 문장으로 쓴다.

## RedefineFX 참고 개선 실험

[제작 실험 절차](redefinefx-production-lab.md)와 [빈 실험 기록](improvement-experiment.json)을 사용한다. 참고 출처의 확인 주장과 자체 가설을 분리하고 같은 조건의 후보를 비교한다.

| 추가 확인 | pending / pass / fail | 근거 |
| --- | --- | --- |
| 큰 형태와 작은 디테일의 계층·압축본 가독성 | pending | |
| 접촉 전 상태·국소 활성·인접 비대상/연쇄 반응 | pending | |
| force/collider/시각 노이즈의 역할과 실제 반응 | pending | |
| 변형/고정 시드·gameplay RNG 보존 | pending | |
| 변경 제어군·보존 조건·기각 사유/후보 이력 | pending | |

형태·시간·인과·계층·변형·비용 gate는 실제 근거를 따로 남긴다. 하나의 총점이나 자료의 효과 수로 AAA를 승인하지 않는다.
