# 회전 후 정상 좌표와 잘못된 최종 raster의 재진입 오류

고정 Godot4.7.2 소스 `ed1daf0bf001b61586d9930840f2f1394092c079`의 Window::_update_viewport_size는 old content에서 screen attach rect를 계산한 뒤 `_set_size`를 호출하고, 돌아온 뒤 cached rect를 최종 화면에 붙인다. Viewport::_set_size는 중간에 size_changed를 동기 emit하며, set_content_scale_size는 Window 갱신을 즉시 재호출한다. 따라서 그 signal의 동기 content setter는 nested 설정 이후 outer cached rect에 덮인다. [공식 Window](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/main/window.cpp#L1428)와 [Viewport](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/main/viewport.cpp#L1188)에서 순서를 확인했다.

실제 초기390×844/DPR2에서844×390으로 회전하면, 옛390×844를 새 physical1688×780에 KEEP fit한360.43×780/x663.79가 최종 출력에 남았다. DOM bitmap/client, Window/display/content/visibleRect, public final/stretch transform은 모두 정상이어도 최종 raster만 틀릴 수 있었다. metadata/texture getter 검사를 actual screen 결과로 간주하지 않는다.

| 동일 조건 A/B | 수정 전 | 수정 후 |
| --- | --- | --- |
| fresh profile, quality0, 기존 double driver |126.958초·오류0|112.238초·오류0|
| PNG1688×780의 nonblack span |x664..1023,360px|x0..1687,1688px|
| 실제 이미지 |[압축된 세로 띠](before/rotation-landscape.png)|[정상 가로 화면](after-double/rotation-landscape.png)|
| DOM/native geometry |정상|정상|

[비교 manifest](after-double/ab-comparison.json)의 wrapper 기록 source inputs 중 바뀐 것은 TouchControls 하나뿐이다. 이미지·GLB·driver·품질은 같고 screenshot 파일은 수정하지 않았다. 최초 quality1에서도 같은360px가 나타나 3D 품질과 독립임을 확인했다. 이것은 finite diagnostic A/B이며 full/실기기/성능 승인이 아니다.

수정은 소유 입력 cancel/pause를 즉시 수행하고 content scale 적용을 coalesced deferred callback으로 옮긴다. outer Window 계산이 끝난 뒤 최신 CSS를 읽어 적용한다. native override fixture는 `_applying_metrics`로 callback을 비켜갈 수 있어 실제 browser 원본 PNG 검증이 필수다. daylight first-room 조건의 read-only PNG span guard는 수치만 정상인 이 오류를 재현·거부한다. 일반적인 어두운 게임 장면 전체에 적용하는 보증이 아니다.

최종 단일 Playwright 경로·375 native·전체 모바일/데스크톱·공개 URL 결과는 [PR #8](https://github.com/kosj/next-action-rpg/pull/8)의 실제 실행과 별도로 대조한다. 초기 실패·진단을 전체 합격으로 덮지 않는다.

중복 CDP override를 제거한 단일 공식 Playwright 경로도 fresh132.368초·오류0으로 정상 가로 비율과 portrait780px/landscape1688px의3개row 전체폭을 확인했다. 최종 default full은 이 단일 경로를 사용한다. [실제 잘못된 PNG를 fail·수정 PNG를 pass로 분류한 guard 재현](raster-guard-repro.json)도 보존한다. 고정 daylight first-room PNG만 읽고 이미지 파일은 수정하지 않는다.
