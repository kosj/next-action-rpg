---
name: runefall-release
description: Build, validate, and publish RUNEFALL web or Windows distributions on GitHub within the authorized task scope. Use for exports, version tags, release assets, Pages deployment, or deployment failures.
---

# RUNEFALL 빌드와 GitHub 배포

상세 실행 방법은 [README](../../../README.md)·[배포 문서](../../../docs/DEPLOYMENT.md), 플랫폼 근거는 [godot-export](../godot-export/SKILL.md)를 참조합니다. 명령은 저장소 루트 기준입니다.

## 준비

1. `python tools/knowledge.py search --tag deployment`와 `--tag toolchain`으로 이미 확인한 제약을 찾습니다.
2. 요청 범위·작업 트리·대상 커밋과 CI 상태를 확인합니다. 소스 저장소는 비공개로 유지합니다.
3. 엔진의 원본은 `tools/toolchain.json`, 게임 버전의 원본은 `game/project.godot`입니다. 동일 버전 엔진·템플릿을 준비합니다. `tools/build.py`가 버전·태그 불일치를 거부하는 계약을 유지합니다.

## 빌드와 실행

```bash
python tools/knowledge.py check
python tools/build.py --windows
python tools/check_web.py
```

웹 전용 변경이면 `--windows` 없이 실행합니다. 실제 웹 검사는 하위 URL과 동일 프로필의 브라우저 종료·재시작을 포함합니다. 실패한 산출물을 성공 빌드로 배포하지 않습니다. Windows 내보내기 성공과 Windows 실기기 실행·성능 측정을 구분합니다.

## GitHub 릴리스

- 기존 권한과 사용자 요청 범위에서 검증한 커밋을 main에 반영합니다. 병합 API 오류가 나면 실제 PR 상태를 확인한 뒤 일반 Git 병합/푸시를 사용할 수 있습니다. 강제 푸시·보호 규칙 우회는 하지 않습니다.
- 새 버전은 앱 버전과 일치하는 `v*` 태그를 사용합니다. `gh release create`는 `--target`에 확인한 커밋을 지정하고 실제 줄바꿈의 메모 파일을 `--notes-file`로 전달합니다.
- 현재 환경의 로컬 바이너리 첨부는 인증에 실패한 전례가 있습니다. 태그 CI의 `release` job이 검증된 웹·Windows ZIP과 매니페스트를 일회성 Actions 토큰으로 첨부하도록 합니다. 장기 키를 채팅에 요청하지 않습니다.
- 태그 run의 build·release 성공과 실제 첨부 3개를 확인합니다. 내려받을 수 있으면 매니페스트의 크기·SHA-256·버전·커밋과 ZIP 무결성을 확인합니다. 릴리스 페이지 생성만으로 완료 처리하지 않습니다.

## GitHub Pages

main의 build 성공 → deploy 성공 → 실제 URL의 HTTP 응답과 실행을 확인합니다. ZIP 다운로드 성공은 Pages 게시 성공과 별개입니다. 예상 URL을 활성 주소로 표시하지 않습니다.

Pages가 아직 설정되지 않았거나 연결 권한이 없으면 실패한 작업·HTTP 상태와 필요한 최초 설정을 보고합니다. 계정 플랜 부족이라고 단정하거나 소스를 공개로 바꾸지 않습니다. 활성화한 뒤에는 지식 DB의 제약 상태를 실제 확인 결과로 갱신합니다.

## 결과 기록

지식에는 버전·커밋·CI/릴리스의 영구 URL과 검증 범위를 기록합니다. 토큰·서명된 만료 URL·전체 비밀 로그는 보관하지 않습니다. 매번 달라지는 검사 수나 릴리스 버전을 이 스킬에 고정하지 않습니다.
