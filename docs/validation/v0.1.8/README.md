# v0.1.8 완충 강타 로컬 검증

2026-10-31 UTC. 아래 자료는 `b6af5a51…`를 기반으로 손잡이 판정·실제 밀려남을 수정한 **dirty preview**다. 최종 커밋·전체 브라우저·공개 Pages·릴리스 파일 결과는 [PR #9](https://github.com/kosj/next-action-rpg/pull/9)의 별도 Actions 근거를 따른다. 정상1배속 AV·실제 Android/iOS/Safari/Windows·목표 GPU·AAA 아트 승인은 포함하지 않는다.

- Godot4.7.2 실제 통합 **439개·실패0**, Python **51개·실패0**, 아트 무결성 통과. [native 원문](native-runtime.log), [실행 범위·바이트·SHA](local-preview.json).
- 실제 반입 Grip/Tip은 일곱 active phase·두 actor scale에서 최대 **.326mm/1.122mm** 오차다. 실제 Player/capsule frame을 사용했다. 명목 .576m 이동의 지지발 drift는 **.0154mm**이며 지형/충돌에 적응하는 foot IK 승인이 아니다. [정합 원문](alignment.json).
- 표시 Grip→Tip **1.19m** 중 손잡이 쪽18%를 제외한 **.9758m**만 피해 캡슐로 사용한다. 총높이에 반구를 포함하고 중심축은 양끝에서.12m 안쪽이다. 근접.725m 회귀는.38초까지HP95를 유지하고 실제 베기.427458초에69.3을 한 번 적용한다. [실제 날·손잡이 회귀](contact.json).
- native 첫 접촉의 query/게임 시각 **.46초**, 실제 표시 포즈 **.459999975초**다. 실제 표시 검과 표면점 거리는 **.071864m**다. 잔상8표본·mesh·age·양쪽53본·루트·시계가 이후3physics frame 동안 유지됐다. 표면점은 hurtbox ray 근사이며 삼각형 충돌 승인은 아니다.
- 실제 겹침 조건(몸체 간격.744995m/반경합.76m)에서 첫 이동.039993m를 포함한 최종 수평 변위·경로는 **.349991m**다. 열린 바닥은.349976m, 벽 앞은.197510m로 줄었다. 충돌 복구 이동도 요청한.35m 예산에서 소비하며 관찰값을 잘라내거나 순간 이동하지 않는다. 틱별 원문은 같은 [접촉 기록](contact.json)에 있다.
- 실제 WAV 분리·동시32음성 상한·WeakRef 종료 검사가 통과했다. [음향 API 원문](audio.json). 청취 감상·실기기 믹스 승인은 별도다.
- Web/Windows 내보내기와 ZIP CRC·크기·SHA·실행 파일·의존 라이선스 검사가 통과했다. Web 원시 **146,279,323B**, 기존150MB 제한 유지. 씬 전체500Hz 반입152,592,309B는 기각하고 새 두 동작의 정밀도를 유지하며 원본 동작100Hz 표본·끝점·채널을 복원했다.

실제 CDP 다중 터치 집중 검사는 **282.938초·오류0**으로 통과했다. 안전 구역의 완충 빗맞힘은 contact/spawn0을 유지했다. 정상 이동·게이트·타깃 고정 후 실제 피격/복귀에서 강공 버튼을 놓아 피해 **69.3(95→25.7)**, `heavy_hit .48초`, 양측 정지 요청 `.075초`, 실제 effect setup1회와 strike-target 중복0을 확인했다. 실제 접촉.432222222초의 전체 검 방향 투영은 **.263749**로 손잡이 제외 경계.18을 넘고, 독립 재구성한 캡슐 중심축과의 거리는 **.118551m**로.125m 기준 안이다. 실제 수평 recoil은 **.349998m**, 마지막 실제 일시정지는HP72·소유 포인터0이다. [요약](mobile-focused-summary.json), [검사 원문](mobile-focused-proof.json), [읽기 전용 입력/상태 타임라인](mobile-release-timeline.json), [동일 export·소스 해시](mobile-export-context.json).

브라우저는 짧은 정지 순간의 표시 포즈를 포착하지 못했다. 따라서 paired gate는 **unobserved**이며 native의 실제 positive 검사를 별도로 사용한다. 정상1배속 화면·음향이나 기기 성능의 통과로 승계하지 않는다. 직접 확인한 [일시정지 PNG](mobile-after-contact-paused.png)는 적중 뒤 메뉴 상태이며 접촉 최고점 이미지가 아니다.

초기435검사·터치299.510초와 첫 clean PR CI의 녹색 결과는 손잡이 접촉을 놓쳐 기각했다. 날 구간을 수정한 다음 실행도 접촉 기하는 통과했으나 실제 밀림.365349m가.355m 기준을 넘어 실패했다. [기각한 접촉·밀림 원문](rejected-contact-summary.json)을 보존하며 현재 성공과 합산하지 않는다. 초기 두 driver 실패도 성공에 합치지 않는다. 최종 도구는 bounded readonly 기록과 실제 피격 복귀를 사용하며 기존 전체 검사·UI15초/IDB30초/이동60초/정지1.2m를 유지한다. 게임/저장 상태 주입이나 강제 동기화는 사용하지 않았다.

제작 중 기각한 첫 새 후보의174도 팔 회전 점프는 key의 손 목표가 정확해도 중간 시각의 칼끝을 약1.77m 벗어나게 했다. [기각 원문](../../../art_source/production/candidates/lyra-impact-001/rejected-b6bc-summary.json)과 [동일 카메라 정적 비교](../../../art_source/production/candidates/lyra-impact-001/studio-review/midpoint-old-new.png)를 보존한다. 이 후보는 v0.1.7에 배포된 동작이 아니며 비교 그림은 제작 당시의 스튜디오 자료다.
