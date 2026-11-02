---
name: runefall-art
description: Create and import RUNEFALL Blender or VARCO assets, evaluate Blender upgrades, and migrate prototype pivots to skeletal animation. Use for model generation, rigging, animation, or art-pipeline changes.
---

# RUNEFALL 아트 제작과 반입

[아트 파이프라인](../../../docs/ART_PIPELINE.md)과 [재검증 기록](../../../docs/ART_REVIEW.md)을 먼저 확인합니다. `python tools/knowledge.py search --tag art`로 실험 결과와 라이선스 조건을 찾습니다. 리그·애니메이션 변경에는 [godot-animation](../godot-animation/SKILL.md)을 적용합니다.

현재 사용자 목표는 AAA 아트 품질입니다. [대표 구간 AAA 승인 기준](../../../docs/AAA_ART_QUALITY.md)을 적용하고 리라·일반 근접 수호병·첫 전투 공간을 함께 검수합니다. 현재 스켈레톤·재질·장면 프리뷰는 검토 가능한 제작 단계이며 최종 AAA 승인은 `pending`입니다. 생성 성공·삼각형/본/클립 수·텍스처 해상도·구조 검사나 저작 표본 수치를 시각 품질 인증으로 사용하지 않습니다.

## 원본과 생성

- 현재 검증된 Blender 버전은 아트 가이드에서 확인합니다. 새 버전은 별도 디렉터리·체크아웃에서 먼저 시험합니다.
- `art_source/generate_assets.py`는 기존 원본과 GLB를 덮어씁니다. 수작업 자산을 보존하고 임시 출력에서 비교한 뒤 적용합니다. `.blend`는 LFS, 런타임 GLB는 일반 Git으로 관리합니다.
- 고유 주인공·룬도 VARCO 생성 후보와 Blender 후처리를 조합합니다. 생성 사용 범위를 소품으로 제한하지 않습니다. VARCO 사용 전 생성 당시 플랜·라이선스·공개 범위를 공식 정책과 대조하고 자산 URL·제작자·귀속 표기를 기록합니다.
- [공식 MCP 연결 가이드](../../../docs/VARCO_MCP.md)에 따라 서버 존재·현재 클라이언트 등록·OAuth·도구 발견·실제 호출을 구분합니다. 사용 가능한 도구와 플러그인을 검색하기 전에 연결 불가로 단정하지 않습니다. 클라이언트의 OAuth를 사용하고 MCP 엔드포인트나 토큰 교환을 수동 호출하지 않습니다.
- 현재 환경은 `tools/varco_mcp.py`를 통해 공식 Codex app-server의 도구 발견·호출 API를 사용할 수 있습니다. 새 세션에서는 `catalog`와 실제 읽기 호출로 상태를 확인합니다. Flow 목록이 비어 있으면 대상 Flow를 준비하고, 실제 스키마의 `flowId`를 명시합니다. 임의 ID나 오래된 workflow 이름을 만들지 않습니다.
- `art_source/production/`의 입력 명세와 실제 생성 후보는 분리합니다. `tools/check_art_production.py`는 입력·참조 해시·게임 공격 값의 일치만, `tools/inspect_glb.py`는 바이너리 구조와 명시 요구 조건만 검사합니다. 최종 반입은 두 검사와 실제 화면·변형·성능 검수까지 확인합니다.
- 현재 도형 블록아웃은 최종 제작 방식이 아닙니다. 주인공 1명·적 1종·전투 공간 1개부터 형태·재질·리그·모션·조명·VFX를 함께 검수한 뒤 확장합니다. 상세 범위는 아트 가이드에서 확인합니다.

## 실제 후보 검수와 재사용 절차

1. 새 Flow 목록이 비거나 오래돼도 사용자가 준 실제 Flow ID를 `get_flow_graph`로 직접 확인합니다. 빈 대상인지 확인한 뒤 명시적인 `flowId`·노드 scope로 실행합니다. 이미 완료한 생성물을 리깅/모션에 사용할 때는 그 task를 참조하는 입력 노드로 고정해 유료 upstream 재실행을 막습니다. 실행 직전 실제 비용·사용자 승인 범위를 대조합니다.
2. 원본 GLB는 해시와 생성 설정을 보관하고 수정하지 않습니다. `tools/render_glb_review.py`는 새 출력 디렉터리에 정면·측면·후면 REST 렌더를 생성합니다. Blender 이미지의 lazy loading 여부를 텍스처 누락으로 판정하지 않습니다.
3. `tools/prepare_character_candidate.py`는 검증된 Blender에서 같은 리그의 대기/조깅/달리기 후보를 결합합니다. 이름·부모·rest 행렬·mesh topology·named weights가 일치해야 합니다. 원점 차이는 `--normalize-origin-translation`을 명시하고 전체 본/메시의 공통 평행이동을 입증한 경우에만 메모리에서 정규화합니다. 허용오차를 늘려 다른 bind pose를 통과시키지 않습니다.
4. 각 모션의 시작·중간·끝에서 source→target evaluated vertex 오차를 다시 확인합니다. 전체 리그·메시·모션에 공통인 정적 wrapper로 키를 맞추고 `--ground-rest-feet`로 REST 바닥을 맞춥니다. 이 정적 변환을 게임 이동이나 동적 root-motion 검수 완료로 간주하지 않습니다. 원본 SHA 불변, 정상 종료, GLB 재반입 높이/바닥, skin/clip 구조를 확인합니다.
5. 실제 결과는 `art_source/production/candidates/`에 입력 명세와 구분해 보관합니다. source/파생 GLB의 bytes·SHA를 manifest에 기록해 CI로 무결성을 확인합니다. 임시 서명 URL·인증·계정 원문은 저장하지 않습니다. 후보가 폴리곤 예산을 초과하면 리토폴로지/LOD 필요를 표시하고, 3개 locomotion+RESET을 필수 9모션 완료로 기록하지 않습니다.

