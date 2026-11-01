# v0.1.11 첫 전투 공간의 조명·품질 모드·지면 표현

2026-11-01 UTC. 시작점은 공개 v0.1.10의 `a07f91db392d39494cd5bb635d579b3eb3d15663`다. **후보002는 실제 정지 전투 화면 q0/q1의 조명·근사 접지 prototype 범위에서 채택했다. 최종 frozen source의 native508/0·Python51·Web/Windows export를 통과했고 브라우저·clean CI·공개/릴리스·실기기·AAA 승인은 pending**이다. 앱 버전의 원본은 [project.godot](../game/project.godot), 실행 결과는 [판본별 검증 기록](validation/v0.1.11/README.md)에 둔다.

## 먼저 바로잡은 품질 모드 해석

[설정 UI](../game/scripts/ui/hud.gd)와 [품질 적용](../game/scripts/game.gd)을 함께 읽으면 숫자의 의미를 확인할 수 있다. `0`은 균형 모드, `1`은 성능 모드다. 숫자가 크면 더 높은 품질이라는 가정을 적용하지 않는다. 기존 v0.1.10 실제 비교 영상은 품질1에서 촬영됐으므로, 그림자가 없는 그 화면만 보고 균형 모드의 그림자 결함을 확정할 수 없다. 초기에 제기한 **고품질에서 그림자가 꺼지는 역전 버그라는 해석은 기각**했다.

| 설정 값 | UI의 뜻 | 기존 실제 정책 | 비교 시 주의점 |
| --- | --- | --- | --- |
| `0` | 균형 · 기본 해상도 / 그림자 | 주광 그림자 켬, native3D scale1.0 / Web 기본.8 | Web의 DPR 보정은 별도이며 native1.0 캡처를 Web.8 캡처라고 부르지 않음 |
| `1` | 성능 · 낮은 해상도 / 간단한 그림자 | 주광 그림자 끔, native/Web 기본3D scale.65, 새 후보에서 근사 ellipse | 기존 모드의 실제 주광 그림자 생략을 유지하면서 근사 지면 표현을 추가. 캐릭터·바닥의 가독성은 같은 모드끼리 비교 |

모바일 Web은 실제 DPR에 따라 추가 상한을 적용한다. 설정값·실제 viewport scale·CSS/backing/논리 크기와 실제 광원 shadow flag를 기록하며, 저장된 기존 `quality`0/1의 의미를 바꾸지 않는다. 화질 모드 간 비교와 source 전후 비교는 각각의 축이다.

## 제작 방향과 보존 경계

기존 화면에서는 밝기가 비슷한 하늘·석재·캐릭터와 성능 모드의 지면 그림자 생략이 공간의 깊이와 발의 접지 인상을 약하게 만들었다. 이를 조명·반사·안개와 근사 지면 표현의 별도 검수 대상으로 다룬다. 새 질감이나 외부 생성물을 더한 것이 이번 결과의 전제는 아니다.

- [Sanctuary](../game/scripts/world/sanctuary.gd)의 key/fill·sky/ambient/reflection·fog 조합을 조정한다. 같은 몸체·재질·포즈를 사용해 흰 머리/밝은 돌의 날아감, 검은 갑옷의 뭉개짐, 적과 출구의 구분을 확인한다.
- 품질 적용은 광원의 밝기 문턱으로 역할을 추정하는 기존 결합을 줄이고, 주광 역할과 명시적인 품질 정책으로 다룬다. 밝기 변경이 성능 모드의 그림자를 다시 켜는 결과를 만들지 않는지 native에서 실제 q0→q1→q0 전환을 확인한다.
- 성능 모드의 새 지면 표현은 실제 지면 질의를 근거로 한 유한 soft ellipse 후보다. **근사 grounding이며 물리적으로 정확한 접촉 그림자나 AAA 승인이 아니다.** 깊이 검사·무지면/높이/경사 조건·업데이트/노드 수 한도와 균형 모드의 중복 방지를 검사한다. 실제 구현과 관찰 결과가 나오기 전에는 이 조건을 통과했다고 쓰지 않는다.
- 전투 판정·피해·이동·충돌·저장 스키마·입력·게임 RNG와 기존 source GLB/이미지/무기·카메라/모션은 이 제작 단위의 변경 대상에서 제외한다. 보존 여부는 실제 diff·source hash·회귀 검사로 확인한다.

[GroundingShadow](../game/scripts/actors/grounding_shadow.gd)의 현재 정책은 q1에서만 실제 layer1 지면으로 ray를 쏘고, 지면 법선과 capsule 하단 높이를 사용해 유한 ellipse를 놓는다. 최대 불투명도.21, 지면 위12mm, 높이.05~1m에서 감쇠, 일반 질의.1초/강제 질의 최소1/30초, 표시 최대8개다. 무지면·과도한 경사·높이·숨김/죽음·지원하지 않는 scale에서는 숨기며 깊이 검사를 유지한다. shared quad/shader와 개별 fade material을 사용한다. 이는 구현된 정책이며 목표 기기의 비용 측정값은 아니다. [첫 native checkpoint](validation/v0.1.11/native-first-checkpoint.json)는508/0과 실제 floor/ledge/height/quality fixture를 보존하지만, 그 뒤 변경된 source bytes의 최종 통과 근거로 사용하지 않는다.

[최종 native checkpoint](validation/v0.1.11/native-final-checkpoint.json)는 실제 frozen9개 source의 해시 일치와508/0을 확인했다. 최신 grounding fixture는 바닥 불투명도.21, 높인 capsule의.049599, 실제12physics frame 중 정지 질의1회와 표시7개를 기록했다. 실제 floor/ledge/높이/경사·품질 전환·자원 공유·수명/표시 한도의 유한 검증이며 상시 목표 GPU 비용이나 움직이는 발의 물리적 그림자 품질을 증명하지 않는다.

