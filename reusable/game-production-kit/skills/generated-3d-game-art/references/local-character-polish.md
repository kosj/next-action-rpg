# 국소 캐릭터 수정: 눈 소켓·웨이트·검 궤적

이 문서는 대상 프로젝트에서 다시 측정할 절차다. 특정 캐릭터의 치수·상한·solver 결과·승인을 상속하지 않는다. [검수 양식](art-review.md)에 원본/후보/도구 해시와 판정 범위를 기록하고 [자산 기록](asset-record.json)에 연결한다. 해당 수정을 하지 않는 자산에 모든 항목을 강제하지 않는다.

## 눈의 표면 디테일과 실제 소켓 구조

1. 실제 source mesh의 동일 정면·사선·측면 카메라로 결함을 먼저 구분한다. 선명한 동공이나 양의 표면 clearance가 있어도 불투명한 눈 표면이 얹힌 인상일 수 있다. 정면 시각 gate에서 기각되면 색 변형을 계속 만들거나 나머지 시점을 통과했다고 기록하지 않는다. 전체 얼굴 실루엣이 유지 가능한 경우 국소 수정부터 검토한다.
2. 원본은 불변으로 보관한다. 구조 수정이 필요하면 파생에서 기존 눈 내부의 실제 삼각형을 절단하고 경계를 연결해 안쪽 눈꺼풀/소켓 깊이를 만든다. 그 뒤에 별도의 곡면 안구를 배치한다. 원래 표면을 덮는 또 다른 평면을 소켓 수정으로 표시하지 않는다. 새 경계 속성과 skin weights의 유도 방법, 의도된 눈 개구부와 새 비다양체/틈을 구분한다.
3. 원본의 이미지 bytes·텍스처/재질·노드/rest·inverse bind·애니메이션을 보존하고 수정 밖의 삼각형·원래 정점 속성도 대조한다. 추가 눈꺼풀 재질과 새 geometry 등 의도된 차이는 명시한다. 원본 BIN prefix나 기존 속성이 동일해도 primitive의 index가 바뀔 수 있으므로 파생 body 전체가 byte 동일하다고 쓰지 않는다.
4. 별도 안구는 source의 Head REST-local **orthonormal basis와 물리 단위**를 계약으로 정하고 identity root로 내보낸다. 전체 Head world 행렬, rigid basis, import 정규화 scale을 따로 기록한다. Skeleton의 실제 Head 본 소켓에 연결하고 최종 수동 포즈/보간/modifier 결과 직후 같은 프레임에 갱신한다. 그 자식에서 확인된 양의 균일 import scale만 역수 보정해 actor 자체 scale과 물리적 안구 크기를 보존한다. 비균일·음수 scale이나 예상 밖 asset root는 조용히 추정 보정하지 말고 별도 처리한다.
5. 실제 GLB를 재반입해 같은 카메라의 외관과 측면 깊이, 눈꺼풀 안쪽 rim, 곡면 안구의 가림을 확인한다. 원본에서 보간한 skin을 따르는 rim과 별도 rigid Head 안구를 각각 검증하고 모든 exported key와 interval midpoint의 **상대 drift**를 측정한다. Head weight가 높아도 다른 influence가 남으면 rigid rim이 아니다. recipe 설명보다 실제 exported joint/weight와 evaluated pose를 기준으로 판단하고, 별도 실제 head-pose 화면도 검토한다. 수치 표본은 그 사이 모든 시점의 연속성을 증명하지 않는다.
6. 완전한 구면의 최근접 signed distance만으로 피부 바깥 비관통을 판정하지 않는다. 안구 뒤쪽이 피부 안에 있는 의도와 실제 triangle 교차를 구분하고 눈 앞면뿐 아니라 주변 body 전체와의 clearance를 검사한다. 독립 glTF/Blender REST 재구성이 허용오차 안에서 일치하면 실제 교차를 fixture 오류로 치부하지 않는다. 실패 후보를 기각/대체하고, body를 고정한 안구 중심 등 한정된 수정도 새로운 해시의 후보로 다시 충돌·시각 검수한다.
7. 고밀도 스튜디오 후보, 경량 파생의 shape 보존, 실제 Web/Windows 반입·얼굴/게임 카메라·모션·성능을 각각 판정한다. 경량 파생은 눈에 보이는 곡률·홍채/동공 경계를 다시 검수한다. REST나 스튜디오 합격만으로 runtime 채택 또는 최종 AAA 품질을 승인하지 않는다.

