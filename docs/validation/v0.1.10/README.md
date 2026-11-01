# v0.1.10 활성 동작·칼날·표현 검증 기록

2026-11-01 UTC. **최종 native486/0·Web/Windows preview·정상 종료한 실제 Game capture와 유한 프레임의 프로토타입 화면 개선을 확인했다.** 연속1x AV/청취·실기기·AAA와 최종 clean CI/브라우저/공개는 별도다. 시작점은 v0.1.9/`1e524b1275c6c55d3020ea5c3122afbb8db403e9`다. [제작 계약](../../COMBAT_MOTION_POLISH_SLICE.md)·[초기 source 범위](source-review.json)와 source별 원문을 구분한다. 앱 버전은0.1.10이다.

| gate | 현재 확인 범위 | 남은 판정 |
| --- | --- | --- |
| 새 Hero007·원본 보존 | [manifest](../../../art_source/production/candidates/lyra-fury-001/manifest.json),body/rest/skin/material/이미지·기존 BIN·unrelated clip 보존 보고 | 실제 import/source cache와 같은 판본인지 확인 |
| active 팔 raw 수치 | [raw audit](../../../art_source/production/candidates/lyra-fury-001/raw-motion-audit.json),53본/동일60Hz 전체local/global peak 감소 | 누적 axial twist·실제 skin/변형·front/반대3quarter·key/midpoint·연속1x |
| 곡선 출처/파일 pin | 91표본·.002초·.34–.52초,GLBf2ed…/curve601a…·resource pin 정적 일치 | 실제 imported markers·scale/floor/큰delta·첫 engine receipt |
| early loaded contact | 006기하거부→007초기.614684m>.52m;raw첫LUT.354초 | [실제close receipt](native-contact.json)는.358초·hilt0·1회69.3. 기하예측과 실제값을 구분;화면/skin은별도 |
| Hero-only broadblade | [raw파생](../../../art_source/production/weapon_profiles/hero-broadblade-001/derivation.json)·[native](native-weapon.json),factor1.8·atlas0B·PBR surface공유 | native triangle대응20.94µm/100µm기준;UV오차는정규화좌표. 장착피부/시각승인pending |
| VARCO twohand 참고 | [sanitized metadata](varco-reference.json),공식0point1후보·구조/공통원점이동 raw검사 | reference-only;정규화/retiming/양손그립·시각·runtime 채택·권리 별도 |
| 이전 카메라/잔상/impact | [native fixture](native-feedback.json)의 nominal 투영/mesh/수명/중단 확인 | actual target/contact 가림을 검출하지 못함. 새 카메라/brief core의 실제 projection/raster는 별도 |
| 이전 native 전체·Web/Windows | [native482/0](native-runtime.log),Web원본146513443B/150MB·WebZIP115767875B/Windows143609182B preview | `74d3a14`/`6144593`의 이전 카메라 범위;새 수정의 통과로 승계하지 않음 |
| 최초 actual gameplay capture | [attempt4 진단](diagnostics/initial-gameplay-occlusion/README.md):624틱/10.4초,실제69.3 접촉1회·pause5표본·잔상4표본/12tri | 주인공이 적/접촉점을 가림;ObjectDB2/resource1 종료오류. 기능 통과와 clean capture 실패를 분리 |
| 첫 higher-view/core | [native486/0](native-readability.log)·[feedback](native-feedback-readability.json),head 분리1.723823배/core27.0556px² | [실제 clean take](diagnostics/weak-camera-core/README.md)는 섬광이 약해 시각 기각;중심이 몸/무기에 묻혔다는 원인도 입증 안 됨 |
| 최종 camera/core native | [486/0 로그](native-visible-contact.log)·[feedback](native-visible-contact.json):head 분리1.993686배/core78.2599px²·반경.12m/75ms·기존 계약 | nominal projection/mesh API와 실제 raster를 따로 확인 |
| 최종 Web/Windows preview | [manifest/ZIP hash](visible-contact-preview.json),Web원시146517123B/150MB·WebZIP115769331B/Windows143610638B | dirty614head;최종 source/clean CI·브라우저·공개와 별도 |
| 최종 actual Game capture | [원본 영상/PNG/report/trace](native-gameplay/final/README.md),624frame/10.4초·69.3 한 번·pause5표본·오류0/WeakRefs0 | 선택 birth/+1/+2/+4에서 작은 국소 섬광/적 상체 구분 개선 채택;큰 도약/전체 AV/AAA 승인 아님 |
| 로컬 Web 집중 검사 | [trusted touch277.923초/errors0](focused-browser/SUMMARY.json),69.3 한 번·recoil.350000406m·최종HP72 | browser frozen pair 미관찰/native pause5표본은 별도;full 여정은 후속 gate |
| clean CI·공개/릴리스 | pending | 이후 최종 커밋/Actions·공개 빌드·파일 결과 |
| 연속1x AV·청취·실기기·AAA | pending | 기능·raw수치·정지표본과 별도 승인 |

