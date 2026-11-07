# VFX 제작의 런타임 기능 대조

확인일: **2026-11-07 UTC**. 프로젝트 엔진은 [toolchain](../../tools/toolchain.json)의 **Godot 4.7.2**, 기존 아트 기준은 [Blender 4.3.2](../ART_PIPELINE.md)다. 아래는 공개 공식 문서 대조이며 새 이펙트의 실행·성능·시각 품질을 승인한 기록은 아니다. 4.7 문서는 수정될 수 있으므로 엔진을 바꾸거나 세부 기능을 구현할 때 해당 버전의 소스와 실제 브라우저에서 다시 확인한다.

## 1. 웹에서 GPU 파티클을 일괄 배제하지 않는다

Godot 4의 Vulkan과 GLES3 모두 GPU 파티클을 지원한다. CPU 파티클은 더 단순한 대안이며 GPU의 모든 기능을 동일하게 대체하지 않는다. 이 사실을 명시한 [공식 개발 보고서](https://godotengine.org/article/progress-report-state-of-particles/)는 2023년 글이므로 현재 API 제한은 [4.7 GPUParticles3D](https://docs.godotengine.org/en/4.7/classes/class_gpuparticles3d.html)와 함께 읽는다.

- `GPUParticles3D` **자체**의 지원과 개별 기능의 지원을 구분한다. `emit_particle()`의 수동 단일 입자 방출은 Compatibility에서 지원하지 않는다.
- 따라서 웹용 일회성 접촉 효과는 일반 emitter의 `one_shot`/`restart()` 경로, 제한된 CPU emitter 또는 직접 소유한 메시 등 실제 지원 경로로 설계한다. 어떤 경로가 빠른지는 목표 기기에서 측정한다.
- 고정 seed는 비교 촬영에 쓸 수 있지만 게임의 판정·난수 소유권과 분리한다. `visibility_aabb`는 표시와 파티클 상호작용 영역에 영향을 주므로 전 수명·최대 속도·카메라 경계에서 확인한다.

[4.7 파티클 개요](https://docs.godotengine.org/en/4.7/tutorials/3d/particles/index.html)는 CPU/GPU의 기능·비용 차이를 설명한다. 입자 수가 작으면 CPU가 무조건 빠르다거나 GPU면 웹에서도 비용이 없다고 단정하지 않는다.

## 2. Compatibility 기능표를 기준으로 표현을 선택한다

[4.7 렌더러 비교](https://docs.godotengine.org/en/4.7/tutorials/rendering/renderers.html)의 확인 범위:

| 기능 | Compatibility | 제작 판단 |
| --- | --- | --- |
| Web 렌더링 | 지원 | 이 프로젝트의 웹 기준 경로 |
| screen/depth texture | 지원 | soft intersection·약한 왜곡의 후보, 실제 export에서 검증 |
| Glow | 지원 | 사용 여부와 비용·클리핑을 별도 검수; 형태를 bloom에만 의존시키지 않음 |
| volumetric fog | 미지원 | 웹에서는 카드·메시·구운 시퀀스 등의 대체 표현 검토 |
| normal/roughness buffer | 미지원 | Forward+ 전용 버퍼를 웹 공통 셰이더 전제로 삼지 않음 |
| compute shaders | 미지원 | compute 기반 실시간 유체를 웹 공통 경로로 가정하지 않음 |

이 표는 기능 유무의 대조이며 실행 프레임 시간·메모리·모바일 브라우저 호환성의 통과 증거가 아니다. Windows에서도 Compatibility를 쓰면 그 렌더러의 제한이 유지된다.

## 3. 충돌·난류는 입자 시스템 전체와 별도로 확인한다

[4.7 particle collision](https://docs.godotengine.org/en/4.7/tutorials/3d/particles/collision.html)은 SDF particle collision이 Compatibility에서 지원되지 않음을 명시한다. GPU 입자는 게임의 물리 월드에 자동 접근하지 않으며 전용 particle collider가 필요하다. [GPUParticlesCollision3D](https://docs.godotengine.org/en/4.7/classes/class_gpuparticlescollision3d.html)는 CPU 입자에는 적용되지 않는다.

그러므로 표시용 불꽃의 충돌과 전투 피해·벽 차단을 같은 권한으로 취급하지 않는다. 피해·검기 hull은 게임 물리에서 결정하고, 장식 입자는 그 결과를 표시한다. 낙하 파편을 실제 몸체로 만들 때는 별도 수량·수명·충돌 예산을 정한다.

[4.7 turbulence](https://docs.godotengine.org/en/4.7/tutorials/3d/particles/turbulence.html)는 3D noise의 GPU 비용 때문에 mobile/web 사용을 권장하지 않는다. 난류를 크게 켜서 형태를 만드는 대신 구운 흐름, 작은 속도 변형 또는 셰이더 UV 변화로 대체하는 것은 **프로젝트의 제작 선택**이며 동등한 유체 정확도 보증은 아니다.

## 4. 플립북은 유체 캐시와 다른 산출물이다

[Sprite3D](https://docs.godotengine.org/en/4.7/classes/class_sprite3d.html)의 `hframes`/`vframes`/`frame` 또는 [AnimatedSprite3D](https://docs.godotengine.org/en/4.7/classes/class_animatedsprite3d.html)의 `SpriteFrames`로 3D 공간에 시퀀스를 표시할 수 있다. [SpriteBase3D](https://docs.godotengine.org/en/4.7/classes/class_spritebase3d.html)에는 billboard와 depth-test 설정이 있으며 alpha 혼합에는 정렬 문제가 생길 수 있다. 벽 뒤까지 보이게 하는 depth-test 비활성화를 기본 해법으로 쓰지 않는다.

입자 sprite sheet에는 [BaseMaterial3D](https://docs.godotengine.org/en/4.7/classes/class_basematerial3d.html)의 `BILLBOARD_PARTICLES`, 행·열 설정과 애니메이션 속도를 함께 맞춘다. 같은 atlas라도 Sprite3D frame 제어와 particle 재생 설정은 다른 경로다.

[Blender 4.3 fluid cache](https://docs.blender.org/manual/en/4.3/physics/fluid/type/domain/cache.html)는 Replay/Modular/All과 볼륨 캐시를 설명한다. 이는 재계산을 줄이기 위한 **저작 캐시**다. 이 페이지는 직접 열기에서 fetch 오류가 났으나 공식 URL의 검색 인덱스 본문을 확인했다. 캐시·렌더 시퀀스·게임용 atlas를 별도 기록하고, 캐시가 만들어졌다고 atlas·알파·런타임 재생을 완료 처리하지 않는다.

이 문서에서 Blender→투명 이미지 시퀀스→atlas→Godot 표현은 **제안한 제작 경로**다. 새 플립북의 bake/render/import·프레임 순서·pivot·색/알파·여백·mipmap 경계는 아직 실행하지 않았다.

## 5. depth fade와 화면 왜곡은 렌더러 좌표계를 따른다

[Advanced post-processing 4.7](https://docs.godotengine.org/en/4.7/tutorials/shaders/advanced_postprocessing.html)은 depth texture의 비선형 값과 역투영을 설명한다. Compatibility의 OpenGL NDC Z는 `[-1,1]`, Forward+/Mobile은 `[0,1]`이므로 같은 reconstruction 식을 무조건 복사하지 않는다. 현재 viewport의 depth를 사용하고 역투영·나눗셈·근/원거리·바닥 교차를 실제 화면에서 검사한다.

[Screen-reading shaders 4.7](https://docs.godotengine.org/en/4.7/tutorials/shaders/screen-reading_shaders.html)의 3D screen texture는 불투명 pass 뒤·투명 pass 전에 복사된다. 다른 투명 VFX까지 정확히 굴절한다고 가정하지 않는다. depth fade는 장식의 교차를 부드럽게 할 뿐 실제 벽 충돌이나 피해 범위를 대신하지 않는다.

## 6. unshaded 출력은 실제 색이 있어야 한다

[Spatial shader 4.7](https://docs.godotengine.org/en/4.7/tutorials/shaders/shader_reference/spatial_shader.html)은 `unshaded` 결과가 albedo임을 명시한다. EMISSION만 쓰고 화면에 보일 것이라고 가정하지 않는다. `ALBEDO`·`ALPHA`·blend mode와 텍스처의 색공간을 맞춘 뒤 실제 Compatibility raster를 확인한다. [4.7.2 GLES3 scene source](https://github.com/godotengine/godot/blob/4.7.2-stable/drivers/gles3/shaders/scene.glsl)를 버전 대조 근거로 둔다.

배경이 검은 미리보기에서 빛나는 것과 밝은 전투 바닥에서 핵심 형태가 읽히는 것은 다른 검수다. 빛·입자량을 늘려 애니메이션·접촉·입체감의 결함을 숨기지 않는다.

## 7. Niagara는 표현 참고와 별도 도구 경로다

[Epic Niagara Fluids 공식 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/niagara-fluids-in-unreal-engine)는 Unreal plugin과 그 template를 설명하고, 무거운 유체를 flipbook으로 구워 material에서 쓰는 방법을 안내한다. 따라서 Niagara 시스템·시뮬레이션 캐시가 Godot 리소스로 자동 변환된다고 전제하지 않는다. 이 마지막 비자동 이식 판단은 도구·리소스 경계에 대한 **엔지니어링 판단**이며 해당 강좌가 Godot 변환을 제공한다는 주장이 아니다.

이번 스킬에서 가져갈 것은 레이어의 역할·시간 구조·표현을 고르는 절차다. Niagara 실습을 추가로 수행한 경우에만 해당 버전·강의 접근 범위·직접 수행 결과를 새 근거로 남긴다.
