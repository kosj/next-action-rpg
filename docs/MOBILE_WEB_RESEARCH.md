# 모바일 Web 입력·화면 배율 공식 근거

조회일: **2026-10-31 UTC**. 조사 범위는 공식 API·소스와 공개 스킬의 검토다. 모바일 브라우저 실행·실기기 성능·현재 변경분의 QA는 이 문서로 승인하지 않으며 **pending**이다. 조사 당시 기반 HEAD는 `1ea09a2d110f14086df15be7ca38f99236a2d61b`이고 모바일 구현은 별도 작업 트리에서 진행 중이었다.

엔진 원본은 [toolchain](../tools/toolchain.json)의 Godot **4.7.2**다. [공식 태그 API](https://api.github.com/repos/godotengine/godot/git/ref/tags/4.7.2-stable)에서 `4.7.2-stable`이 커밋 `ed1daf0bf001b61586d9930840f2f1394092c079`를 가리키는 것을 확인했다. 아래 엔진 소스 링크는 이 커밋에 고정했다. MDN 페이지는 조회 당시의 현행 문서이며, 브라우저 지원 수치는 별도의 고정 BCD 스냅샷으로 남긴다.

## 현재 프로젝트의 입력 경계

기존 [Player](../game/scripts/actors/player.gd)는 물리 틱에서 이동·공격/차지·회복을 읽고 피해·회피·쿨다운을 결정한다. [Game](../game/scripts/game.gd)의 상호작용·대상 고정/전환과 [HUD](../game/scripts/ui/hud.gd)의 일시정지는 이벤트 경로도 사용한다. [Camera](../game/scripts/world/camera_rig.gd)는 마우스/패드 시점을 처리한다. `TouchControls`는 이 입력 경계에 터치 액션·축·look를 제공하고 기존 게임 권한을 유지하는 설계다. 이 문서는 변경 중인 코드의 통과 보고서가 아니다.

[기존 UI 입력 누수 지식](../knowledge/entries.json)의 `web-input-after-ui`처럼 GUI에서 이벤트를 소비해도 전역 `Input` 상태는 이미 갱신될 수 있다. 메뉴 복귀 입력 가드·버퍼/차지 정리를 유지하고 새 터치 입력의 소유권과 해제를 별도로 검증한다.

## 1. 포인터의 수명과 Web 취소 이벤트

| 확인한 사실 | 구현에 적용할 조건 | 공식 근거 |
| --- | --- | --- |
| `InputEventScreenTouch.index`는 손가락 식별자이며 press/release와 별도 `canceled` 속성이 있다. position은 받는 노드의 viewport 좌표다. | 연속된0/1이나 현재 손가락 개수를 index로 가정하지 않는다. ID별 소유권·이전 위치를 Dictionary 등으로 보관하고 release/cancel 후 제거한다. | [ScreenTouch 4.7](https://docs.godotengine.org/en/4.7/classes/class_inputeventscreentouch.html) |
| Web JS는 `changedTouches`의 `Touch.identifier`를 index로 전달한다. | 이동·look·버튼의 소유 pointer를 touch 시작 시 정하고 드래그 중 다른 역할로 자동 이관하지 않는다. 영역 밖 release도 해당 ID를 해제한다. | [Web JS touch 전달](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/platform/web/js/libs/library_godot_input.js#L577) |
| 이 판본의 Web JS는 `touchcancel`을 `touchend`와 같은 type1로 넘기고, C++은 `pressed=false`를 만들며 `canceled`를 설정하지 않는다. | `canceled=true`만 기다리면 안 된다. `not pressed`도 항상 terminal로 처리하고 blur·메뉴/타이틀·복귀·비활성화·화면 재배치 시 소유권과 터치 액션을 정리한다. | [JS type 매핑](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/platform/web/js/libs/library_godot_input.js#L601), [C++ touch callback](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/platform/web/display_server_web.cpp#L742) |

Web C++은 drag의 이전 위치를 `touches[i]`, 즉 현재 전달 배열의 순서로 찾는다. 여러 손가락의 `changedTouches` 순서가 달라질 때의 `relative` 영향은 별도 실제 재현이 필요하다. 방어적 설계로 look 소유 index별 이전 `event.position`을 보관해 delta를 계산할 수 있다. 이것은 소스에서 도출한 설계 판단이며 현재 앱의 다중 터치 버그가 재현됐다는 주장은 아니다. 같은 [C++ callback](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/platform/web/display_server_web.cpp#L749)이 근거다.

## 2. 터치→마우스 에뮬레이션과 메뉴 재진입

`Input._parse_input_event_impl()`은 ScreenTouch에서 첫 소유 손가락의 에뮬레이션 MouseButton을 만들고 **원래 ScreenTouch를 SceneTree로 보내기 전에** 그 MouseButton을 재귀 처리한다. 마우스의 전역 action cache도 SceneTree 전달 전에 갱신된다. 따라서 나중에 원래 터치의 `_input()`에서 handled를 설정해도 앞선 에뮬레이션 mouse의 polling 상태를 취소하지 않는다. [고정 입력 소스](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/core/input/input.cpp#L908).

`set_emulate_mouse_from_touch(false)`는 bool 대입만 한다. 이미 소유한 `mouse_from_touch_index`를 지우거나 release 이벤트를 보내지 않는다. TouchDown 뒤 TouchUp 전에 끄면 자동 해제를 기대할 수 없다. canonical mouse action을 강제 `action_release()`해서 숨기면 다른 실제 장치 상태까지 지울 수 있다. [setter](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/core/input/input.cpp#L1477).

기본 Button의 순서는 구분해서 판단한다.

1. `BaseButton.action_mode` 기본값은 `ACTION_MODE_BUTTON_RELEASE`다. 현재 HUD helper도 `pressed` 신호를 연결한다. [기본값](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/gui/base_button.h#L58), [신호 발생 조건](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/gui/base_button.cpp#L253).
2. emulated pointer의 TouchUp에서는 먼저 index를 `-1`로 지우고 synthetic MouseRelease를 재귀 처리한다. 이 MouseRelease의 global 상태 갱신과 GUI `pressed` 콜백 다음에 원래 ScreenTouchUp이 전달된다. 따라서 **기본 release 콜백에 들어온 해당 pointer**는 이미 마우스 release가 처리됐다. 이것을 모든 UI 전환의 일반 보장으로 확대하지 않는다.
3. `button_down`·press-mode·키보드/패드로 메뉴 닫기·다른 손가락 hold는 조건이 다르다. 특히 synthetic MouseDown 안의 press 콜백은 원래 ScreenTouchDown의 `_input()`보다 먼저라, 그 순간 GUI ID map이 비었다고 안전한 것은 아니다. 실제 활성화/에뮬레이션 전환을 deferred 경계로 옮겨 원래 touch 이벤트를 먼저 관찰하고 모든 GUI pointer가 끝난 뒤 commit하는 설계는 이 재진입 순서에 대한 방어책이다. 실제 fixture 검증은 필요하다.

Godot4.7.2의 `BaseButton`은 실제 ScreenTouch/ScreenDrag를 직접 처리하고 Viewport도 index별 `gui.touch_focus`를 관리한다. **에뮬레이션 off가 기본 Button의 터치 경로까지 없앤다고 단정하지 않는다.** 실제/에뮬레이션 경로와 다른 GUI 위젯을 함께 검사한다. [BaseButton 직접 touch 처리](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/gui/base_button.cpp#L67), [Viewport touch focus](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/main/viewport.cpp#L2213).

## 3. 액션 전달·동시 물리 입력·프레임 경계

- `Input.action_press()`는 polling 상태를 바꾸지만 `_input()` 호출을 만들지 않는다. `Input.parse_input_event(InputEventAction)`는 SceneTree 이벤트도 전달한다. 이벤트 전용 interact/lock/target/pause를 polling 주입만으로 구현했다고 판단하지 않는다. [Input 공식 문서](https://docs.godotengine.org/en/4.7/classes/class_input.html#class-input-method-action-press), [parse_input_event](https://docs.godotengine.org/en/4.7/classes/class_input.html#class-input-method-parse-input-event).
- 터치 전용 `touch_<action>` alias를 사용하면 물리 장치와 소유권을 나눌 수 있다. polling은 canonical과 alias의 merged level을 읽고 event handler도 alias를 명시적으로 해석해야 한다. alias 이벤트를 만들었다고 기존 canonical-only 이벤트 조건까지 자동으로 맞지는 않는다. 같은 전투 동작을 이벤트와 polling 양쪽에서 중복 실행하지 않는다.
- 이 엔진의 `action_release(action)`는 그 action의 `device_states.clear()`까지 수행한다. 물리 release 이벤트도 같은 action의 API-pressed 상태를 지운다. 그러므로 터치 cleanup은 자기 alias만 release하고 canonical 물리 action을 지우지 않는다. [API release](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/core/input/input.cpp#L1430), [실제 event release의 API 상태 처리](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/core/input/input.cpp#L1017).
- merged held 상태가 true인 동안 다른 장치의 press/release가 새 공격 edge를 만들지 않게 한다. 터치 hold 중 실제 키 release, 실제 키 hold 중 터치 release, 두 방향 충돌·패드 분리까지 확인한다. 이 계층의 합성 정책을 명시하고 기존 공격/차지 버퍼와 피해 권한은 유지한다.

공식4.7.2의 event transition과 `action_press()`는 press edge를 **physics counter+1**, **현재 process counter**에 기록한다. release도 대응하는 식을 쓴다. just-pressed/released는 실행 중인 loop의 counter와 비교한다. 별도 merged edge를 저장한다면 callback의 현재 physics counter에 바로 맞춰 다음 틱의 입력을 잃지 않게 한다. [event stamp](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/core/input/input.cpp#L1033), [API stamp](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/core/input/input.cpp#L1410), [counter 비교](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/core/input/input.cpp#L418).

`input_devices/compatibility/legacy_just_pressed_behavior`의 이 판본 기본값은 false다. true이면 현재 pressed/released level 조건도 추가된다. 매우 짧은 tap·한 process frame 안의 press/release·physics 경계 fixture는 프로젝트 설정과 실제 효과까지 확인한다. 고정 sleep이나 gameplay 조건 완화로 입력 fixture를 통과시키지 않는다. [설정 기본값](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/core/input/input.cpp#L2364).

## 4. 아날로그 strength와 원형 deadzone

`Input.get_vector()`는 방향별 **raw strength** 차이로 축을 만들고, 네 action deadzone의 평균 또는 지정 deadzone을 적용한다. 원형 deadzone 안은0, 바깥 구간은 길이를 재매핑하며 길이1을 넘으면 제한한다. `action_press()`로 준 strength도 API raw strength로 반영된다. [get_vector 구현](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/core/input/input.cpp#L580), [cache 합성](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/core/input/input.cpp#L1846).

터치/물리 축을 병합할 때 방향별 max를 취할지, 축 벡터를 병합할지, 장치 우선순위를 둘지 정하고 반대 방향/대각선을 검사한다. 이미 deadzone을 통과한 벡터에 무심코 두 번째 deadzone을 적용하지 않는다. 최종 방향을 무조건 normalize하면 약한 스틱 입력의 속도 크기가 사라진다. facing·회피 방향 정규화와 일반 이동 velocity에 사용할 크기는 구분한다.

## 5. CSS·canvas backing·논리 viewport 좌표

Web JS의 좌표 변환은 다음과 같다. 이는 앱이 추가로 DPR을 곱하라는 지침이 아니라 **엔진에서 이미 일어나는 처리**다.

```text
backing.x = (clientX - canvas_rect.x) * canvas.width  / canvas_rect.width
backing.y = (clientY - canvas_rect.y) * canvas.height / canvas_rect.height
```

[Web computePosition](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/platform/web/js/libs/library_godot_input.js#L490)이 CSS rect와 canvas backing 비율을 적용한다. [Viewport._make_input_local](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/main/viewport.cpp#L1467)은 final transform의 역변환으로 이벤트를 로컬화한다. `_input()`의 touch position에는 DPR을 다시 곱하지 않고 같은 논리 좌표의 UI 영역과 비교한다. `_gui_input()`에서는 해당 Control의 로컬 변환까지 적용됐다는 점도 구분한다.

`Window.content_scale_size`는 virtual design pixels이고 `Window.size`는 물리 window pixels다. 런타임 크기 변경은 `ProjectSettings.set_setting()`만 바꾸는 대신 Window의 실제 content scale 속성을 사용한다. canvas_items는 UI를 논리 크기에서 현재 출력 크기로 렌더한다. 현재 프로젝트의 기존 design size를 작은 모바일 CSS 화면과 무관하게 유지하면 버튼·글자가 작아질 수 있으므로 responsive logical size와 anchors/containers를 실제 화면에서 확인한다. [Window 문서](https://docs.godotengine.org/en/4.7/classes/class_window.html#class-window-property-content-scale-size), [고정 설명](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/doc/classes/Window.xml#L657), [Multiple resolutions](https://docs.godotengine.org/en/4.7/tutorials/rendering/multiple_resolutions.html#base-size).

`ScreenDrag.relative`는 content scale의 영향을 받고 `screen_relative`는 그 stretch/xformed_by 영향이 없다. 다만 Web에서는 앞서 CSS→backing 변환이 이미 있으므로 screen_relative를 항상 CSS px라고 부르지 않는다. look 감도를 화면 분율로 정한다면 소유 ID의 논리 position delta를 현재 논리 viewport 크기로 나누는 방식처럼 단위를 명시하고 DPR/창 크기 변경 후 확인한다. [공식 Drag 속성](https://docs.godotengine.org/en/4.7/classes/class_inputeventscreendrag.html#class-inputeventscreendrag-property-screen-relative), [Web callback](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/platform/web/display_server_web.cpp#L749).

[Web display sizing](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/platform/web/js/libs/library_godot_display.js#L235)은 HiDPI 설정과 DPR, canvas resize policy에 따라 CSS/backing 크기를 조정한다. DPR 상한으로 렌더 부하를 낮추는 것과 논리 UI 크기를 정하는 것은 별개다. 페이지 zoom도 DPR에 영향을 줄 수 있다. [MDN devicePixelRatio](https://developer.mozilla.org/en-US/docs/Web/API/Window/devicePixelRatio).

## 6. safe area와 화면 회전

`DisplayServer.get_display_safe_area()`는 native Android/iOS 구현이며 다른 플랫폼은 screen usable rect로 fallback한다. Web의 fallback은 canvas나 실제 노치 insets를 보장하지 않는다. 화면 해상도를 canvas 크기로 취급하거나 native safe rect를 논리 MarginContainer에 그대로 넣지 않는다. [고정 API 설명](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/doc/classes/DisplayServer.xml#L865), [Web usable rect](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/platform/web/display_server_web.cpp#L1272).

Web은 `viewport-fit=cover`와 CSS `env(safe-area-inset-*, 0px)`의 현재 computed 값을 읽을 수 있다. CSS viewport의 safe rect와 실제 canvas CSS rect를 대조/교차하고, 해당 inset만 논리 viewport 좌표로 한 번 변환한다. canvas 자체가 이미 padding 안에 있으면 중복 inset을 피한다. 브라우저 주소창 변화·portrait/landscape·fullscreen 진입/해제 때 재측정하고 재배치 중인 손가락은 정리한다. [MDN env](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/env), [viewport-fit](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/name/viewport#viewport-fit).

## 7. Pointer Lock·fullscreen·렌더러 지원

모바일 look는 손가락 입력으로 독립 동작하도록 만들고 pointer lock/fullscreen은 선택 기능으로 둔다. 두 API 모두 사용자 gesture와 실제 브라우저 정책을 확인한다. fullscreen을 거부해도 인라인 canvas에서 플레이·메뉴 복귀가 가능해야 한다. DOM 기능 존재만으로 실제 요청 성공을 가정하지 않는다.

[MDN requestPointerLock](https://developer.mozilla.org/en-US/docs/Web/API/Element/requestPointerLock)은 사용자 활성화를 요구하며 fullscreen과 한 gesture에서 함께 요청하면 pointer lock을 먼저 요청하도록 설명한다. [requestFullscreen](https://developer.mozilla.org/en-US/docs/Web/API/Element/requestFullscreen#security_considerations)도 사용자 활성화와 iframe 권한 정책의 영향을 받는다. canvas click을 요구하는 데스크톱 capture UI를 터치 이동/공격의 필수 조건으로 사용하지 않는다.

조회한 [MDN BCD 커밋](https://github.com/mdn/browser-compat-data/commit/381650773ddc196a34cbf759f31adba457e6bf46)은 **2026-10-30** 상태다. 아래는 API 지원 데이터이며 해당 기기에서 이 게임이 실행·성능 검증됐다는 뜻이 아니다.

| API | 고정 BCD에서 읽은 주요 항목 | 이 프로젝트의 조건 |
| --- | --- | --- |
| WebGL2RenderingContext | Chrome Android58+, Safari15+, Safari iOS는 Safari mirror | WebGL2 feature check와 실제 context 생성·드라이버/메모리·기기 실행을 확인한다. Safari 전면 미지원으로 표현하지 않는다. |
| Element.requestPointerLock | Chrome Android144+, Safari iOS false | 모든 모바일에서 지원/미지원이라고 묶지 않는다. touch look를 기본 경로로 유지한다. |
| Element.requestFullscreen | Safari iOS16.4 항목은 iPad만 partial이며 iPhone은 제외한다. Chrome Android는 desktop Chrome mirror | fullscreen 없는 작은 화면도 검수한다. 기능 요청 실패를 게임 시작 실패로 만들지 않는다. |

근거: [고정 WebGL2 BCD](https://github.com/mdn/browser-compat-data/blob/381650773ddc196a34cbf759f31adba457e6bf46/api/WebGL2RenderingContext.json), [고정 Element BCD](https://github.com/mdn/browser-compat-data/blob/381650773ddc196a34cbf759f31adba457e6bf46/api/Element.json). 조회한 Git blob은 각각 `da527e8b0d60c0cf631a8a820ed5f7c17d214d2c`, `ec6f9650e3321a468406e857df6b514bd0b10c03`였으며 고정 커밋과 당시 main에서 같았다.

[Godot4.7 Web 공식 문서](https://docs.godotengine.org/en/4.7/tutorials/export/exporting_for_web.html)는 Compatibility/WebGL2 경로와 모바일에서의 CPU/GPU·로딩 비용, Safari의 남은 WebGL2 차이를 설명한다. 이 작업은 기존 single-thread static export를 유지할 수 있으며 WebGPU나 SSR 도입을 요구하지 않는다. 멀티스레드용 cross-origin isolation 조건과 단일 스레드 배포를 구분한다. 실제 모바일 호환성·품질별 프레임/메모리는 별도 검증이다.

## 8. 실제로 읽은 공개 스킬과 채택 범위

네트워크 인스톨러·외부 스크립트 실행은 하지 않았다. 아래 자료의 원문을 고정 리비전으로 읽었고, 명시된 사용자 요청에 따라 두 MIT 스킬은 원본 bytes와 직접 링크한 로컬 참조를 보존해 저장했다. 로컬 [input-handling](../.agents/skills/input-handling/SKILL.md)과 [responsive-ui](../.agents/skills/responsive-ui/SKILL.md)의 각 폴더에 원본 LICENSE·출처 NOTICE·파일별 upstream.json을 둔다. 기존 Apache 자료의 공통 provenance는 변경하지 않았다. 스킬의 일반 예제를 공식 Web API 확인보다 우선하지 않는다.

| 자료 | 리비전·라이선스 | 이번에 사용할 부분과 제한 |
| --- | --- | --- |
| [input-systems](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/blob/19d93f97c9c1ea0f8b306e77aa81e0d3e352d3e9/skills/disciplines/input-systems/SKILL.md)와 [touch/accessibility 참조](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/blob/19d93f97c9c1ea0f8b306e77aa81e0d3e352d3e9/skills/disciplines/input-systems/references/buffering-and-accessibility.md) | 현재 collection HEAD `19d93f97c9c1ea0f8b306e77aa81e0d3e352d3e9`, 2026-10-28. 기존 프로젝트에서 검토한 Apache-2.0; [LICENSE](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/blob/19d93f97c9c1ea0f8b306e77aa81e0d3e352d3e9/LICENSE)·[NOTICE](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/blob/19d93f97c9c1ea0f8b306e77aa81e0d3e352d3e9/NOTICE). | named action 경계, edge/held 구분, 원형 deadzone, 장치 전환·손가락 크기·hold 접근성 검수. 다른 장르의 buffer/coyote 수치를 전투 데이터에 복사하지 않는다. |
| [GodotPrompter input-handling](https://github.com/jame581/GodotPrompter/blob/d7b26cdb5fae14d4ef7b713c5bf259395e75c3c6/skills/input-handling/SKILL.md)·[touch 참조](https://github.com/jame581/GodotPrompter/blob/d7b26cdb5fae14d4ef7b713c5bf259395e75c3c6/skills/input-handling/references/touch.md), [responsive-ui](https://github.com/jame581/GodotPrompter/blob/d7b26cdb5fae14d4ef7b713c5bf259395e75c3c6/skills/responsive-ui/SKILL.md)·[mobile 참조](https://github.com/jame581/GodotPrompter/blob/d7b26cdb5fae14d4ef7b713c5bf259395e75c3c6/skills/responsive-ui/references/mobile.md) | 당시 master HEAD `d7b26cdb5fae14d4ef7b713c5bf259395e75c3c6`, 2026-10-24. [MIT LICENSE](https://github.com/jame581/GodotPrompter/blob/d7b26cdb5fae14d4ef7b713c5bf259395e75c3c6/LICENSE), Copyright2026 GodotPrompter Contributors. | API/이벤트와 polling 구분, runtime Window 속성, anchors/containers, size_changed 검수를 선택 적용한다. 기존 Player의 physics polling을 전면 개편하는 지시로 쓰지 않는다. native safe-area/DPI 예제를 Web에 그대로 적용하지 않는다. |

GodotPrompter 각 파일의 관측 Git blob은 input-handling=`01f299df638147c950a00538c16c3557419be251`, touch 참조=`620c9538d927ad9ba51da75d9c6641008645d34c`, responsive-ui=`a15428e599c7025f04adcdc49e5c3d64e14d8865`, mobile 참조=`9f34f61dbe8f8aa902b1fc920c4061b712433acd`, LICENSE=`f5058316879cd83ed9ee5eec4cb1a180479ffa38`이다. 이 값은 Git blob ID다. 원문 다운로드 bytes로 Git blob을 재계산해 고정 소스와 일치시켰으며 실제 로컬 bytes의 SHA-256·크기·고정 URL·조회일은 [입력 provenance](../.agents/skills/input-handling/upstream.json)와 [UI provenance](../.agents/skills/responsive-ui/upstream.json)에 기록했다. 원문 frontmatter와 참조 링크도 확인했다. 실행 스크립트나 연결된 다른 스킬 전체는 복사하지 않았다.

검색된 `thedivergentai/Game-Dev-Agentic-Skills`는 조사 당시 [LICENSE](https://github.com/thedivergentai/Game-Dev-Agentic-Skills/blob/db004d74c40686ca2f7a35fe067b119a9cda593e/LICENSE)가 LGPL3.0이었다. MIT 자료로 잘못 표시하거나 새 설치를 수행하지 않았다. 이번 기능에는 위의 더 좁은 스킬과 공식 소스로 필요한 원칙을 확인했다.

## 9. 남은 실행 검증과 재사용할 원칙

다음은 조사 완료가 아닌 실제 구현/기기 검증의 조건이다.

- 서로 다른 ID의 이동+look+차지/버튼을 동시에 유지하고 한 손가락만 해제·영역 밖 해제·OS cancel·재사용 ID·알 수 없는 drag를 확인한다.
- 메뉴/touchDown 중 키보드로 닫기, 기본 release Button, press-mode 재진입, 다른 pointer hold, pause·초점 손실·타이틀/체크포인트 복귀 후 남는 이동/차지·false attack이 없는지 검사한다.
- 실제 키/패드와 touch alias의 동시 hold/release, merged edge·아날로그 강도·반대 방향·대각선 속도 제한을 확인한다.
- portrait/landscape·최소 CSS 화면·DPR 차이·주소창/viewport 변경에서 버튼 hit rect·글자·modal scroll·safe insets와 look 감도를 대조한다.
- pointer lock/fullscreen 미지원 또는 요청 거부, 오디오 첫 gesture, WebGL2 생성 실패 안내와 인라인 플레이를 확인한다.
- desktop mouse emulation/Chromium touch fixture와 실제 Android Chrome·iOS Safari 결과를 나눠 기록한다. 같은 빌드의 실제 기기 GPU/OS/브라우저·품질·frame time·메모리·로딩을 확보하기 전에는 실기기 합격을 붙이지 않는다.

다른 프로젝트에 옮길 때는 **포인터 소유권과 모든 종료 경로**, **원래/에뮬레이션 이벤트 순서와 설정 전환**, **각 입력 장치의 action 해제 범위**, **loop별 edge 시점**, **CSS/backing/논리 좌표의 단일 변환**, **native/Web safe area 차이**, **선택적 브라우저 기능과 실제 기기 검증**을 절차로 재사용한다. 이 프로젝트의 버튼 위치·크기·감도·공격 값이나 특정 브라우저 지원표를 영구 기본값으로 복사하지 않는다.
