# v0.1.10 활성 동작·칼날 곡선·표현 제작 단위

2026-11-01 UTC. **로컬 native482개/실패0·Web/Windows preview 확인,skin/최종 시각·브라우저·공개/AAA 승인 pending**. 실제 앱 버전은0.1.10이며 시작점은 `1e524b1275c6c55d3020ea5c3122afbb8db403e9`의 v0.1.9다. [현재 source/native 기록](validation/v0.1.10/README.md)은 dirty 구현의 한정된 검증이다. 이전 [무게/회수 자료](WEIGHT_RECOVERY_SLICE.md)를 새 판본의 근거로 바꾸지 않는다.

사용자는 v0.1.9의 개선이 충분하지 않다고 평가했다. 이번 범위는 기존 active 팔 경로를 보존하는 데서 나아가 **준비→몸통이 이끄는 하강 베기→받기/회수**를 다시 저작하고, 그 실제 source와 피해용 칼날 곡선을 연결하는 것이다. 넓어진 Hero 검과 제한된 카메라·잔상·접촉 표현도 함께 검수하지만, 기능·수치 변화나 효과 개수로 AAA 품질을 승인하지 않는다. 현재 [검증 기록](validation/v0.1.10/README.md)은 확인 범위와 미실행 gate를 분리한다.

## 보존할 것과 바꾸는 것

- Hero body/rest/skin/이미지·재질·원래 BIN prefix와 unrelated clip은 보존하고 `charge/charged_heavy`를 별도 Fury 출력에서 교체한다. 기존 weight GLB와 저작 도구를 덮어쓰지 않는다. Sentinel의 실제 채택 source `e7e2b5bd…`는 유지한다.
- 완충 timing `.34/.18/.54초`, 피해69.3/poise79.2(업그레이드0), 양측 hitstop 요청.075초·recoil 요청.35m, 명목 active 이동.576m와 기존 입력·방패·보스·중단 규칙을 유지한다.
- **active 몸/검 경로는 변경 대상**이다. 이전 수평/고정 공식을 그대로 맞춘다고 승인하지 않고 같은 새 source에서 실제 Grip/Tip 곡선을 bake한다. 장착 Grip→Tip1.19m·손잡이 쪽18% 제외·반경.12m와 충돌/한 swing 중복 방지 계약은 유지한다.
- 새 넓은 날은 Hero instance의 geometry만 바꾼다. 원본 검·Sentinel 검·hilt/guard/apex·마커·길이·UV/index/topology·기존 PBR material/atlas를 유지한다. 폭이 커졌다는 이유로 피해 거리나 반경을 늘리지 않는다.

## 현재 source 판본

| 항목 | 확인한 판본 | 실행/품질 상태 |
| --- | --- | --- |
| Hero Fury007 | GLB25,032,860B,`f2edbd3709d2f06ceb2f4c7ec7ddecdbf80cc2e97bee71664044eeac04a74beb` | 현재 native482/0에서 실제 marker 확인; local skin 악화/최종 시각 채택은 pending |
| 실제 source 곡선 | `601adad7389ae4f22563db2deeb6982651c9776daa05be070a781d44bd322e6e`,91표본 | .34–.52초/.002초 간격,source SHA·resource pin의 정적 연결 확인 |
| 보류한 Fury006 | GLB`2edd552b…`,curve`848cb4e8…` | 준비 자세의 early contact 기하 발견으로 보류;007 결과로 혼합하지 않음 |
| Hero broadblade | geometry160,248B,`4fd76a77ea3a796ecb84750cd74d9efdd709a760e6902735026fd1d42b7fbf7b` | raw 보존·native surface/triangle 대응 확인; 손/피부 간섭·화면 채택 pending |

[현재 manifest](../art_source/production/candidates/lyra-fury-001/manifest.json), [semantic](../art_source/production/candidates/lyra-fury-001/semantic-review.json), [raw audit](../art_source/production/candidates/lyra-fury-001/raw-motion-audit.json), [곡선](../art_source/production/candidates/lyra-fury-001/blade-curve.json)과 [source 대조 기록](validation/v0.1.10/source-review.json)에 원문·해시·방법을 연결한다. stage한 bytes와 실제 importer가 사용한 파일/cache·최종 표시 source는 native 원문으로 다시 확인해야 한다.

## raw 동작 수치의 의미와 한계

Fury는 흉부가 이끄는 하강 경로·해부학적 elbow swivel·축 twist 분배로 팔 동작을 다시 저작했다. 동일 charged_heavy 전체 구간의53본/65개60Hz FK 표본에서 전체 최대 local 회전은62.12068→23.32374°/표본, global은58.62970→20.44841°/표본으로 줄었다. 가장 큰 본도 바뀌므로 손목 하나의 수치만 비교하지 않는다. 이 수치는 공학적 검토 기준이며 AAA 달성률·정상속도·목표 기기 성능이 아니다.

