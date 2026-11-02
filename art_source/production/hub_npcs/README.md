# 에린·로엔 NPC 후보 제작 기록

2026-11-02에 이 프로젝트의 독자 전신 참조 2장으로 VARCO 모델을 각각 한 번 생성했다. 기존 Flow의 67개 노드·46개 연결은 보존하고 전용 입력/작업 12개 노드와 6개 연결을 추가했다. 실행 응답의 포인트는 모델 400점(200점씩), 리그 0점, 대기 모션 0점이다. 추가 구매·유료 재생성·기존 유료 작업 재실행은 없었다. 계정 잔액/최종 청구 내역은 현재 MCP에서 제공되지 않는다. 설정·작업 ID·원본 해시는 [provider-run.json](provider-run.json)에 있다.

모델은 `PRIVATE`, 16,000개 삼각형, 알베도/ORM 1k로 생성됐다. 노멀맵은 요청 1k와 달리 실제로 2k가 반환돼 파생물에서 1k 비색상 다운샘플·벡터 정규화를 수행했다. 각 캐릭터 원본 모델·리그·stock idle은 `candidates/{erin,roen}-001/`에 별도 보존했다. 대기 동작은 VARCO `standing_idle_1_looping`의 in-place 리타게팅이며 프로젝트가 독자 저작한 동작이 아니다. 실제 권리 검토 범위와 접근 한계는 `docs/validation/v0.1.13/rights-evidence/review.json`을 참조한다.

공급자 idle 원본은 21개 LINEAR sampler 모두 마지막 시간값이 두 번 반복돼 엄격 glTF 검사에서 실패했다. 원본은 `source/idle-source.glb`, 실패 근거는 `source/raw-idle-strict-failure.json`으로 보존했다. `canonicalize_idle_times.py`는 정확히 마지막 중복 하나만 있고 마지막 값이 첫 루프 자세와 byte 단위로 같을 때만 앞의 중복을 제거한다. 내부 중복·비유한 값·다른 종료 패턴·잘못된 경계는 거부한다. `idle-canonical-validation.json`은 강화된 검사로 다시 계산한 결과가 기존 canonical GLB와 같음을 증명한다.

재현 순서는 다음과 같다. 기존 출력은 덮어쓰지 않는다.

```sh
python3 art_source/production/hub_npcs/canonicalize_idle_times.py --input art_source/production/candidates/erin-001/source/idle-source.glb --output NEW_CANONICAL.glb --report NEW_REPORT.json
/usr/bin/blender -b --factory-startup --python art_source/production/hub_npcs/prepare_idle_npc.py -- --recipe art_source/production/hub_npcs/erin.json
python3 tools/inspect_glb.py art_source/production/candidates/erin-001/erin-idle.glb --require-embedded --require-skin --require-clip idle --require-clip RESET
python3 -m unittest discover -s art_source/production/hub_npcs -p 'test_*.py' -v
```

Blender 4.3.2 파생물은 `idle`(10.1667초)과 bind `RESET`만 포함하며 53개 bone을 유지한다. 에린 1.70m·로엔 1.82m의 REST 높이와 발바닥 0을 재반입 검사했고, wrapper가 이미 −Z 방향을 적용하므로 presenter는 추가 PI 회전을 적용하지 않는다. 실제 121개 idle 발 샘플은 에린 최대 18.19mm·로엔 20.29mm의 수평 변화와 소량의 바닥 관통/뜸을 보였다. REST 정규화는 접지·IK·지형 대응 완성을 뜻하지 않는다.

에린 001의 로브 앞면 두 검은 패치는 실제 clay/flat-normal 진단에도 남았다. 002는 실제 skin ray를 Blender와 대조한 뒤 같은 triangle을 REST로 옮겨 설계한 국소 수정 후보다. UV·topology·skin·rest·모션·텍스처와 무관한 bytes는 보존한다. 초기 잘못된 좌표 가정은 GLB를 쓰기 전에 거부했고 `rejected-setup-summary.json`에 기록했다. 002의 자동 채택은 금지하며 실제 비교 화면과 TBN/수입 게임 검사를 통과하기 전까지 001의 런타임 바이트를 유지한다.

참조 그림, 구조 검사, 유한 스튜디오 화면은 서로 다른 근거다. 얼굴/손/로브 연속 변형, 실제 게임 시인성, 웹 150MB 예산, 브라우저, 실기기, 최종 AAA 품질은 각 최종 검증 결과로 판단한다.

003은 표면 법선 교정과 제한된 UV clone을 마친 임시 런타임 후보이다. 002의 남은 두 잘못된 surface NORMAL 면만 조사해 13개 NORMAL 행을 추가 교정한 `normal-source.glb`를 만들었다. POSITION·bone pose·UV·모션·텍스처는 이 단계에서 바뀌지 않는다. 큰 법선 회전 수치는 관절/손목 회전 수치가 아니다. 경계 22면을 REST+idle 5개 시각에서 검사했고 새 normal/face 음수는 없지만 일부 면은 grazing 방향에 가까워 실제 화면 검수가 필수다.

`clone_robe_texture.py`는 Blender image datablock으로 해당 로브 chart만 인접 ivory weave에서 clone한다. `paint-mask.json`은 glTF PNG top-left 픽셀 좌표를 기록하며 Blender 버퍼 접근에서만 행을 반전한다. 얼굴/손의 UV overlap은 0이다. 우선 albedo·ORM.R AO·normal의 같은 UV 값을 진단하고, 실제 artifact가 확인된 채널만 선택한다. ORM.G roughness/ORM.B metallic과 허용 mask 밖의 모든 pixel은 저장·재로드 뒤 8bit 단위로 같아야 한다. 원래 3개 image index/name과 mesh/skin/UV/clip/material 선언을 유지해 추출 PNG roster가 늘어나지 않게 한다. 전역 atlas 재생성·해상도 하향·유료 모델 재생성은 수행하지 않는다.

실제 진단에서 AO.R는 대상/인접 천이 모두 거의 1이어서 ORM 전체를 그대로 보존했다. 큰 gray 패치 chart만 인접 ivory weave에서 albedo 378픽셀·normal 369픽셀을 clone했고 383개 허용 픽셀 밖의 RGBA8은 모두 같다. 얼굴/손·UV·skin·clip·image 3개 이름/index도 유지한다. 임베디드 PNG를 독립 Blender 프로세스로 재로드해 확인한 근거는 `candidates/erin-003/embedded-pixel-audit.json`이다. 최종 후보 SHA는 `801f50dff21cc071ffca61673595948c750152a85fe03764627570ec8f347c63`이며 root가 실제 게임 검사용 임시 반입만 승인했다. 작은 청회색 꼭지·dark tail·깊은 slit가 남아 있어 완전히 수리된 옷이나 AAA 품질로 표시하지 않는다. 실제 게임 q0/q1·최종 native/export·웹 예산·브라우저 검증은 별도 결과를 기다린다.