## 배치 생성과 검수 결과의 해석

- 사용자에게 필요한 애셋의 포인트 사용이 위임되어 있으면 실제 작업 범위에서 생성합니다. 원본 설정의 과거 1회 한도를 새 위임의 전역 한도로 해석하지 않습니다. 기본 모델은 실제 노드의 기억/추천 값을 따르고, `run_flow`가 반환한 실행별 포인트를 합산합니다. 카탈로그의 action 기본값을 모델별 실제 비용으로 고정하지 않습니다. 추가 포인트 구매는 별도 요청 범위와 구분합니다.
- 완료된 이미지도 고정 `ImageInput`, 완료 mesh/rig도 task를 참조하는 입력 노드로 재사용하고 실행 scope를 명시해 유료 upstream을 다시 실행하지 않습니다. Graph의 `output=null`만으로 실패나 재생성 필요를 판단하지 않고 status와 `get_output_downloads(nodeId=…)`를 확인합니다. 일괄 export 조회가 실패하면 생성은 반복하지 말고 노드별 export 조회를 시도합니다. 이미지의 `/api/objects/…` 상대 URI는 공식 origin에 결합해 파일만 내려받으며 MCP 엔드포인트를 직접 호출하지 않습니다.
- stock 원본도 엄격한 GLB 검사를 거칩니다. 이번 일부 raw 파일에는 값이 서로 다른 중복 최종 timestamp가 있었습니다. 원본은 보존하고, Blender 해석을 재샘플한 검수용 파생의 구조 합격과 원본 fidelity·게임 타이밍 합격을 구분합니다. `--candidate-motion candidate_…=GLB`는 기본 idle/walk/run 계약을 유지하면서 미승인 소스 클립을 묶으며 실제 gameplay 상태로 이름을 바꾸지 않습니다.
- Remesh는 요청 삼각형 수와 실제 수, 이미지 재베이크, 파일 크기를 각각 확인합니다. 폴리곤 감소가 파일 크기·프레임 개선을 뜻하지 않습니다. 목표를 넘긴 실측값을 반올림해 합격 처리하지 않습니다.
- 정적 소품의 실제 치수·원점·앞뒤 형태를 확인합니다. 단일 이미지에서 생성한 문이 4면 구조가 될 수 있습니다. 이번 파생 recipe는 `art_source/production/batches/2026-10-31/derive_portal.py`와 `derive_props.py`에 보존합니다. 원본 해시를 유지하고 새 출력에서 치수·통과 공간·UV·노멀·재반입을 확인합니다. 평면 절단 캡·휴리스틱 그립은 최종 재질/접촉 승인과 분리합니다.
- 게임 반입에서는 기존 피벗의 무기 축과 수입 모델의 축을 실제 marker로 대조합니다. 정적 장식과 잠금 장벽의 제어 트리를 분리하고, 시각물만 숨길 때 기존 충돌을 삭제하지 않습니다. source tree 밖의 runtime GLB도 CI 구조 검사에 포함하고 두 품질 모드·진행·카메라 접촉을 실제 검사합니다.

## 실제 캐릭터 프리뷰를 반복 제작할 때

1. 원본 weighted mesh/rest skeleton과 stock 개발 입력을 보존합니다. 새 runtime actions는 [저작 도구](../../../tools/author_character_actions.py)·[gait 도구](../../../tools/character_gait.py)·`art_source/production/character_actions/` recipe에서 provenance와 함께 만들며, stock 이름 변경이나 FCurve/수치 포즈 복사를 프로젝트 저작으로 표시하지 않습니다. 공격창은 현재 gameplay 데이터의 초를 원본으로 사용합니다.
2. Blender가 glTF를 반입하며 만든 `pose.bones[].custom_shape` 객체는 source geometry와 구분합니다. 공유 REST renderer의 제외 목록·원본 mesh 수/삼각형·source SHA를 대조합니다. 이름이 같거나 작다는 이유로 실제 메시를 제거하지 않습니다.
3. BoneAttachment는 실제 Skeleton 자식에 실제 본 이름을 지정하고 고정 offset은 별도 WeaponGrip 자식에 둡니다. baked/manual Tree는 그 표본 직후 attachment를 동기화해 world 본/그립/칼끝을 확인합니다. 향후 Modifiers가 있으면 최종 skeleton_updated 이후를 검사합니다. import normalization scale만 역수 보정하고 actor 자체 scale와 실제 검 길이는 보존합니다.
4. source REST 발바닥0과 CharacterBody capsule bottom을 대조합니다. 필요한 시각 자식 offset만 계산하고 collider·피해·HP·이동 값을 바꾸지 않습니다. 실제 source별 scale/offset은 [그립 데이터](../../../game/data/character_grips.json)·반입 보고서·지식 DB를 참조하고 스킬에 중복 고정하지 않습니다.
5. runtime Animation은 source와 공유한 채 loop/marker를 수정하지 않습니다. 복제한 리소스에 검수 cycle만 loop로 지정하고 action은 gameplay snapshot elapsed를 수동 샘플링합니다. 방향 이동·회피·charge/heal·death/restore·epoch·hit pause와 서로 다른 actor 재생 독립성을 실제 모델에서 확인합니다. charge 같은 hold는 마지막 키와 duration 이후에도 실제 몸/검의 장전 변위를 유지하는지 검사합니다. 상태명·clip 존재·손가락만의 변화로 장전 포즈를 승인하지 않습니다.
6. standalone gait의 reach/loop/sole 수치, 결합 후 실제 runtime scene, 전 프레임 변형·교차 전환·하드웨어 성능을 별도 범위로 기록합니다. headless 입력 검사는 process/physics 신호 경계와 실제 just_pressed·행동 효과를 함께 확인하며 fixture 시간 오류를 gameplay 완화나 고정 sleep으로 통과시키지 않습니다. 실제 모델 검사와 기존 runner를 따로 실행했다면 합산 통과로 기록하지 않고 최종 통합 실행 결과를 기다립니다.