## 고정 영역의 웨이트 제약 최적화

1. 결함의 정확한 source edge·시점·의상/금속/피부 소유를 확인한다. REST 표면 graph의 geodesic 영역과 고정 바깥 ring, 경계로 사라지는 변화 envelope를 선언한다. 이산 graph regularization이 연속 표면의 C1 연속성을 입증하지는 않는다. 모든 후보는 같은 영역·source SHA·topology·시점 schedule을 사용한다.
2. 원래 joint 슬롯과 support를 보존한다. 네 슬롯인 원본에 새 influence를 추가하고 export 때 잘라내는 방식으로 제약을 우회하지 않는다. 비음수·합 유지·고정 경계, 같은 시점 원본 대비 새 edge 늘어짐 상한, 압축 하한과 triangle의 면적/반전 guard를 물리 단위로 명시한다. 상한을 solver 편의에 맞춰 완화하지 않는다.
3. raw-unit SLSQP가 사실상 영 이동을 성공으로 반환하거나 line-search 오류를 내면 실행 상태와 물리적 feasibility를 나누어 기록한다. analytic 목적함수 gradient를 독립 central difference와 대조하고 step·최대 차이·검사한 pose를 남긴다. 이 검사는 모든 nonlinear constraint Jacobian이나 전역 최적성을 증명하지 않는다.
4. 같은 물리 문제를 유지한 채 변수·목적·제약을 적절한 기준 단위로 정규화해 다시 푼다. normalized 제약을 다시 물리 단위로 평가하고, 최종 float32 등 실제 저장 dtype에서도 검증한다. solver 성공 flag나 출력 반올림을 엄밀한 상한 통과로 쓰지 않는다. 근사 feasibility와 strict physical gate를 분리한다. 실패한 한 solve를 그 영역·다른 topology·다른 support의 기하학적 불가능성으로 일반화하지 않는다.
5. 변한 정점에 연결된 모든 edge/triangle을 모든 exported key와 midpoint에서 비교하고, 나머지 weights/joint bytes가 불변인지 확인한다. baseline의 전체 분포를 재사용하면 SHA·schedule·edge identity가 같아야 한다. 원래 불량의 절대 감소량, 같은 시점 새 최대 악화, 이미 압축된 triangle의 추가 면적 손실도 그대로 기록한다. 좋은 최대치나 백분위가 새 국소 결함을 가리지 않게 한다.
6. 개선이 보이는 결함을 해결하기에 너무 작거나 strict gate가 실패하면 원래 runtime을 유지한다. 수치상 pass 후보도 시각적 수선 채택과 별개다. 메모리에서만 평가한 제안에는 렌더·export·시각 검수를 했다고 쓰지 않는다. 새 geometry나 의상 분리 같은 다음 작가 수정은 별도 후보로 평가한다.

## source 색 데이터와 실제 반입 재질

