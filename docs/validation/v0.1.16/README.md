# v0.1.16 검증 범위

[제작 계약](../../LOCOMOTION_WAVE_SLICE.md) · [native/첫 시각 판정](native-and-first-visual.json) · [실행 입력 고정](runtime-source-freeze.json)

최종 local native는 실제 Player 입력·move_and_slide 변위·벽·상하체 layer·검기 range/sweep/ledger/수명·늦은 hitpause와 기존 회귀를 포함해 843검사/0실패·ERROR0이다. 이전 실패 원인을 보존했다.

첫 실제 Game 화면에서 검기가 불투명한 cyan 판으로 보여 기각했다. 완성된 영상/전체 trace로 표시하지 않는다. 두 번째 실제 화면에서는 EMISSION-only unshaded 색이 표시되지 않아 다시 기각했다. ALBEDO 수정 뒤 기술용 실제 raster에서 밝은 선두 핵을 확인했고 내부 cap의 가산 seam도 줄였다. 타이틀·체크포인트 복귀 후 남은 검기 수명도 실제 Game 회귀로 막았다. 최종 일반 입력 take003와 웹·모바일/배포 검증은 source 기록 시점에 pending이다. 전체 연속 시청·직접 청취·terrain IK/최종 skin·목표 기기·AAA는 미승인이다.
