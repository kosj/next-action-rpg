# 저장 관찰의 범위와 미완료 값

동일7061앱에서localUIquality0/Done성공후30초안에primary0을확인하지못했다. 기존Python왕복loop의완료3회와새awaited in-browser loop의완료6회는모두이전1이었다. 기한말pending의결과는없으므로영구저장실패·이후성공을단정하지않는다. 새loop는샘플수가늘었지만미관측이해소되지는않아Python왕복만의문제라고도확정하지않는다.

반면[같은hosted앱](hosted-quality0-then-narrow-failure.json)은실제primary0을읽었고그뒤별도narrowCSS문제로실패했다. 지역차이를섞지않는다. 소프트웨어구간의기록FPS1~2·primary하나읽기4~7초·엔진IDBFS timestamp index33cursor는지연정황이며sync내부를계측한확정원인은아니다.

공식4.7.2 OS_Web는WRITE-close때dirty를설정하고다음mainiteration에sync를시작한다. sync중새dirty는완료때지우지않아다음sync로남는다. 고정5초timer/dirty-loss를이데이터로주장하지않는다. 별도의readonly save_primary/mtime/persistent를추가해volatile파일과durable값을구분했고, 이후quality1의완전재시작은두JSON일치가확인됐지만loader오류로전체FAIL을유지했다.

어느경우에도force sync·파일쓰기·판정시간증가로통과시키지않았다. 최종full/defaultworkflow의0→1→0·실제primary·완전재시작검사는유지하며[PR #8](https://github.com/kosj/next-action-rpg/pull/8)의최종actualhosted/public실행을승인근거로사용한다. 지역subset과실제Android/iOS·GPU성능은별도다.