독립 raw glTF TRS/slerp·normalized quaternion abs(dot)의 shortest 비교에서 실제 idle/recovery53본 join은 위치최대.329761mm·local회전최대.000581324°이고 held→release는 위치/회전 모두0이다. 저작도구의 별도 float 각도 계산과 이 방법의 값을 섞지 않는다. IK reach clamp0·선택 명목 sole drift약1.024mm·raw2ms 최대인접회전2.836°는 각 방법의 유한 결과다. peak 감소는 누적 axial twist·실제 피부의 자연스러움·모든 접지 승인과 다르다. LeftForeArm local 축의 누적 절대 경로약283.93°(왕복합),rest-relative localY 범위약160.95°가 남아 있어 실제 skin/팔/갑옷을 검수해야 한다.

## 현재 남은 국소 피부 위험

[실제 raw LBS key/midpoint 보고서](validation/v0.1.10/skin-midpoint.json)는1712개 표본·팔/손/어깨 영향영역23800edge를 비교했다. 전체 최대 절대 extension은53.062→34.083mm로 좋아졌지만 **2054개 edge의 envelope 악화가1mm를 넘었다**. 최악의 같은 edge는 charge.296초 왼팔꿈치이며 old envelope−14.607mm→new+17.948mm,변화량 **+32.555mm**다. 새 extension 자체가32.555mm라는 뜻은 아니다.

이 결과는 유한 raw 변형 지표이며 시각/관통 판정과 구분한다. [선택12개 실제 still의 판정](../art_source/production/candidates/lyra-fury-001/skin-review/README.md)은 canonical 왼팔꿈치와 정면/반대쪽에서 뚜렷한 새 붕괴·가시·찢김을 보지 못해 **runtime QA 후보로 잠정 채택**했다. 공개 대표6장과 [카메라/해시/관찰 범위](../art_source/production/candidates/lyra-fury-001/skin-review/review.json)를 보존한다. 이는2054개 edge의 수치를 지우거나 전체 skin/관통·양손·연속1x·AAA를 승인하지 않는다. 비교는 양쪽 모두 기존 중립 룬검을 써서 새 broadblade의 실제 가독성도 별도다. [독립 raw 검토](validation/v0.1.10/independent-raw-review.json)의 누적 twist/방법·전체/본별 범위도 유지한다.

## 칼날 곡선의 권한과 출처

[AttackData](../game/scripts/core/attack_data.gd)는 [곡선 파일](../game/data/charged_blade_curve.json)의 SHA pin·좌표계·active timing·길이·단일 floor offset·finiteness·표본 순서와 양끝을 검증한다. actor Y-up/−Z-forward·floor offset.025m를 한 번 적용하는 source 계약이다. source GLB SHA는 metadata로 고정하고 실제 파일과의 연결도 정적/fixture 검사에서 대조한다. metadata 문자열만으로 실행한 모델의 동일성을 승인하지 않는다.

현재 stdlib 대조의91표본 길이 최대오차는약.00104mm,Grip/Tip 선형 보간 중간 chord 오차는약.25039mm다. 이는 raw 데이터의 유한 검사이며 실제 imported marker3mm gate나 피부/접촉 시각 검수를 대신하지 않는다. [Strike](../game/scripts/core/strike.gd)는 원래 curve key를 보존하며 실제 endpoint·해결된 actor 이동량에 따라 query를 세분화한다. 잘못된 pinned curve는 오류로 남기고 물리 query를 하지 않는다. curve가 지정되지 않은 기존 리소스만 analytic 경로를 사용할 수 있으며, 새 source의 검증 실패를 옛 경로로 조용히 덮지 않는다.

## 준비 자세에서 너무 이르게 닿는 문제

[보류 이력](../art_source/production/candidates/lyra-fury-001/rejected-motion-summary.json)의006은 팔 peak 감소를 통과했지만,root 간격.725m의 일반 적 capsule에 준비한 높은 날이 active 시작부터 닿을 수 있었다. 초기 sharp 안쪽 축 거리.427485m가 반경합.52m보다 작고 초기 하강 속도는약.7664m/s였다. 이는 **raw 기하 발견**이며 실제 native receipt나 타격 시각 측정이 아니다.

