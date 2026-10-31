# Web 사용자 저장소와 미지원 셰이더 캐시

Godot 4.7.2의 Web GLES3 바이너리 셰이더 캐시는 load/save 함수가 즉시 반환한다. 하지만 기본 설정은 enabled이며 초기화 과정은 `user://shader_cache` 아래 셰이더 이름·해시 디렉터리를 만든다. 이는 실제 shader compilation이나 브라우저의 드라이버 캐시와 다른 경로다.

실제 v0.1.6 Web의 새 프로필에서 readonly IndexedDB 메타데이터를 조사한 결과, 33키 중 29개가 이 캐시의 빈 디렉터리였다. 저장 파일은157bytes였다. 원본·공식 고정 소스와 전체 메타데이터는 [검증 기록](validation/v0.1.7/README.md)에 있다.

main/tag 첫 배포 검사는 실제 품질0 파일을 썼지만 30초 안에 durable primary의 새 값을 관찰하지 못해 실패했다. 두 실행의 FPS는1, readonly open/transaction callback은 약1.12초 단위로 늦어졌다. Emscripten IDBFS는 원격 timestamp 키를 cursor로 순회한 뒤 reconcile write를 시작한다. 불필요한 키가 이 순회 비용을 늘리는 것은 소스와 맞지만, 현재 실패 trace만으로 GPU·게임 CPU·engine cursor의 각 기여도나 dirty 유실을 확정하지 않는다.

Web 전용 설정 `rendering/shader_compiler/shader_cache/enabled.web=false` 한 줄만 바꾼 실제 fresh Web A/B에서33→5키, cache29→상위1디렉터리로 감소했다.67.148초·오류0으로 확인했다. export의 변경 파일은PCK와 그 크기만 갱신한HTML이며JS/WASM/CSS/DOM은 동일하다. 화질·그림자·렌더 해상도·실제 셰이더 컴파일과 Windows 캐시 설정은 바꾸지 않는다. 기존 프로필의 디렉터리는 자동 삭제하지 않는다. 새 프로필의 키 감소와 기존 프로필의 개선·전체 저장 재시작 승인도 서로 다른 검증이다.

설정 한 줄만 바꾼 동일 Web의 전후 키 조사와 실제 설정·primary·재시작 결과를 먼저 확인한다. timeout을 늘리거나 강제 sync·QA 상태 쓰기로 통과시키지 않는다. 최종 main·공개 주소·배포 파일의 실제 결과는 [PR #8](https://github.com/kosj/next-action-rpg/pull/8)에 기록한다. 다른 Godot 판본이나 WebGPU에서는 지원 여부를 다시 확인해야 한다.

수정후 실제UI의품질1→0→1 primary를각6.339/10.663/4.899초에확인했고세화면·전체브라우저재시작집중검사가471.265초·오류0이었다. 이는전체입력/전투·최종main/public검증과분리한다. 원본main의단독재시도도같은30초단계에서실패했으므로동시실행만의문제로판단하지않는다.
