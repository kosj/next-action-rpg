---
name: runefall-development
description: Implement and verify RUNEFALL GDScript gameplay changes, especially combat, saves, UI input, and checkpoint recovery. Use before changing game scripts or regression tests.
---

# RUNEFALL 게임 구현

## 입력과 근거

현재 요청, [설계](../../../docs/DESIGN.md), 관련 코드와 지식 DB를 확인합니다. `python tools/knowledge.py search --tag combat` 또는 `--tag save`로 기존 실패 사례를 찾습니다. 물리·질의는 [godot-physics](../godot-physics/SKILL.md), 테스트 방식은 [godot-gdscript-headless-testing](../godot-gdscript-headless-testing/SKILL.md)을 필요에 맞게 읽습니다.

## 변경과 회귀 확인

1. 예상 동작과 문제가 생기는 입력·프레임·저장 상태를 먼저 특정합니다.
2. 전투 판정은 물리 틱에서 처리합니다. 베기의 경로·안쪽·큰 delta, 벽 가림, 한 번의 공격에서 중복 피해, 패링에 따른 공격 취소를 관련 변경에서 확인합니다. `intersect_shape`가 모션까지 쓸어 준다고 가정하지 않습니다.
3. UI에서 게임으로 복귀할 때 전역 `Input` 폴링에 클릭이 남을 수 있습니다. 일시정지·이어하기·모달 종료 입력과 새 공격의 경계를 보존합니다.
4. 저장은 유효성 검사·스냅샷·백업·실패 롤백 계약을 유지합니다. 저장 실패를 휴식·구매 성공으로 표시하지 않습니다. 설정 저장과 실제 여정 존재를 구분하고 정상적인 기존 v1 저장과 호환합니다.
5. 의미 있는 동작 변경은 기존 `combat_regressions.gd`·`save_regressions.gd`·`test_runner.gd`의 알맞은 검사로 확인합니다. 코드의 문장을 그대로 복제하는 테스트는 추가하지 않습니다.

차지 강타·접촉 피드백은 [제작 단위 계약](../../../docs/CHARGED_IMPACT_SLICE.md)을 읽습니다. 확정 hurtbox 접촉/ray/proxy의 근거를 구분하고 같은 결과에서 공격자·피격자·카메라·VFX·음향을 연결합니다. 공통 gameplay/presentation clock과 양쪽 hitstop·입력 버퍼·phase 이동·최종 검/발 위치를 실제 모델로 확인합니다. dense bake·기능 통과와 의미 있는 안무·정상1배속 AV·실기기/AAA 승인은 각각 판정하며, 새 입력/자산의 결과가 나오기 전에는 `pending`을 유지합니다.

표시용 검 소켓 전체와 실제 날 피해 구간을 분리하고 캡슐 반구가 손잡이까지 닿는지 확인합니다. 독립 재구성한 날 중심축·접촉점 거리·날 방향 투영을 함께 검사합니다. 피격 이동은 실제 CharacterBody 변위와 요청 거리를 구분하며, 근접 겹침의 충돌 복구도 이동 예산에서 소비하는지 재현합니다. [초기 통과를 기각한 기록](../../../docs/validation/v0.1.8/rejected-contact-summary.json)처럼 새 결함이 확인되면 과거 CI의 녹색 결과를 현재 승인으로 승계하지 않습니다.

## 실행

활성 동작과 물리 곡선을 함께 바꾸는 경우 [v0.1.10 제작 계약](../../../docs/COMBAT_MOTION_POLISH_SLICE.md)을 확인합니다. curve 파일 SHA·source GLB SHA·좌표계·floor offset·active 양끝/표본 순서·길이·보간 오차를 검증하고, 잘못된 pin을 이전 analytic 경로로 숨기지 않습니다. 모든 curve 경계를 보존한 세분화와 실제 해결된 actor 이동을 사용하며 첫 geometric receipt·최종 표시 시계/잔상을 다시 검사합니다. source/raw 통과·native 기능·실제 화면/skin/브라우저·최종 배포 승인은 별도입니다.

`tools/toolchain.json`에 맞는 엔진과 동일한 템플릿을 사용하고 `GODOT_BIN`을 해당 실행 파일로 지정합니다. 새 환경은 `bash tools/setup_godot.sh`가 출력한 경로를 사용합니다.

```bash
python tools/build.py --test-only
```

