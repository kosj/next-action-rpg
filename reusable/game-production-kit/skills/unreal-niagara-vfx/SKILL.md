---
name: unreal-niagara-vfx
description: >
  Design, author, integrate, bake, cache, and profile Unreal Engine combat VFX
  with Niagara, Niagara Fluids, materials, ribbons, mesh/sprite renderers,
  Blueprint, and Sequencer. Use for gameplay-timed effects, Sim Cache versus
  flipbook decisions, Effect Types, scalability, and packaged-build visual QA.
---

# Unreal Engine · Niagara VFX 제작

언리얼 프로젝트에서 이펙트를 **설계 → Niagara/머티리얼 저작 → 게임플레이 연결 → 실제 화면·성능 검수**까지 제작한다. 이 폴더 전체를 대상 프로젝트의 `.agents/skills/unreal-niagara-vfx/` 등에 복사한다. 다른 스킬이나 원래 저장소의 상대 경로에 의존하지 않는다.

[출처·버전·열람 범위](references/source-notes.md), [효과별 제작안](references/effect-recipes.md), [제작 명세](references/unreal-vfx-brief.json), [검수 기록](references/review-checklist.md)을 사용한다. 공개 RedefineFX 강좌 소개와 Epic 공식 문서를 참고해 독립 작성했다. 전체 강의 실습이나 실제 `.uasset` 제작을 완료했다는 뜻은 아니다.

## 1. 대상 프로젝트와 효과 계약을 확인한다

1. 실제 `.uproject`, Unreal 버전/빌드, Niagara 관련 plugin, 대상 RHI/플랫폼·품질, 카메라·노출, 목표 기기와 성능 예산을 확인한다. 참고 페이지의 버전을 설치 버전이나 권장 최신 버전으로 간주하지 않는다. 기존 사용자 답변을 재사용하고 통상적인 제작 선택은 작은 실험으로 결정한다.
2. 효과가 예고·무기 궤적·진행체·확정 접촉·잔향 중 무엇을 표현하는지 정한다. gameplay의 판정·피해·소유권과 표시의 경계를 적는다. 멀티플레이면 실제 이벤트 전달과 로컬 표현 정책도 확인한다. VFX spawn이 자동으로 네트워크에 복제된다고 전제하지 않는다.
3. 참조에서 바꿀 실루엣·진행 방향·시간 대비·재질을 구체화한다. 원본 자산/recipe·engine/plugin 버전·source commit·SHA를 보존하고 별도 후보에서 작업한다. 기존 이펙트나 template의 이름 변경을 새 저작으로 표시하지 않는다.
4. [제작 명세](references/unreal-vfx-brief.json)에 미지정 값을 채운다. 권한·예산은 현재 프로젝트 지시에서 확인하며 이전 프로젝트의 실행 권한을 승계하거나 새 승인 단계를 만들지 않는다.

## 2. Niagara 구성과 표현을 선택한다

| 구성 | 담당 역할 | 처음 확인할 것 |
| --- | --- | --- |
| Niagara System | 효과 전체의 emitter·수명·외부 매개변수 | 한 번 발동/유지/중단과 인스턴스 소유자 |
| Emitter | 입자의 생성과 갱신 | CPU/GPU Sim Target, 좌표계와 필요한 데이터 |
| Module stack | 초기화·힘·시간 변화 등 처리 | 실행 그룹·순서·자료형·공간 변환 |
| Renderer + Material | sprite·ribbon·mesh 등의 표시 | 주 실루엣·alpha·정렬·실제 비용 |
| User Parameters | 게임/Sequencer에서 넘길 인스턴스 입력 | 이름·자료형·기본값·활성화 전 초기화 |

주 형태, 빠른 디테일, 접촉, 잔향을 역할별로 설계한다. 역할 하나마다 emitter를 반드시 추가하는 것은 아니다. 실제 움직임이 같은 요소는 renderer/속성으로 합칠 수 있는지 검토하고, 결합 전후의 비용과 제어 편의성을 비교한다.

방향과 두께가 중요한 대검 검기는 mesh·ribbon 후보를 비교한다. sprite는 불꽃·먼지·구운 연기의 후보이며, 어떤 renderer도 실제 무기/진행체 경로를 자동으로 맞춰 주지 않는다. CPU/GPU 선택 역시 입자 수만으로 고정하지 않는다.

## 3. 머티리얼을 먼저 작은 씬에서 검수한다

