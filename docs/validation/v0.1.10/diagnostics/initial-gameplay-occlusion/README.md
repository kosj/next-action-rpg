# 최초 실제 교전 화면의 가림 실패

2026-11-01 UTC. 이전 카메라의 scripted native MovieMaker attempt4 진단 자료다. [접촉 PNG](contact.png)를 직접 확인했으며 주인공이 잠긴 적과 접촉점을 가렸다. 물리적인 blade plane과 AABB가 회전한다는 검사만으로 효과가 화면에 보인다고 승인할 수 없었다. 새 카메라/brief core 수정의 결과는 이 자료에 소급하지 않는다.

[실제 report](review.json)는 기능 gate 통과와 `engine_clean=false`를 분리한다. 600 gameplay+24 UI 틱을60Hz 논리 시간으로 담았고, tick359/공격.386초/phase.255556에서69.3 피해1회·양쪽 pause5표본·잔상4표본/12tri·종료HP56을 기록했다. [로그](gameplay.log)의 ObjectDB2개 및 resource1개 종료 오류 때문에 clean capture 통과가 아니다. 최종 마커 world 좌표는 이 take에 없으며 query 벡터/마커UV와 다음 fixture의 명시적 world 검사를 섞지 않는다.

[evidence](evidence.json)와 세 입력 manifest는 실제 source/fixture/runtime 파일 해시와 차이를 보존한다. source→capture에서 `project.godot`, capture→runtime에서 기존4개 GLB import sidecar가 달라졌으므로 모든 입력이 동일하다고 쓰지 않는다. 로그의 build-label만으로 source 커밋을 판단하지 않는다. 원문 log·report·PNG·입력 manifest는 byte-exact 복사본이며 [archive manifest](archive-manifest.json)로 묶었다.

이 자료는 선택 raster와 기능 trace의 근거다. 새 카메라의 시각 채택·정상 종료, 연속 정상1x AV/청취, 실제 브라우저·기기 성능·AAA 승인은 별도이며 `pending`이다.
