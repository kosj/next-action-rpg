# v0.1.11 조명·품질·근사 지면 표현 검증

2026-11-01 UTC. baseline은 공개 v0.1.10/a07f91db다. **후보002의 실제 q0/q1 정지 전투 화면을 조명·근사 접지 prototype 범위에서 채택했다. 최종 frozen source의 native508/0·Python51·Web/Windows export를 통과했고 브라우저·clean CI·공개/릴리스 판정은 pending**이며, [제작 경계](../../ENVIRONMENT_LIGHTING_SLICE.md)를 따른다. 로컬 빌드는 dirty0.1.11·a07 preview이며 clean release로 표시하지 않는다.

| gate | 현재 근거/조건 | 상태 |
| --- | --- | --- |
| 품질 모드 의미 | HUD0균형/1성능, Game의 실제 scale/shadow flag; 기존 q1-only 영상의 범위 | 코드 대조로 의미 확인; 역전 버그 해석 기각 |
| renderer 지원/ambient 혼합 | [6개 공식 원문 bytes/SHA·HTTP/TLS·읽기 구간](renderer-evidence.json), tone mapper dispatch·C++/shader ambient 구성 대조 | source capability 및 실제 native runtime/raster 확인; 기능별 비용·실기기 성능 별도 |
| 새 key/fill/sky/reflection/fog | [후보002 원본·기각001·검수 경계](lighting-review/README.md), postprocess 지원과 활성화·비용 구분 | 실제 q0/q1 전투 화면의 prototype 범위 채택; 최종 native 통과, Web·성능 별도 |
| 품질 역할과 전환 | `SanctuaryKey` 역할, q0→q1→q0 flag/scale 및 key<1/fill>1, fill OFF | [최종 frozen native508/0](native-final-checkpoint.json); source9개 해시 일치 |
| q1 근사 지면 ellipse | 실제 layer1 ray·normal/높이/no-hit·cache/노드 한도·q0중복 방지 | 최종 b1 source native fixture 통과; actual12physics frame/정지 질의1회/표시7개. 정지 raster의 근사 접지만 채택 |
| source/품질별 원본 raster | [8원본 SHA·shot별 runtime·짝 조건](paired-capture-checkpoint.json), baseline001/후보002 × q0/q1 × fight/overview, 실제1280×720 | baseline64.096초/후보00253.105초, engine오류 없음. root는 q0/q1 fight 직접 검수·제한적 채택; 담당자는 q0 overview도 검수 |
| 촬영 뒤 관측용 telemetry | [촬영/최종6파일 bytes/SHA](post-capture-telemetry.json), Game/HUD/ActorVisual 변경, Sanctuary/grounding/shader 동일 | 촬영 source 전체와 최종 source의 exact 일치를 주장하지 않음; 최종 native/브라우저는 별도 |
| 핵심 source 보존 | [baseline과 같은10개 critical 파일](source-preservation.json): camera/strike/공격데이터/player/enemy/차지데이터·curve/배우·무기 GLB | 선택한10파일 bytes 동일; native 계약 통과. 모든 미기재 파일·플랫폼의 동일성을 주장하지 않음 |
| source 고정 native·Web/Windows | [닫힌 최종 native/Python 로그와9source](native-final-checkpoint.json), [로컬 export](local-preview-build.json) | native508/0·Python51/0·build exit0. rawWeb146,543,039B/14files<150MB; Windows export만 검증 |
| 최종 source 브라우저 | source56개 provenance, 실제 품질/grounding·저장·재시작·오류 수 | pending; 촬영 뒤 telemetry를 실제 브라우저에서 별도 검증 |
| clean CI·Pages·릴리스 | 최종 커밋·Actions·실제 공개 runtime·다운로드 파일 | pending |
| 연속 AV·실기기·AAA | 실제 목표 기기·모션/표면/공간 전체 검수 | pending |

조명 fixture는 실제 Game의 표시 장면을 통제한 것으로 실제 입력을 재현한 전투 take가 아니다. Linux Compatibility native q0의 scale1.0과 Web q0의.8/DPR 정책, shadow getter와 그림자가 보이는 실제 픽셀, 원본 파일 용량과 상주 GPU 비용을 각각 기록한다. 과거 native486/브라우저 통과나 이번 source field 값만으로 새 장면을 승인하지 않는다.

실제 결과별 source/frozen input·renderer/adapter·위치/pose/camera·품질·runtime light/env·rawPNG bytes/SHA·종료 상태와 발견 결함을 보존한다. 채택/기각은 같은 조건의 원본에 근거한다. 최종 묶음은 카탈로그·근거 source snapshot을 먼저 커밋한 뒤 다음1.4.5를 그 실제 Git object에 고정한다. 공개된1.4.4를 덮어쓰지 않는다.