## 완전한 본 포즈의 제한적 전환 보간

1. 현재 production은 `ActorVisual`의 명시적 opt-in으로 정규화된 보행 phase를 유지하고 최대80ms 동안 `Skeleton3D` local position/rotation/scale와 시각 yaw를 보간합니다. AnimationTree는 실제 gameplay 시간의 목표 포즈를 먼저 표본화하고, 이후 보간한 최종 손 본에 같은 프레임 소켓을 맞춥니다. 기본 sparse fixture의 즉시 표본 계약은 유지합니다. [실제 리라 전환27개 검사](../../../docs/validation/v0.1.4/transition-polish-runtime.log)와 [범위·입력 해시](../../../docs/validation/v0.1.4/transition-polish.json)를 참조합니다. runtime 발 IK·속도 연속성·최종 접촉/시각 품질의 완료 주장은 포함하지 않습니다.
2. 수동 본 보간은 모든 클립과 RESET이 모든 본의 position·rotation·scale을 덮어써야 합니다. Godot의 `animation/remove_immutable_tracks=true`가 이번53본의 저작159채널을55트랙으로 줄여 RootMask0·RightHandMask2를 만들었습니다. source GLB가 완전해도 imported Animation을 검사합니다. production `.glb.import` 두 파일은 `false`로 고정하고 재반입해 완전성을 복구했습니다. 불완전한 target을 거부하는 guard를 유지하며, 이전 프레임의 blended pose가 미기록 채널로 feedback되는 것을 허용하지 않습니다. 다른 sparse 자산에 이 opt-in을 강제하지 않습니다.
3. hit·dodge·parry·death는 즉시 정확한 목표를 표본화합니다. 공격 진입 보간은 남은 startup 이내에 끝내며 active 구간은 원래 저작 목표와 같아야 합니다. hit pause의 같은 zero-delta snapshot은 phase·가중치·본·검을 고정하고, 명시적 시점 이동은 정확한 target을 사용합니다. epoch 복귀는 이전 phase/보간 이력을 지웁니다. 판정·이동·HP·actor transform은 보간이 변경하지 않습니다. 클립 전환·중단·소켓·clock 검사를 시각 및 전체 빌드 검증과 분리합니다.

## 웨이트 보정을 시도할 때

- 원본·runtime SHA를 고정하고 새 출력에서만 실험합니다. [현재 실패 기록](../../../art_source/production/character_actions/deformation_review/README.md)의 자동 보정 후보는 전부 기각됐고 원래 리라·수호병 runtime GLB를 유지합니다. 글로벌 최대/백분위·선택한 근접 샷 개선만으로 채택하지 않습니다.
- 모든 exported timestamp와 interval midpoint에서 같은 edge ID·순서·topology·시점의 원본/후보를 대조합니다. edge별 최대 extension envelope 변화와 같은 peak pose의 새 악화를 확인하고, 최악 원래 부위와 새로 악화된 부위를 같은 조명·카메라로 렌더합니다. 이번에는 다른 torso 경계가 리라+22.635mm·수호병+49.450mm 더 늘어났습니다. 손/손가락 weight 보존·정규화·불변 geometry/UV/재질/키 검증은 별도로 유지합니다.
- 부위·의상 소유권·관절 변형을 시각적으로 확인해 수정 범위를 정합니다. 미세한 rest-edge 기준, finite sampling, 표면 용접으로 확인한 topology와 실제 garment opening/self-intersection을 구분합니다. 전체 분포가 좋아져도 새 국소 결함이 있으면 보정을 기각하고 AAA 상태를 `pending`으로 유지합니다.

### 작은 고정 영역의 제약 solver