통합 runner는 autoload·전체 씬·물리 프레임이 필요한 Node 씬입니다. 단순 SceneTree 예제로 교체하지 않습니다. 검사 수를 스킬에 고정하지 않고 실행 결과의 실패 수·종료 코드·watchdog·각 suite 완료를 확인합니다.

웹 입력·저장·UI를 바꿨으면 웹을 다시 내보낸 뒤 실제 브라우저도 검사합니다.

모바일 입력은 [공식 근거](../../../docs/MOBILE_WEB_RESEARCH.md)와 고정 공개 [입력 스킬](../input-handling/SKILL.md)·[반응형 UI 스킬](../responsive-ui/SKILL.md)의 관련 부분을 읽습니다. 기존 전투 polling을 일괄 재설계하지 않으며 native safe-area/DPI 예제를 Web에 그대로 복사하지 않습니다. CSS·canvas backing·논리 viewport 변환을 한 번만 적용하고 터치 별칭만 해제합니다. 같은 frame의 짧은 탭, 실제 키와 동시 hold, 취소/메뉴/회전/포커스·복귀에서 실제 캐릭터 효과와 잔여 입력을 확인합니다. [모바일 브라우저 도구](../../../tools/check_mobile_web.py)를 한 개의 Chromium으로 실행한 뒤 기존 데스크톱 검사도 유지합니다. 에뮬레이션을 실제 Android/iOS·성능 승인으로 승계하지 않습니다.

```bash
python tools/build.py
python tools/check_web.py
```

Playwright/Chromium 준비는 루트 README를 참조합니다. QA 데이터는 읽기 전용으로 유지합니다. 소프트웨어 WebGL 성공을 Windows GPU 성능으로 해석하지 않습니다.

## 완료

문제·해결 조건·검증 근거를 지식 DB에 갱신합니다. 게임 코드 검사와 별도로 `python tools/knowledge.py check`를 통과시킵니다. 배포가 작업 범위에 있으면 [릴리스 스킬](../runefall-release/SKILL.md)로 이어갑니다.

자동 터치 조작에서는 [피드백·짧은 상태 실패](../../../docs/validation/v0.1.6/driver-failures/README.md)를 확인합니다. 움직이는 포인터를 유지하며 geometry RPC를 반복하지 않고 한 gesture의 좌표를 재사용하되 layout 세대를 검증합니다. 단발/회피/차지 release는 입력 전에 읽기 전용 관찰자를 arm해 미래 physics snapshot을 복사합니다. 이동량·소유권·실제 효과·영구 저장의 assertion과 유한 시간은 유지하고, 검사 도구 실패·앱 실패·집중/전체 통과를 구분합니다.

Window.size_changed 안에서 content scale을 동기로 재설정하지 않습니다. [실제 screen-attach 재진입 사례](../../../docs/validation/v0.1.6/rotation/README.md)처럼 public 좌표/transform이 정상이어도 outer cached rect가 최종화면을 덮을 수 있습니다. 소유 입력은 즉시 정리하고 최신 CSS 설정은 1회 coalesced deferred로 적용합니다. 같은 driver/품질/자산의 실제 PNG A/B와 고정 장면 raster guard로 검증하며 headless getter 검사로 대체하지 않습니다.

모바일 modal 스크롤은 빈 여백만 테스트하지 않습니다. [Button-start 드래그 실패/수정](../../../docs/validation/v0.1.6/scroll/README.md)처럼 실제 버튼에서 시작해 부모 ScrollContainer 전달·SCROLL_BEGIN 클릭 취소·fresh scroll값·Done과 실제 저장까지 확인합니다. wheel 전파 옵션을 touch drag 보증으로 간주하지 않고 Slider의 별도 소유권을 보존합니다. 같은 gesture geometry를 재사용하고 progress가 없으면 유한 시간에 실패시킵니다.

모바일 축소에서는 [canvas CSS feedback](../../../docs/validation/v0.1.6/canvas-css/README.md)의 inline/computed/client/inner/documentScroll/visualViewport·DPR/bitmap·실제PNG를 대조합니다. 표시영역소유권만수정하고숫자clamp로가리지않습니다. [로딩callback](../../../docs/validation/v0.1.6/loader/README.md)은UI제거뒤late실행을재현하고원본callback/실제DOM으로검사합니다. 기능성공과pageerror0을별도로판정합니다.