1. 실제 사용할 renderer에 맞춰 particle color/alpha·UV·필요한 material usage를 확인한다. mask, dissolve, emissive, 왜곡 등 입력의 의미와 범위를 정한다. 각 인스턴스 입력은 User Parameters 또는 renderer/material binding 등 적절한 경로로 전달한다.
2. core/body/tail의 밝기와 밀도를 나눈다. 기본 실루엣을 읽을 수 있게 만든 후 noise와 작은 디테일을 추가한다. 넓은 면 전체를 흰색 additive로 덮어 입체감 부족을 숨기지 않는다.
3. Translucent/Additive 등 혼합 방식과 straight/premultiplied alpha가 맞는지 확인한다. 밝고 어두운 배경의 halo·sort·겹침을 시험한다. depth fade와 refraction은 교차 표현용이며 gameplay 벽 차단을 대신하지 않는다.
4. 고정 노출의 전후 화면과 실제 게임 노출을 모두 확인한다. bloom에만 기대지 말고 낮은 품질과 작은 화면에서도 주 형태를 보존한다. 왜곡/광원·그림자는 필요한 레이어에만 사용한다.

## 4. Niagara Fluids를 쓸 때

필요한 경우 실제 설치 버전에서 Niagara Fluids plugin을 활성화하고 template가 보이는지 확인한다. plugin 재시작·Beta/Experimental 표시·지원 플랫폼은 해당 설치본을 원본으로 기록한다. 공식 문서의 오래된 소개 문장을 현재 상태의 증거로 확대하지 않는다.

- 먼저 작은 domain·낮은 해상도에서 주입 위치/방향·팽창·부력·소멸을 조정한다. 값은 현재 template의 source/control 구조와 실제 노출된 입력에서 읽는다.
- **WorldSpaceSize와 격자 해상도**를 함께 본다. domain만 키우면 디테일 밀도와 비용 조건이 달라진다. 전체 수명의 bounds·잘림·카메라 진입/이탈을 검수한다.
- template의 collision data interface·태그·연결 대상은 시뮬레이션 입력이다. 특정 tutorial의 actor tag가 모든 Niagara 시스템이나 gameplay 물리를 자동 연결한다고 설명하지 않는다.
- 게임용 단순 표현, 실시간 유체, Sim Cache, 플립북 중 역할·상호작용·기기 예산에 맞게 고른다. 고해상도3D 유체를 모든 전투 효과의 기본으로 삼지 않는다.

## 5. Sim Cache와 플립북을 구분한다

| 선택 | 저장하는 것 / 적합한 경우 | 다시 검수할 것 |
| --- | --- | --- |
| Live simulation | 현재 입력으로 갱신하는 효과 | 실제 상호작용·비용·시드/재현 조건 |
| Niagara Sim Cache | 선택된 시뮬레이션 frame/attribute 데이터, 반복 촬영·정해진 연출 후보 | 캡처 속성·시작/끝·bounds·용량·재생 시 적용 가능한 입력 |
| Baker flipbook | 일정 시점·카메라에서 렌더한 이미지 atlas, sprite/material 재생 후보 | 관찰 각도·조명 한계·frame/grid·색/alpha·텍스처 비용 |

Sim Cache는 텍스처 atlas나 Godot용 리소스가 아니다. 캐시에 저장되지 않은 attribute나 data interface를 재생 시 얻을 수 있다고 가정하지 않는다. 캡처 이후 입력을 바꾸면 live와 동일하게 반응하는지도 별도 실험한다.

**플립북 절차:** 시뮬레이션 형태를 먼저 고정한다 → Baker에서 카메라/범위/FPS·frame count·grid·텍스처 크기/출력 의미를 정한다 → 다른 출력 경로에 bake한다 → sprite renderer의 Sub UV와 재질을 연결한다 → 전체 frame 순서·빈 셀·여백/mipmap·alpha 외곽을 검사한다. 정수 셀 크기를 사용하고 `frame_count <= columns * rows`를 지킨다. 파일이 생성됐다는 사실과 실제 재생 성공을 분리한다.

**Sim Cache 절차:** 설치 버전의 지원 경로와 필요한 plugin을 확인한다 → system/입력·시간 범위·시드를 고정한다 → Sequencer 또는 지원되는 Baker/캡처 API로 별도 cache asset에 기록한다 → 해당 component/track에서 재생한다 → 원본과 동일한 시각·입력에서 비교한다. plugin/경로가 제공하는 실제 동작을 확인하고 임의 API를 지어내지 않는다.

Sequencer/Movie Render Queue 촬영은 편집·검수용이다. temporal sampling과 cache interpolation은 simulation 종류와 데이터에 따라 다르다. 정상 gameplay 실행·프레임 시간 검증을 고품질 촬영 결과로 대신하지 않는다.

## 6. Blueprint·애니메이션·타격 이벤트에 연결한다

아래는 **제안하는 통합 흐름**이며 실행해 검증한 Blueprint graph가 아니다. 노드/pin 이름과 자료형은 설치본에서 확인한다. 구체적인 데이터 계약과 [연결 예시](references/effect-recipes.md)를 맞춘다.

