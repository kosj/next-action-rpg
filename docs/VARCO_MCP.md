# VARCO 3D 공식 MCP 연결

확인일: 2026-10-30. VARCO 3D는 공식 Streamable HTTP MCP 서버와 Codex/Claude 연결 문서를 제공합니다. 현재 세션의 미연결 상태를 서비스의 연결 불가로 해석하지 않습니다.

## 공식 근거와 연결 주소

- [공식 MCP 설정 가이드](https://3d.varco.ai/mcp/setup.md)
- [Codex 또는 Claude에서 연결하는 공식 안내](https://3d.varco.ai/docs/blog/2026-07-14-connect-varco-3d-to-codex-or-claude-with-one-prompt)
- [Claude 앱의 커넥터 설정 예시](https://3d.varco.ai/docs/blog/2026-07-14-connect-varco-3d-mcp-to-claude-app)
- 서버 URL: `https://3d.varco.ai/api/mcp`

초기 세션의 도구 목록과 플러그인 검색에는 VARCO가 없었지만 공식 Codex 클라이언트에 `varco-3d` 서버를 등록하고 OAuth에 성공했습니다. 실제 계정/가격·Flow 목록·노드 카탈로그 호출과 프로젝트의 클라이언트 도구를 통한 Flow 조회까지 확인했습니다. 이 연결은 현재 클라우드 Codex 클라이언트 기준이며 사용자의 다른 앱 설정까지 완료했다는 뜻은 아닙니다. 새 환경에서는 실제 도구 발견과 인증 상태를 다시 확인합니다.

## Codex 클라이언트 설정

공식 설정 가이드의 명령은 다음과 같습니다. 연결할 Codex 클라이언트의 환경에서 실행합니다.

```bash
codex mcp add varco-3d --url https://3d.varco.ai/api/mcp --oauth-resource https://3d.varco.ai/api/mcp
codex mcp login varco-3d
```

이 작업 환경에서는 Codex CLI 0.163.0으로 서버 등록·OAuth·실제 읽기 호출까지 검증했습니다. 클라우드의 CLI 설정과 사용자가 쓰는 앱의 커넥터 설정이 같은 환경이라고 가정하지 않습니다.

공식 안내에 따라 OAuth URL이 나타나면 사용자에게 보여 주고 사용자가 직접 승인하도록 합니다. 토큰을 읽거나 채팅·저장소에 복사하지 않습니다. MCP 엔드포인트에 curl/fetch로 직접 요청하거나 OAuth 교환을 수동 구현하지 않습니다. 클라이언트가 인증과 토큰 보관을 담당합니다.

서버 등록 뒤에도 현재 대화에 도구가 나타나지 않으면 앱을 다시 시작하거나 새 대화에서 발견 여부를 확인합니다. 플러그인 설치 완료, OAuth 완료, 도구 발견, 실제 호출 성공은 각각 결과를 확인합니다.

클라우드처럼 사용자의 브라우저가 클라이언트의 localhost callback에 접속할 수 없는 환경에서는 공식 `codex mcp login varco-3d --no-browser`를 사용합니다. 사용자가 승인 후 받은 전체 callback URL을 클라이언트의 숨김 입력에 그대로 전달합니다. PTY의 실제 Enter 입력은 `\r`이며 LF만 보낼 때 입력이 확정되지 않을 수 있습니다. 일회성 링크가 만료되면 새 클라이언트 인증 절차를 시작하고 이전 링크를 재사용하지 않습니다. callback·인증 코드를 파싱하거나 수동 교환하지 않습니다.

## 프로젝트의 재사용 클라이언트

```bash
python tools/varco_mcp.py catalog > build/varco-catalog.json
python tools/varco_mcp.py call list_flow_sessions --arguments build/empty-arguments.json > build/varco-flows.json
```

`empty-arguments.json` 내용은 `{}`입니다. 이 도구는 **공식 `codex app-server --stdio`**의 발견/도구 호출 API를 사용합니다. MCP 서버에 직접 HTTP 요청을 보내거나 인증 파일을 읽지 않으며 모델 추론 turn 없이 ephemeral thread에서 명시한 도구만 호출합니다. 발견한 도구 이름·필수 인자를 확인하고 전체 인자 스키마 검증은 서버가 담당합니다. 예상치 못한 대화형 승인 요청은 자동 승인하지 않습니다. 이 API는 Codex 0.163.0에서 확인한 experimental API이므로 클라이언트 업데이트 시 호환성을 다시 검사합니다.

성공 결과에는 계정·Flow 내용이나 일시적인 다운로드 URL이 포함될 수 있어 `build/` 또는 임시 디렉터리에만 보관합니다. 인증 정보·콜백·계정 요금제·임시 URL을 지식 DB나 소스에 옮기지 않습니다. 첫 생성 계획은 [varco_lyra_plan.json](../art_source/production/varco_lyra_plan.json)에 있습니다. 리라 참조 이미지는 구체적인 사용자 승인을 받은 뒤 실제 업로드에 성공했으며 3D 생성은 새 대상 Flow를 확인한 뒤 실행합니다. 이전 결과가 있는 Flow를 빈 Flow로 간주하거나 조용히 수정하지 않습니다.

## 첫 호출과 Flow 선택

1. 계정과 대상 Flow를 식별하는 읽기 전용 호출부터 시작합니다. 도구 이름과 인자는 연결 후 발견한 실제 스키마를 사용합니다.
2. 공식 라이브 `setup.md`는 모든 도구가 열린 에디터 없이 동작하며, `flowId`를 생략하면 브라우저에서 가장 최근 열었던 Flow에 적용된다고 설명합니다. 7월 블로그의 열린 워크플로 안내와 구분하고, 작업 대상을 명확히 하도록 `flowId`를 확인합니다.
3. 새 검수용 Flow에 입력 노드 하나를 만드는 등 작은 변경으로 연결을 확인합니다. 기존 제작 Flow를 임의로 수정하지 않습니다.
4. 사용할 생성 모델·입력·생성량·크레딧과 사용자 요청 범위를 확인한 뒤 실제 생성을 실행합니다. 인증 성공을 유료 생성의 완료나 품질 검증으로 간주하지 않습니다.
5. 생성 결과·재질·리그·모션을 [아트 파이프라인](ART_PIPELINE.md)의 검수 절차로 넘깁니다.

MCP는 VARCO Flow를 조작하는 경로이고, [Blender Bridge](https://3d.varco.ai/docs/blog/2026-03-19-varco-3d-bridge-for-blender)는 자산을 DCC로 전달하는 경로입니다. 용도를 구분하고 Godot 반입에는 최종 GLB와 프로젝트 래퍼 씬을 사용합니다.
