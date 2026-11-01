# v0.1.9 전신 무게 전달·피격 회수 제작 단위

기록일: **2026-11-01 UTC**. **로컬 native448/0·Python51/0·Web/Windows 패키지·fresh003 무음 캡처/유한 raster·실제 집중 브라우저290.733초/오류0을 확인했다.** 근거는 분석 커밋 `a98ef0758d9b4f722b74fbe899504aefcb032641` 이후 dirty 구현이다. [native/패키지](validation/v0.1.9/local-preview.json)·[캡처](validation/v0.1.9/native-motion/README.md)·[집중 브라우저](validation/v0.1.9/focused-browser/SUMMARY.json)는 각각의 범위로 확인한다. 이 로컬 기록 작성 시점의 최종 clean 커밋 CI·전체 여정·공개/릴리스는 pending이며 후속 PR/Actions 근거를 따른다. 연속1x AV·직접 청취·실기기·AAA도 pending이다.

## 목표와 근거의 범위

대표 범위는 리라의 `charge`·`charged_heavy`와 일반 근접 수호병의 `heavy_hit`이다. 준비의 큰 전신 실루엣, 몸통과 검으로 이어지는 힘의 방향, 관성을 받는 낮은 자세와 guard 복귀를 읽히게 하는 것이 목표다. 같은 카메라에서 효과를 끈 몸 동작과 효과를 켠 접촉을 비교하며, 새 효과의 수나 피해량으로 몸 동작의 무게감을 대신하지 않는다.

| 근거에서 확인한 것 | 이번 제작에 적용할 방향 | 아직 승인하지 않은 것 |
| --- | --- | --- |
| 공식 영상 표본에서 달라지는 어깨·몸 방향·검 면과 전신 높이, 준비/방출/후속 자세의 대비 | 골반·몸통의 선행과 검의 방출, 힘을 받아 낮아졌다가 회수하는 자세를 구별해 저작 | 참고 영상의 정확한 골반 선행 시간·실제 입력 지연·모든 프레임의 손/발 고정 |
| 강한 섬광 뒤 몸이 다시 드러나는 표본과 서로 다른 방향의 기술 | 준비·접촉 최고점·회복에서 몸과 적 예고가 다시 읽히는지 같은 거리에서 확인 | 광역 기술의 효과를 한 베기에 합치거나 근거 없는 지면 폭발을 추가한 품질 승인 |
| 다른 shot의 적·이미 떠 있는 적·컷 전환이 포함된 홍보 영상 | 같은 shot에서 관찰한 동작만 연결하고 우리 게임의 현재 조작 계약을 유지 | 전체 적의 새 launch·지형 파괴·편집 구간을 하나의 스킬 시간으로 해석 |

[원본 식별·검수 근거](validation/zeus-reference-2026-11-01/evidence.json)는 확보한 공개본·해시·직접 프레임과 provider 보고를 구분한다. encoded60fps는 실제 게임 성능이 아니다. 오디오 stream은 있지만 독립 청취를 하지 못했으므로 참고 음향의 정체·mix·정밀 동기는 provider-only다. 이 근거를 현재 게임의 정상1배속 AV·실기기·AAA 승인으로 승계하지 않는다.

## 보존할 게임 계약

아래는 제작에서 유지해야 할 계약이다. 현재 코드의 값 대조와 새 자산/동작을 실제 실행한 결과는 별도다.

