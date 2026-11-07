# Niagara 효과별 제작안과 연결 계약

독립 작성한 시작점이며 RedefineFX 영상의 실제 그래프·수치를 복원한 것이 아니다. 아래 자산·User Parameter 이름은 예시이고 프로젝트의 기존 규칙과 실제 설치 기능이 우선이다.

## 효과별 시작점

| 효과 | Niagara/재질 구성 후보 | 확인할 핵심 |
| --- | --- | --- |
| 대검 검기 | 곡면 Mesh Renderer + 감쇠하는 material mask, 짧은 보조 sprite | release와 실제 진행체를 연결한다. 중앙 두께·끝 taper·사선 실루엣을 먼저 보고 과한 흰 면을 줄인다. |
| 무기 잔상 | 무기 양끝/소켓 표본의 ribbon 또는 별도 생성 strip | link order·world 이력·빠른 스윙 표본 간격·hitstop·중단을 검사한다. 검기 발사체와 다른 시간/이력이다. |
| 불·연기 폭발 | 저해상도 Fluids 후보 또는 flipbook sprite + ember | domain 잘림·압축/alpha·노출을 확인한다. 반응형 live와 고정 bake를 구분한다. |
| 번개 | 시작/끝 anchor가 있는 ribbon/mesh 분기 + 작은 spark | 진단용 고정 seed로 연결과 깜빡임을 본다. 장식 분기를 실제 미명중 적에게 붙여 명중처럼 보이게 하지 않는다. |
| 보호막 | 곡면 mesh material + 접촉 위치 중심 ripple | 방어 성공과 impact normal을 연결하고 카메라가 안/밖에 있을 때의 정렬·가독성을 확인한다. |
| 링·충격파 | 지면 annulus mesh + 방향성 먼지 sprite | 실제 지원 바닥·피해 반경과 장식을 구분하고 경사/벽·낮은 카메라에서 검사한다. |
| 미사일 | 진행체 소유 mesh + wake/ribbon + 독립 impact | gameplay 충돌이 VFX보다 권한을 갖는다. 발사자 회전에 과거 wake가 끌려가지 않게 한다. |
| 포털·흡입 | 테두리 mesh + 내부 material + 제한된 inward 입자 | 물체 이동/흡입은 별도 게임 규칙이며 시각용 vector field만으로 물리 흡입을 완료했다고 하지 않는다. |

## 예시 Blueprint 수명 흐름

```text
권한 있는 AttackRelease / ConfirmedHit 이벤트
  → 공유 attack-target ledger와 이벤트 중복 확인
  → source/target 식별자, world point/normal, strength, material 확인
  → 필요한 NS 후보 선택
  → Auto Activate 꺼진 NiagaraComponent 생성/획득
  → 유효한 component인 경우만 인스턴스 User Parameters 입력
  → Activate
  → 정상 완료 또는 중단 정책
  → 선택한 소유권/pooling 정책으로 정리
```

이 흐름은 제안이지 복사해 바로 실행할 노드 그래프가 아니다. cull/pooling 등의 조건에서 유효 component를 얻지 못한 경우도 처리하고 게임 판정을 VFX 생성 성공에 종속시키지 않는다. 풀로 반환한 component 참조를 다음 공격의 것으로 계속 쓰지 않는다.

## 매개변수 계약 예시

| 제안 이름 | 의미 | 실제 프로젝트에서 정할 것 |
| --- | --- | --- |
| `User.FXIntensity` | 표현 강도 | 범위·기본값·실제 사용하는 module/material binding |
| `User.Tint` | 인스턴스 색 | Linear Color와 노출에서의 해석 |
| `User.ImpactNormal` | 확정 접촉 방향 | world/local Vector와 정규화·orientation 변환 |
| `User.TravelProgress` | 권한 있는 진행 정도 | 원점/거리 정책·0~1 clamp·gameplay 시계 소유자 |
| `User.EffectAge` | 표현용 시계 | material/particle에서 소비되는 경로와 pause/dilation 반응 |

공유 Niagara Parameter Collection/공유 Material Parameter Collection을 개별 타격의 사설 상태 저장소로 사용하지 않는다. 여러 인스턴스를 동시에 발동시켜 서로의 값이 덮이지 않는지 확인한다. 외부 gameplay 식별자와 Niagara particle/ribbon ID도 서로 다른 용도로 유지한다.

## 검기 비교 후보의 작업 순서

동일 gameplay release/trajectory에서 **geometry만 변경 → mask/밝기 분포 → tail → 접촉 디테일** 순으로 비교한다. 각 후보의 renderer/material·입자 수·bounds·품질을 기록하고 최종 후보만 다중 교전/packaged build로 확대한다. 카메라·노출·피격 모션을 바꿨다면 VFX 단독 개선 결과와 나눠 기록한다.

## 국소 반응·크기 계층·힘을 포함한 제작 실험

[RedefineFX 참고 실험 절차](redefinefx-production-lab.md)를 적용한다. 파괴/보호막 후보는 원상태와 확정 접촉 후 상태, 인접 비대상의 무반응을 분리해 시험한다. 큰 조각/주 실루엣과 미세 입자는 독립된 후보로 비교하고, 작은 변형군은 진단용 고정 시드와 별도 시각 RNG로 재현한다. 충돌 표면·반발/흡입·장식 흐름의 소유자를 명시하고, 시각 노이즈를 실제 힘 구현으로 승인하지 않는다. 아래의 레시피·선택은 자체 응용이며 공개 강의의 내부 구현이 아니다.

### Fluids 제어군을 순서대로 확인

Source/debug로 주입의 위치·속도를 확인한다 → domain/해상도·경계를 맞춘다 → 흐름/감쇠를 조정한다 → density/temperature의 Render mapping을 다듬는다 → 낮은 품질·실제 교전에서 비용을 확인한다. 실제 template에 없는 pin/속성을 추측하지 않는다. Chaos 파괴가 요청된 경우에만 anchor/strain/force·활성 영역을 다루고 원래 gameplay의 확정 접촉과 분리한다.
