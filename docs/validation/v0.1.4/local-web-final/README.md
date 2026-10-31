# 최신 아트·전환 프리뷰의 로컬 전체 Web 검사

2026-10-31, Chromium SwiftShader·Godot4.7.2 Compatibility의 새 전용 프로필에서 전체316.961초·exit0·오류0을 확인했습니다. [요약](character-qa-summary.json)·[실제 단계 로그](run.log)·[입력/manifest](run-context.json)를 보관합니다. 현재 원본 A89/214, 첫 방 PBR·80ms 전환·오디오 종료 수정과 최종 QA reader를 포함한 frozen export입니다. build ID `0.1.4 · 1b8d95b9`에는 당시 커밋 전 runtime 변경이 포함되며 정확 공개 SHA 검증은 후속 CI가 담당합니다.

실제 UI로 새 여정·품질1→0→1을 조작했고 안전 구역의HP120을 유지했습니다. 실제 좌클릭 light_1과 RightHand 변화, 칼끝1.19m를 확인한 뒤 일반 근접 수호병3명과 첫 전투를 검사했습니다. 완전히 닫은 Chromium과 같은 프로필의 새 Chromium에서 quality1·checkpoint0·z6·HP120·hero 스킨/무기를 복원했습니다. [전투 화면](04-gameplay.png)·[실제 베기](08-skeletal-attack.png)·[재시작](05-continue.png)은 생성 이미지나 고정 게임 상태 fixture가 아닙니다.

기존15초 UI/30초 저장 assertion을 유지했습니다. 읽기 전용 IndexedDB9회가 모두 완료됐고 처음/재시작은34keys에서 primary payload1개, 중간7회는 발견한 키의 직접get을 사용했습니다. 테스트가 게임 저장을 쓰거나 강제 sync하지 않았습니다. 최대 readonly 관찰4.178초, 첫/재시작 최대 rAF gap10.433/9.216초가 기록됐습니다. 이는 소프트웨어 렌더링/셰이더 준비 지연이며 목표 GPU60fps의 성능 자료로 사용하지 않습니다.

클립 전체 변형·양손/얼굴·공격 접촉·의상·머리·실기기 품질의 AAA 승인은 계속pending입니다. 이 검사 성공과 공개 Pages의 실제 새 커밋 실행 검증을 구분합니다.
