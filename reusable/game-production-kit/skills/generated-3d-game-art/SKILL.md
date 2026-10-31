---
name: generated-3d-game-art
description: >
  Create, rig, animate, review, or import generated and licensed 3D game assets
  with Blender, Godot, and MCP services. Use for asset provenance, paid generation
  reuse, GLB skinning, sockets, PBR import, deformation repair, and platform art QA.
---

# 생성형 3D 게임 아트

이 폴더만 복사해 사용할 수 있는 제작·검수 절차다. [자산 기록 양식](references/asset-record.json)과 [검수 양식](references/art-review.md)을 현재 프로젝트에 맞게 채운다. 눈 소켓·국소 웨이트·피부 재질·검 궤적을 수정할 때는 [국소 캐릭터 수정 절차](references/local-character-polish.md)를 함께 읽는다. 빈 값과 `pending`은 미확인이며 승인·실행 이력이 아니다.

## 시작할 때

현재 요청의 작업 범위, 비용 사용 권한, 업로드할 자료, 배포 대상, 목표 품질·기기, 도구 버전을 확인한다. 다른 프로젝트의 계정·승인·예산·생성 횟수 제한은 옮겨 오지 않는다. 현재 요청이 이미 위임한 반복 작업에 새 승인 절차를 만들지 않는다. 라이선스 확인도 별도의 공개 승인 절차를 만드는 근거로 쓰지 않는다.

Godot **4.7.2**, Blender **4.3.2**는 아래 실패 유형을 관찰한 과거 사례의 버전이다. 권장 최신 버전이나 필수 버전이라는 뜻이 아니다. 대상 프로젝트의 실제 실행 파일·importer·렌더 경로와 공식 문서를 다시 확인한다. 출력 파일 생성, 정상 프로세스 종료, 구조 검사, 시각 검수, 실기기 성능을 각각 기록한다.

## 1. 생성 서비스 연결과 원본 보존

1. 현재 도구 목록과 공식 제공자 문서를 찾아 **서버 존재 → 클라이언트 등록 → 필요한 경우 지원되는 인증 → 도구 발견 → 실제 읽기 호출**을 구분한다. 로컬/stdIO 도구에 원격 계정이나 OAuth를 강제하지 않는다. API 키 등 다른 인증을 쓰는 서비스는 그 서비스의 지원 SDK/설정 경로를 사용한다. OAuth 서비스는 공식 클라이언트의 절차를 사용하며 토큰 교환을 수동 구현하지 않는다. 연결 도구를 찾기 전에 서비스가 불가능하다고 단정하지 않는다. 토큰·인증 코드·일회성 다운로드 주소를 자산 기록에 넣지 않는다.
2. 실제 schema와 저장된 대상 그래프를 읽고 대상·노드 실행 범위를 지정한다. 목록이 비었다는 이유로 새 유료 작업을 실행하지 않는다. 현재 프로젝트에서 확인한 실제 대상만 사용한다.
3. 완료한 이미지·메시·리그는 완료 task를 참조하는 고정 입력으로 재사용한다. downstream 리깅·모션·export가 유료 upstream 생성을 다시 호출하지 않는지 확인한다. 그래프의 빈 output만으로 실패를 단정하지 말고 상태와 노드별 다운로드를 확인한다.
4. 실행 직전 현재 견적과 위임 범위를 대조하고, 실행 후 **실제 청구 단위·비용·성공/실패**를 기록한다. 카탈로그 기본 비용을 실제 모델 비용으로 대체하지 않는다. 추가 구매 권한을 생성 권한에서 추론하지 않는다.
5. 원본 파일·SHA-256·제공자·제작자·모델/설정·생성 시점·당시 플랜/라이선스·귀속 및 재배포 조건·영구 출처 URL을 남긴다. 생성 당시의 조건을 나중에 바뀐 계정 플랜으로 덮어쓰지 않는다. 원본을 보존하고 파생 파일·recipe·도구 버전·실행 결과를 따로 연결한다.

## 2. GLB·리그·모션 반입

- glTF의 노드·mesh·skin·joint·inverse bind·정규화 weights·애니메이션 시간·텍스처를 검사하고 실제 evaluated skin의 bounds를 구한다. Blender가 만든 bone widget은 실제 `pose.bones[].custom_shape` 참조와 source mesh를 대조해 제외한다. 이름이나 크기만으로 production geometry를 숨기지 않는다. lazy-loaded 이미지를 곧바로 누락 텍스처로 판정하지 않는다.
- 모션 결합 전 본 이름/부모/rest 행렬, topology, named weights를 대조한다. 원점 차이는 모든 본·메시의 공통 평행이동을 입증한 경우에만 정규화한다. 사본에서 rest의 linear basis와 roll을 검사한다. 변환 API가 roll을 바꾸면 연결·roll을 보존하는 단회 head/tail 이동 등을 검증하고 기존 허용오차는 유지한다.
- 키·바닥·앞축은 리그·메시·모션 전체의 일관된 정적 변환으로 맞춘다. 원본/파생 SHA, source→target 정점 오차, 재반입한 rest bounds를 확인한다. 바닥 정규화가 동적 발 접지나 root motion 검수를 대신하지 않는다.
- stock·생성 모션·프로젝트 저작을 구분한다. 이름 변경이나 곡선/포즈 복사를 신규 저작으로 표시하지 않는다. 중복 timestamp에 서로 다른 값이 있으면 원본을 보존하고 거부하거나 별도 파생을 만든다. importer 재샘플링의 구조 합격과 원본 동등성·게임 타이밍 합격은 별개다.