| 항목 | 유지 대상 |
| --- | --- |
| 입력 | 기존 charge threshold `.65초`, hold/release·취소·공유 입력 경계와 hitstop 중 edge 버퍼 |
| 완충 동작 | startup/active/recovery `.34/.18/.54초`, 합계 `1.06초` |
| 이동 | 준비/active/회복 `0/3.2/0 m/s`, 막힘 없는 active 명목 이동 `.576m`; 실제 충돌·소비한 phase 구간 적분 유지 |
| 피해·강인도 | 업그레이드0에서 피해 `69.3`, poise `79.2`; 일반 적 HP95를 한 번에 처치하는 계약으로 바꾸지 않음 |
| 검·피해 구간 | Grip→Tip `1.19m`, 손잡이 쪽18% 제외한 `.9758m` 날 구간, 반경 `.12m`; 반구를 포함한 총높이·안쪽 중심축·projection 검증 유지 |
| 접촉 시계 | 확정 접촉 세부 시각과 최종 표시/양손·잔상 일치, 양측 hitstop 요청 `.075초` |
| 강피격 | `heavy_hit .48초`, recoil 요청 `.35m`; 실제 충돌 복구도 이동 예산에 포함하고 벽이 이동을 제한 |
| 다른 전투 결과 | 방패·보스 강인도·death/중단 우선순위, 한 swing/target의 중복 피해·effect 방지, miss의 contact0 유지 |

권한 있는 원본은 [완충 공격 리소스](../game/data/charged_heavy.tres), [AttackData](../game/scripts/core/attack_data.gd), [Player](../game/scripts/actors/player.gd), [Enemy](../game/scripts/actors/enemy.gd)다. 새 전신 자세는 표현을 바꾸며 피해·판정 거리를 시각 소켓에서 새로 결정하지 않는다. active 검 경로와 양손 정합은 보존해야 한다.

## 기존 자산 보존과 새 경로

v0.1.8의 source·기존 파생 GLB와 당시 보고서는 보존한다. 이번 출력은 별도 이름으로 생성하고 새 manifest에 변경한 clip·입력 SHA·도구/recipe와 출력 SHA를 남긴다. 기존 파일을 덮어써 이전 판본의 검증 근거를 바꾸지 않는다.

| 보존할 v0.1.8 입력 | 문서 작성 시 확인한 SHA-256 |
| --- | --- |
| `game/assets/models/production/lyra_impact_gameplay.glb` | `0aa78c46c0453f8286785ee937ef9388324dc4312bb076f5179934f08e44d57d` |
| `game/assets/models/production/sentinel_impact_gameplay.glb` | `6180967f4220651f5a9a343109e07bfab5831252c875170d008d17072d09c576` |

새 출력은 `game/assets/models/production/lyra_weight_gameplay.glb`와 `game/assets/models/production/sentinel_weight_gameplay.glb`이며 [profile 매핑](../game/scripts/actors/production_character_art.gd)은 이 경로를 사용한다. hero의20개 상태+RESET, sentinel의10개 상태+RESET 이름은 유지한다. 파일 설치와 경로 매핑은 최종 runtime·시각 채택 승인이 아니다.

| 현재 raw 후보 | 크기 | SHA-256 |
| --- | --- | --- |
| 리라 weight | 23,174,144B | `27fbed52e1e7011e66f4d0347827db7aa35cb035fbb2dd23df873de752fa1d83` |
| 수호병 weight001 (실패 이력·002로 대체) | 17,410,020B | `1efa1e1c92caeecc614ec3d48ee297c0fea58871cdc1fc0376510462e6f8a1df` |
| 현재 수호병 weight002 | 17,533,004B | `e7e2b5bd5d5d6dbf0e3ada3fe373c3bb8acbd4918ece0519a2e5c55417d5f619` |

[별도 저작 도구](../tools/author_weight_actions.py), [리라 recipe](../art_source/production/character_actions/lyra-weight.json)·[수호병 recipe](../art_source/production/character_actions/sentinel-weight.json)를 사용했다. [리라 authoring](../art_source/production/candidates/lyra-weight-001/authoring.json)·[수호병 authoring](../art_source/production/candidates/sentinel-weight-001/authoring.json)은 body JSON·기존 BIN prefix의 정확한 보존, 기존 source 불변과 교체한 animation 이름을 기록한다. 리라는 `charge/charged_heavy`, 수호병은 `heavy_hit`만 교체했다. 기존 source와 기존 impact 저작 도구를 덮어쓰지 않았다.

