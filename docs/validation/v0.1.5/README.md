# v0.1.5 캐릭터 눈·검 잔상 검증

2026-10-31. 이 폴더는 각 입력 판본의 검증 범위를 보존한다. **최종 AAA·목표 GPU 성능·Windows 실기기 실행은 pending**이다. source의 버전은0.1.5이며 로컬 uncommitted 빌드·PR 합성 merge·최종 main/tag의 식별자는 구분한다.

- [native.log](native.log): 최종 몸체4cc9/안구d7d를 사용한 Godot4.7.2 전체345검사·실패0, 정상 종료. 기존305에 독립 실행 수치를 중복 합산하지 않는다.
- [눈 부착/색상 근거](character-eyes.json)와 [집중 로그](eyes-native.log): 실제 source-world REST anchor,19클립57표본, 같은 프레임 Head·외부1.25배·정지·명시 고개 회전·해제를 확인한다.21집중 검사·실패0이며 최종345에 포함된 회귀와 같은 계약이다.
- [검 잔상 수치](blade-trail.json): 실제 표시된 칼끝·world history·권한 있는 active 시간·중단/복귀·bounded geometry를 확인한다. [고정 Web ADD/MIX 비교](../../../art_source/production/character_polish/blade_trail_review/README.md)는 눈 변경 전 별도 fixture이며 라이브 교전 검증이 아니다.
- [반입 전 독립 재현](eye-colors-before-import-fix.log): 원래 색 배열이 남아도 Godot4.7.2 첫 primitive의 vertex-color 사용 flag가 꺼졌다. [자산 전용 보정](../../../game/import/eye_materials.gd) 뒤 세 재질·실제8bit색을 엄격 검사했다. 다른 엔진 판본에서도 같은 버그라고 가정하지 않는다.
- [Web 눈 기준 화면](eyes-web-reference/review.json): 실제 Game 조명/재질의 정지 fixture6구도×품질0/1,12장·317.962초·오류0. 안구/눈꺼풀 가림과 Head socket오차0을 확인했다. 큰 어두운 동공과 피부/머리의 근접 품질 한계는 그대로 기록했다. 정상 입력·저장·타이밍·성능 검사가 아니다.
- [반복 fixture 도구](../../../tools/build_eye_fixture.py)와 [실제7가드 결과](eye-fixture-tool.json): 기존 d7d 입력으로 좌표/색/계약 fixture를 재현하고 source overwrite·변조 Head·무단 RGB 외 변경을 거부한다. 기본 덮어쓰기는 거부하며 검토한 변경만 `--replace`로 반영한다.
- [Python 최종 로그](python-final.log): 도구41검사·실패0. 초기 상세 로그는 [별도 보관](python-tests.log)한다. 새 standalone 지식 패키지의7무결성 검사는 [별도 보고서](../knowledge-kit/verification.json)로 확인한다.

원본 보존·실패한 첫 fit·전체 표면 refit·삼각형 계획 초과는 [아트 후보](../../../art_source/production/candidates/lyra-eye-sockets-001/README.md)와 [국소 개선 기록](../../CHARACTER_POLISH.md)을 참조한다. [최종 로컬 export](local-build-summary.json)는 native345·실패0, Web/Windows 정상 종료, Web원시142,040,736bytes/150,000,000예산과 실제ZIP CRC·SHA·실행파일/라이선스를 확인했다. [최종 정상 브라우저](local-web-final/README.md)는0.1.5·c6be1dce에서471.812초·오류0·exit0이다. 품질1→0→1·실제 primary커밋·베기·전투·완전 종료/동일프로필 재시작과 눈/무기/체크포인트 복원을 통과했다. 기존15/30초 검사 한도와 read-only IDB 계약은 유지했다. 로컬C1과 공개 main/tag의 commit은 구분한다. 공개 배포는 [Actions](https://github.com/kosj/next-action-rpg/actions/workflows/build.yml)의 해당 main SHA `deploy`와 `verify_public_web`, 릴리스는 해당 태그의 `release` 및 실제 첨부 파일 검사로 별도 확인한다.

홍채 밝기·동공 색상 크기만 변경한 후보9f는 실제 Web PCK에서 색 적용을 확인했으나, 같은 정면/사선 품질0/1에서 개선이 미미해 [기각](../../../art_source/production/character_polish/rejected_eye_palette/decision.json)했다. 최종 runtime은 d7d를 유지한다. 최종 얼굴의 피부·머리카락·시선/깜빡임·주변 형태는 후속 AAA 제작 과제다.