## 3. 런타임 표현 연결

- 게임의 이동·공격창·피해·HP·충돌·난수 상태가 권한을 갖는다. 시각 교체로 collider나 캡슐을 지우거나 재배치하지 않는다. VFX·장식의 랜덤 소비가 전투 RNG 순서를 바꾸지 않도록 분리하고 전후 동작을 확인한다.
- 실제 본 이름으로 Skeleton 아래에 소켓을 두고 별도 자식에 그립 offset을 둔다. marker와 실측 치수로 축·검 길이를 확인한다. import 정규화 scale만 역수 보정하고 actor scale은 보존한다. source 발바닥과 실제 capsule bottom을 대조해 필요한 시각 offset만 적용한다.
- 수동 AnimationTree/포즈 표본 뒤 **같은 프레임의 최종 본**에 무기를 동기화한다. modifier가 있다면 그 최종 결과를 기준으로 검사한다. 오래된 attachment 신호를 현재 포즈라고 가정하지 않는다. world 본·그립·끝점과 여러 actor scale을 대조한다.
- 수동 본 보간을 사용할 때는 importer가 상수 트랙을 제거했는지도 확인한다. 대상 클립과 RESET이 필요한 모든 본의 position/rotation/scale을 완전히 덮어쓰도록 검증하거나, 빠진 채널을 명시적으로 초기화한다. 이전 blended pose가 다음 target으로 되먹임되지 않게 한다. 이 계약을 선택하지 않은 sparse 자산까지 강제로 바꾸지 않는다.
- 공유 Animation을 직접 수정하지 말고 필요한 런타임 리소스를 복제한다. gameplay 시간·hit pause·취소·hold 끝·복귀·다른 actor의 독립 재생을 확인한다. 전환 보간 때문에 active 공격창이나 즉각 반응 상태의 타이밍을 늘리지 않는다.
- 검 궤적은 최종 포즈와 같은 프레임에 동기화한 실제 그립·칼끝 marker의 world 위치로 만든다. 이동/회전한 actor 아래의 local 이력이나 임의 원호로 과거 궤적을 대신하지 않는다. 새 표본은 권한 있는 반열린 active 구간에서만 추가하고 presentation delta로 수명을 계산한다. hit pause는 이력과 나이를 고정하며, 중단 우선 상태·epoch 복귀·시점 이동·순간이동에는 연결 이력을 지운다. 제한된 시각 이력을 피해·접촉·reach의 근거로 쓰지 않는다. 상세 경계와 비교 검수는 [국소 수정 절차](references/local-character-polish.md)를 따른다.

## 4. 재질과 배포 예산

맵별 의미·채널·색 공간과 normal Y 규약을 제공자 자료 및 실제 픽셀/재질 설정으로 대조한다. 보통 albedo는 sRGB, normal·packed 재질 데이터는 linear지만 이름만으로 단정하지 않는다. AO/roughness/metallic 채널 배치, 단위가 확인된 물리적 표면 크기, UV 반복을 기록한다.

source `COLOR_0`와 실제 imported vertex-color array, primitive별 effective material의 vertex-color 사용 flag를 따로 검사한다. 색 데이터가 보존돼도 flag가 꺼지면 화면에 반영되지 않을 수 있다. 현재 엔진의 독립 씬·고정 importer source로 재현하고 필요한 자산에 한정한 post-import 보정을 검토한다. [국소 수정 절차](references/local-character-polish.md)의 범위/재반입 gate를 따르며 다른 엔진 판본의 보편적 결함으로 일반화하지 않는다.

