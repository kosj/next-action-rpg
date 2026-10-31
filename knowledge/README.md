# 프로젝트 지식 DB

반복 절차는 [프로젝트 스킬](../.agents/skills/README.md), 재사용할 결정·실패 사례·미검증 제약은 [entries.json](entries.json)에 저장합니다. 문서와 코드가 상세 내용의 원본이며 이 DB는 검색 가능한 짧은 결론과 근거를 연결합니다.

JSON 파일을 Git으로 관리하므로 별도 서비스·계정·유료 DB가 필요하지 않습니다. Python 표준 라이브러리만 사용하며 게임 런타임과 웹 빌드에 포함하지 않습니다. 자동으로 대화를 수집하거나 백그라운드에서 내용을 갱신하지 않습니다. 작업자가 근거를 확인하고 같은 변경에서 기록합니다.

## 조회

저장소 루트에서 실행합니다. 도구 자체는 어느 디렉터리에서 실행해도 같은 DB를 사용합니다.

```bash
python tools/knowledge.py search
python tools/knowledge.py search 패링
python tools/knowledge.py search save backup
python tools/knowledge.py search --tag deployment --status pending
python tools/knowledge.py search --status all --json
python tools/knowledge.py show blender-lts-batch-exit
python tools/knowledge.py check
```

검색은 제목·요약·태그·적용 조건·근거의 대소문자 구분 없는 부분 일치입니다. 여러 검색어는 모두 포함해야 합니다. `--tag`도 반복해 좁힐 수 있습니다. 기본 결과는 `verified`와 `pending`이며 `superseded`는 명시적으로 요청할 때 보여 줍니다. 결과의 안정적인 ID로 상세 항목을 조회합니다.

## 기록 형식

최상위 `schema_version`은 현재 `1`, `entries`는 항목 배열입니다. 항목은 다음 필드를 가집니다.

| 필드 | 의미 |
|---|---|
| `id` | 영문 소문자·숫자·하이픈의 고유 ID. 참조에 사용하므로 재사용하지 않음 |
| `kind` | `decision`, `pitfall`, `limitation`, `workflow` |
| `status` | `verified`, `pending`, `superseded` |
| `title`, `summary` | 검색할 짧은 제목과 결론. 제한·남은 조건도 명시 |
| `tags` | `combat`, `save`, `web`, `art`, `deployment` 등 검색 분류 |
| `checked_on` | 실제 확인한 ISO 날짜 `YYYY-MM-DD`. pending도 마지막 조사 날짜를 기록 |
| `context` | 확인 당시 버전·플랫폼·대상 커밋 등의 문자열 맵 |
| `sources` | 저장소 루트 기준 파일 경로 또는 영구 HTTPS URL. 하나 이상 |
| `supersedes` | 선택 필드. 이 항목이 대체한 과거 항목의 ID 목록 |

`verified`는 특정 조건에서 확인했다는 뜻입니다. 이미 재현한 실패는 verified로 기록하고, 해결·실기기 확인이 남은 제약은 pending으로 분리합니다. 오래된 항목을 새 엔진·계정·정책에도 그대로 적용하지 않습니다.

`check`는 필수 필드·상태·날짜·중복 ID·대체 참조·로컬 근거 경로를 검증합니다. 외부 URL의 가용성·내용·최신성은 검사하지 않습니다. 검사 성공만으로 `checked_on`을 변경하지 않습니다.

## 갱신 규칙

1. 먼저 검색해 같은 항목을 갱신합니다. 같은 설명을 새 문서에 복제하지 않습니다.
2. 새 결론은 재현 검사·공식 문서·CI 등의 근거를 연결합니다. 실행했다고 주장하는 결과는 해당 버전과 범위를 적습니다.
3. 결론이 달라졌으면 요약·날짜·적용 조건·근거를 갱신합니다. 별도 결정으로 대체하면 이전 상태를 `superseded`로 표시하고 새 항목에서 `supersedes`로 연결합니다. Git 이력이 과거 내용을 보존합니다.
4. 반복할 작업 방법은 프로젝트 스킬로 옮기고 이 DB에서는 스킬을 참조합니다. 공식 설정 값은 원본 파일을 참조합니다.
5. `python tools/knowledge.py check` 후 같은 변경으로 커밋합니다. CI에서도 검사합니다.

토큰·개인정보·서명된 임시 URL·대화 전문은 저장하지 않습니다. 외부 스킬 원문의 출처와 해시는 [.agents/skills/upstream.json](../.agents/skills/upstream.json)에 별도로 유지합니다.

## 다른 프로젝트로 가져가기

[재사용 지식 묶음](../reusable/game-production-kit/README.md)에 현재 축적한 내용의 일반 원칙을 스킬 3종·사례집·빈 템플릿으로 정리했습니다. 원본 46항목의 당시 상태와 근거는 고정 커밋 스냅샷으로 추적합니다. 새 프로젝트에는 필요한 스킬 폴더 전체를 복사하고 실제 버전·저장 경로·자산 축·예산 등을 채운 뒤 `pending`에서 재검증합니다. 이 프로젝트의 `verified`나 인증/실행 권한을 그대로 승계하지 않습니다.

[ZIP](../reusable/game-production-kit.zip)과 [SHA-256](../reusable/game-production-kit.zip.sha256)도 함께 보관합니다. ZIP은 전체 게임 저장소를 복사하지 않고 사용할 수 있습니다.

```bash
python reusable/game-production-kit/scripts/package.py --check
python reusable/game-production-kit/scripts/package.py --output build/knowledge/game-production-kit.zip
python reusable/game-production-kit/scripts/package.py --verify build/knowledge/game-production-kit.zip
```

묶음 자체의 재현/검사는 Python 표준 라이브러리만 사용합니다. 게임 엔진 검사와 별개로 실행할 수 있습니다.
