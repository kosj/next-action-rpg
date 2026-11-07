# 검사 리라의 실제 스킬 VFX 개선

제작일: 2026-11-07 UTC. 대상 후보 버전 **0.1.18**. 사용자가 요청한 것은 게임에서 발동하는 기술의 이펙트다. 이 문서는 제작·검수 계약이며 아래의 실행/게시 결과는 아직 `pending`이다.

## 현재 문제와 제작 범위

기존 `RunePlayer.use_skill()`은 세 기술 모두 발동 순간 `skill_effect`를 발생시키고 `Game.spawn_ring()`의 동일한 `RuneEffect` 토러스를 재생했다. 스킬별 동작·범위·역할과 링 연출이 구분되지 않았고, 준비/활성/회수 시간과도 별도의 `.5s` 재생이었다.

[프로젝트 VFX 스킬](../.agents/skills/runefall-vfx/SKILL.md)과 [RedefineFX 참고 실험](../reusable/game-production-kit/skills/realtime-combat-vfx/references/redefinefx-production-lab.md)을 적용한다. 큰 형태·타이밍·접촉 인과를 먼저 고치고 작은 디테일을 보완한다. 공개 제작글을 참고한 자체 설계이며 특정 강좌의 노드/설정을 복원하거나 전체 강의를 실습한 결과가 아니다.

| 기술 | 새 표현의 방향 | 보존할 실제 게임 계약 |
| --- | --- | --- |
| 섬광 돌진 | 청록색 방향 검광과 실제 이동 위치에서 남는 잔향 | 비용25, 피해65·poise65, 전방160도·reach4.5, 기존 돌진 motor |
| 룬 폭풍 | 보라/청록색 입체 회전 검기·분절된 지면 룬·짧은 부유 조각 | 비용45, 피해55·poise65, 원형360도·reach5.5, 정지 motor |
| 성역의 심판 | 금빛 거대 룬검의 낙하·방사형 지면 균열·잔여 조각 | 비용80, 피해150·poise160, 원형360도·reach7, 정지 motor |

세 기술 모두 기존 startup `.16s`·active `.35s`·recovery `.28s`와 업그레이드 배율·무적/입력/취소·기존 clip을 보존한다. 독립 `AttackData.new()`를 유지하고 heavy/charged의 physical blade profile을 상속하지 않는다. 원형 기술의 판정은 active에 전체 범위를 검사하므로 확장하는 잔향을 별도 이동 피해파로 표시하지 않는다.

## 연결과 수명

발동이 실제 수락된 경우의 `skill_started(CombatStrike)`에서 전용 표시 객체를 만든다. 회복·패링 등 기존 링 사용은 별도로 유지한다. 표시 객체는 원래 strike의 권한 있는 elapsed와 actor의 실제 해결된 위치를 읽으며 새로운 판정·피해·Rune 소비·공유 gameplay RNG를 만들지 않는다.

준비는 응축, active는 주 형태 방출, 회수/완료는 제한된 잔향이다. 접촉 tick에서 strike 시계가 진전하고 hitpause가 시작되면 그 새 시각을 한 번 표시한 뒤 동결한다. 다음 공격/피격·회피 중단·죽음·inactive·source 해제·restore epoch·encounter/title reset에서 이전 효과를 정리한다. SceneTree pause와 공격 hitpause는 구분한다.

동시 효과 수와 mesh/재질·소형 디테일을 제한하고 q0 균형/q1 성능의 기존 의미를 따른다. 대형 텍스처를 추가하지 않는 절차적 메시/셰이더 후보부터 실제 Web 예산을 확인한다. shader `TIME` 대신 효과별 시계로 구동하고 Compatibility의 실제 ALBEDO/ALPHA 출력을 검수한다.

확정 hurtbox 접촉에서만 스킬별 국소 타격 팔레트·카메라 pulse를 적용한다. 심판의 저역 음향도 기존 접촉 dispatcher에서만 발생한다. 공격 시작·빗나감에는 명중 섬광/접촉 카메라/저역을 추가하지 않는다. 사용자 shake 설정을 유지한다.

## 채택 기준과 근거 범위

1. 실제 Player의 수락/거절·세 cast와 실제 Game 표시 연결, 준비/활성 차이·동결·완료/중단·복귀·동시 인스턴스를 native 회귀로 확인한다.
2. 동일 UI/품질/카메라의 전후 기술 비교에서 세 기술의 큰 형태와 팔레트·준비/방출/회수, 캐릭터/HUD 가독성을 검수한다. 자원 보충이나 actor 배치를 사용하는 기술 씬은 명시적으로 기술 비교로 표시한다.
3. 정상 입력·실제 적·획득 Rune를 사용한 별도 gameplay에서는 실제로 발동한 기술과 접촉을 기록한다. 세 기술을 모두 쓰지 못하면 그 범위를 미확인으로 남기고 기술 비교를 정상 플레이 증거로 바꾸지 않는다.
4. 최종 Web/Windows export와 raw Web 용량, 실제 PC/모바일 WebGL·터치·저장/재시작, CI/Pages/릴리스의 동일 source를 확인한다. 파일 다운로드·Windows export를 실기기 실행으로 확대하지 않는다.
5. 실제 1배속의 유한 관측·연속 직접 시청/청취·목표 기기 성능·AAA를 각각 판정한다. 기능/삼각형 수·파일 생성만으로 AAA 완료를 표시하지 않는다.

## 현재 기록

- source 구현: 세 cast의 전용 표시와 실제 접촉 피드백 연결 완료. [실제 세 번째 후보](validation/v0.1.18/README.md)의 유한 PNG 비교에서 프로토타입 시각 채택
- [초기 native 진단](validation/v0.1.18/initial-native.json): 910검사/0실패·ERROR0. 이후 추가한 실제 벽 이력 fixture를 포함한 최종 native는 별도
- [기술 비교·원본 미디어와 source SHA](validation/v0.1.18/technical-visual.json): 후방 카메라에서 가려진 섬광 두 후보를 기각하고 큰 전방 초승달을 채택. 정상 gameplay·최종 export/browser·게시는 별도 검증
- 새 유료 생성: 없음

최종 검증 기록은 해당 source와 실제 산출물이 확보된 뒤 이 절의 링크로 연결한다.