새 runtime만 export에 포함하도록 기존 impact GLB의 패키지 제외를 확인하되 저장소의 원본 파일은 보존한다. geometry·skin/named weights·rest·이미지/재질·기존 clip과 각 변경 clip의 보존/변경 경계는 실제 원문 감사로 증명한다. 선택적 고정밀 반입은 새 동작을 위한 것이며 기존 모든 clip의 불필요한 재표본이나 용량 증가를 숨기지 않는다.

## 실제 저작 표본과 기각한 후보

[리라 semantic 원문](../art_source/production/candidates/lyra-weight-001/semantic-review.json)과 [수호병 semantic 원문](../art_source/production/candidates/sentinel-weight-001/semantic-review.json)은 실제 raw GLB 재반입 포즈의 before/after 수치다. 아래 위치 delta는 해당 보고서의 raw 저작 좌표이며 게임 root의 실제 이동이나 terrain IK가 아니다.

| 표본 | 확인한 저작 변화 | 한계 |
| --- | --- | --- |
| 정지 charge 끝 | 골반 delta 약(-45,+60,-70)mm, 골반/흉부 회전차7.90°/15.55°, 좌/우 무릎 굽힘+12.11°/+17.72° | 이동 charge는 기존 Spine 상체 레이어로 Hips/다리를 보존하므로 이 전신 압축이 이동 중에도 적용된다고 주장하지 않음 |
| 리라 startup/active/회수 | .20초 골반 높이 delta−104.18mm; active 몸통·어깨/팔·pole은 v0.1.8 경로를 보존. 새 stance/뒤발 catch와 .64초 골반−60mm·무릎+10.51°/+9.96°,1.06초 guard 복귀 | active 상체까지 새 전신 안무로 바꿨다는 뜻이 아니며 새 하체 변화의 시각 적합성은 별도 |
| 수호병001 .24/.32/.48초 | .24초 골반 delta(+26.79,−50.89,−85.88)mm·흉부차32.00°·무릎+18.09°/+10.64°; .32초 낮은 제동; .48초 저작한 manual guard 목표 | 001의 실제 원본 idle 회수가 실패해002로 대체. 몸/다리의 local step·brace는 보존하고 팔 branch를 수정; 추정 world recoil 보정은0 |

리라 charge 끝→release 시작의 전신 join은 raw 검사에서 위치0·회전 약.0322°이고188개 active key/midpoint에서 Grip/Tip 최대오차는 약.3202mm/1.2794mm다. 이는 finite raw/FK 정합이며 연속 surface·실제 gameplay·시각 승인으로 확대하지 않는다. [리라 스튜디오 표본](../art_source/production/candidates/lyra-weight-001/studio-review/contact-sheet.png)·[수호병 스튜디오 표본](../art_source/production/candidates/sentinel-weight-001/studio-review/contact-sheet.png)은 정지 포즈 자료다.

[기각 이력](../art_source/production/candidates/lyra-weight-001/rejected-motion-summary.json)에서 초기 리라002/004는 표시 검 marker를 맞춰도60Hz 비교의 손목 local 회전이 약116.931°/109.433°씩 반대로 돌았다. 조밀한2ms 저작 key의 작은 인접 차이나 최종 Grip/Tip만으로 이 문제를 승인할 수 없었다.005/006은45° 인접 관절 gate에서 기각했다. 최종007은 기존 active 몸통·어깨 경로와 pole을 보존하고 load/stance/catch·회수를 바꾸었다. 첫 quaternion의 antipodal 표현을360°로 읽은 진단 오류는 shortest 회전 계산을 바로잡은 것으로 실제 물리 snap과 구분한다.