- [이번 국소 실험](../../../art_source/production/character_polish/weight_review/README.md)은 원래 최악 edge의 REST anchor 주변 geodesic 영역만 바꿨습니다. 바깥 ring과 원래 네 joint 슬롯을 고정하고 경계로 사라지는 변화 bound와 graph regularization을 사용했습니다. 연속 표면의 C1 보증이나 새 influence 추가 후 export 절단으로 해석하지 않습니다. 실제 영역·손상 상한·압축/면적 guard는 보고서를 원본으로 사용합니다.
- raw-unit SLSQP의 영 이동/line-search 오류는 기하학적 불가능성의 근거가 아닙니다. [독립 finite-difference 검사](../../../art_source/production/character_polish/weight_review/validation.json)는 해당 목표 edge·pose의 목적함수 gradient만 확인했습니다. 같은 영역·support·물리 제약을 유지한 normalized solve가 정상 종료했으므로 모든 constraint Jacobian·전역 최적성이나 다른 topology의 불가능성을 주장하지 않습니다.
- 실제 저장 float32의 반올림 전 값을 적용합니다. normalized 결과의 목표 감소는 리라0.365232mm·수호병0.515069mm로 원래 갑옷 변형을 해결하기에 작았습니다. 리라의 새 악화0.250005164mm는0.25mm 상한을 엄밀히 넘으므로 approximate feasibility와 strict gate를 구분합니다. 수호병의 내부 numeric pass도 추가 triangle 압축과 시각 효과 부족을 숨기지 않으며 채택하지 않습니다.
- 최종 normalized 제안은 메모리 평가만 했고 GLB·PNG를 만들거나 최종 시각 검수를 수행하지 않았습니다. 이 웨이트 실험으로 두 runtime body를 교체하지 않았다는 사실과 별도의 눈 소켓 geometry 변경은 분리합니다. [재현 도구](../../../tools/repaint_character_regions.py)의 raw/normalized 단위 선택은 물리 조건을 바꾸는 옵션이 아닙니다.

## 국소 눈 구조를 수정할 때

