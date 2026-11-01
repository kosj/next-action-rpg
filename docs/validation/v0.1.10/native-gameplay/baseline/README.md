# v0.1.9 실제 Game 비교 take

Published v0.1.9 source `1e524b1275c6c55d3020ea5c3122afbb8db403e9`의 scripted native MovieMaker 비교 자료다. 기존 Hero27fb/Sentinele7e·production Game/물리/카메라를 사용했다. [실제 report](review.json)·[로그](gameplay.log)·[capture](capture.json)와 원본 [접촉 PNG](contact.png)·[무음 논리1x MP4](gameplay-logical1x.mp4)를 보존한다. 624 delivery frame/60Hz/10.4초,600 gameplay 틱,실제69.3 접촉1회/tick362/공격.446667초·양쪽 pause5표본·종료HP56이다.

엔진 오류/종료 누수는 기록되지 않았지만 이 baseline fixture는 최종 fixture의 WeakRef 정리를 관찰하지 않았다. 같은 입력 일정의 release tick334까지 일치한다는 비교와 실제 접촉 tick의 차이를 구분한다. production camera에서 대상/접촉이 가려지는 비교 자료이며 현재 판본의 시각 채택 근거로 승계하지 않는다.

[원본 trace의 lossless gzip](frames.json.gz)과 [decoded SHA](trace-provenance.json), 세 input manifest를 함께 보존한다. MP4·PNG·report·log·입력 manifest는 byte-exact 복사본이다. 생성한 논리1x 파일과 연속1x 시청/음향 청취·실시간 처리속도·브라우저/목표 기기·AAA 승인은 별개다. [파일 해시](archive-manifest.json).
