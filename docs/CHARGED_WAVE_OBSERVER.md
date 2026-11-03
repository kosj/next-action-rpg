# 칼날과 검기 명중의 검증 경계

2026-11-03. v0.1.16 후보의 Main80/Tag81은 native843/0과 desktop Web을 통과했지만 집중 모바일 검사가 새 wave45.045를 physical blade69.3으로 검사해 실패했다. 게시·릴리스 gate가 막혔으므로 후보16을 공개 완료로 쓰지 않는다. 태그를 옮기지 않고 v0.1.17에서 검증을 보완한다.

[실제 실패와 수정된 순수 데이터 replay](validation/v0.1.17/charged-observer-failure-and-fix.json)는 동일 attack5의 서로 다른 세 적에 physical69.3 한 번과 wave45.045 두 번을 확인했다. 이는 제공된 증거에서 런타임 중복 피해가 아니라 오래된 오라클 분류의 결함이다.

같은 attack id/serial로 서로 다른 전달 수단이 생겨도 물리 칼날69.3·curve/marker·sharp capsule·hitstop 검사는 유지한다. observer는 선택한 target의 physical receipt를 필수로 받고, wave는 빈 LUT/phase-1·45.045·launch offset·폭/높이·실제6/8segment swept prism·travel/age를 따로 검사한다. 먼저 전체 `(attack_instance_id,target_id)` 중복을 검사한 뒤 분리하며 새 전달 수단을 무시하지 않는다. 실제 물리 freeze와 wave freeze의 시계도 구분한다. proof의 `contact_events`는 physical 목록을 유지하고 `all_charged_events`/`wave_contact_events`에 전체와 검기를 기록한다.

실제3receipt를 포함한 새13개의 양/음성 검사와 전체 Python104개를 통과했다. 새 live browser/모바일/게시 검증은 source 기록 시점 pending이다. 버전 표기 외 `game/scripts`, `game/assets`, `game/data`는 채택된9a1e9dc와 모두 byte 동일하며 [이전 실제 플레이 영상](validation/v0.1.16/README.md)의 gameplay 관측 범위를 유지한다. 최종 v17 source/공개 byte와 동일한 촬영이라고 표시하지 않는다.
