# v0.1.6 모바일 조작 검증

이 파일은 구현 커밋의 로컬 개발 근거를 보관한다. 이후 최종 브라우저·CI·Pages·릴리스 결과는 [PR #8의 실제 실행과 판정](https://github.com/kosj/next-action-rpg/pull/8)에서 확인한다. 초기 집중 검사를 전체 승인으로 승계하지 않는다. 공개 URL은 https://kosj.github.io/next-action-rpg/ 이며 현재 실행 판본은 그 빌드 번호·Actions 결과로 대조한다.

- `native-initial.log`: Godot4.7.2 통합374검사·실패0, 터치 입력29검사 포함. 엔진 오류·종료 누수 없음.
- `mobile-input-focused.log`: 실제 native InputEventScreenTouch/Drag의 장치·소유권·종료 경로 검사.
- `prior-web-texture-probe.log`: 이전0.1.5 실제WebPCK의 Hero/Sentinel2048² map8개를 읽은 진단. CompressedTexture2D지만 실제 image format4/RGB8·compressed=false였다. 현재 최종 패키지나 모든 텍스처·실기기 승인은 아니다.
- `preliminary/`: 동결한 개발 preview003의 실제 CDP trusted touch 검사. 최초 full 시도는 휴식·상점 후 원점 복귀 검사에서 실패했다. 이후 input-focus는 실제 이동 두 구간을 통과했으나 pointer release 직후 stale QA snapshot을 읽어 실패했다. 둘 다 실패 그대로 보존했다. 도구의 한 RPC 조건 대기·아날로그 접근·fresh empty ownership 대기를 수정한 별도 multitouch-focus가148.304초,오류0으로 통과했다. 이는 새 여정→실제 세 손가락 이동/시점/약공격과 독립 해제의 한정 검사이며 full 합격이 아니다.

게임·저장 상태를 강제로 변경하거나 UI15초·IDB30초·각 이동60초 조건을 완화하지 않았다. 원점 도착 검사는 release 후 실제 위치1.2m 이내 확인을 추가했다. 실패/후속 도구 원문과 contemporaneous export/source hashes를 각 preliminary 디렉터리에 보관한다.

구현 `31bc679b`의 Web·Windows 내보내기·파일 검사는 [local-build.json](local-build.json)·[local-distributions.json](local-distributions.json)에 보관한다. 같은 실행 커밋의 전체 모바일·데스크톱 및 공개 URL 결과는 PR #8의 확정된 실행 URL·artifact와 별도로 대조한다. Chromium 에뮬레이션은 실제 Android Chrome·iOS Safari·Windows 실행·목표 GPU/AAA 승인을 대신하지 않는다.

최종 resize 수정과 freed-UI 복원 가드는 [375 native·오류0](native-final.json)·[원본 native log](native-final.log)·[Python41](python-final.log)에서 확인했다. [실제 화면 회전 A/B·raster guard](rotation/README.md)는 별도 진단이며 최종 빌드 전체·공개 주소 검증은 PR #8의 확정 실행으로 대조한다.

이후 실제 Button-start 스크롤 실패를 [동일 경로 A/B](scroll/README.md)로 수정했고 [native375·오류0](native-after-scroll.json)을 확인했다. 전체 최신 실행 판정은 PR #8의 실제 커밋·CI와 대조한다.

[Canvas 축소 CSS](canvas-css/README.md)·[로딩 callback](loader/README.md)·[저장 관찰의 지역/hosted 범위](storage-observation/README.md)를 구분한다. 최신 native375·오류0은 [native-css-loader.json](native-css-loader.json), 실제 loader DOM 회귀는 [fixture-current.json](loader/fixture-current.json)이다. 최종 actual 전체·공개 주소 결과는 PR #8의 확정 실행으로 확인한다.