[독립 raw 미분 도구](../tools/inspect_motion_derivatives.py)와 [고정 감사 원문](validation/v0.1.9/raw-motion-audit.json)의 charged_heavy 전체65개60Hz 표본은53본의 local/global 회전과 world 변위를 구분한다. **53본을 합친 전체 최대값**은 local 약62.12066→62.12068°/표본, global58.62970°/표본, world 변위.245367m/표본으로 기존 수준이다. 이는 각 본의 peak가 모두 불변이라는 뜻이 아니다. 의도한 골반/다리 변화로 Hips world step은6.8705→30.3579mm, LeftLeg local step은13.1586→16.6169°로 증가했다. 전체 최대값 유지나 raw schedule60Hz가 자연스러운 변형·rendered60fps를 승인하지 않는다.

수호병의 초기 시간 기반 world recoil 발 보정도 기각했다. 벽에서 줄거나 옆으로 풀리는 실제 root 이동을 오프라인에서 고정.35m로 가정할 수 없고 actor 크기 비율을 다시 곱하면.375m가 되는 문제도 있었다. 현재 후보는 그 보정을 제거하고 local braking step만 저작한다. 실제 접지와 벽/방향 조건은 runtime에서 다시 확인한다.

### 실제 표시 표본과 남은 팔 동작

이전 MovieMaker run002는 Hero의25mm 높이 fixture 차이와 이전 수호병 때문에 historical body-relative 진단으로만 보존했다. 현재 공개 근거는 [수정된 fresh003](validation/v0.1.9/native-motion/README.md)뿐이다. 현재 Hero27fbed/Sentinel002e7e2와 ownerY=-visual.ground_offset_y를 사용했고, source cache/runtime offset/geometry는 변경하지 않았다. 모든 Hero162frame+팔5표본은 ownerY약−.025m, 수호병84frame은0이었다. 이는 명목 평면 배치 확인이며 모든 vertex의 실제 접지·terrain IK·충돌 승인이 아니다.

현재003의 [리라 전신9시점](validation/v0.1.9/native-motion/hero-contact-sheet.png)·[수호병 전신9시점](validation/v0.1.9/native-motion/sentinel_melee-contact-sheet.png)은 loading·낮은 stance·뒤발 catch·제동·피격/회수 자세의 차이를 보인다. [팔5개 정지 표본](validation/v0.1.9/native-motion/hero-arms-static-strip.png)에서는 기존·새 모델 모두 charged .4667–.4833초의 전완/건틀릿 roll이 급하다. **v0.1.9가 어색한 손목 동작을 모두 고친 것은 아니다**. 이 잔존 동작은 다음 실제 skin·팔/양손 시각 검수의 우선 항목이다. 밝은 중립 fixture 바닥도 재질/조명 승인 근거가 아니다.

## 실제 원본 idle로 수정한 수호병002

[별도 recovery wrapper](../tools/author_sentinel_recovery.py)는 frozen base 저작 도구와 수호병001을 보존한 채 원래 `PoseRig.limb`의 팔 branch로 다시 연결했다. [새 recipe](../art_source/production/character_actions/sentinel-weight-recovery.json)·[002 authoring](../art_source/production/candidates/sentinel-weight-002/authoring.json)·[semantic 원문](../art_source/production/candidates/sentinel-weight-002/semantic-review.json)은 몸/발/brake를 보존하고 `heavy_hit`만 수정한 범위를 기록한다. 수호병001의 source·실패 보고서·스튜디오 표본은 그대로 남긴다.

실제 반입/표현 검사에서 near-end guard 오차는 **4.517256mm**, 첫 idle은 **.487623mm**로 기존20mm 기준 안이다. 정지 charge 끝→release join은 위치 **7.45×10⁻⁹m**, 회전 **.00097656rad**다. startup 골반 이동은 약75mm(이전 약0), 수호병 골반/발의 최대 pose 차이는 actor-local **103.360mm/106.959mm**였다. 이는 실제 world recoil 동안 발이 고정됐다는 뜻이 아니다. raw FK·Blender 재반입·실제 Godot의 회전 오차는 각각의 방법·단위로 기록하며 서로 다른 측정치를 하나로 합치지 않는다.