피부의 metallic처럼 물성 오류가 의심되면 실제 UV의 packed channel과 생략된 factor의 실효값을 읽고 재질 소유 부위를 검토한다. 국소 material을 물리적으로 타당한 값으로 고쳐도 mask 경계가 새 polygon seam을 만들 수 있다. 원본 geometry·이미지·리그 보존과 최종 외관은 별개이며, 동일 조명·정면/측면에서 경계 결함이 보이면 후보를 기각하고 원본을 유지한다. [국소 피부 재질 절차](references/local-character-polish.md#국소-피부-재질과-semantic-경계)를 따르고 미실행 Game A/B를 합격으로 기록하지 않는다.

필터 설정과 실제 mip 생성은 별개다. 최초 headless import와 에디터 감지 결과가 다를 수 있으므로 재현 가능한 import 정책과 반입된 mip를 확인한다. 원본 이미지 bytes, 압축·mip 포함 import bytes, 전체 배포 전송량, 상주 메모리를 구분한다. LOD·텍스처 축소 후 얼굴·손·실루엣·재질·전투 가독성을 다시 검토하고 최종 export를 측정한다.

## 5. 전체 변형과 아트 판정

모든 exported key timestamp와 interval midpoint에서 같은 topology·edge ID·시점의 원본/후보를 비교한다. 최악 정점의 좌표·부위·named weights, rest/posed 길이와 **절대 mm 변화**를 남긴다. per-edge 최대 envelope와 같은 시점의 변화는 구분한다. 작은 rest edge의 분석 하한과 finite sampling 한계도 기록한다.

웨이트 보정은 의상·금속·피부의 실제 소유 부위를 확인한 뒤 국소적으로 적용한다. geometry·UV·재질·rest·키를 보존하는 수정이라면 해당 불변성도 검증한다. 최대 비율·p99·선택한 근접 샷이 좋아져도 **새 부위가 악화되면 기각**한다. 원래 최악 부위와 새 악화 부위를 동일 카메라·조명으로 확인하고 실패한 후보도 재현 근거와 함께 보존한다. 표면 weld의 boundary 검사만으로 의도된 옷 트임이나 self-intersection을 판정하지 않는다.

국소 solver는 고정 영역·원래 influence support·물리적 제약을 먼저 선언한다. raw-unit SLSQP의 정지나 line-search 실패를 불가능성으로 해석하지 않는다. 목적함수 미분을 독립 finite difference로 확인하고 같은 물리 문제의 변수·목적·제약 단위를 정규화해 재검사한다. 실제 저장 dtype의 결과에서 반올림하지 않은 물리 상한을 적용한다. solver 성공·수치 허용오차 안의 근사 feasibility·시각적으로 충분한 수선은 별도 판정이다. [상세 절차](references/local-character-polish.md)에 실패 원인과 불채택 조건을 남긴다.

눈이 평면 삽입물로 보이면 색·동공 선명도·양의 clearance만으로 승인하지 않는다. 같은 카메라의 정면·사선 검수에서 구조 결함이 확인되면 국소 눈 개구부·안쪽 눈꺼풀/소켓 깊이와 뒤쪽 곡면 안구를 검토한다. 원본 이미지·재질·rest·skin·모션과 수정 밖의 형상을 보존하고 실제 변경을 증명한다. Head-local 물리 단위·동일 프레임 소켓·import scale 보정, 눈꺼풀과 안구의 포즈별 적합성은 [국소 수정 절차](references/local-character-polish.md)를 따른다. 스튜디오 후보의 합격을 Web 반입·동작·최종 아트 승인으로 확대하지 않는다.

같은 판본의 플레이 화면과 근접 얼굴·양손·그립, 머리카락/의상, 어깨·손목·골반·무릎 체적, 발 접촉·공격 발디딤, 상태 전환·조명·VFX를 검토한다. 실제 목표 GPU/CPU·OS·브라우저·렌더러·해상도에서 프레임 시간·메모리·로딩을 측정한다. 소프트웨어 WebGL/headless 결과와 실기기 성능을 혼동하지 않는다. 생성 완료·폴리곤/본/클립 수·해상도·자동 검사 수는 AAA 품질 인증이 아니다. 미검증 항목은 `pending`, 기각한 수정은 `rejected`로 남긴다.

## 공식 참조

- [MCP 도구 발견](https://modelcontextprotocol.io/specification/2025-11-25/server/tools), [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- [glTF 2.0 명세](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html), [Blender glTF 입출력](https://docs.blender.org/manual/en/latest/addons/import_export/scene_gltf2.html), [PoseBone API](https://docs.blender.org/api/current/bpy.types.PoseBone.html)
- [Godot 3D 반입](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/index.html), [BoneAttachment3D](https://docs.godotengine.org/en/stable/classes/class_boneattachment3d.html), [Skeleton3D](https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html)
- [AnimationTree](https://docs.godotengine.org/en/stable/tutorials/animation/animation_tree.html), [이미지 반입](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_images.html), [StandardMaterial3D](https://docs.godotengine.org/en/stable/tutorials/3d/standard_material_3d.html)

공식 문서 링크도 대상 버전의 실제 동작을 대신하지 않는다. 필요한 버전의 문서·schema와 작은 독립 반입 실험으로 현재 조건을 확인한다.
