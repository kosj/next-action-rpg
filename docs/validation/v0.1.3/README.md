# v0.1.3 개발 트리 검증

2026-10-31 Godot4.7.2·Blender4.3.2·실제 Chromium/Playwright1.62.0 검사입니다. 이 폴더의 웹 캡처는 생성 소품을 포함한 로컬 개발 export(`/web/`, 빌드번호 `0.1.3 · 4702b815`)의 결과입니다. 빌드번호는 export 당시 HEAD이며 커밋 전 개발 변경을 포함합니다. 공개 배포의 정확한 커밋은 GitHub Actions의 `verify_public_web`과 릴리스 manifest가 별도로 대조합니다.

- `godot-regressions.log`: 179개·실패0. `python-tests.log`: 36개 통과.
- `browser-quality.json`: 실제 W입력으로 도달한 교전 전 z≈−11 구역에서 성능1→균형0→성능1 선택, HP120 확인. 실제 두 화면은07·06이며, 이어서 원래 전투 진입·10회 공격·회피·생존을04에 기록합니다.
- `browser-storage.json`: 읽기 전용 primary 관찰. 균형 변경 직후1→커밋0, 성능 복원 직후0→커밋1→완전 종료 전1→같은 프로필 재시작1.
- `browser-persistence.json`: 이어하기·체크포인트0·시작위치6·품질1 복원. `browser-errors.json`: 오류0.

고정 대기·강제 FS.syncfs·테스트의 저장값 쓰기를 사용하지 않습니다. 앱 저장 코드는 변경하지 않았습니다. 실제 IDB transaction을 Python에서 await하고 다음 animation frame 뒤 조건을 다시 검사합니다. SwiftShader 소프트웨어 렌더링의 기능 검증이며 목표 하드웨어 FPS나 Windows 실기기 실행 검증은 아닙니다.

## GitHub CI

[run41161650156](https://github.com/kosj/next-action-rpg/actions/runs/41161650156)의 코드 head `655b587b630aa28fb277effd80d208614bab299f`가 build·실제 브라우저 검사를 통과했습니다. PR 합성 merge의 실행 빌드번호는 `0.1.3 · e0a04a15`입니다. `ci/`에 그 실행의 상태·저장·오류0·품질비교·전투·이어하기 근거를 보존합니다. 최초 실패는 별도 `ci-before-safe-quality/`에 원인 단정 없이 남깁니다. 이후 main의 배포·공개 URL·태그 Windows 빌드는 각 workflow가 별도 검증합니다.