## 렌더러 지원과 실제 조명은 각각 확인한다

엔진 원본은 [toolchain.json](../tools/toolchain.json)의 Godot4.7.2다. Compatibility에 대해 오래된 판본의 지원표를 그대로 적용하지 않는다. [고정 source·공식 문서 원장](validation/v0.1.11/renderer-evidence.json)은6개 원문의 HTTP200·default TLS·bytes/SHA와 읽은 구간을 보존한다. 4.7 공식 표와4.7.2 GLES3에서 AgX를 포함한 tone mapping, depth/height fog, 기본 SSAO와 glow 경로를 확인했다. SSR·volumetric fog·PCSS의 지원을 추정하지 않는다. 고급 property 일부는 Compatibility에 노출되지 않으며 지원과 비용·화면 채택은 각각 확인한다. 이번 첫 후보는 SSAO/glow를 켜지 않고 직접광·환경광·반사·안개 분리를 우선한다.

완전한 sky contribution에서는 ambient energy 하나를 줄여도 기대한 diffuse 대비가 나오지 않을 수 있다. [GLES3 shader](https://github.com/godotengine/godot/blob/4.7.2-stable/drivers/gles3/shaders/scene.glsl#L2472)의 혼합과 [C++ 입력 구성](https://github.com/godotengine/godot/blob/4.7.2-stable/drivers/gles3/rasterizer_scene_gles3.cpp#L1598)을 함께 읽었다. explicit ambient RGB는 color×energy, sky 항은 background multiplier와 혼합 비율을 사용한다. 비율1은 앞 항을 대체하므로 `.ambient_light_energy`만의 변화가 전체 sky diffuse를 감쇠한다고 가정하지 않는다. 실제 ambient source·sky contribution·background energy·reflected source와 key/fill을 함께 기록한다. 이 source 해석과 실제 픽셀 결과는 별도다.

[tone mapper dispatch](https://github.com/godotengine/godot/blob/4.7.2-stable/drivers/gles3/shaders/tonemap_inc.glsl#L172)는 LINEAR/REINHARD/FILMIC/ACES/AGX를 선택하고 실제 `tonemap_agx()`를 호출한다. UBO 설정·shader 호출 경로가 존재한다는 증거이며, Environment property 숫자 하나나 매크로 이름 검색만으로 실제 화면의 tone mapping·품질을 승인하지 않는다.

## 같은 실제 장면으로 비교한다

[조명 비교 도구](../tools/render_lighting_review.py)와 [fixture](../game/tests/lighting_review_capture.gd)는 서로 독립된 baseline/candidate 프로젝트의 실제 `main.tscn`·Hero/Sentinel·courtyard·RuneCamera를 사용하도록 준비한다. 정해진 위치와 idle 포즈, 고정 camera/overview, 실제 HUD를 둔 **controlled scene-view**다. 실제 플레이 입력·적 AI·명중·성능 검증으로 해석하지 않는다.

baseline/candidate 각각 q0/q1의 싸움 카메라와 overview를 비교해 원본 PNG와 source/renderer/품질·광원·환경·재질·카메라·포즈를 보존한다. 한 source의 그림자 모드와 다른 source의 성능 모드를 비교해 조명 개선이라고 부르지 않는다. UI가 켜진 원본에서 적·발·검·바닥·출구와 예고의 구분을 확인하고, 노출이나 색보정으로 후보 이미지만 후처리하지 않는다.

[baseline4장과 최종 후보002의4장](validation/v0.1.11/paired-capture-checkpoint.json)을 각각64.096초/53.105초의 실제 실행으로 확보했다. 원본 SHA를 직접 재계산했고 fixture·엔진·viewport·renderer/adapter와4개 shot의 camera/품질/scale/배우 profile/위치가 일치했다. 후보 q0에서는 실제 주광 그림자 ON·근사 ellipse4개 숨김, q1에서는 주광 OFF·근사 ellipse4개 표시/불투명도.21이 관찰됐다. Linux OpenGL Compatibility/Mesa llvmpipe이며 엔진 오류는 없었다. 소프트웨어 renderer의 캡처 시간은 목표 GPU의 게임 FPS가 아니다.

첫 후보001은 q0 바닥에 촘촘한 규칙적 격자가 생겨 기각했다. 후보002에서 주광 normal bias만1.1→2.0으로 복구한 뒤 실제 q0 격자가 사라졌다. 두 q1 원본은001과 byte 단위로 같다. 루트 검수자는002의 q0/q1 전투 화면을 직접 보고 바닥·금속 세부와 유한 근사 접지를 prototype 범위에서 채택했다. [원본·기각 근거·검수 경계](validation/v0.1.11/lighting-review/README.md)를 보존한다. 평평한 중립색 하늘, 어두운 갑옷 전면, 단순한 건축 형태는 남았으며 상세한 움직이는 발 그림자나 AAA 접촉 품질로 승인하지 않는다.

## 완료 범위

새 source 구조·native 품질/지면 계약, source 고정 원본 raster의 유한 관찰, 최종 Web/Windows export, 실제 브라우저와 공개/릴리스는 각자의 결과로 판정한다. 이전 [v0.1.10 공개 검증](validation/v0.1.10/published-verification.json)은 그 판본의 완료 근거이며 새 조명을 검증하지 않는다. 얼굴·손·갑옷·머리카락·전체 이동/접촉, 연속 AV·청취·목표 Android/iOS/Safari/Windows 성능과 대표 구간 AAA 최종 판정은 계속 별도다.