[현재 marker/native](native-alignment.json)는 Hero f2ed/curve601a를 실제로 대조했다. Grip.066516mm/Tip.303980mm·명목발.015378mm이다. [독립 robust join](independent-raw-review.json)은 normalized quaternion shortest 방법으로53본최대.329761mm/.000581324°,held→release0을 기록한다. 저작도구의 다른 float각도값을 섞지 않는다.

[국소 skin](skin-midpoint.json)은1712표본에서 전체최대신장이 좋아져도2054edge가1mm이상 새로 악화됨을 보였다. charge.296초 왼팔꿈치 same-edge envelope는−14.607→17.948mm,차이+32.555mm다. [선택12개 still](../../../art_source/production/candidates/lyra-fury-001/skin-review/README.md)은 뚜렷한새붕괴를보지못해runtimeQA잠정채택했다. 공개대표6장/판정은유한범위이며2054개수치·전체skin/양손·연속1x/AAA미승인은유지한다.

[첫native실패](native-first-failure.log)는 material부착 계약·naive index/order/압축오차 fixture·feedback타입parse문제였다. 수정후 두 번째482/0이며 raw/접촉기준을 넓혀 숨기지 않았다.

[실제 접촉 PNG](diagnostics/initial-gameplay-occlusion/contact.png)는 기존 nominal body projection과 물리 cut AABB 검사만으로 화면 가독성을 승인할 수 없음을 보였다. [원문 report](diagnostics/initial-gameplay-occlusion/review.json)는 기능과 정상 종료를 나누며 최종 marker world 좌표가 이 take에 없다는 한계도 보존한다. [source/fixture/runtime 입력](diagnostics/initial-gameplay-occlusion/evidence.json)은 각각의 해시와 차이를 남긴다. 새 카메라 결과가 와도 이 실패를 소급 통과시키지 않는다.

camera `e97cbf03…`/impact `fc39d672…`/fixture `554198d5…`의 최종 native486/0은 오류·누수 marker0이다. 첫75mm/52ms/.06 core가 실제 raster에서 약해 명시적으로120mm/75ms/.18 art budget으로 수정했고 기능 threshold·피해 권한·실제 접촉점은 유지했다. [baseline](native-gameplay/baseline/README.md)·[최종 take](native-gameplay/final/README.md)와 원본 lossless 접촉/후속 프레임을 보존한다. 무음 논리1x 파일 생성과 유한 화면 채택은 연속 AV 시청/청취나 목표 기기 승인이 아니다.

[기존614 CI](diagnostics/old-camera-ci.json)·[run41312088764](https://github.com/kosj/next-action-rpg/actions/runs/41312088764)는 필수3job/전체 mobile954.339초/errors0으로 통과했어도 이전 카메라만 검증했다. 실제 화면 실패를 지우거나 새 카메라/core의 CI로 승계하지 않는다. 첫 higher-view preview는 [당시 hash](readability-preview.json)로 보존한다.

007이 stage된 사실과 실제 importer/native가 이를 실행한 사실은 구분한다.006/007·기하 예측/실제 receipt·source-only 표현/관찰한 화면을 섞지 않는다. 실패한 초기 자세를 phase gate·피해 지연·완화한 threshold로 숨기지 않는다. raw 팔 peak 감소는 공학적 guard이며 AAA 비율이 아니다.

현재 [이전006 기각 원문](../../../art_source/production/candidates/lyra-fury-001/rejected-motion-summary.json)을 보존한다. 실제 결과가 오면 원문 로그/asset/curve/fixture 해시와 관찰 범위를 추가하며 이전v0.1.9의 통과를 새 source로 승계하지 않는다. source commit 전에는 미래 source pin을 만들지 않으며 kit version/provenance/ZIP은 별도 절차로 갱신한다.

[실제 Game 비교 묶음](native-gameplay/README.md)은 원본 baseline/최종 무음 MP4·접촉/후속 PNG·전체 trace gzip과 입력 일정 대조를 연결한다.
