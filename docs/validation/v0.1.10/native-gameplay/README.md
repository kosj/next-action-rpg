# 실제 Game의 baseline·최종 프로토타입 비교

2026-11-01 UTC. production Game/물리·카메라·확정 피해를 실행한 scripted native MovieMaker 자료다. 사용자가 조작한 영상·브라우저 검사가 아니며 두 MP4는 무음 논리1x delivery다. 원본 입력 일정은 [release tick334까지 직접 대조](comparison.json)했고 실제 첫 접촉은 baseline tick362/최종359로 다르다. 좋은 장면을 맞추려고 contact를 강제하거나 시간을 바꾸지 않았다.

| take | 보존한 실제 근거 | 판정 범위 |
| --- | --- | --- |
| [v0.1.9 baseline](baseline/README.md) | 원본 MP4/접촉PNG/report/log/전체 trace gzip·입력 해시 | 오류/누수 marker0이나 WeakRef 해제는 당시 fixture 관찰 범위 아님. 비교 자료이며 시각 승인 아님 |
| [첫 higher-view/core 진단](../diagnostics/weak-camera-core/README.md) | clean report/접촉PNG/전체 trace·source-bound ray 감사 | native486/0·정상 종료여도 섬광이 약해 시각 기각. 중심의 몸/검 burial을 확정 원인으로 쓰지 않음 |
| [최종 readable-contact](final/README.md) | 원본 MP4/접촉 및 birth/+1/+2/+4 PNG/report/log/WeakRef cleanup/전체 trace·입력 해시 | 오류0·69.3 한 번·양쪽 pause5표본. 적 상체/작은 금백색 국소 섬광이 더 보이는 프로토타입 개선만 채택 |

[최초 low-camera 실패](../diagnostics/initial-gameplay-occlusion/README.md)는 기능 통과와 실제 가림·종료 오류를 함께 보존한다. [이전614 CI 성공](../diagnostics/old-camera-ci.json)도 실제 타격 가독성을 승인하지 않았다. source/capture/runtime 차이는 각 manifest와 최종 [source differences](final/source-differences.json)를 참조한다. 최종 source는 dirty614 기반 snapshot이며 release commit이라고 표시하지 않는다.

선택 프레임/기능 검수와 전체 연속1x AV/직접 청취·실시간 frame pacing·목표 하드웨어·전체 skin/관통·AAA 승인은 별도다. 로컬 Web 다중터치 집중 검사는 [277.923초/errors0](../focused-browser/SUMMARY.json)으로 통과했으며 full 여정·최종 clean CI·공개/릴리스는 이 기록 작성 시점에 후속 gate다.