실제 active Grip/Tip 최대오차 **.325742mm/1.127059mm**, 명목 지지발 **.015378mm**, 새 손531/기존 light53key를 확인했다. [현재 접촉 원문](validation/v0.1.9/native-contact.json)은 새 Hero에서 실제 접촉 시계·날 구간·양쪽 정지와8개 잔상 표본/mesh/age의3개 물리 프레임 유지를 기록한다. native 통과는 게임/표현 계약의 확인이며 시청각·브라우저·하드웨어 승인이 아니다.

[로컬 패키지 기록](validation/v0.1.9/local-preview.json)은 Web 원본 **146,306,891B/150,000,000B**, Web ZIP **115,614,322B**, Windows ZIP **143,455,629B**와 version/pinned engine·SHA·CRC·필수 파일/라이선스 확인을 담는다. 이 dirty a98 기반 패키지를 최종 커밋의 CI·공개 Pages·릴리스 파일과 동일한 결과로 취급하지 않는다.

[Python 검사 원문](validation/v0.1.9/python-tests.log)은51개/실패0·1.659초를 기록한다. 이는 도구 검사 범위이며 새 캡처·interactive 게임 AV·실기기·아트 승인과 별도다.

## 저작·통합에서 확인할 순서

1. **준비에서 release까지:** `charge` 끝과 `charged_heavy` 시작의 전신/검/양손을 같은 actor frame으로 비교한다. 골반·몸통·어깨와 검 면의 역할을 구분하고 무기 경로만 유지한 채 몸이 튀는지를 확인한다. charge 중 이동 레이어와 locomotion 우선순위도 실제 상태에서 확인한다.
2. **active와 회수:** 현재 판정 경로·양손을 유지하며 몸통·골반·다리의 힘 전달과 회수 자세를 저작한다. 원본 key·모든 interval midpoint와 실제 imported 최종 Grip/Tip을 대조하고 팔꿈치·관절 shortest 회전의 연속성을 검사한다. 끝점이나 조밀한 bake만으로 통과시키지 않는다.
3. **피격자의 질량:** `.48초` 안에서 recoil을 받기→낮게 제동→다리 재정렬→guard 회수를 구별하는 것을 목표로 한다. 실제 root 이동과 시각 골반/발 보정을 분리하고 열린 바닥·근접 겹침·벽 앞에서 source 이동을 이중 적용하거나 순간 이동하지 않는지 확인한다.
4. **실제 전환:** 명중/빗맞힘/방어/처치, hold/release·취소·피격·회전·벽·복귀에서 몸/검·발·잔상과 공통 시계를 검사한다. nominal 지지발 drift와 지형 적응 IK·모든 실제 접지 승인은 구분한다.
5. **표현과 기능의 분리:** 같은 카메라·거리·품질에서 이전/새 몸 동작과 효과off/on을 비교한다. 동작이 읽히는지, 손·발·갑옷 관통과 적 예고 가독성을 확인한다. native·export·브라우저 성공, 정지 화면, 정상1배속 AV와 목표 기기 평가는 각기 판정한다.

실패하면 실패 입력/샘플과 원문을 남긴다. 허용오차 확대·실패 구간 제외·좋은 카메라만 선택·QA 상태 주입으로 성공시키지 않는다. 당시 실패를 수정한 뒤에도 이전 판본의 통과를 새 자산으로 승계하지 않는다.

## 실제 집중 브라우저의 통과와 첫 실패

[두 번째 실행](validation/v0.1.9/focused-browser/SUMMARY.json)은 신뢰된 CDP 다중 터치의 완충 빗맞힘/명중 범위에서 **290.733초·오류0**이었다. 첫 시도와45개 source hash·모든 export 파일이 같고 앱·driver·품질·assertion·시간 제한도 바꾸지 않았다. whiff contact/spawn0, 피해 **69.3(HP95→25.7)**,impact/effect 각각1회, `heavy_hit .48초`·양측 hitstop 요청`.075초`, 실제 recoil **.350000381m≤.355m**, 마지막 실제 pause **HP88·소유 pointer0**을 기록했다.

