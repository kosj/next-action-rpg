# v0.1.10 활성 동작·칼날·표현 검증 기록

2026-11-01 UTC. **로컬 native482/0·Web/Windows preview 확인 / 최종 skin·시각·브라우저·공개/AAA pending**. 시작점은 v0.1.9/`1e524b1275c6c55d3020ea5c3122afbb8db403e9` 이후 dirty 구현이다. [제작 계약](../../COMBAT_MOTION_POLISH_SLICE.md)·[source/native 범위](source-review.json)와 원문을 구분한다. 실제 앱 버전은0.1.10이다.

| gate | 현재 확인 범위 | 남은 판정 |
| --- | --- | --- |
| 새 Hero007·원본 보존 | [manifest](../../../art_source/production/candidates/lyra-fury-001/manifest.json),body/rest/skin/material/이미지·기존 BIN·unrelated clip 보존 보고 | 실제 import/source cache와 같은 판본인지 확인 |
| active 팔 raw 수치 | [raw audit](../../../art_source/production/candidates/lyra-fury-001/raw-motion-audit.json),53본/동일60Hz 전체local/global peak 감소 | 누적 axial twist·실제 skin/변형·front/반대3quarter·key/midpoint·연속1x |
| 곡선 출처/파일 pin | 91표본·.002초·.34–.52초,GLBf2ed…/curve601a…·resource pin 정적 일치 | 실제 imported markers·scale/floor/큰delta·첫 engine receipt |
| early loaded contact | 006기하거부→007초기.614684m>.52m;raw첫LUT.354초 | [실제close receipt](native-contact.json)는.358초·hilt0·1회69.3. 기하예측과 실제값을 구분;화면/skin은별도 |
| Hero-only broadblade | [raw파생](../../../art_source/production/weapon_profiles/hero-broadblade-001/derivation.json)·[native](native-weapon.json),factor1.8·atlas0B·PBR surface공유 | native triangle대응20.94µm/100µm기준;UV오차는정규화좌표. 장착피부/시각승인pending |
| VARCO twohand 참고 | [sanitized metadata](varco-reference.json),공식0point1후보·구조/공통원점이동 raw검사 | reference-only;정규화/retiming/양손그립·시각·runtime 채택·권리 별도 |
| 카메라/잔상/impact | [native fixture](native-feedback.json)의투영/mesh/수명/중단확인 | 실제화면/skin·UI가림·연속AV/기기/AAA별도 |
| native 전체·Web/Windows | [native482/0](native-runtime.log),Web원본146513443B/150MB·WebZIP115767875B/Windows143609182B preview | dirty source;최종브라우저/cleancommit배포와별도 |
| 실제 브라우저·full 여정 | pending | 현재 새source의 실제 입력/저장/접촉 원문 |
| clean CI·공개/릴리스 | pending | 이후 최종 커밋/Actions·공개 빌드·파일 결과 |
| 연속1x AV·청취·실기기·AAA | pending | 기능·raw수치·정지표본과 별도 승인 |

[현재 marker/native](native-alignment.json)는 Hero f2ed/curve601a를 실제로 대조했다. Grip.066516mm/Tip.303980mm·명목발.015378mm이다. [독립 robust join](independent-raw-review.json)은 normalized quaternion shortest 방법으로53본최대.329761mm/.000581324°,held→release0을 기록한다. 저작도구의 다른 float각도값을 섞지 않는다.

[국소 skin](skin-midpoint.json)은1712표본에서 전체최대신장이 좋아져도2054edge가1mm이상 새로 악화됨을 보였다. charge.296초 왼팔꿈치 same-edge envelope는−14.607→17.948mm,차이+32.555mm다. [선택12개 still](../../../art_source/production/candidates/lyra-fury-001/skin-review/README.md)은 뚜렷한새붕괴를보지못해runtimeQA잠정채택했다. 공개대표6장/판정은유한범위이며2054개수치·전체skin/양손·연속1x/AAA미승인은유지한다.

[첫native실패](native-first-failure.log)는 material부착 계약·naive index/order/압축오차 fixture·feedback타입parse문제였다. 수정후 두 번째482/0이며 raw/접촉기준을 넓혀 숨기지 않았다.

007이 stage된 사실과 실제 importer/native가 이를 실행한 사실은 구분한다.006/007·기하 예측/실제 receipt·source-only 표현/관찰한 화면을 섞지 않는다. 실패한 초기 자세를 phase gate·피해 지연·완화한 threshold로 숨기지 않는다. raw 팔 peak 감소는 공학적 guard이며 AAA 비율이 아니다.

현재 [이전006 기각 원문](../../../art_source/production/candidates/lyra-fury-001/rejected-motion-summary.json)을 보존한다. 실제 결과가 오면 원문 로그/asset/curve/fixture 해시와 관찰 범위를 추가하며 이전v0.1.9의 통과를 새 source로 승계하지 않는다. source commit 전에는 미래 source pin을 만들지 않으며 kit version/provenance/ZIP은 별도 절차로 갱신한다.
