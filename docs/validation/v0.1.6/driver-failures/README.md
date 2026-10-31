# 실제 터치 드라이버의 실패 근거

게임 구현31bc679b를 유지한 실행이다. 아래는 실패이며 전체 모바일 합격이 아니다.

- local-nav: 전체485.534초·오류0. 실제3pointer/외부drag/독립해제/질주 후 helper 원점 이동60초에서 실패했다. 진단 마지막 위치(−.64897,5.92852)는 목표 .653m 이내·HP120·idle·pointer0였다.
- ci-41195933000: [실제 CI](https://github.com/kosj/next-action-rpg/actions/runs/41195933000/job/124523618477) 전체433.972초·오류0. `navigate→css→canvas→bounding_box`에서60초 timeout. 마지막(0.28903,5.33368)은 목표 .726m 이내·HP120이었다. snapshot에는 stick ID13이 남아 있으므로 이것만으로 최종 해제나 앱 입력 누수를 단정하지 않는다. 배포 gate는 실패를 유지했다.
- local-transient: lifecycle 집중171.437초·오류0. 차지/강공 release와 부족한 스킬2/3 차단은 통과했지만 dodge cooldown의 늦은 조회가15초 timeout이었다. 실제z3.90875→−1.75791 이동과 start1.710초/end2.343초 응답, 마지막idle/cooldown0/pointer0를 관찰했다.

수정 driver는 gesture 안에서 좌표를 한 번 읽고 layout_generation을 대조하며, 이동 성공 후 소유권을 유지한 stick center와 독립 해제로 추가 이동을 줄인다. 단발 상태는 실제 touch 전에 별도 readonly rAF 관찰자를 arm하고 미래 physics snapshot을 복사한다. 이 관찰자는 게임 QA 객체·게임/저장 상태를 쓰지 않는다. Python 전체15초·JS15초, IDB30초·각이동60초·정지후목표1.2m 조건은 유지한다. 조향의 stop threshold는 최종 검사 조건보다 안쪽이며 최종거리 검사를 제거하지 않는다.

이 디렉터리는 원래 실패 시점의 JSON을 보관한다. 실제 수정본 전체·공개 URL 결과는 [PR #8](https://github.com/kosj/next-action-rpg/pull/8)의 확정 실행과 대조하며, 이 실패를 나중 성공으로 덮지 않는다.
