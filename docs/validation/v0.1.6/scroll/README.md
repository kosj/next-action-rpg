# 실제 버튼에서 시작한 모바일 스크롤

landscape 설정의 완료 버튼은91px 아래에 있었다. QA를 빈 여백으로 옮기는 대신 실제 품질 Button 위에서 시작하는 원래 사용자 경로를 유지했다. [공식 Button](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/gui/button.cpp#L878)은STOP, Container는PASS이며 Viewport의 force-pass-scroll 예외는wheel뿐이다. [ScrollContainer](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/gui/scroll_container.cpp#L237)는 touchscreen의emulated MouseDown/Motion으로 drag를 시작한다. [BaseButton SCROLL_BEGIN](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/gui/base_button.cpp#L180)이 pending click을 취소하므로 부모 전파와 클릭 소유권을 함께 검증한다.

| 같은 fresh Button-start 경로 | 수정 전 | 수정 후 |
| --- | --- | --- |
| 시작/끝·실제 move |(422,293)→(422,107.5),4moves|동일|
| 시작 widget |균형 Button|동일|
| 실제 scroll range |max441/page350/value0|동일 초기값|
| fresh scroll 결과 |0,frame1341에서도0|91,frame1178|
| 실행 |233.834초·실패·오류0|261.750초·scroll subset 통과·오류0|
| 이후 UI·저장 |완료 offscreen|완료 실제tap→idle/HP120/Rune35/pointers0→quality0 primary|

[비교 manifest](after/scroll-ab-comparison.json)에서 기록된 source inputs의 유일한 차이는 HUD다. QA·TouchControls·아트·에뮬레이션·시간과 실제 입력 경로는 같다. 모바일 helper Button과 직접 생성 CheckButton에만 PASS를 주고, 음량 Slider는STOP를 유지했다. [원본 복귀 화면](after/scroll-gameplay-after.png)은 정상1688px 전체폭을 확인했다. 이 검사는 품질0 primary를 읽은 subset이며 full workflow·브라우저 재시작·실기기 승인으로 표시하지 않는다.

같은 gesture의 canvas geometry는 한 번만 읽고, 이동 뒤 fresh scroll progress가15초 안에 없으면 실제 snapshot으로 실패한다. 이미지나 게임/저장 상태는 수정하지 않는다. [이전 긴 tail](long-tail-aborted/mobile-result.json)은1047.529초에 진단 중단했으며10회 loop 완료나 최종값을 알았다고 주장하지 않는다. 실제 post-scroll0은 새 짧은 before 검사로 별도 실측했다.

최종 native375는 [수정 후 기록](../native-after-scroll.json)으로 확인한다. 최종 커밋의 전체 모바일·데스크톱·공개 URL 검증은 [PR #8](https://github.com/kosj/next-action-rpg/pull/8)의 확정 실행과 대조한다.