007은 release를 옆으로 옮기고 heading을 조정했다. raw초기거리.614684m>.52m·명목 첫LUT겹침.354초/하강4.095m/s는 기하예측이다. [실제 native](validation/v0.1.10/native-contact.json)의 .725m close 회귀는 .339초 HP95를 유지하고 **.358초**에69.3을1회 적용했다. projection.261452·안쪽축거리.115748m,격리 hilt접촉0을 확인했다. 예측.354와 실제.358을 구분하며 임의 phase gate·피해 지연·threshold 완화로 숨기지 않았다. 이는 native 범위의 확인이며 최종 실제 화면/skin 승인은 아니다.

## Hero 전용 넓은 날과 같은 atlas

[정적 파생 보고서](../art_source/production/weapon_profiles/hero-broadblade-001/derivation.json)는 원본2799vertex/4000triangle 중1550vertex의 blade 폭을 최대1.8배로 바꾼다. y=.35/.55/.75/.95m band 폭은약57.27/57.15/54.20/52.88→103.08/102.88/97.55/95.19mm다. hilt/guard/apex·모든Y/Z·node/marker·UV/index/topology를 보존하고,변하는 normal/tangent는 Jacobian inverse-transpose·Gram-Schmidt와 기존 handedness로 처리한다.

[ActorVisual](../game/scripts/actors/actor_visual.gd)은 새 geometry ArrayMesh를 복제하고 원래 active PBR material을 mesh surface에 지정한다. instance material override는 사용하지 않으며 기존 weapon/marker·원본 atlas와 Sentinel검은 유지한다. [native 무기 원문](validation/v0.1.10/native-weapon.json)은 원래 material resource 재사용·삼각형 대응·normal/tangent를 확인했다. raw좌표/index/UV 보존과 native importer의 압축·순서 변화를 나눠 비교하며 위치대응 오차약20.94µm는100µm 기준 안이다. native UV오차약2.1263e-5는 정규화 좌표값이다. 손/피부 간섭·시각 승인은 별도다.

변경한 vertex의 기존 capsule 안쪽 축 거리 최대는.112457m다. 전체 damage-zone 최대.124849m는 원래부터 있는 미변경 vertex에서 같으므로 **모든 검 메시가 반경.12m 안에 들어간다고 주장하지 않는다**. 변경 전후 같은 조명/카메라의 neutral·실제 room·양손/갑옷·전체 동작과 날 contact를 확인해야 한다.

## VARCO 후보와 표현 코드의 범위

[공식 zero-point two_hand_attack 참고 후보](validation/v0.1.10/varco-reference.json)는 한 번 생성한 provider-stock 비교 자료다. 새 mesh/rig를 재실행하거나 production clip으로 바꾸지 않았다. 31.9초 unnamed/21channel clip과53joint·공통 원점 이동의 정적 호환성만 확인했으며 retiming·원점 정규화·양손 그립·연기·권리·실제 runtime 채택은 별도다. 원본 미디어·account/task/flow 식별자·서명 URL을 저장소에 넣지 않는다. zero-point 성공이 최종 모션 품질이나 재사용 권한을 자동 승인하지 않는다.

카메라의 거리/lock-pair framing·복귀,실제 world marker의 charged 두 잔상 layer와 확정 packet의 blade-motion impact는 [native fixture](validation/v0.1.10/native-feedback.json) 범위에서 확인했다. portrait 명목 body 높이 비율은.318912,이전 대비1.284176배이고 회전시 cut AABB 방향·depth·수명/중단 계약을 검사했다. 이는 투영/mesh API/수명 증거이며 실제 게임 UI가림·evaluated skin·타격감/음향·GPU 승인이나 최종 가독성은 아니다.

## 완료 gate

[두 번째 native 로그](validation/v0.1.10/native-runtime.log)는482개/실패0이다. [첫 실패](validation/v0.1.10/native-first-failure.log)는 material override 계약·native index/order/정확좌표를 잘못 가정한 fixture·feedback Variant추론 parse 오류를 보존한다. material 부착 방식을 수정하고 raw보존/native양자화의 triangle 대응을 분리했으며 fixture 타입을 고쳤다. source raw 보존 기준이나 접촉 기준을 완화한 것으로 설명하지 않는다. 현재 imported Grip/Tip 최대오차.066516mm/.303980mm와 명목발.015378mm를 확인했고,main contact.406초의 양쪽 시계·root/skeleton·5개 잔상표본/16tri가3physics frame 유지됐다. preview Web146,513,443B/150MB,WebZIP115,767,875B·WindowsZIP143,609,182B는 로컬 dirty 출력이다. skin 국소 검수·최종 시각·실제 브라우저·clean CI/공개/릴리스·연속1x AV/청취·목표 하드웨어·AAA는 pending이다. [v0.1.9 proof](validation/v0.1.9/README.md)는 당시 판본으로 보존한다.
