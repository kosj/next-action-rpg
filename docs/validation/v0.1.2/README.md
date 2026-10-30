# v0.1.2 공개 배포와 릴리스 검증

2026-10-30의 실제 [main 실행](https://github.com/kosj/next-action-rpg/actions/runs/41123086701)은 build·Pages deploy·공개 URL 브라우저 검사를 통과했습니다. 공개 HTTPS 주소에서 실행 중인 `0.1.2 · 7162bd25`를 직접 대조했습니다. [공개 웹 요약](public-web-verification.json), [전투 상태](public-browser-state.json), [브라우저 재시작 후 상태](public-browser-persistence.json), [오류 목록](public-browser-errors.json)과 [실제 게임 캡처](public-gameplay.png)를 보관합니다. 프로필은 이 검사만을 위해 만든 임시 프로필입니다.

[v0.1.2 태그 실행](https://github.com/kosj/next-action-rpg/actions/runs/41123131649)은 같은 커밋의 웹·Windows ZIP과 매니페스트를 Releases에 첨부했습니다. 실제 다운로드의 크기·SHA-256·ZIP CRC와 버전/커밋을 [검증](release-verification.json)했고 [원본 매니페스트](release-manifest.json)를 보관합니다.

이 기록은 해당 커밋의 검증입니다. 이후 main 배포의 통과 여부는 해당 Actions 실행에서 다시 확인합니다. 소프트웨어 Chromium 조작 성공과 Windows 내보내기는 실기기 성능·패드·최종 아트 품질의 합격이 아닙니다. 리라의 생성 후보는 별도로 보관하며 이 게임 캡처의 기본 캐릭터는 기존 피벗 모델입니다.
