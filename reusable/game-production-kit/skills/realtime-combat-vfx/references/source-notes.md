# 출처와 적용 범위

조사일: **2026-11-07 UTC**. 아래는 공개 페이지와 공식 문서 열람 결과이며 이 스킬로 새 효과를 실행·제작·성능 승인했다는 기록이 아니다. 특정 버전의 지원 표를 미래 버전이나 다른 기기로 승계하지 않는다.

## 사용자가 지정한 자료

[RedefineFX — The Witcher Niagara Fluids Beginner Course](https://redefinefx.com/witcher/)의 공개 소개·커리큘럼을 읽었다. 확인 당시 페이지는 Unreal Engine 5.8, Jesse Pitela, 영상 20개와 완성 효과 setup 7개를 소개한다. 연기/불·전기/불꽃·링·보호막·미사일·포털, 시퀀싱과 simulation caching이 목차에 포함되어 있다.

**열람 경계:** 공개 페이지의 목차와 소개를 확인했다. 링크된 트레일러는 웹 읽기 도구에서 throttling으로 가져오지 못했다. 강의실의 20개 영상·자막·노드 값·제공 프로젝트 파일은 열람/실습 완료하지 않았다. 별도 HTTPS 클라이언트의 페이지 요청도 HTTP403이었다. 이를 강의가 유료라는 증거나 모든 클라이언트에서 접근 불가라는 결론으로 쓰지 않는다.

이 스킬의 단계별 제작 지침·레이어 틀·검수 기준은 독립 작성한 실무 종합이다. 강좌의 정확한 recipe·타이밍·셰이더 그래프로 귀속하지 않는다. 강의·이미지·자산을 재배포하지 않으며, 공개 무료 수강 표시를 프로젝트 자산의 재배포 라이선스로 해석하지 않는다.

## 공식 자료와 옮겨 쓸 판단

| 자료 | 확인한 범위 / 이 스킬에서 사용하는 판단 |
| --- | --- |
| [Epic Niagara Fluids, UE5.8](https://dev.epicgames.com/documentation/en-us/unreal-engine/niagara-fluids-in-unreal-engine) | Unreal의 plugin 기반 유체 효과이며 게임용2D/시네마틱용3D template과 베이크 선택을 설명한다. Godot의 동일 기능 존재로 추론하지 않는다. |
| [Epic Flipbook Baker, UE5.8](https://dev.epicgames.com/documentation/en-us/unreal-engine/niagara-flipbook-baker-quick-start-guide-in-unreal-engine) | 비싼 시뮬레이션을 sprite용 atlas로 만드는 대안. 카메라/시간/grid·alpha 표현을 고려한다. 캐시와 플립북을 구분하고 프로젝트별로 재저작한다. |
| [Godot 4.7 렌더러 비교](https://docs.godotengine.org/en/4.7/tutorials/rendering/renderers.html) | 웹은 Compatibility. 내장 particle trails·SDF collision·volumetric fog·compute는 해당 경로에서 미지원이다. depth/screen texture와 glow는 지원 표에 있으므로 일괄 미지원으로 쓰지 않는다. 지원과 실제 성능·화질은 별도다. |
| [Godot 4.7 GPU particles](https://docs.godotengine.org/en/4.7/classes/class_gpuparticles3d.html), [CPU particles](https://docs.godotengine.org/en/4.7/classes/class_cpuparticles3d.html) | GPU/CPU emitter는 별도 선택지. `emit_particle()` 수동 호출의 렌더러 제한과 GPU emitter 전체의 지원을 혼동하지 않는다. restart·좌표계·수명과 실제 target AABB를 확인한다. |
| [Godot 4.7 particle trails](https://docs.godotengine.org/en/4.7/tutorials/3d/particles/trails.html), [particle collision](https://docs.godotengine.org/en/4.7/tutorials/3d/particles/collision.html) | 내장 trail과 SDF particle collision의 Compatibility 제한을 기능별 문서에서도 대조한다. 직접 만든 메시 trail이나 게임 물리 collider의 지원과 혼동하지 않는다. |
| [Godot 4.7 공간 셰이더](https://docs.godotengine.org/en/4.7/tutorials/shaders/shader_reference/spatial_shader.html) | unshaded의 결과는 albedo이며 `TIME`은 scene pause의 시계가 아니다. 효과별 시간과 실제 색 출력을 검수한다. |
| [Godot 4.7 파티클 개요](https://docs.godotengine.org/en/4.7/tutorials/3d/particles/index.html) | emitter와 particle, process와 표시의 역할을 구분한다. CPU/GPU의 비용·기능 차이는 실제 목표 장면에서 선택한다. |

Blender 베이크는 이 스킬의 **제안 경로**다. 특정 `.blend`·캐시·플립북을 생성해 검증하지 않았다. Blender 공식 캐시 매뉴얼의 직접 열람 시도가 실패했다면 세부 API나 버튼 순서를 확인한 것처럼 적지 않는다. 실제 작업 시 사용하는 설치 버전의 공식 매뉴얼과 설정으로 확인한다.

## 다음 프로젝트에서 다시 확인할 것

엔진/Blender 실제 버전, 사용 렌더러·브라우저·기기, 필요한 파티클 기능, atlas alpha/색공간/크기, 타격 이벤트와 시계, 성능 예산을 새로 채운다. 이 폴더의 빈 검수 양식은 전부 `pending`이며 원본 프로젝트의 배포·유료 도구 권한·AAA 승인을 전달하지 않는다.
