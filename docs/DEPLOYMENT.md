# GitHub 웹 배포 · Windows 빌드

## 현재 공개 배포

**플레이 URL: https://kosj.github.io/next-action-rpg/**

2026-10-30 사용자가 Pages Source를 GitHub Actions로 활성화한 뒤, 이미 성공한 build를 유지하고 실패했던 deploy만 재실행했습니다. [최초 배포 실행의 2번째 시도](https://github.com/kosj/next-action-rpg/actions/runs/41076834637/attempts/2)가 성공했고 공개 URL의 HTTPS HTTP 200 응답을 확인했습니다. 최초 배포 소스는 `4b182802e6138e66b42fc91f15b0dadd5c97acc1`의 v0.1.1이며, 이후 main의 검증된 빌드가 같은 주소에 자동 게시됩니다. 현재 실행 버전·커밋은 타이틀의 빌드 번호와 해당 Actions 실행으로 확인합니다.

v0.1.2에서는 [build·deploy·공개 URL 브라우저 검사](https://github.com/kosj/next-action-rpg/actions/runs/41123086701)를 모두 통과했습니다. 실제 실행 커밋과 WebGL·입력·브라우저 재시작 저장을 검증했으며, [릴리스 다운로드 무결성과 함께 근거](validation/v0.1.2/README.md)를 보관합니다.

## GitHub Pages 최초 설정

아래 최초 설정은 이 저장소에서 완료됐습니다. 새 저장소로 이전할 때 참고합니다.

1. [Settings → Pages](https://github.com/kosj/next-action-rpg/settings/pages)에서 **Build and deployment → Source → GitHub Actions**를 선택합니다.
2. main의 **Validate and build RUNEFALL** 워크플로를 실행합니다. main 변경 시 자동으로 실행되며 Actions 화면에서 수동 실행할 수도 있습니다.
3. `build`가 검사와 내보내기를 마치면 `deploy`가 실행 빌드를 게시합니다. Pages 환경과 워크플로 요약에 실제 배포 주소가 표시됩니다.
4. 사용자 지정 도메인이 없다면 예상 주소는 `https://kosj.github.io/next-action-rpg/`입니다. **Pages 설정과 배포 성공을 확인하기 전에는 이 주소를 활성 서비스로 안내하지 않습니다.**

초기에는 공개 전환 후에도 Pages 생성 요청이 연결 앱의 권한 부족으로 HTTP 403을 반환했습니다. 사이트 조회의 HTTP 404와 생성 요청의 HTTP 403은 별개입니다. 이 문제는 소유자가 최초 Pages 설정을 완료한 뒤 해결됐습니다. 같은 오류만으로 계정 플랜 부족이라고 단정하지 않습니다.

[`configure-pages@v5`의 공식 입력 정의](https://github.com/actions/configure-pages/blob/v5/action.yml)에 따르면 `enablement: true`로 사이트를 생성하려면 기본 `GITHUB_TOKEN` 이외의 토큰이 필요합니다. 따라서 워크플로에 이 옵션만 추가해 최초 설정을 해결하려고 하지 않습니다. Source를 GitHub Actions로 설정한 후에는 기존 성공 build를 유지하고 실패한 deploy 작업만 재실행할 수 있습니다.

배포는 GitHub가 발급하는 일회성 `GITHUB_TOKEN`과 OIDC를 사용하므로 별도의 itch.io 계정이나 장기 배포 키가 필요하지 않습니다. 워크플로의 배포 작업에만 `pages:write`, `id-token:write`를 부여합니다. PR은 배포하지 않습니다.

## 로컬 웹 빌드

Godot 4.7.2 Standard와 동일 버전 템플릿을 사용합니다. 웹은 Compatibility / WebGL 2.0, 스레드·GDExtension·PWA 비활성으로 내보냅니다. 배포는 HTTPS, 로컬 개발은 localhost를 사용합니다.

```bash
python tools/build.py
python -m http.server 8060 --directory build/web
```

`build/runefall-web.zip`의 루트에는 `index.html`과 JS/WASM/PCK가 함께 있습니다. 파일 이름을 바꾸지 마세요. 웹 예산은 압축 해제 기준 150MB 이하이며, Godot 파일 경로는 저장소 하위 URL에서도 동작하는 상대 경로입니다. `.nojekyll`을 포함합니다.

업데이트 후 이전 화면이 보이면 강력 새로고침(Ctrl+Shift+R)을 사용하고 타이틀의 빌드 번호를 확인합니다. PWA 서비스 워커는 사용하지 않습니다.

## Windows

```bash
python tools/build.py --windows
```

Windows x86_64 EXE와 PCK를 ZIP으로 제공합니다. Forward+가 기본이며 호환 렌더러 대체는 Godot 기본 동작을 사용합니다. 현재 빌드는 코드 서명이 없습니다. 실제 Windows 기기에서 실행·입력·저장·그래픽 검증이 필요합니다.

## GitHub Actions

- PR / main: 반입 검사 → 회귀 검사 → 웹 내보내기 → 데스크톱 Chromium·저장 재접속 검사 → ZIP 업로드 → 그 ZIP을 내려받아 별도 runner에서 실제 다중 터치·세 화면 크기·모바일 재시작 저장 검사.
- `v*` 태그 / 수동 Windows 선택: Windows 빌드 추가. 버전 태그의 ZIP·매니페스트는 GitHub Releases에도 자동 첨부합니다.
- main: 데스크톱·모바일 빌드 검사가 모두 성공해야 Pages 배포를 진행합니다. 배포 후 별도 runner에서 공개 HTTPS 주소의 데스크톱 검사와 모바일 다중 터치·메뉴·브라우저 재시작 저장 검사를 병렬 실행하고 실제 커밋을 대조합니다.
- 큰 `.blend` 원본은 실행에 필요하지 않으므로 CI에서 LFS 다운로드를 하지 않습니다.

실제 GPU 성능·Windows 플레이·Edge 동작은 별도 확인 항목입니다. headless 검사와 소프트웨어 WebGL 검사가 이를 대신하지 않습니다.

## 롤백

이전 정상 커밋을 대상으로 한 되돌리기 PR을 main에 반영하면 이전 동작을 재배포합니다. 과거 실행의 산출물은 Actions Artifacts에서 내려받을 수 있습니다. 세이브 v1을 깨는 변경은 이전 저장의 처리 정책을 구현한 뒤 배포합니다.
