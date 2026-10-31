# 읽기 전용 저장 관찰 fixture

`browser_smoke.py`의 실제 `read_persisted_saves` 문자열을 Python AST로 추출해 Node 이벤트 fixture에서 실행합니다. reader 복제본·Playwright·npm 패키지는 필요 없습니다.

```bash
python -m unittest discover -s tools/tests -p 'test_browser_storage.py' -v
python tools/tests/test_browser_storage.py --report docs/validation/v0.1.4/readonly-storage/result.json
```

일반 `python -m unittest discover -s tools/tests -p 'test_*.py'`에도 5개 검사가 포함됩니다. Node가 없는 로컬 환경에서는 이 클래스만 skip하며, `CI` 환경에서 Node가 없으면 설정 오류로 실패합니다. 현재 GitHub Ubuntu runner에는 Node가 제공됩니다.

검사하는 성질은 다음과 같습니다.

- 202개 키에서 primary 값 1개만 읽고 다른 파일·백업 payload를 읽지 않습니다.
- 발견한 primary 키의 다음 관찰은 재탐색 없이 직접 조회합니다.
- `FILE_DATA`가 없을 때 스키마를 만들지 않고 연결을 닫습니다.
- 예기치 않은 version upgrade를 abort합니다.
- 손상된 primary JSON은 성공한 저장으로 표시하지 않고 거부합니다.

모든 데이터와 IndexedDB 이벤트는 테스트가 만든 모형입니다. 결과 파일의 reader/fixture SHA는 어떤 구현을 검사했는지 식별하며, 이 검사는 실제 Chromium의 커밋·재시작·프레임 지연 검증을 대체하지 않습니다. 앱 저장값에 직접 쓰거나 강제 `FS.syncfs`를 호출하지 않습니다.