- source GLB의 primitive별 `COLOR_0` 유무·encoding·실제 비백색 값을 먼저 읽는다. 반입한 mesh의 color array와 대응시키고 저장/반입 양자화와 색 공간의 예상 차이를 기록한다. 데이터 보존과 색의 실제 표시는 별도다. imported surface의 effective material이 vertex color를 albedo에 사용하는지 primitive마다 확인한다.
- 게임의 ActorVisual·runtime 재질 조작을 제거한 독립 씬에서도 같은 현상인지 재현한다. 특정 primitive 순서에서만 다르면 실제 엔진 고정 리비전의 importer 처리 순서를 조사하고 source를 연결한다. 한 판본에서 확인한 처리 순서 결함을 모든 엔진/버전의 일반 규칙으로 쓰지 않는다.
- 원본 GLB·이미지를 그대로 두고 고칠 수 있으면 필요한 자산의 import sidecar에만 post-import hook을 지정한다. 예상 part 이름/개수·color array·재질을 검증하고 해당 material을 복제한 뒤 필요한 사용 flag만 바꾼다. 구조가 달라지면 조용히 전체 재질을 덮어쓰지 않고 명시적으로 실패시킨다. 공유 재질이나 프로젝트 전체의 global override로 결함을 가리지 않는다.
- 실제 재반입 후 모든 해당 part의 color array·effective flag와 독립 씬/목표 renderer 화면을 다시 확인한다. hook 작성·source 원인 확인·재반입 성공·시각 승인 상태를 나누어 기록한다. 엔진 교체 때 재현과 보정 필요성을 재검사해 더 이상 필요한지 판단한다.

## 실제 칼끝으로 만드는 시각 궤적

- 최종 본 포즈의 무기 소켓을 같은 프레임에 갱신한 다음 실제 그립/칼끝 marker를 표본화한다. history는 world 좌표로 보관해 actor가 이동·회전해도 지난 궤적이 따라 움직이지 않게 한다. 존재하지 않았던 startup 원호나 임의 sweep을 만들어 채우지 않는다.
- 권한 있는 공격 snapshot의 `[startup, startup + active)`에서만 새 표본을 추가한다. 준비·charge·회복·광역 효과는 검 접촉을 추정하는 근거가 아니다. 회복에는 남은 짧은 history만 presentation clock으로 감쇠시키며 gameplay 공격 시간·reach·충돌·피해는 바꾸지 않는다.
- presentation delta로만 표본 수명을 진행한다. 같은 zero-delta hit-pause snapshot은 geometry와 age를 모두 고정한다. 명시적 seek, 공격 변경/동일 공격 재시작, elapsed 역행, 복귀 epoch, 순간이동/큰 위치 불연속에는 이전 연결을 지운다. death·stagger·dodge·parry 같은 프로젝트의 우선 중단 상태는 즉시 clear한다. 유효하지 않은 시간/좌표도 reset하고 표본 수·삼각형·수명을 제한한다.
- clock·경계·우선 중단·복귀·actor 이동/scale을 자동 검사하되 그 통과를 외관 승인으로 쓰지 않는다. 고정 카메라·조명·포즈·품질에서 ribbon on/off와 blend 후보를 비교한다. 밝은 배경, edge-on 검, 적 공격 예고/UI와의 대비를 확인한다. 가독성을 위해 실제 칼보다 궤적을 늘리거나 active 창을 넓히지 않는다.
- 깊이 테스트·depth write·그림자·blend 설정을 기록하고 실제 가림을 검수한다. 몇 장의 정지 화면에 관통이 없다는 사실을 전체 장애물 가림 검수로 확대하지 않는다. 고정/일시정지 Web 캡처는 실시간 교전·중단 타이밍·다른 품질/플랫폼·목표 GPU 성능의 근거와 구분한다. 재생 속도의 다중 공격/중단과 최종 패키지의 전투 가독성이 남으면 `pending`이다.

## 실제 적용과 지각 가능한 효과

색상만 바꾼 후보도 source hash나 material flag만 보고 화면에 적용됐다고 가정하지 않는다. 실제 export에서 remap된 scene/mesh의 색을 위치 대응으로 원본과 대조한다. importer가 vertex/index를 재정렬하면 같은 index를 비교하지 말고 펼친 삼각형 위치와 대응하는 속성을 확인한다. 채널 양자화와 허용 오차는 실제 형식으로 설명한다.

변경이 적용됐다는 기술 증거는 시각 개선의 증거와 다르다. 같은 조명·카메라·포즈·품질의 원본 화면에서 해결하려던 결함이 줄었는지 판단한다. 효과가 미미하면 원본을 유지하고 기각 사유를 남긴다. 기하학적 불변·수치 통과·약간의 색 차이를 자연스러움이나 최종 품질의 승인으로 바꾸지 않는다.
