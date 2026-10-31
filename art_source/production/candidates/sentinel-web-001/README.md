# 수호병 웹용 정규화 개발 후보

기존 `sentinel-native-001`의 42,000삼각형 PRIVATE 원본을 재사용해 Remesh·humanoid-fingers 리깅·이동 샘플 4종을 확보했습니다. 새 실행 3건의 실제 사용 포인트는 모두 0이며, 추가 구매나 유료 upstream 재실행은 없습니다. 실행 ID와 포인트는 `generation-receipts.json`에 보관합니다.

- `source.glb`: 22,000삼각형 정적 Remesh 원본. 스킨과 클립 없음.
- `rig.glb`: 같은 22k 메시의 53본·스킨1 리그 원본. 클립 없음.
- `locomotion.glb`: 1.95m·REST 발바닥 기준으로 정규화한 53본·스킨1·idle/walk/run/RESET 개발 라이브러리. `walk`는 stock `jog_looping`에서 온 샘플이며 적의 3.6m/s 보행·접지나 루프 품질을 승인한 이름이 아닙니다.

최종 runtime 모션은 이 메시·rest skeleton을 입력으로 별도 프로젝트 저작 도구에서 만듭니다. 이 폴더의 stock FCurve를 최종 전투·이동 클립으로 이름만 바꾸지 않습니다. 사용하지 않은 `walk_looping` 대안도 task ID·바이트·SHA는 manifest에 기록했으며 원본 메시가 중복되는 raw 이동 GLB 4개는 Git에 추가하지 않았습니다.

## 실제 검증

Blender4.3.2의 정규화에서 본 이름·부모·rest matrix·topology·named weights·공통 원점 이동을 기존1e-5 허용 오차로 검사했습니다. 시작·중간·끝 표본의 최종 스케일 기준 source→target 오차는 최대8.3385e-7m이며 입력4개와 이전 native 원본 SHA는 변하지 않았습니다. 정규화 wrapper scale은1.95146937입니다.

Blender 재반입 REST 높이는1.949999988m, 바닥Z는5.96046e-8m입니다. `rest-review/`는 실제 정면·측면·후면 Cycles 렌더입니다. 공유 검수 도구는 importer가 만든 bone-display `Icosphere`를 source mesh에서 제외하므로 실제1mesh·22,000삼각형 bounds로 프레이밍합니다. source GLB는 수정하지 않습니다.

독립 Godot4.7.2 fresh 반입·runtime 감사는 오류·경고 없이 통과했습니다. 실제53본·53 skin binds·4클립과 비RESET3개에서22~25본 pose 변화를 확인했습니다. CPU skin REST 높이1.94998467m·바닥Y1.4782e-5m는 기존1e-4m 게이트 안입니다. `godot-audit.gd`는 별도 최소 project에 `candidate.glb`로 복사한 이 라이브러리를 실제 반입해 재현합니다.

Raw idle에는 provider timestamp 순서 위반이 있습니다. 원본 해시와 `raw-motion-inspection.json`을 보존하며, strict 검사기를 완화하지 않았습니다. 정규화 파생은 Blender가 해석한 동작을 별도 재샘플한 결과로, 원본의 fidelity나 끝점 보간이 수정·승인됐다는 뜻은 아닙니다.

손가락·어깨/엉덩이 armor·천의 전 동작 변형, 무기 그립, 프로젝트 저작 전투 모션, 실제 게임 조명과 목표 하드웨어 성능은 후속 검수입니다. 이 개발 후보와 구조/반입 합격을 최종 아바타·AAA 아트 승인으로 표시하지 않습니다.
