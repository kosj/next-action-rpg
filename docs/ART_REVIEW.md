# 아트 파이프라인 재검증

확인일: **2026-10-30**. 저장소의 실제 자산·반입 설정과 공식 자료를 대조했습니다. 아래 성능 수치는 목표 PC의 실측 결과가 아니라 GLB 파일 구조를 읽은 정적 계수입니다.

## MCP와 제작 방향 정정

추가 조사에서 [VARCO의 공식 MCP 설정 문서](https://3d.varco.ai/mcp/setup.md)와 [Codex 연결 안내](https://3d.varco.ai/docs/blog/2026-07-14-connect-varco-3d-to-codex-or-claude-with-one-prompt)를 확인했습니다. 서버는 `https://3d.varco.ai/api/mcp`이며 연결 가능성과 현재 세션의 등록·인증 상태는 별개입니다. 기존 조사에서 Blender Bridge만 확인하고 MCP 경로를 빠뜨린 것은 조사 누락입니다. [연결·인증 검증 절차](VARCO_MCP.md)를 추가했습니다.

단순 도형을 조합한 현재 화면은 Blender의 품질 한계를 보여 주는 근거가 아닙니다. 최종 조형·텍스처·스킨·모션·장면 조명이 없는 블록아웃의 한계입니다. 주인공을 포함한 VARCO 생성 후보와 Blender 후처리, Godot의 조명·VFX를 함께 검수하는 방식으로 방향을 갱신했습니다. 첫 범위와 합격 기준은 [아트 제작 가이드](ART_PIPELINE.md)에 기록합니다.

## 버전과 판단

재검증 시작 시 실행 기준은 Godot 4.6.3, 원본 생성기는 Blender 4.3.2입니다. [Godot 공식 최신 릴리스](https://github.com/godotengine/godot/releases/tag/4.7.2-stable)는 4.7.2-stable(2026-08-18), [Blender 공식 유지 버전 목록](https://www.blender.org/download/lts/)에는 5.2.3 LTS와 4.5.15 LTS(2026-10-22)가 표시됩니다.

- Godot 4.7.2는 격리한 환경에서 기존 저장 v1, 전투 회귀 검사, 캐시 없는 반입, 웹/Windows 내보내기와 실제 브라우저 검증이 통과한 뒤 기본 버전으로 승격합니다. 스킬이 4.7을 대상으로 한다는 이유만으로 엔진을 바꾸지 않습니다.
- Blender 원본은 4.3.2로 재현할 수 있게 유지합니다. 새 LTS는 기존 원본의 사본에서 생성기 실행, 재내보내기와 모션·재질 동등성을 확인한 뒤 별도로 전환합니다. 기존 원본을 새 버전으로 일괄 덮어쓰지 않습니다.
- Blender 4.4 이후 Action Slots 도입으로 glTF 애니메이션 병합의 기본 동작이 달라졌으므로, 향후 모션 제작에선 exporter의 Animation Mode와 Actions/NLA 구조를 버전과 함께 기록합니다. 현재 생성기는 `export_animations=False`여서 이 경로를 검증하지 않았습니다. [Blender 5.2 glTF 공식 설명](https://docs.blender.org/manual/nl/5.2/addons/scene_gltf2.html)

## 현재 자산에서 확인한 사실

GLB JSON의 노드·프리미티브·접근자 정보를 읽어 다음을 확인했습니다. 삼각형 수는 인덱스 수를 기준으로 한 원본 계수이며 LOD와 렌더 패스는 포함하지 않습니다.

| 자산 | 노드 | 메시 프리미티브 | 머티리얼 | 삼각형 | 스킨 | 클립 |
|---|---:|---:|---:|---:|---:|---:|
| hero | 56 | 42 | 7 | 6,272 | 0 | 0 |
| sentinel | 51 | 37 | 5 | 5,372 | 0 | 0 |
| boss | 53 | 39 | 5 | 5,588 | 0 | 0 |
| keeper | 51 | 38 | 7 | 5,840 | 0 | 0 |

이 자산은 독립 피벗과 다수의 개별 메시로 표현하는 블록아웃입니다. 스켈레톤·웨이트·완성 모션이 검증된 자산으로 분류하지 않습니다. 프리미티브 수를 실제 드로콜 수와 동일하게 취급하지는 않지만, 적 수가 늘어날 때 CPU 렌더 제출과 머티리얼 비용을 살필 근거가 됩니다. 단순히 폴리곤을 늘리는 것이 다음 작업의 우선순위는 아닙니다.

반입 파일에는 `meshes/generate_lods=true`가 이미 설정되어 있습니다. 그러나 `Sanctuary`가 런타임에 만드는 BoxMesh·CylinderMesh는 GLB 반입 경로와 별개이므로 이 옵션이 전체 성역을 자동 최적화하지 않습니다. 반복 정적 장식은 메시 공유와 구역별 묶음을 먼저 검토하고, 프로파일링에서 효과가 확인되는 항목만 MultiMesh나 HLOD로 전환합니다.

## 최종 캐릭터로 전환할 계약

1. **한 캐릭터부터 검증:** 리라의 최종 스킨과 이동·회피·핵심 베기만 작은 검수 씬에 반입합니다. 본체의 실제 크기, 발바닥, 무기 그립과 공격 범위를 맞춘 뒤 나머지 모션을 확장합니다.
2. **리그 방향·본 매핑:** 게임 루트는 이동 전방 -Z를 유지하고, Humanoid 프로필은 T-pose/+Z의 리타겟 규칙에 맞춥니다. 표현 래퍼에서 방향을 한 번만 변환합니다. 같은 본 이름만으로 모션 공유가 보장되지 않으므로 Bone Rest와 BoneMap도 검사합니다. [Godot 4.6 리타겟](https://docs.godotengine.org/en/4.6/tutorials/assets_pipeline/retargeting_3d_skeletons.html), [4.7 리타겟](https://docs.godotengine.org/en/4.7/tutorials/assets_pipeline/retargeting_3d_skeletons.html)
3. **원본과 게임 씬 분리:** 반입된 GLB를 게임 래퍼 씬 안에 인스턴스화하고, 무기 부착·AnimationTree·게임 스크립트는 래퍼에서 관리합니다. 재반입으로 덮어쓰는 캐시 씬을 직접 편집하지 않습니다.
4. **표현 소유권:** AnimationPlayer는 클립을 제공하고 AnimationTree가 전환·블렌딩을 소유합니다. Tree가 활성화된 같은 트랙을 Player.play로 동시에 구동하지 않습니다. 이동은 in-place 클립을 우선하고, 현재의 물리 이동·공격 데이터·피해 판정이 권한을 유지합니다. 공격 완료를 시각 클립의 종료 신호 하나에만 의존시키지 않습니다. [Godot 4.6 AnimationTree](https://docs.godotengine.org/en/4.6/tutorials/animation/animation_tree.html), [4.7 AnimationTree](https://docs.godotengine.org/en/4.7/tutorials/animation/animation_tree.html)
5. **클립 검수:** RESET, 루프, 해결되지 않는 트랙, 레이어 필터, 고정 시각의 포즈, 발 접지와 실제 이동 속도를 검사합니다. 체격 변경 후 보폭도 다시 확인합니다. Root motion은 현재 필수가 아니며 채택할 경우 물리 이동과 중복 적용되지 않는 별도 검증을 거칩니다.
6. **메시와 재질 정리:** 최종 웨이트를 만든 뒤 공통 재질과 아틀라스를 검토합니다. 현재의 피벗 메시를 먼저 단순 병합하면 코드가 움직이는 관절 계층이 사라지므로 리깅 전 최적화로 수행하지 않습니다.

## LOD·렌더 품질 검증

Godot는 반입 시 자동 메시 LOD를 만들 수 있지만, 스킨 메시의 변형 오류가 생길 수 있으므로 원거리 실루엣·관절을 직접 확인합니다. LOD는 메시 복잡도를 줄이는 수단이고 텍스처·드로콜·조명 비용 전체를 대신하지 않습니다. 웹 Compatibility와 Windows Forward+에서 대표 전투의 프레임 시간·실제 드로콜·메모리·최초 셰이더 준비 시간을 각각 기록합니다. [공식 Mesh LOD 설명](https://docs.godotengine.org/en/4.6/tutorials/3d/mesh_lod.html)

## VARCO 최신 기능의 적용 범위

[In-Place 옵션](https://3d.varco.ai/docs/release-notes/2026-02-04-in-place-animation-control)과 [휴머노이드 루프 모션](https://3d.varco.ai/docs/release-notes/2026-10-07-looping-animations-ready-to-use)은 코드 주도 이동에 사용할 후보입니다. 생성 결과가 게임에 맞는 보폭·관절 품질을 보장한다고 간주하지 않고 같은 검수 씬을 통과시킵니다.

[2026-10-12 라이선스 변경](https://3d.varco.ai/docs/release-notes/2026-10-12-choose-a-license-when-you-generate)은 Free 생성물이 Public(CC BY 4.0), Private 선택은 Plus 이상임을 명시합니다. Community 게시는 CC0로 유지되므로 자동 게시를 제작 파이프라인에 넣지 않습니다. 현재 자산에는 VARCO 생성물이 없습니다. 생성 범위를 소품으로 제한하지 않고 캐릭터·룬도 생성 후보에 포함하며, 자산 용도와 계정 플랜에 맞는 공개 범위·귀속 조건을 생성 전에 확인합니다.

## 읽고 선택 적용한 공개 스킬

공개 스킬은 제3자 작업 지침이며 공식 엔진 규격은 아닙니다. 최신 파일 변경일·대상 버전·라이선스를 확인한 뒤, 현재 프로젝트에 해당하는 원칙을 공식 문서에 대조했습니다. 설치 스크립트나 외부 에이전트 키트는 실행하지 않았습니다.

| 스킬 | 확인 리비전·파일 변경일 | 채택 범위와 제한 |
|---|---|---|
| [godot-animation](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/blob/a873f517e5a0f3a2bf5b2414688e811c783b042c/skills/godot/godot-animation/SKILL.md) | `a873f517e5a0f3a2bf5b2414688e811c783b042c`, 2026-10-24, Apache-2.0 | Player/Tree 역할 분리, 파라미터 경로·활성화·재생 소유권 검수. 4.7 전용 API는 4.6 기준에 그대로 쓰지 않습니다. |
| [scenario-godot-animation](https://github.com/scenario-labs/skills/blob/b8544b9c86e0685844cc6effbb27f3885f744d3a/skills/game-engines/godot/scenario-godot-animation/SKILL.md) | `b8544b9c86e0685844cc6effbb27f3885f744d3a`, 2026-10-29, MIT | 게임 상태와 표현 분리, RESET·트랙·발 속도 검수. 자체 macOS/Forward+/Jolt 결과는 이 프로젝트의 검증 결과로 재사용하지 않습니다. 전용 MCP·키트 설치 지시도 채택하지 않습니다. |
| [Godot development](https://github.com/saschb2b/skills/blob/72111b74be5f21b59a3f247d40ef570365042f33/skills/engineering/godot/SKILL.md) | `72111b74be5f21b59a3f247d40ef570365042f33`, 2026-06-21, MIT | 먼저 실제 엔진 버전을 확인하고 오래된 버전 주장을 공식 자료에 재확인하는 원칙. 문서 스냅샷 자체는 2026-06-19입니다. |

`godot-animation` 파일의 최신 변경은 10월 24일이며, 컬렉션 HEAD는 확인 당시 `19d93f97c9c1ea0f8b306e77aa81e0d3e352d3e9`(10월 28일)였습니다. 전체 컬렉션을 도입한다면 개별 파일 변경일과 컬렉션 고정 리비전을 구분해 기록합니다. 원문을 저장소에 복사할 때는 해당 리비전의 [LICENSE](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/blob/a873f517e5a0f3a2bf5b2414688e811c783b042c/LICENSE)와 [NOTICE](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/blob/a873f517e5a0f3a2bf5b2414688e811c783b042c/NOTICE)를 함께 보존합니다. 이 검토 문서는 원칙을 요약해 적용하며 외부 스킬 원문·코드를 복사하지 않았습니다.
# 추가 실험: Blender 5.2.3 LTS

공식 Linux 아카이브의 SHA-256 `78486c018b4443efe5e75ab54c290ed8c15abafd249b862c2c9ce2530a918eec`를 검증하고, `/tmp`의 별도 복사본에서 기존 생성기를 실행했습니다. 공유 Blender 원본과 게임 GLB는 바꾸지 않았습니다.

- 네 GLB의 노드명·부모·전체/관절 로컬 행렬(최대 오차 0), 재질 JSON, 메시·프리미티브·삼각형 수가 일치했습니다.
- Godot 4.7.2에서 양쪽 파일을 실제 반입하고 NodePath·Node3D 변환·surface 수를 비교해 실패 0개, 반입 오류·경고 0개를 확인했습니다.
- 생성 완료 뒤 프로세스가 PulseAudio 경고와 함께 남아 최종 30초 제한을 넘겼습니다. 정상 배치 종료 게이트는 미통과입니다.
- 원시 BIN/accessor는 바이트 동일하지 않고, keeper BIN은 186,680→187,688바이트입니다. 시각적 동등성·스킨·모션은 검증하지 않았습니다.

따라서 자동 생성 실행 기준은 Blender 4.3.2로 유지합니다. 구조 비교 통과를 전체 파일·최종 아트 동등성으로 확대해 해석하지 않습니다. [구조 비교](validation/blender-lts/comparison.json), [프로세스 종료 기록](validation/blender-lts/export-process-result.json), [Godot 비교 로그](validation/blender-lts/godot-comparison.log)를 보존합니다.
