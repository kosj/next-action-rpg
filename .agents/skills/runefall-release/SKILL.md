---
name: runefall-release
description: Build, validate, and publish RUNEFALL web or Windows distributions on GitHub within the authorized task scope. Use for exports, version tags, release assets, Pages deployment, or deployment failures.
---

# RUNEFALL 빌드와 GitHub 배포

상세 실행 방법은 [README](../../../README.md)·[배포 문서](../../../docs/DEPLOYMENT.md), 플랫폼 근거는 [godot-export](../godot-export/SKILL.md)를 참조합니다. 명령은 저장소 루트 기준입니다.

## 준비

1. `python tools/knowledge.py search --tag deployment`와 `--tag toolchain`으로 이미 확인한 제약을 찾습니다.
2. 요청 범위·작업 트리·대상 커밋과 CI 상태를 확인합니다. 저장소 공개 범위는 사용자의 최신 결정과 실제 API 상태를 따릅니다. 과거의 비공개 유지 지침을 현재 결정으로 오인하지 않습니다.
3. 엔진의 원본은 `tools/toolchain.json`, 게임 버전의 원본은 `game/project.godot`입니다. 동일 버전 엔진·템플릿을 준비합니다. `tools/build.py`가 버전·태그 불일치를 거부하는 계약을 유지합니다.
4. `/tmp`의 로그·도구·중간 파일이 다음 작업까지 남거나 다른 작업자와 공유된다고 가정하지 않습니다. 장시간 검사나 유료 생성 직후에는 `/workspace`의 프로젝트 작업 루트 아래에 재개용 체크포인트를 남깁니다. 대상 커밋·판본, 완료/진행 중인 task와 실제 비용, 원본·산출물 경로 및 SHA, 재실행할 단계와 남은 검사를 구분합니다. 인증 값·계정 원문·서명된 다운로드 URL은 제외하고, 공개 근거로 남길 결과는 검토한 문서·manifest·검증 기록에 옮깁니다. 재개 시 파일과 실제 서비스 상태를 확인한 뒤 이어서 실행하며, 임시 파일 소실만으로 유료 작업을 다시 생성하지 않습니다.

## 빌드와 실행

```bash
python tools/knowledge.py check
python tools/build.py --windows
python tools/check_web.py
```

웹 전용 변경이면 `--windows` 없이 실행합니다. 실제 웹 검사는 하위 URL과 동일 프로필의 브라우저 종료·재시작을 포함합니다. 실패한 산출물을 성공 빌드로 배포하지 않습니다. Windows 내보내기 성공과 Windows 실기기 실행·성능 측정을 구분합니다.