1. 소켓을 따라갈 장전/무기 효과는 `Spawn System Attached`, 독립 접촉은 `Spawn System at Location` 또는 프로젝트의 FX 관리자를 검토한다. Attach Point/Location Type과 local/world 공간을 명시하고 실제 반환 component가 유효한지 확인한다.
2. 첫 tick 전에 초기값이 필요하면 Auto Activate를 끈 생성/획득 경로를 사용한다. **component 유효성 검사 → 인스턴스 User Parameters 설정 → Activate** 순서를 적용한다. 위치·방향·색·강도·시드·scale은 선택한 emitter/material에서 실제 소비되는지 확인한다. pool 획득/비활성 상태도 함께 검사한다.
3. 예시 `User.FXIntensity`, `User.ImpactNormal` 같은 이름은 프로젝트가 정의할 인터페이스다. Niagara 내장 이름이나 자동 binding이라고 설명하지 않는다. Position/Vector·Linear Color·단위/좌표계를 구분한다. 기본 Unreal cm·Z-up 관례도 현재 프로젝트의 실제 해석과 대조한다.
4. Anim Notify/Notify State는 준비/스윙 창을 여닫는 표현 트리거로 쓴다. 확정 접촉은 실제 trace/collision/서버 판정 등 프로젝트의 권한 있는 결과를 따른다. Notify가 재생됐다는 이유로 명중 burst나 피해를 생성하지 않는다.
5. 무기 trail은 실제 최종 소켓·Grip/Tip 표본을 사용한다. ribbon ID·link order·표본 간격/좌표계와 빠른 회전의 빈틈을 검사하고, 취소·teleport·respawn에서는 과거 선을 끊는다. attachment와 emitter local-space는 별개 설정이다.
6. hitstop, actor/world time dilation, scene pause, Sequencer 시간이 각 component·particle/material에 어떻게 적용되는지 정한다. 이미 날아간 검기의 소유권과 새 공격의 시계를 구분한다. 효과별 동결을 하나의 age uniform이나 debugger pause만으로 보장하지 않는다.
7. 종료와 중단을 나눈다. 정상 잔향, 즉시 소멸, detach 후 잔류, pool 반환 중 정책을 정하고 레벨 전환/소유자 해제/재사용을 시험한다. Auto Destroy·pooling·참조 보관은 함께 검토하며 모든 경우에 DestroyComponent를 호출하는 일반 규칙을 만들지 않는다.

## 7. 품질 분기와 비용을 검수한다

Effect Type과 프로젝트의 scalability 정책에 맞춰 거리·가시성·동시 인스턴스·emitter/renderer·입자·광원을 제어한다. 낮은 품질에서도 필수 공격 예고와 방향/접촉 정보는 읽히게 한다. VFX가 cull되어도 gameplay가 임의로 바뀌지 않아야 한다.

Niagara Debugger의 Debug HUD·FX Outliner로 실제 활성 system/emitter/입자·bounds·cull 이유를 조사한다. frame time·draw/translucency·메모리는 대상 빌드/RHI·기기에서 제공되는 profiler로 측정한다. 에디터의 단일 효과 미리보기와 packaged build의 다중 교전을 나눠 기록한다.

효과 OFF/ON을 동일 카메라·노출·품질·교전 조건에서 비교한다. warmup·pool priming·첫 shader/asset 사용·재사용의 hitch를 따로 확인한다. GPU sim에도 system/emitter 쪽 CPU 비용이 있을 수 있으므로 GPU 입자 전환만으로 최적화를 완료했다고 쓰지 않는다.

## 전달물과 채택 기준

제작 요청에는 해당 범위의 System/Emitter/Material·텍스처/메시·Blueprint 연결·원본/베이크 recipe·짧은 정상1배속 전후 영상·[검수 기록](references/review-checklist.md)을 남긴다. 에셋명 예시는 `NS_`, `NE_`, `M_`, `MI_`, `T_`, `BP_`, `NET_`이며 프로젝트 명명 규칙이 우선이다.

실제 게임에서 근/원거리·밝고 어두운 배경·명중/빗나감/방패/벽/다중 적·연속 발동·중단/복귀를 확인한다. 형태가 판/흰 띠처럼 보이거나 적·주인공·HUD가 가려지면 기각 이유를 기록한다. 불꽃의 크기만으로 약한 애니메이션을 해결했다고 판단하지 않는다.

문서/스킬 작성 요청이라면 스킬·출처·빈 템플릿·독립 설치 검증까지 완료한다. 실제 Unreal 제작/실행·cook/package·게임플레이·연속 AV·목표 기기 성능·AAA는 각각 새 근거가 생기기 전까지 `pending`이다.