질의 시각.432222222초의 projection **.263683717>.18**, 독립 내부 축 거리 **.113384302m≤.125m**가 날 구간 기준을 충족했다. trusted release→읽기 전용 receipt **6.1115초<15초**는 검사 응답 제한이며 실제 공격 시간·입력 지연의 측정값이 아니다. 브라우저 frozen pair는 **unobserved**다. native의 실제 양측 root/skeleton/시계·잔상 동결 검사를 독립 근거로 유지한다. [실제 proof](validation/v0.1.9/focused-browser/proof.json)·[release timeline](validation/v0.1.9/focused-browser/release-timeline.json)·[source/export](validation/v0.1.9/focused-browser/export-context.json)에 관측 범위를 고정했다.

[첫129.577초 실패](validation/v0.1.9/browser-first-failure.json)·[당시 PNG](validation/v0.1.9/browser-first-failure.png)는 최초 charge-ready15초 timeout이다. 나중 charge.8/statecharge·HP120/errors0은 deadline 내 성공을 입증하지 않는다. 최초 만족 시각의 startup timeline이 없어 원인은 미확정이며 게임 결함·환경 원인·수정 완료를 단정하지 않는다. 동일 조건의 반복 통과가 첫 실패를 지우거나 코드 수정 효과를 증명하지 않는다.

## 현재 완료 판정

[두 번째 native 실패 원문](validation/v0.1.9/rejected-native-join.json)은 실제 모델·fixture SHA,448개/2실패·exit1, 회수와 첫 idle 오차·유지한2cm 기준을 보존한다. 첫 fixture 초기화 오류와 이 실제 자산 회수 실패는 다른 원인이다.

첫 native443개/2실패는 새 비교 fixture의 baseline loop flag 준비 차이였다. 정정 뒤 두 번째448개/2실패는 수호병001의 실제 원본 idle 회수 결함(near-end11.002cm/1.58rad·첫 idle2.055cm>2cm)이었다. 실패 입력·이전 자산을 보존하고 임계값을 바꾸지 않은 채 수호병002의 팔 branch를 수정했다. 세 번째 실제 실행은 **448개/실패0·exit0**이며 [native 로그](validation/v0.1.9/native-runtime.log)와 [현재 회수 원문](validation/v0.1.9/native-recovery.json)에 고정했다. 이전 실패를 성공 검사 수에 합산하지 않는다.

현재003의 [검증/출력 원문](validation/v0.1.9/native-motion/verification.json)·[capture metadata](validation/v0.1.9/native-motion/capture.json)는 같은 카메라·source freeze와 종료 중복 frame의 decoded 동일성을 기록한다. [Hero 무음 논리1x](validation/v0.1.9/native-motion/hero-1x.mp4)는720p60·162frame/2.7초, [수호병 무음 논리1x](validation/v0.1.9/native-motion/sentinel_melee-1x.mp4)는84frame/1.4초다. 파일과 유한 정지 raster만 확인했으며 연속1x 재생·음향 승인은 아니다. 이동은 명목 처방으로 실제 input/move_and_slide/contact를 실행하지 않는다. 실제 집중 브라우저 기능은 별도 근거이며 전체 여정·clean CI/공개·interactive AV/청취·목표 GPU·AAA는 pending이다.

기존 [v0.1.8 기능/실패 이력](CHARGED_IMPACT_SLICE.md)은 당시 자료로 유지한다. v0.1.9의 실제 proof가 나온 뒤 새 기록으로 연결하며, 그 전에는 이전 문서를 새 판본의 검증 완료로 바꾸지 않는다. **정상1배속 AV·실제 Android/iOS/Safari/Windows·목표 GPU·AAA 품질은 pending**이다.