- [기존 눈 inlay](../../../art_source/production/character_polish/rejected_eye_inlays/decision.json)는 표면 clearance를 통과해도 불투명한 표면 삽입물로 보여 기각됐습니다. 선명한 동공·색 보정·양의 거리만으로 채택하지 않으며 정면 시각 gate에서 실패한 뒤 미실행 측면/머리 포즈를 승인하지 않습니다. 후속 후보는 실제 눈 내부 triangle을 절단한 개구부·안쪽 lid/socket 깊이와 뒤쪽 곡면 안구를 검토합니다.
- 원본 body·이미지는 보존하고 파생의 의도된 눈 영역/inner rim 변경을 명시합니다. 원래 이미지/재질·노드/rest·skin/inverse bind·모든 애니메이션과 수정 밖 geometry의 보존을 확인합니다. [소켓 body 보존 감사](../../../art_source/production/candidates/lyra-eye-sockets-001/source-audit.json)는 현재 소켓 body와 **이전 안구**를 검사한 역사적 기록이며 최종 refit 안구의 source audit로 확대하지 않습니다. 원래 BIN prefix가 같다는 사실을 파생 전체 body의 byte 불변으로 표현하지 않습니다. topology의 의도된 눈 개구부·새 경계/비다양체와 skin 속성 유도도 구분합니다.
- 별도 안구는 source Head REST-local orthonormal basis의 물리 m와 identity root를 계약으로 둡니다. 실제 Head 소켓을 수동 포즈·보간의 최종 표본 직후 같은 프레임에 갱신하고 확인된 양의 균일 import rig scale만 역수 보정해 actor scale을 유지합니다. 고정 world offset이나 추정 Blender 축 보정으로 맞추지 않습니다.
- 같은 source/candidate 카메라의 정면·사선·측면과 실제 head pose를 확인합니다. 원본에서 보간한 skin을 따르는 rim과 별도 rigid Head 안구를 각각 검증하고 모든 exported key/midpoint의 상대 drift를 기록합니다. Head weight가 높아도 Neck 등 다른 influence가 남는 inner rim을 rigid로 표시하지 않습니다. 실제 exported weights·evaluated pose를 기준으로 판단하며 수치와 시각 검수를 나눕니다.
- [첫 소켓의 실제 BVH 실패](../../../art_source/production/character_polish/rejected_socket_fit/bvh-pose-check.json)는 독립 glTF/Blender REST가 일치해도 실제 triangle 교차를 clearance gate에서 발견한 결과입니다. 이를 fixture 오류나 통과로 바꾸지 않습니다. [중심 재적합](../../../art_source/production/candidates/lyra-eye-sockets-001/refit.json)은 소켓 body를 고정한 채 안구만 안쪽으로 옮겨 주변 body 전체의 정적 거리와 모든 exported key/midpoint의 근접 triangle에 보수적 구면 clearance를 검사했습니다. [최종 실제 GLB BVH](../../../art_source/production/candidates/lyra-eye-sockets-001/bvh-pose-check.json)의 다섯 머리 포즈는 교차0입니다. 유한 프레임·포즈의 확인이며 연속 충돌 안전성을 증명하지 않습니다. refit 이후의 최종 재반입·native/Web 화면은 별도 판정으로 남기고, 고밀도 studio·경량 안구·최종 AAA를 함께 승인하지 않습니다.
- source의 비백색 `COLOR_0`가 실제 imported array에 보존돼도 material의 사용 flag까지 확인합니다. 이번 Godot4.7.2의 첫 눈 primitive는 양자화된 색을 유지했지만 vertex-color albedo flag가 꺼졌고 뒤의 두 part는 켜졌으며, ActorVisual 없는 독립 씬에서도 재현됐습니다. [고정 importer source](https://github.com/godotengine/godot/blob/4.7.2-stable/modules/gltf/gltf_document.cpp#L1414)의 flag 검사와 color decode 순서를 확인한 이 판본의 문제이며 다른 버전에서도 같다고 가정하지 않습니다. [자산 전용 post-import](../../../game/import/eye_materials.gd)는 예상 세 part와 color를 검증하고 복제 material의 flag만 고칩니다. 원본 GLB·이미지·공유 재질이나 global override를 바꾸지 않습니다. 이전 중심 안구의 focused native 검사와 최종 refit 안구의 재반입·화면 검증을 구분하고, 이전 입력의 통과를 최종 입력으로 승계하지 않습니다.

## 검 궤적의 구현과 시각 검수

- [BladeTrail](../../../game/scripts/actors/blade_trail.gd)은 최종 손 소켓을 갱신한 뒤 실제 그립·칼끝 marker를 읽는 world-space ribbon입니다. actor 이동/회전에 과거 이력이 따라 움직이거나 임의 startup 원호를 만들지 않습니다. source marker의 물리 길이를 사용하며 `attack_reach`를 시각 크기나 접촉/피해 권한으로 사용하지 않습니다.
- 새 표본은 권한 있는 snapshot의 `[startup, startup + active)`에만 추가합니다. presentation delta로만 age를 늘리고 같은 zero-delta hit pause에는 geometry와 age를 고정합니다. death·stagger·dodge·parry 우선 중단, 공격 변경/재시작·elapsed 역행, 명시적 seek·epoch 복귀·순간이동·비정상 입력은 이전 연결을 지웁니다. 회복의 짧은 감쇠와 bounded samples는 공격창을 늘리지 않습니다. [회귀 검사](../../../game/tests/blade_trail_regressions.gd)는 이 계약을 검사하며 외관 승인을 대신하지 않습니다.
- [고정 Web 검수](../../../art_source/production/character_polish/blade_trail_review/README.md)는 실제 첫 방·몸체·RuneCamera와 실제60Hz marker 이력을 사용한 일시정지 fixture입니다. 같은 화면의 ribbon on/off를 비교했고 MIX는 밝은 돌 바닥에서 대비가 더 약해 기각됐습니다. ADD는 절제된 preview 기준이며 기본 거리의 edge-on 가독성·실시간 교전/UI/적 예고·다중 공격/중단·장애물 가림·품질1·Windows/목표 GPU·새 눈 후보와 결합한 최종 검수는 별도입니다. 이 정지 화면을 timing QA·목표 GPU 성능·AAA 승인으로 표시하지 않습니다.

## 버전 실험의 완료 기준

프로세스 정상 종료, GLB 구조·재질·변환·메시 비교, Godot의 오류 없는 반입, 실제 씬의 시각·모션 확인을 분리해 기록합니다. 출력 파일이 존재한다고 배치 성공으로 처리하지 않습니다. 현재 보관한 LTS 실험은 구조·반입 비교를 통과했어도 배치 종료 실패가 남아 있으므로 제작 버전을 자동 교체하지 않습니다.

## 공개 PBR 재질과 반입 용량을 반복 관리할 때

1. 공개 원본은 공식 제공자의 자산 ID·작가·영구 URL·라이선스·다운로드 URL·원본 MD5·SHA-256·실제 크기를 manifest에 보관합니다. Poly Haven CC0의 현재 recipe는 [courtyard 기록](../../../art_source/production/courtyard_materials/README.md)입니다. API `dimensions`의 단위는 공식 schema에서 확인한 mm이므로 m로 환산합니다. 형식·해상도와 물리적 반복 크기를 혼동하지 않습니다.
2. base color는 sRGB, normal·ARM/ORM은 linear이며 OpenGL +Y를 확인합니다. 이번 packed ARM은 R=AO/G=roughness/B=metallic입니다. 재질 slot과 실제 채널을 대조하고 금속이 아닌 돌·흙의 metallic은 0으로 유지합니다. 공유 재질·맵을 재사용하고 각 메시의 실제 길이/타일 m로 UV 반복을 정합니다.
3. headless 최초 import는 3D 자동 감지가 일어나기 전 `mipmaps/generate=false`일 수 있습니다. 재현 가능한 `.import` 정책에 밉맵·노멀·압축 방식을 명시하고 반입 후 실제 Image의 mip 존재와 재질 채널을 확인합니다. 필터를 이방성으로 설정한 것만으로 밉맵 생성까지 완료됐다고 기록하지 않습니다.
4. 원본 JPG/PNG와 밉맵 포함 `.ctex`, 전체 PCK/Web 전송량, 상주 메모리를 따로 측정합니다. 이번 원본9,785,368 bytes가 독립 lossless+mip import에서21,504,226 bytes가 됐습니다. 소스 파일 예산만으로 Web 빌드 용량 통과를 예상하지 말고 최종 export gate를 실행합니다. 압축·LOD 변경 뒤에는 비스듬한 바닥의 반짝임·얼굴/손·재질 구분을 다시 봅니다.
5. `python art_source/production/courtyard_materials/sync_materials.py`로 pinned 해시·용량·import 정책을 검증합니다. `--download`는 누락 원본만 공식 공개 URL에서 복구하며 기존 파일을 조용히 교체하지 않습니다. 새 원본은 새 manifest와 중립 조명·실제 게임 검토를 거칩니다.

## 조명과 품질 모드를 비교할 때

[첫 공간 조명 제작](../../../docs/ENVIRONMENT_LIGHTING_SLICE.md)처럼 UI label·저장 index·실제 shadow flag·render scale/DPR부터 확인합니다. `0/1`의 일반적 관례로 그림자 역전 버그를 추정하지 않습니다. 같은 source/pose/camera/UI의 q0/q1와 source 전후를 각각 비교하고, controlled scene-view의 원본 PNG를 실제 입력·Web/DPR·실기기 성능 승인으로 바꾸지 않습니다.

고정 엔진의 renderer source와 해당 버전 공식 표에서 실제 tone mapper dispatch·sky/ambient/reflection 혼합·fog/postprocess 경로를 확인합니다. 오래된 Compatibility 한계나 getter 숫자만으로 지원·화면을 확정하지 않습니다. 광원의 밝기 변경과 quality shadow 권한을 분리하고 실제 모드 전환을 검사합니다. 근사 지면 ellipse는 실제 support ray·높이/normal/no-hit·깊이·모드별 중복 방지·노드/질의 수명 한도와 원본 raster를 남기며 정확한 접촉 그림자·물리/AAA 승인과 구분합니다. 구체적 값은 recipe/source와 [검증 기록](../../../docs/validation/v0.1.11/README.md)을 원본으로 사용합니다.

[조명 후보 검수](../../../docs/validation/v0.1.11/lighting-review/README.md)처럼 shadow acne가 생긴 원본을 기각하고 실제 그림자 모드·단일 bias 변수·후보별 source inventory로 원인을 좁힙니다. 촬영 뒤 getter/telemetry가 바뀌어도 예전 원본이 최종 HUD source와 exact하다고 표시하지 않습니다. 촬영 입력과 후속 native/브라우저의 입력 해시를 따로 보존합니다.

## 분위기·원경과 바닥을 마감할 때

[성역 분위기 제작](../../../docs/ENVIRONMENT_ATMOSPHERE_SLICE.md)처럼 지평선·전면 재질·원경·진입 바닥을 실제 플레이 카메라에서 함께 확인합니다. 하늘의 색/curve와 sky/ambient/reflection의 source 식, runtime 설정, 보이는 horizon band를 나누어 기록합니다. 밝은 하늘·갑옷 전면·석재/금속 중 한쪽을 읽기 위해 다른 쪽의 세부를 없애지 않았는지 같은 몸체·재질·pose로 대조합니다.

표시 전용 ruins/cliffs나 floor skin은 실제 collision/RID·support ray·actor transform을 새로 소유하지 않습니다. 노드/삼각형/표면·재질·그림자·가림과 깊이 겹침은 별도 비용/품질입니다. landing·fight·overview와 q0/q1의 원본을 확보하고, 원경이 공간을 풍부하게 해도 전투 예고·발·출구·UI를 가리지 않는지 봅니다. 바닥 재질의 물리 반복 크기·채널·노멀과 실제 지지면을 구분하며, 구체적 수치·채택 결과는 [해당 판본 검증](../../../docs/validation/v0.1.12/README.md)에 기록합니다. 이전 판본 공개 검증이나 source 노드 수만으로 새 공간을 승인하지 않습니다.

unindexed ArrayMesh의 index는 null일 수 있으므로 정밀 report/fixture가 이를 처리하는지 확인하고, 전체 triangle 감사는 빈번한 HUD 관측과 분리합니다. native 통과와 시각 채택을 나누며, 가까운 건축 PBR을 원경 지질에 재사용한 후보가 형상/거리상 부적절하면 원본을 보존해 기각합니다. construction source/count/AABB 보존과 실제 vertex payload 해시의 수집 여부도 구분합니다. 색·재질을 수정한 뒤에는 그 새 입력의 native와 원본 raster를 별도로 확인합니다.

## 대표 구간 최종 아트 판정

- 실제 게임의 전신·얼굴·양손 근접과 플레이 카메라 영상, Web 품질0/1·Windows 같은 구도를 확보합니다. 콘셉트·스튜디오 렌더·게임 캡처와 당시 커밋/입력 해시를 구분합니다.
- 모든 저작 key timestamp와 클립 전체의 출력 프레임 표본을 평가하고 실제 렌더를 봅니다. 어깨·손목·골반·무릎의 체적과 갑옷/천/머리/무기 관통, 손가락·그립·발 접촉을 확인합니다. 수치와 시각 결과를 각각 기록하고 REST·세 시점·손가락만의 변화로 전체 모션을 승인하지 않습니다.
- 실제 이동·공격 발디딤과 코드 판정, 취소·hit pause·상태 교차 전환·복귀를 1배속과 느린 재생에서 확인합니다. 머리카락·의상의 방식/충돌 범위와 연속성, 첫 방의 구도·표면 크기·조명·공격 예고·VFX 가독성을 함께 검토합니다.
- Web 경량화에서도 실루엣·얼굴·손·무기·대표 재질과 전투 가독성을 보존합니다. 목표 GPU/CPU·OS·렌더 경로·해상도를 기록하고 실제 교전의 프레임 시간·메모리·로딩을 측정합니다. 소프트웨어 WebGL이나 headless 검사에 목표 하드웨어 성능 합격을 부여하지 않습니다.
- 판정은 해당 판본의 증거·결함·수정·남은 조건과 함께 남깁니다. [AAA 기준](../../../docs/AAA_ART_QUALITY.md)의 항목이 미검증이면 `pending`을 유지하고 과거 자동 검사 결과를 새 runtime의 통과로 바꾸지 않습니다.

## 반입 계약

1. 단위 1m·발바닥 높이·무기 위치를 확인합니다. 게임 이동 -Z와 Humanoid 리타겟 +Z를 구분하고 180도 보정을 중복 적용하지 않습니다.
2. 현재 GLB의 임시 피벗과 최종 `Skeleton3D`·스킨 웨이트를 구분합니다. 최종 자산은 BoneMap, RESET 포즈, 클립 트랙, 루프·발 접지를 검사합니다.
3. `AnimationPlayer`는 클립, `AnimationTree`는 블렌딩·표현을 담당합니다. 실제 이동·공격 타이밍·피해 판정은 게임 코드가 소유합니다.
4. 웹 Compatibility의 재질·조명 대체와 Windows 화면을 확인합니다. LOD 설정만으로 성능을 합격 처리하지 않고 드로콜·프레임 시간을 측정합니다.

## 완료

변경한 자산의 원본·수정 이력·사용 조건과 실제 검증 범위를 기록합니다. 최종 리그·성능이 미검증이면 지식 상태를 `pending`으로 유지합니다. 반입 후 게임 검사가 필요하면 [개발 스킬](../runefall-development/SKILL.md)을 따릅니다.

- 리그 원점 평행 이동은 먼저 armature 사본에서 기존 rest 허용 오차를 검사합니다. `Armature.transform()`이 roll/basis를 다시 계산해 오차를 늘리면 연결을 잠시 해제한 head/tail 단회 이동과 roll·연결 복원을 검증합니다. 원본 공통 이동·토폴로지·웨이트·재질·표본 포즈 검사는 유지하며 허용 오차를 넓혀 통과시키지 않습니다.

## 피부 PBR 국소 수정

ORM의 실제 UV 표본·linear 채널과 metallic/roughness factor를 확인합니다. 수치가 잘못됐다는 사실만으로 얼굴 일부 재질을 바꿔 채택하지 않습니다. [피부 재질 기각 사례](../../../art_source/production/character_polish/skin_material_review/decision.json)처럼 경계가 얼굴 안에서 끊기면 새 불연속이 생깁니다. 검토한 의미 경계와 불확실 영역을 분리하고 원본 이미지·UV·웨이트·모션·BIN 보존을 입증한 뒤 동일 중립 front/quarter/side에서 우선 비교합니다. 여기서 실패하면 actual Game A/B·runtime 편입 전에 기각하고 원본을 유지합니다. Blender 표본/재질 통과와 AAA/실기기 검수는 별개입니다.

## 전투 기능과 대검 타격감의 비교 검수

- active 몸/검 경로를 다시 저작할 때는 [활성 동작·곡선 제작 계약](../../../docs/COMBAT_MOTION_POLISH_SLICE.md)을 적용합니다. 실제 source GLB·원래 body/clip 보존·게임용 curve의 SHA/좌표·timing/길이를 함께 고정하고 실제 imported marker와 대조합니다. 준비한 높은 날이 active 시작에 가까운 적과 이미 겹치는지 검사하며, phase 지연이나 피해 기준 완화로 숨기지 않습니다. raw 기하 예측과 실제 첫 receipt는 구분합니다.
- 팔의 peak 감소와 피부의 국소 악화를 별도 검사합니다. normalized quaternion의 shortest 비교 방법을 명시하고 서로 다른 float/표현의 join 각도를 섞지 않습니다. 전체 신장 최대값이 줄어도 같은 edge의 새 악화·압축·실제 피부/갑옷을 확인하며 [국소 skin 보고서](../../../docs/validation/v0.1.10/skin-midpoint.json)의 미해결 포즈를 검수하기 전 최종 채택/AAA로 표시하지 않습니다.
- 폭/profile만 바꾸는 무기도 원본 hilt/guard/apex·node/마커·UV·topology와 새 normal/tangent를 검사합니다. Hero-only 조립은 기존 imported PBR material/atlas를 재사용하며 [raw 정확 보존과 native 반입](../../../docs/validation/v0.1.10/native-weapon.json)의 양자화/정렬 차이를 구분합니다. native vertex index의 단순 순서 비교 대신 실제 triangle 대응과 측정한 오차를 남깁니다. provider-stock 무료 참고 후보는 프로젝트 저작·채택과 분리합니다.
- 회수 목표는 수작업 guard 함수와 실제 원본 idle clip을 구분합니다. [실제 native 회수 실패](../../../docs/validation/v0.1.9/rejected-native-join.json)처럼 raw/manual 끝점이 맞아도 반입된 half-open 말미→첫 idle에서 큰 차이가 날 수 있습니다. baseline loop 준비 오류와 실제 자산 오류를 나누고 기존 임계값을 유지합니다. capture의 owner/capsule·visual ground offset도 실제 actor와 맞추며 떠 있는 fixture의 상대 몸 포즈를 최종 발 접지 근거로 쓰지 않습니다.
- 회수 수정도 기존 입력·도구를 동결한 별도 후보에서 수행합니다. [Sentinel recovery wrapper](../../../tools/author_sentinel_recovery.py)는 실제 원본 idle의 팔 branch를 연결하고 [동일 native 기준](../../../docs/validation/v0.1.9/native-recovery.json)으로 재검사한 사례입니다. 저작한 몸/발·입력 보존과 오류 부위의 수정을 분리하고 전체 native 통과·패키지·브라우저·새 캡처·최종 시각 승인을 각각 기록합니다.
- [전신 무게 전달·회수 제작](../../../docs/WEIGHT_RECOVERY_SLICE.md)은 기존 impact GLB와 도구를 보존하고 별도 weight 출력/recipe·기각 요약을 남깁니다. 실제 marker가 맞아도 local wrist counter-rotation이 빠를 수 있으므로 [독립 미분 도구](../../../tools/inspect_motion_derivatives.py)로 동일 key/midpoint·전체 clip의 균일 시간 표본에서53본 local/global 회전·world 이동과 Δt를 비교합니다. [기각 이력](../../../art_source/production/candidates/lyra-weight-001/rejected-motion-summary.json)처럼 저작 key당 작은 차이나 marker pass로 큰 시간 간격의 팔 반전을 승인하지 않습니다. 전체 최대값과 본별 최대값, 의도한 골반/다리 증가와 기존 active 팔 경로 보존을 각각 기록합니다.
- 실제 충돌 root를 오프라인의 명목 recoil 거리로 추정해 발을 world에 고정하지 않습니다. 벽·방향·겹침·actor scale에 따른 차이를 확인하고 local step/brace만 저작했다면 실제 접지는 별도 pending입니다. 이동 charge의 Spine 상체 레이어가 Hips/다리를 제외한다는 한계도 유지합니다.
- MovieMaker 고정 step 비교는 같은 실제 ActorVisual bridge·카메라에서 논리1x 몸 동작을 검수하는 보조 수단입니다. 출력 파일 생성·같은 프레임/시간축의 시각 검수·interactive 입력/접촉·audio/mix·목표 하드웨어 성능을 별도 판정합니다. 출력60fps를 실제 기기60fps나 정상 gameplay AV 승인으로 쓰지 않으며 현재 실제 결과는 [검증 기록](../../../docs/validation/v0.1.9/README.md)에 연결합니다.
- 표시용 Grip/Tip과 실제 피해용 칼날 구간을 분리합니다. 아주 가까운 적에게 손잡이·가드 쪽으로 준비 중 피해가 먼저 들어가지 않는지 검사하고, 캡슐의 바깥 끝과 반구 중심축을 구분해 실제 날 구간까지의 거리·투영을 함께 확인합니다. 비율과 길이는 현재 무기/공격 데이터에서 읽습니다.
- [실제 반입 정합 검사](../../../game/tests/charged_blade_alignment_regressions.gd)처럼 실제 컨트롤러·캡슐 바닥을 기준으로 key와 중간 시각의 Grip/Tip을 비교합니다. [원본 FK 감사](../../../tools/audit_impact_curve.py)로 팔의 회전축 뒤집힘을 찾고, import의 재표본화·최적화와 좌표계 오류를 분리합니다. 일부 클립의 정밀도를 올리면 전체 씬이 재표본화될 수 있으므로 실제 반입 키 수·웹 용량을 확인하고 필요한 클립의 정밀도와 원본 클립의 표본을 함께 보존합니다.
- [전투 품질 검수 절차](../../../reusable/game-production-kit/skills/godot-web-production/references/combat-quality-review.md)를 적용합니다. 기능 검사·피해량·클립 수는 시청각 품질 승인이 아닙니다. 촘촘한 저작 키와 현재80ms bounded blend가 이미 존재하는지 확인하고, 그 존재를 동작의 의미·가감속·발디딤·차지 레이어 완성으로 해석하지 않습니다. 실제 선택 clip과 이동/차지 우선순위를 대조합니다.
- 참고 게임·직업·무기·버전의 동일성은 사용자 확인과 공식 자료로 검증합니다. 영상 접근이 막혔으면 보지 못한 범위를 명시하고 타격 시점이나 음향을 측정했다고 쓰지 않습니다. 사용자 평가·정적 코드·정지 화면·실제1배속 영상/음향·목표 기기 측정을 별도 근거로 남깁니다.
- 약공격/강공격/차지의 명중·빗나감·막힘·처치 조합을 실제 게임에서 비교하고 공격자·피격자·카메라·VFX·음향을 같은 확정 접촉 시점과 대조합니다. MMORPG의 대검 연출 스타일과 이 실시간 액션 RPG의 입력 반응·취소/복귀 품질을 따로 판단합니다. 임의 AAA 달성률이나 미관찰 영상의 타이밍을 만들지 않으며 미검증 품질은 `pending`입니다.
