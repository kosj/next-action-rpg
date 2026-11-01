# 최종 readable-contact 프로토타입 take

2026-11-01 UTC. 실제 production Game/물리·카메라/core를 사용하는 scripted native MovieMaker take다. source는 dirty `61445931` 기준이며 HeroFury007 `f2ed…`/Sentinel `e7e…`/curve `601a…`, camera `e97cbf03…`/impact `fc39d672…`를 report/input manifest로 고정했다. [실제 report](review.json)·[contact frame](contact-frame.json)·[입력 차이](source-differences.json)와 원문 [로그](gameplay.log)를 보존한다.

600 gameplay+24 UI 틱=624 delivery frame/60Hz/10.4초,실행462.367초다.69.3 피해1회·적HP95→25.7·양쪽 pause5표본·실제 drawn blade1.1900017m·접촉점→실제 날 안쪽축.0784555m·최대 recoil.3500023m·종료HeroHP56을 기록했다. 오류0, [cleanup](cleanup.json)의 audio WeakRefs 해제/pending playback0/player0,입력 source 불변·프로세스 종료를 확인했다. 이는 실제 script 입력의 기능 capture이며 사람의 play나 브라우저 검사는 아니다.

[원본 lossless 접촉 PNG](contact.png)와 [원본 MJPEG에서 해상도 변경 없이 복원한 birth/+1/+2/+4 프레임](contact-sequence/provenance.json)을 검수했다. 적의 투구/상체가 더 구분되고 어깨/칼날 부근의 작은 금백색 섬광이 보이는 범위에서 root가 프로토타입 개선으로 채택했다. 겹침은 남고 효과는 짧고 작다. +4의 큰 금색 세로 사각형은 주변 적의 기본 startup 경고이며 contact 효과로 세지 않는다. 큰 시각 도약·전체 타격감·AAA 판정은 아니다.

[무음 논리1x MP4](gameplay-logical1x.mp4)는624frame/1280×720/60fps의 원본 delivery다. 생성/선택 프레임 검수와 연속1x AV 시청/직접 청취·실시간 FPS·목표 기기 승인은 구분한다. [전체 trace lossless gzip](frames.json.gz)·[decoded SHA](trace-gzip.json)와 세 input manifest는 실제 query/marker/clock 관찰을 보존한다. 원문 artifact는 byte-exact 복사했으며 [파일 해시](archive-manifest.json)로 묶었다. clean committed CI·실제 브라우저/full 여정·공개/릴리스는 이 로컬 기록 작성 시점에 별도 pending이다.
