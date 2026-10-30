# 대표 구간 제작 입력

이 폴더는 리라·근접 수호병·순례자 전투 공간의 **제작 입력·계약과 실제 생성 후보**를 관리합니다. JSON의 `planned`·`pending` 상태는 생성·반입·품질 확인을 완료했다는 뜻이 아닙니다. 생성된 2D 참조와 실제 게임용 3D 자산도 구분합니다.

| 파일 | 용도 |
|---|---|
| [asset_specs.json](asset_specs.json) | 모델 3종의 정체성, 단일 이미지/정면/측면/후면 프롬프트, 부정 요소, PBR·크기·그립·좌표 계약과 파생물 목표 |
| [motion_contract.json](motion_contract.json) | 실제 게임 소스와 대조한 9개 기본 모션의 시간·루프·발 접지·이벤트·취소 계약 |
| [varco_lyra_plan.json](varco_lyra_plan.json) | 실제 ImageInput→Generate3D 설정과 리라 1건의 실행 결과. 업로드·서명 URL은 보관하지 않음 |
| [references/manifest.json](references/manifest.json) | 생성된 참조 PNG의 출처·해시·용도. 이 이미지는 2D 콘셉트이며 VARCO 모델이나 실제 게임 화면이 아님 |
| [candidates/lyra-001/manifest.json](candidates/lyra-001/manifest.json) | 실제 VARCO 원본·53본/3모션+RESET 파생 후보의 해시·비용·검수 상태 |
| [docs/ART_SLICE.md](../../docs/ART_SLICE.md) | 생성에서 실제 게임 화면까지의 검수 절차와 완료 기준 |

## 첫 실제 후보

리라 이미지를 사용자가 지정한 빈 Flow에 업로드하고 3D 후보 1건을 생성했습니다. 생성 당시 VARCO 설정은 `PRIVATE`, 메시 생성은 200포인트였습니다. 완료 task를 별도 입력 노드에 고정한 뒤 0포인트 리깅과 0포인트 대기·조깅·달리기 샘플을 만들었으며 추가 구매·유료 재생성은 없습니다.

- [source.glb](candidates/lyra-001/source.glb)는 수정하지 않은 8만 삼각형 원본이며 스킨·클립이 없습니다. [정면](candidates/lyra-001/front.png)·[측면](candidates/lyra-001/side.png)·[후면](candidates/lyra-001/back.png)은 실제 원본의 REST 렌더입니다.
- [lyra-locomotion.glb](candidates/lyra-001/lyra-locomotion.glb)는 53본·스킨 1개와 `idle`/`walk`/`run`/`RESET`을 포함하는 별도 검수용 파생물입니다. `walk`는 stock 조깅, `run`은 stock sprint에서 왔습니다. `RESET`은 bind pose이며 네 번째 동작이 아닙니다.
- Blender 4.3.2에서 공통 원점 차이를 입증해 정규화한 뒤 키 1.82m·REST 바닥 0으로 맞췄습니다. 시작·중간·끝 표본의 포즈 오차는 최대 7.1e-7m이고 원본 4개 SHA는 불변입니다. [후처리 보고서](candidates/lyra-001/preparation.json)에 근거를 보관합니다.
- 8만 삼각형은 Windows 6.5만·웹 3.2만 목표를 모두 넘습니다. 리토폴로지/LOD와 손·어깨·의상 정리, 전투 6모션, BoneMap·루프·발 접지·실제 게임 화면 검수가 남아 있습니다. 현재 게임의 기본 피벗 캐릭터를 이 후보로 교체하지 않았습니다.

## 생성에 사용할 입력

캐릭터는 `reference_prompts.single_view`와 하나의 전신 이미지로 image-to-3D 후보를 만듭니다. 정면/측면/후면 프롬프트는 같은 인물과 의상의 일관성을 확인할 자료입니다. 여러 인물이 나오는 턴어라운드 시트를 단일 인물 모델 생성에 그대로 넣지 않습니다. 무기는 몸체와 분리해 생성·반입하고 오른손 소켓에 부착합니다.

환경의 `sanctuary-courtyard-target.png`는 화면 톤과 구도를 정하는 목표 이미지입니다. 전체 그림을 거대한 단일 메시로 변환하지 않습니다. 기둥·문·포장·파편·화로별 단독 입력을 만들고 기존 방의 충돌·문·진행 조건에 맞춰 조립합니다.

이 JSON은 MCP 도구의 요청 스키마가 아닙니다. OAuth와 실제 도구 발견 후 지원하는 Flow 노드·모델·입력 형식으로 번역합니다. 생성할 계정·Flow·작업량·라이선스를 확인하고 실행 결과가 생겼을 때만 실제 후보 경로와 출처를 기록합니다. 완료된 리라 결과는 위 후보 manifest와 실행 기록으로 연결하며, 다른 두 자산의 `planned` 상태는 유지합니다. 토큰이나 만료되는 인증·다운로드 URL은 넣지 않습니다.

## 원본과 후보 분리

- 생성 후보는 작업용 `build/art-candidates/<asset-id>/<candidate-id>/`처럼 기존 게임 파일과 분리한 곳에서 검수합니다.
- 선택한 원본과 수정 이력은 `art_source/`에 관리하고, 통과한 실행 자산만 별도 게임 경로에 반입합니다.
- 기존 `game/assets/models/{hero,sentinel,boss,keeper}.glb`를 후보 파일로 바로 덮어쓰지 않습니다. 현재 도형 모델은 게임 회귀 검사의 기준입니다.
- `derived_profiles`의 삼각형·재질·텍스처 값은 첫 제작 예산이며 측정 결과가 아닙니다. 최종 여부는 변형·화면·프레임 시간까지 확인해 판단합니다.

## 모션의 원본

공격 값은 `AttackData`의 기본값에 `.tres`의 덮어쓴 값을 합쳐 확인했습니다. `motion_contract.json`의 `source_commit`은 조사한 소스 스냅샷을 가리킵니다. 게임 데이터를 바꾸면 기본값까지 다시 대조합니다. 이름이 같은 클립이 존재하는 것만으로 타이밍·좌표·스킨 품질을 통과한 것으로 간주하지 않습니다.

## 반복 검사

```bash
python tools/check_art_production.py --json
python tools/inspect_glb.py game/assets/models/*.glb --require-embedded
python tools/inspect_glb.py art_source/production/candidates/lyra-001/lyra-locomotion.glb --require-embedded --require-skin --require-clip idle --require-clip walk --require-clip run --require-clip RESET
```

명령은 저장소 루트에서 실행합니다. 첫 검사는 참조/후보 원본·파생 해시·명세와 실제 공격 수치의 일치를 확인하고, GLB 검사는 구조와 명시한 skin/clip 요구 조건을 확인합니다. 최종 캐릭터 후보에는 `--require-skin`과 필요한 `--require-clip`을 추가합니다. 현재 피벗 모델은 이 최종 기준에 실패하는 것이 정상입니다. 얼굴·의상·변형·발 접지·실제 화면·성능 검수는 별도로 수행합니다.

실제 검수 렌더는 `tools/render_glb_review.py`, 같은 리그의 3개 locomotion 결합은 `tools/prepare_character_candidate.py`를 사용합니다. 두 도구 모두 별도 Blender 배경 프로세스에서 새 출력에만 기록하며 원본을 덮어쓰지 않습니다. 원점 정규화는 본·메시·웨이트 관계와 표본 포즈를 확인하는 명시적 옵션이며, 정적 크기/바닥 정렬을 동적 root-motion 검수로 간주하지 않습니다.
