# Unreal / Niagara 검수 기록

상태: **pending**. 실제 사용한 버전과 근거를 채우고 항목별로 판정한다.

- 프로젝트/engine/plugin·source commit/asset hash:
- target build/RHI·기기/해상도/품질·카메라/노출:
- 효과 역할과 gameplay가 소유하는 판정/시계:
- 변경 전후 차이·유지한 계약·채택/기각 이유:

| 확인 항목 | pending / pass / fail | 실제 근거·미확인 범위 |
| --- | --- | --- |
| plugin/template·System/Emitter/Material 컴파일·asset references | pending | |
| 주 형태·색/alpha·정렬·노출·근/원거리·측면 | pending | |
| attach/local/world·socket·ribbon 경로와 빠른 회전 | pending | |
| 비활성 생성→User Parameters→Activate·동시 인스턴스 | pending | |
| 실제 release/contact·벽/방패/빗나감·공유 ledger | pending | |
| hitstop/dilation/pause·취소·소유자 해제·pool 재사용 | pending | |
| Live/Sim Cache/flipbook의 각 출력과 입력·시간·범위 | pending | |
| Sequencer/MRQ 결과와 실제 gameplay 차이 | pending | |
| Effect Type/scalability·bounds·cull·필수 예고 가독성 | pending | |
| 다중 교전 CPU/GPU·투명도·메모리·첫 사용/재사용 hitch | pending | |
| cook/package·대상 RHI/기기 실제 실행 | pending | |
| 정상1배속 연속 시각·직접 청취·최종 아트/AAA | pending | |

미리보기·단일 emitter·PIE·Sequencer·packaged build를 같은 결과로 취급하지 않는다. 녹화 프레임 수와 실제 측정 frame time을 구분한다. 문서/스킬 자체를 검사한 경우에만 그 구조 검사 결과를 기록하고 나머지는 남겨 둔다.

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
