# Canvas inline CSS와 모바일 viewport feedback

[고정 엔진 JS](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/platform/web/js/libs/library_godot_display.js#L299)의 adaptive policy2는 innerWidth/Height×DPR로 bitmap을 정하고 normal inline px를 쓴다. 원래 author CSS100%보다 우선하는 옛844px가 좁은 기기에서 overflow/autozoom을 만들고 다시 innerWidth844를 공급했다.

| 동일 PCK/WASM/JS/QA의 HTML-only 비교 | before155.660초·실패 | after152.776초·진단/오류0 |
| --- | --- | --- |
| outer/screen/document client |360×640|360×640|
| canvas client/computed·inner·scroll |844×1501|360×640|
| visual viewport scale |.4265403|1|
| bitmap/nativeWindow |1688×3002|720×1280|
| 논리UI |844×1501|360×640|

[export manifest](export-ab-manifest.json)의9파일 중HTML만 다르다. canvas width/height100%의author CSS에만!important를 주어표시영역을페이지가소유하고bitmap/DPR은엔진에유지했다. 지표나게임상태를강제로바꾸지않았다. [동일시점beforeDOM/QA](before/mobile-failure-browser-metrics.json)·[after](after/mobile-narrow-metrics.json)와 [원본720×1280](after/narrow-after.png)의전체폭/3열44CSSpx를확인했다. before의PNG는Screenshot15초timeout으로없었고그실패도보존했다.

이것은 좁힘 CSS 진단이며 설정·전체 재시작 승인이 아니다. 후속실제세viewport복귀/재시작기능은통과했지만로딩pageerror로전체FAIL을유지한[별도기록](../restart-functional-with-loader-error/restart-functional-and-error-summary.json)과구분한다. 최종수정loader와actual전체/public결과는[PR #8](https://github.com/kosj/next-action-rpg/pull/8)의실행으로대조한다.
