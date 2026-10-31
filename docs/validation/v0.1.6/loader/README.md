# 로딩 UI 제거 뒤 late progress callback

실제CSSafter restart-focus는294.612초에기능판정(quality1primary·세viewport·전체Browser종료/재시작·Continue·HP120/checkpoint0/Touch·volatile JSON==durable1)을마쳤지만 `Cannot set properties of null (setting 'value')` pageerror1로FAIL이었다. loading.remove후늦은progress가사라진DOM을참조한문제이며오류를숨기지않았다.

현재progress element가존재할때만값을갱신한다. [실제원본callback+realDOM+stubEngine집중fixture](fixture-current.json)는초기progress.5와제거후latecallback을보존하고before오류1/after오류0을검증했다. [원본beforeHTML](before.html)을사용하며이미지/게임/저장상태는쓰지않는다.

```
python tools/check_loader_lifecycle.py
```

이fixture는WASM/gameplay/저장/재시작전체승인이아니다. CI는실제Web검사전이작은회귀도실행하며, 최종actual전체와공개URL재시작은[PR #8](https://github.com/kosj/next-action-rpg/pull/8)의확정실행으로검증한다.
