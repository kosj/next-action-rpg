# GitHub 웹 배포 · Windows 빌드

## GitHub Pages 최초 설정

1. [Settings → Pages](https://github.com/kosj/next-action-rpg/settings/pages)에서 **Build and deployment → Source → GitHub Actions**를 선택합니다.
2. main의 **Validate and build RUNEFALL** 워크플로를 실행합니다. main 변경 시 자동으로 실행되며 Actions 화면에서 수동 실행할 수도 있습니다.
3. `build`가 검사와 내보내기를 마치면 `deploy`가 실행 빌드를 게시합니다. Pages 환경과 워크플로 요약에 실제 배포 주소가 표시됩니다.
4. 사용자 지정 도메인이 없다면 예상 주소는 `https://kosj.github.io/next-action-rpg/`입니다. **Pages 설정과 배포 성공을 확인하기 전에는 이 주소를 활성 서비스로 안내하지 않습니다.**

현재 작업 연결은 Pages 설정 API를 조회할 권한이 없어 HTTP 403을 반환했습니다. 저장소 소유자가 최초 Pages 설정을 해야 합니다. 이 오류만으로 계정의 플랜이 부족하다고 단정할 수 없습니다.

[GitHub 공식 문서](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)에 따르면 비공개 저장소의 Pages는 GitHub Pro·Team·Enterprise에서 사용할 수 있습니다. 설정 화면에서 사용 불가로 표시되면 소스를 비공개로 유지한 채 배포 전용 공개 저장소를 별도 구성하는 방안을 선택할 수 있습니다. 이 구현은 소스 저장소의 공개 여부를 변경하거나 새 공개 저장소를 만들지 않습니다.

배포는 GitHub가 발급하는 일회성 `GITHUB_TOKEN`과 OIDC를 사용하므로 별도의 itch.io 계정이나 장기 배포 키가 필요하지 않습니다. 워크플로의 배포 작업에만 `pages:write`, `id-token:write`를 부여합니다. PR은 배포하지 않습니다.

## 로컬 웹 빌드

Godot 4.6.3 Standard와 동일 버전 템플릿을 사용합니다. 웹은 Compatibility / WebGL 2.0, 스레드·GDExtension·PWA 비활성으로 내보냅니다. 배포는 HTTPS, 로컬 개발은 localhost를 사용합니다.

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

- PR / main: 반입 검사 → 회귀 검사 → 웹 내보내기 → ZIP·SHA-256 아티팩트 업로드.
- `v*` 태그 / 수동 Windows 선택: Windows 빌드 추가. 버전 태그의 ZIP·매니페스트는 GitHub Releases에도 자동 첨부합니다.
- main의 성공 빌드: Pages 아티팩트 생성 → GitHub Pages 배포.
- 큰 `.blend` 원본은 실행에 필요하지 않으므로 CI에서 LFS 다운로드를 하지 않습니다.

실제 GPU 성능·Windows 플레이·Edge 동작은 별도 확인 항목입니다. headless 검사가 이를 대신하지 않습니다.

## 롤백

이전 정상 커밋을 대상으로 한 되돌리기 PR을 main에 반영하면 이전 동작을 재배포합니다. 과거 실행의 산출물은 Actions Artifacts에서 내려받을 수 있습니다. 세이브 v1을 깨는 변경은 이전 저장의 처리 정책을 구현한 뒤 배포합니다.
