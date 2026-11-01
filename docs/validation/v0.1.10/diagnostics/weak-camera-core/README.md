# 첫 higher-view/core 후보의 시각 기각

camera `95a5602a…`/impact `6c8b3fb7…`의 native486/0·preview 뒤 실행한 scripted native MovieMaker take다. [실제 report](review.json)는 기능 통과와 `engine_clean=true`·WeakRef cleanup을 확인했지만, [원본 접촉 PNG](contact.png)와 후속 frame에서 별도의 core 섬광을 구분하기 어려워 시각 채택하지 않았다. native 투영 면적/mesh 검사와 정상 종료는 화면 가독성 승인과 다르다.

[composition audit](composition-check.json)는 원본 [전체 trace](frames.json.gz)의 SHA에 고정한 유한 raw skin/마커/ray 검사다. 현재 후보의 camera→core 중심은 검토한 Hero body·broadblade·target body/검에 가려지지 않았고 broadblade가 star 외곽12개 중1개만 가렸다. 따라서 core가 약해 보였다는 사실을 주인공/무기에 묻혔다는 확정 원인으로 쓰지 않는다. 6개 bone과 source mesh를 맞춘 CPU 표본이며 full engine raster/전체 시각 판정은 아니다.

624 delivery frame/60Hz/10.4초·실제69.3 한 번·pause5표본·종료HP56·오류0과 유한 관찰은 당시 source의 사실로 보존한다. 이후 core의 반경/수명/대비와 camera art budget을 명시적으로 수정했으며 이 take를 소급 통과시키지 않는다. [원문 log](gameplay.log)·[명시적 contact frame](contact-frame.json)·[cleanup](cleanup.json)·세 input manifest와 [trace SHA](trace-provenance.json)를 보존한다. 무음 MP4는 원본 SHA만 남기며 이 진단 묶음에는 복사하지 않았다. [파일 해시](archive-manifest.json).
