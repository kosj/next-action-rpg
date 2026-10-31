# 리라 웹용 후보 · 32,000 삼각형

`source.glb`와 3면 렌더는 기존 정적 리메시 후보입니다. `rigged-source.glb`는 같은 32,000 삼각형 본체에 생성한 53본 리그를 변경 없이 보관한 파일입니다. `motion-library.glb`에는 이 새 리그의 이동 모션 3개, 추가 `candidate_…` 원본 후보 8개와 bind-pose `RESET`을 결합했습니다. 이전 80,000 삼각형 본체의 모션은 섞지 않았습니다.

Blender에서 본 이름·부모·rest 행렬·메시 topology·named weights·world 관계와 3시점 포즈 오차를 검사하고 원본 12개 SHA가 불변임을 확인했습니다. 기존 평행이동 구현이 만들던 rest basis 수치 오차는 연결을 잠시 해제한 본의 head/tail을 한 번씩 옮기고 roll을 보존하는 방식으로 방지합니다. 허용오차 1e-5는 바꾸지 않았습니다. 기존 이동 3모션 출력 SHA는 이전과 완전히 같고, inverse bind를 의도적으로 바꾼 실제 불일치는 출력을 만들지 않고 거부했습니다.

[Godot 감사](godot-audit-motion-library.json)에서 53본·53binds·12클립의 실제 반입과 모션 11개의 수동 샘플링을 확인했습니다. CPU REST 높이 약 1.81998569m와 바닥 Y 약 0.00001401m는 기존 1e-4m 허용범위 안이며, 바닥이 정확히 0인 것은 아닙니다. 모든 클립의 loop mode는 `NONE`입니다.

원본 모션 수출물 4개에는 서로 다른 값을 가진 마지막 시간키 중복이 있습니다. [원본 구조 검사](raw-source-inspection.json)와 [시간키 문제](raw-source-timestamp-findings.json)를 보관하며 원본을 합격으로 처리하지 않습니다. Blender가 해석한 모션을 새로 샘플링해 내보낸 결합 파생 GLB만 엄격한 GLB 구조 검사에 통과했습니다. 메시가 반복된 모션 원본 11개를 이 폴더에 복제하지 않고 입력 SHA와 검증 결과를 남깁니다.

현재 결과는 검수용 후보입니다. `candidate_…`를 게임의 light/dodge/parry/hit에 바로 연결하지 않습니다. 필수 전투 모션 6개, 전체 구간의 변형·발 접지·루프·방향/그립·BoneMap·전환·최종 화면과 성능 검수는 남아 있습니다.