설정 UI의 완료와 브라우저의 영구 저장 완료는 별도로 확인합니다. [Godot의 웹 파일 close 콜백과 main loop](https://github.com/godotengine/godot/blob/4.7.2-stable/platform/web/os_web.cpp)는 쓰기 후 dirty flag를 세우고 다음 프레임에 비동기 IndexedDB 동기화를 시작합니다. 같은 소스의 `force_fs_sync()`도 그 flag만 세우므로 정상적인 `FileAccess.close()` 뒤에 중복 호출한 것을 저장 결함 수정으로 기록하지 않습니다. 저장 실패·rename 결함과 브라우저 종료 전 미완료 커밋을 실제 파일과 엔진 소스로 구분합니다.

`browser_smoke.py`는 실제 UI로 품질을 바꾼 뒤 격리된 테스트 프로필의 IndexedDB `FILE_DATA` primary를 읽기 전용으로 조회합니다. 기대한 설정·여정·체크포인트가 커밋되는지 제한 시간 안에 조건 대기한 뒤 브라우저를 완전히 종료하고 같은 프로필에서 이어하기를 다시 검증합니다. 고정 sleep, QA 상태 변조, 테스트 측 강제 동기화로 통과시키지 않습니다. UI 상태·커밋 전후 primary·재시작 상태와 실패 screenshot/state를 함께 보관하며, 진단 실행 성공과 최종 패치가 포함된 빌드의 실행 성공을 구분합니다.

## GitHub 릴리스

- 기존 권한과 사용자 요청 범위에서 검증한 커밋을 main에 반영합니다. 병합 API 오류가 나면 실제 PR 상태를 확인한 뒤 일반 Git 병합/푸시를 사용할 수 있습니다. 강제 푸시·보호 규칙 우회는 하지 않습니다.
- 새 버전은 앱 버전과 일치하는 `v*` 태그를 사용합니다. `gh release create`는 `--target`에 확인한 커밋을 지정하고 실제 줄바꿈의 메모 파일을 `--notes-file`로 전달합니다.
- 현재 환경의 로컬 바이너리 첨부는 인증에 실패한 전례가 있습니다. 태그 CI의 `release` job이 검증된 웹·Windows ZIP과 매니페스트를 일회성 Actions 토큰으로 첨부하도록 합니다. 장기 키를 채팅에 요청하지 않습니다.
- 태그 run의 build·release 성공과 실제 첨부 3개를 확인합니다. 내려받을 수 있으면 매니페스트의 크기·SHA-256·버전·커밋과 ZIP 무결성을 확인합니다. 릴리스 페이지 생성만으로 완료 처리하지 않습니다.

## GitHub Pages

main의 build 성공 → deploy 성공 → `verify_public_web` 성공을 확인합니다. 마지막 job은 배포 출력의 HTTPS 주소를 검사하고 `RUNEFALL_EXPECTED_COMMIT`으로 실제 실행 중인 빌드 번호까지 대조한 뒤 WebGL·입력·브라우저 종료/재시작 저장을 검사합니다. ZIP 다운로드 성공은 Pages 게시 성공과 별개입니다. 공개 브라우저 검사 아티팩트의 상태·오류·재접속 JSON과 실행 URL을 근거로 보관하되, 새 main의 성공을 과거 실행 기록으로 대신하지 않습니다. 예상 URL을 활성 주소로 표시하지 않습니다.

공개 URL 검사에서 관리형 클라우드 브라우저만 인증서 오류가 나면 인증서 검증을 유지한 HTTPS 클라이언트 결과와 비교합니다. 이때 GitHub hosted runner의 공개 URL 검사를 사용해 배포 자체의 실행과 로컬 브라우저 신뢰 문제를 따로 확인할 수 있습니다. 프록시 CA의 브라우저 신뢰 설정을 확인하고 TLS 검증을 끄지 않습니다. HTTP 접속·배포 성공과 공개 주소의 실제 브라우저 조작 성공을 별도로 기록하고, 환경 오류를 Pages 배포 실패로 오인하지 않습니다.

Pages가 아직 설정되지 않았거나 연결 권한이 없으면 실패한 작업·HTTP 상태와 필요한 최초 설정을 보고합니다. 저장소 공개 전환과 Pages 최초 활성화는 별개의 설정입니다. 저장소 metadata의 admin=true만으로 연결 앱의 관리 권한을 판단하지 않습니다. 계정 플랜 부족이라고 단정하거나 공개 범위를 임의로 변경하지 않습니다.

`configure-pages@v5`의 `enablement: true`는 기본 `GITHUB_TOKEN` 이외의 Pages 생성 권한 토큰이 필요합니다. [공식 입력 정의](https://github.com/actions/configure-pages/blob/v5/action.yml)를 확인하고, 권한이 부족한 기본 토큰으로 같은 생성 요청을 반복하지 않습니다. 최초 설정이 완료되면 이미 성공한 build를 다시 실행하는 대신 해당 run의 실패한 deploy job만 재실행할 수 있습니다. 활성화한 뒤에는 지식 DB의 제약 상태를 실제 확인 결과로 갱신합니다.

## 결과 기록

지식에는 버전·커밋·CI/릴리스의 영구 URL과 검증 범위를 기록합니다. 토큰·서명된 만료 URL·전체 비밀 로그는 보관하지 않습니다. 매번 달라지는 검사 수나 릴리스 버전을 이 스킬에 고정하지 않습니다.
