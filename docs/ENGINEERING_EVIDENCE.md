# 구현 방향 재검증 — 2026-10-30

전투·저장·아트 검토를 병렬로 수행하고, 공식 문서·공개 Agent Skills·실제 재현 검사를 대조했습니다. 새 기능의 양을 늘리기 전에 공격 판정과 저장 실패가 일관되게 처리되는지를 먼저 보강합니다.

## 결정과 근거

| 항목 | 확인한 근거 | 이번 결정 |
|---|---|---|
| 엔진 | [Godot 4.7.2 유지보수 공지](https://godotengine.org/article/maintenance-release-godot-4-7-2/)의 Windows 고주사율 마우스 입력·Shift 키 수정, [릴리스 정책](https://docs.godotengine.org/en/stable/about/release_policy.html) | 기존 4.6.3과 분리한 깨끗한 환경에서 회귀 검사를 통과한 4.7.2를 검증 대상으로 승격. 동일 버전 에디터·템플릿을 `tools/toolchain.json`으로 고정하고 웹·Windows·브라우저 검증 후 배포합니다. |
| 웹·Windows | [웹 내보내기](https://docs.godotengine.org/en/4.7/tutorials/export/exporting_for_web.html), [렌더러 비교](https://docs.godotengine.org/en/4.7/tutorials/rendering/renderers.html) | GDScript, 웹 Compatibility/WebGL 2.0·단일 스레드, Windows Forward+를 유지합니다. 웹과 Windows는 같은 전투 코드를 공유합니다. |
| 공격·카메라 | [물리 공간 질의](https://docs.godotengine.org/en/4.7/classes/class_physicsdirectspacestate3d.html), [물리 처리](https://docs.godotengine.org/en/4.7/tutorials/physics/physics_introduction.html) | `intersect_shape`가 motion을 처리하지 않으므로 베기의 각도·이동을 명시적으로 표본화합니다. 360도 스킬은 원통 영역으로 검사하고 카메라 충돌 질의는 물리 틱으로 이동합니다. |
| 물리 엔진 | [Jolt 차이](https://docs.godotengine.org/en/4.7/tutorials/physics/using_jolt_physics.html) | 버전 변경과 충돌 엔진 변경을 한 번에 묶지 않습니다. 명시된 GodotPhysics3D를 유지하고 공격 거리·문·벽·패링을 회귀 검사합니다. |
| 저장 | [FileAccess](https://docs.godotengine.org/en/4.7/classes/class_fileaccess.html), [DirAccess](https://docs.godotengine.org/en/4.7/classes/class_diraccess.html), [JSON](https://docs.godotengine.org/en/4.7/classes/class_json.html) | 검증된 primary만 backup으로 회전하고 쓰기·flush·rename 실패를 검사합니다. 새 게임과 강화 실패 시 상태를 복원합니다. 선택 필드로 설정과 여정의 존재를 구분하며 정상적인 기존 v1 파일 호환은 유지합니다. |
| 웹 저장 | [웹 영속 저장 제약](https://docs.godotengine.org/en/4.7/tutorials/export/exporting_for_web.html#using-cookies-for-data-persistence) | `is_userfs_persistent()`만으로 저장을 보장하지 않습니다. 읽기 전용 QA 상태와 별도 Chromium 프로필로 브라우저 종료·재시작 후 이어하기를 검사합니다. |
| 아트 | [3D 반입](https://docs.godotengine.org/en/4.7/tutorials/assets_pipeline/importing_3d_scenes/available_formats.html), [Humanoid 리타겟](https://docs.godotengine.org/en/4.7/tutorials/assets_pipeline/retargeting_3d_skeletons.html), [Blender LTS](https://www.blender.org/download/lts/) | 현재 GLB는 임시 피벗 모델이며 skins/animations가 없습니다. 최종 리그 +Z와 게임 이동 -Z를 분리하고 Skeleton3D·BoneMap·AnimationLibrary·AnimationTree를 갖춘 대표 캐릭터부터 검증합니다. Blender 4.3.2 원본은 LTS 재내보내기 동등성 확인 전까지 보존합니다. |
| 생성 자산 | [VARCO 2026-10-12 라이선스 변경](https://3d.varco.ai/docs/release-notes/2026-10-12-choose-a-license-when-you-generate), [공식 MCP 설정](https://3d.varco.ai/mcp/setup.md) | VARCO MCP 생성 후보와 Blender 후처리를 조합하고 주인공도 후보에 포함합니다. 생성 시 계정 플랜·공개 범위·귀속 조건을 확인합니다. MCP 등록·인증·실제 호출과 자산 품질은 각각 검증합니다. 현재 게임에 VARCO 생성물은 없습니다. |
| 배포 | [GitHub Pages 커스텀 워크플로](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) | headless 검사와 실제 웹 검사를 모두 통과해야 배포 아티팩트를 올립니다. Pages job에만 Pages/OIDC 권한을 주고 릴리스 첨부는 GitHub Actions 토큰으로 처리합니다. |

## 공개 스킬의 실제 적용

프로젝트에 `.agents/skills/`로 보관한 [awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills)는 커뮤니티 자료이며, 엔진 공식 문서와 구분해 검토했습니다. 조사 시 main 리비전은 `19d93f97c9c1ea0f8b306e77aa81e0d3e352d3e9`(2026-10-28)입니다. 원문·참조 파일·Apache-2.0 LICENSE·NOTICE와 파일별 SHA-256을 보존했습니다. 설치 프로그램이나 외부 애니메이션 키트를 실행하지 않았습니다.

- [godot-physics](../.agents/skills/godot-physics/SKILL.md): 레이어·마스크, 물리 틱 질의, 엔진별 차이를 판정·카메라 검토에 적용했습니다.
- [godot-export](../.agents/skills/godot-export/SKILL.md): 에디터/템플릿 버전 일치, 웹 단일 스레드, 내보낸 빌드의 실제 실행 검사를 적용했습니다.
- [godot-gdscript-headless-testing](../.agents/skills/godot-gdscript-headless-testing/SKILL.md): 비정상 종료 코드, 명시적 실패 집계, 완료 반환값과 45초 watchdog을 적용했습니다. 현재 통합 검사는 autoload·전체 씬·물리 프레임이 필요하므로 Node 씬 runner를 유지하며, 스킬의 간단한 SceneTree runner 예제를 그대로 치환하지 않습니다.
- [godot-animation](../.agents/skills/godot-animation/SKILL.md): AnimationPlayer는 클립, AnimationTree는 표현·블렌딩을 소유하는 계약을 아트 가이드에 적용했습니다. 이동과 공격 판정의 권한은 게임 코드에 남깁니다. 실제 최종 리그·모션 구현이 끝났다고 간주하지 않습니다.

## 재현으로 확인한 수정

- 원형 스킬의 안쪽·후방·큰 delta 판정 누락, 방향 베기 안쪽 누락, 벽 너머 피해와 중복 피해를 검사합니다.
- 패링이 준비된 검 공격·충격파를 취소하고, 약한 후속타가 반격 경직을 줄이지 않게 합니다.
- 휴식·사망 복귀가 입력 예약·차지·패링·경직·쿨다운·대상을 정리하고 새 게임은 초기 룬으로 시작합니다.
- [Input 공식 문서](https://docs.godotengine.org/en/4.7/classes/class_input.html)처럼 GUI가 이벤트를 처리해도 전역 Input 폴링은 영향을 받지 않습니다. 이어하기·재개 클릭이 공격으로 누수되는 문제를 재현하고, UI 복귀 시 잠시 입력을 정리한 뒤 새 공격을 받도록 수정했습니다.
- 손상 primary → backup 복구 → 저장 → primary 재손상 순서에서도 정상 backup을 보존합니다.
- 임시 파일 쓰기·backup 쓰기·각 rename 실패, 저장 실패 후 구매와 새 게임 롤백을 검사합니다. 체크포인트 저장 실패를 휴식 성공으로 표시하지 않습니다. 설정만 저장했을 때 여정이 생기지 않도록 선택 필드 `journey_started`를 추가하고 기존 v1 파일의 호환을 유지합니다.
- 실제 웹 검사를 CI에 추가하고 하위 URL, 모달·입력·첫 전투, 브라우저 재시작 후 저장 복원을 검사합니다.

## 남은 검증

실제 Windows/게임패드, RTX 3060급 60fps·장시간 메모리, 고주사율 카메라 보간, 3명 이상의 30~60분 플레이테스트는 별도 검증 대상입니다. 현재 37~42개 모델 프리미티브와 런타임 성역의 드로콜을 측정한 뒤 최적화를 결정합니다. 상세 아트 근거는 [ART_REVIEW.md](ART_REVIEW.md), 실제 검사 결과는 [VALIDATION.md](VALIDATION.md)에 기록합니다.

사용자가 2026-10-30 저장소를 공개로 전환했고 API에서도 public을 확인했습니다. 공개 전환 후에도 Pages 최초 생성 요청은 연결 앱의 권한 부족으로 HTTP 403을 반환했습니다. [`configure-pages@v5`의 입력 정의](https://github.com/actions/configure-pages/blob/v5/action.yml)도 기본 GITHUB_TOKEN으로는 자동 최초 활성화할 수 없음을 명시합니다. 실제 게시 성공과 공개 URL의 HTTP 응답을 확인하기 전에는 웹 배포 완료로 안내하지 않습니다.
