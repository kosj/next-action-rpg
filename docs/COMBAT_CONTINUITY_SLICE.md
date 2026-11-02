# v0.1.14 연속 전투 동작·실제 mixer AV 제작 초안

2026-11-02 UTC. 공개 v0.1.13 `ff1171a1834a99e29b3dfecac2498c84fad4a90e`에서 왼팔의 새 counterguard/guarded wrist를 저작하고, 임시 반투명 forcefield의 camera 가림을 분리했다. 루트와 독립 검토자는006 몸체의 actual broad blade 원본과 최종 after45-002의 entry/contact/end를 보고 **첫 방 전투 가독성의 프로토타입 개선을 채택**했다. 현재 native 692/0/ERROR0·양쪽 export·실제45.4초 AV/PCM을 확인했다. [실제 전후 영상·6원본](validation/v0.1.14/gameplay-comparison/README.md)과 [최종 checkpoint](validation/v0.1.14/final45/checkpoint.json)를 제공한다. **dirty v0.1.14·ff1171 preview이며 clean CI/browser/공개·릴리스·전체 연속 시청/직접 청취·full skin/하드웨어/AAA는 pending**이다. 아래 기각·이전 native·당시 pending 기록은 후속 실제 근거와 구분한다.

## 보존할 key와 고칠 보간을 구분한다

원본 Fury f2ed baseline의 light1/2/3은60Hz LeftForeArm local 회전이 각각152.030/155.451/133.459도였다. light2의.100→.116667 global 차이도105.244도다. 서로 반대로 도는 parent/child 때문에 왼손의.105 FK가 원래 world key endpoint chord에서 약73mm 벗어난다. 001~004에서는 원래100Hz world key target을 보존하며 잘못된 중간FK를 고쳤다.004의 pose 자체가 부자연스러워 기각한 뒤005부터는 명시적으로 새 free-left counterguard target을 저작한다. 이전 keytarget 보존 계약을 새 creative scope로 몰래 승계하지 않는다. 모든 raw local/global 값·실제 Δt·부모/자식 chain과 실제 skin을 함께 확인한다.

[초기001~004 recipe](../art_source/production/character_actions/lyra-continuity.json)와 [004 authoring](../art_source/production/candidates/lyra-continuity-001/source-004.authoring.json)은 세 light clip의 LeftArm/LeftForeArm/LeftHand9TRS channel만 수정한다. raw source BIN prefix·static declarations·나머지 clip/channel을 보존한다. RightHand/body/feet와 두 charged clip, geometry/rest/weights/maps를 손대지 않는 범위다. 실제 hand target/key·idle53본 join은 raw 수치와 Godot 반입/게임 재생에서 각각 확인해야 한다. projection unit-direction norm은 무차원 값이고 metre pole clearance가 아니다.

## 속도 합격과 skin 채택은 다르다

[기각 원장](../art_source/production/candidates/lyra-continuity-001/rejected-motion-summary.json)은001의 새 pole pop,002의2862.309deg/s,003의2776.102deg/s를 원본·recipe/tool snapshot 해시와 함께 보존한다. 상한2700deg/s를 완화하지 않았다. 고정 elbow/hand center와 world hand 방향에서는 twist만 바꾸는 방법의 swing 하한이 이미 상한을 넘을 수 있으므로 elbow plane과 전체 chain을 함께 다룬다. 준비한 finite studio 원본을 runtime/연속 motion 채택으로 표시하지 않는다.

기각된004 SHA `9f0d00aca2a57d328ef45f50d903b251c36bbd0137d9c629d9e5275306e15ee0`는53본 raw60/120Hz·key/mid의 최대값이 light1/2/3 각각2594.19/2585.13/1914.77deg/s로 원래 상한 안이다. 원래100Hz LeftHand key 위치는.001mm 미만 오차, RightHand/body midpoint는0delta이고53본 idle join도 유한 비교했다. 이 수치는 source 후보의 계약이며 runtime/시각 승인이 아니다.

skin의 지역 p99 edge ratio는1.617924→1.552055지만1mm 이상 악화한 edge345개가 있다. 최악의 같은-edge envelope는 light2.250에서−1.143592→+13.707885mm, 악화14.851477mm다. 전체 최대치가 같거나 p99가 좋아졌다는 이유로 이 국소 악화를 숨기지 않는다. 동일 pose·camera·neutral material의 양면 원본과 실제 게임 연속 재생을 보고 shoulder/arm volume·접힘·관통·hands/weapon/feet를 평가해야 한다. 루트는 실제 matched still에서 높은 chicken-wing elbow·매달린 forearm·들린 pauldron·겨드랑이 fold를 보고004를 기각했다. raw속도 통과는 자연스러운 pose의 채택 근거가 아니었다.

## 관측 결과의 수명과 시간축을 보존한다

[실제 mobile observer](../tools/mobile_browser_smoke.py)는 externally cached QA의 terminal matched/expired row를 host가 결과를 수신·검증해 ack할 때까지 남기고64frame timeline·host phase를 제한된 범위에서 기록한다. UI15초 absolute deadline·입력 gesture/predicate를 바꾸지 않는다. browser의 matched와 host의 실제 수신 성공은 별개다. host monotonic과 browser performance.now를 같은 절대 시각으로 직접 빼지 않는다.

[isolated helper](../tools/check_mobile_observer.py)의 실제 about:blank test-double003은 positive50.801ms, deliberate expiry15.016초, browser matched 뒤 host reply를 withheld한15.018초 negative를 확인했다. 두 negative는 예상대로 FAILED/TimeoutError이고 terminal evidence를 유지한다. 실제 Game/input·v13 최초 timeout 원인·고친 환경을 증명하지 않는다. 번들 browser binary 부재로 첫 launch 전에 실패했던 진단도 성공 기록으로 바꾸지 않는다.

## 실제 mixer PCM과 들었다는 주장을 나눈다

과거 v0.1.10 raw MovieWriter AVI에는 실제 48kHz stereo PCM이 존재하고 두 채널 nonzero sample이 확인됐다. 옛 transcode의 `-an`이 이를 최종 MP4에서 버렸다. [고정4.7.2 공식 source ledger](validation/v0.1.14/draft-known-findings.json)는 MovieWriter의 nonthreaded Dummy·AudioServer mix→write_frame와 MJPEG PCM block 경로를 연결한다. Dummy라는 이름만으로 무음이라고 추정하지 않는다.

새 [capture helper](../tools/render_combat_continuity.py)와 [fixture](../game/tests/combat_continuity_capture.gd)는 실제 mixer PCM·WAV·AV를 보존한다. 실제 baseline14-002 take가 완료됐다. baseline45는 이후 완료했고 첫 후보 after45는 이후 완료됐으나 camera 구도는 기각했다. frame/sample 수·원본 SHA·재인코딩·video/audio duration/start/offset과 receipt/audio report를 실제 입력에 맞춰 검증해야 한다. 다른 음악을 얹거나 정지 이미지만 보고 들었다고 기록하지 않는다. PCM nonzero나 peak/RMS는 직접 청취·1배속 시청·실시간FPS/목표GPU/AAA 승인이 아니다.

## 남은 승인

루트의006 guarded finite body/wrist 판단 뒤 runtime 선택·curve/source SHA 연결·최종 native/export150MB gate를 실제 완료했다. 최종 after45는 이후 아래 actual002 근거로 확인했으며 브라우저/공개 검증은 새 근거가 필요하다. 새 actual AV와 실제 desktop/mobile·저장/재시작·cleanCI/Pages/release를 각 source에 고정한다. case69의 제한된 검증을 기록하고 다음 묶음1.4.8의 source를 먼저 커밋한 뒤 존재하는 SHA에만 pin한다. 기존 공개1.4.7은 보존한다.


## 005 새 counterguard와006 bind-neutral wrist

[005 authoring](../art_source/production/candidates/lyra-continuity-001/source-005.authoring.json)은 왼손의 자연스러운 free counterguard를 새로 저작한다. 원래 free-left target을 보존하는004와 다른 creative scope이며 RightHand/body/geometry/timing은 보호한다. 실제53본 local/global·60/120/keymid 최대1363.726deg/s로 원래2700 상한 안이다.3mm 기준도 완화하지 않는다. 그러나005 wrist가 날카롭게 꺾여 시각 채택하지 않았다.

[실제 bind wrist 진단](../art_source/production/candidates/lyra-continuity-001/wrist-rest-diagnosis-005.json)은 idle의 weapon-grasp가 neutral이 아니며 bind-local과64.274도 다름을 확인한다. [006 bind-neutral recipe](../art_source/production/character_actions/lyra-continuity-neutral.json)로 만든 [006 guarded](../art_source/production/candidates/lyra-continuity-001/source-006-guarded.authoring.json) SHA `14e5069ab4fa3b4119c1e1b67cb220300cfd23f0c9ccb1fd18063f9ec8255618`은 free phase의 wrist만 실제 bind-neutral 방향으로 수정하고 시작/끝 grasp를 유지한다. rest/weights를 고친 것이 아니다. 당시006 slim검 studio는 body/wrist만 검토했다. 이후 actual broad blade4원본을 새로 확인해 제한적으로 채택했으며 이전 slim검 이미지를 currentblade clearance/grip/contact 근거로 재표기하지 않는다.

## 실제 baseline14s AV와 별도의 camera 결함

baseline `ff1171a1`의 실제14-002는 physical960×600/source1440×900·q1·840gameplay+24UIframe의864deliveryframe/14.4초를 기록했다. raw는868frame·48kHz stereo PCM868×800sample이고 WAV는 delivery864×800의 정확한 PCM prefix다. MP4의 AAC는 lossy delivery이며 exact PCM은 원본/WAV로 보존한다. 무음악 추가·시간 보간 없이 actual input/physics/production camera로 세 light·charged whiff·실제69.3 hurtbox contact를 관측했다. receipt serial6/tick570과 audio attackID·point가 맞고 sharedpause5frame, HP120→88이었다. heal input1회는 실제 소비0회이며 성공으로 기록하지 않는다.

870.559초는 offline 캡처 비용이지 FPS가 아니다. 기존 runtime 입력 bytes는 같지만 새 fixture UID가 생겨 whole project file-set equality는 false다.31/840 nominal body camera projection이 frame 밖이며 실제 decoded frame418은 오른쪽 심한 crop,420/863은 발이 아래로 잘린다. 이는 이미 해결한 writer physical/aspect 불일치와 별개인 실제 production camera 구도 문제다. 이 과거 take는 ray collider ID를 기록하지 않아 그 장애물의 직접 query receipt는 없다. 이후 별도 native fixture에서 실제 gate collider와 focus lag·latent followbase 문제를 검증했으며, 최종 실제 take와의 대조는 별도다. 선택 still 확인을 연속 시청·직접 청취·하드웨어 승인으로 쓰지 않는다.14초는 LP1 과거 기록이고 baseline45는 실제 요청LP3로 따로 완료했다. 이후 최종 after45 LP3 결과는 아래 actual002에 별도로 기록했다.


## 채택 입력의 native와 metadata 보존

[실제 native 요약](validation/v0.1.14/native-light-continuity.json)은 현재 imported Skeleton/AnimationPlayer와 독립100Hz GLTF original-light control을 비교한다. 새 target의 최대 위치 오차는 light1/2/3 각각1.062569/1.050379/.556431mm로 원래3mm 안이고,53본 local/global60/120/keymid 최대1158.874/1363.726/867.579deg/s로2700 안이다. RightHand world차이는 약.000954mm이며 원래 왼손152/155/133도 control을 실제로 재현한다. 이는 새 freeleft target 계약이고 원래 in-action 왼손 key를 보존했다는 뜻이 아니다.

[원본/adoption 보존](validation/v0.1.14/source-adoption-and-preservation.json)은006 runtime SHA `14e5069ab4fa3b4119c1e1b67cb220300cfd23f0c9ccb1fd18063f9ec8255618`과 원본6atlas/import sidecar·GLB import byte 불변을 연결한다. charged curve는 source SHA metadata만 수정해 SHA `8946d0a499c50a0df8e26576a23221d54ef56d3099f1c2e01cbb25aa4e8f21e2`가 됐고 inverse metadata 치환으로 원래601adad7 SHA가 복원된다. 물리 sample·시간/판정·피해를 바꾼 것이 아니다. 파일 이름이 Fury여도 실제 body/curve/profile 구성과 SHA로 판정한다.

[실패 원장과 최종004](validation/v0.1.14/native-attempts-and-current.json)는 새 fixture type추론 실패001, standalone autoload context가 없어 exit0라도 strict stderr로 기각한002, proper624검사/3실패003을 보존한다.003은 editor-only baseline loader와 실제 landscape/portrait camera latent followbase windup을 드러냈다. 독립100Hz control과 wall-resolved un-kicked followbase sync로 수정하고 **같은 기준의 최종672/0/오류0/exit0**을 확인했다. tools80와 별도hub5·ART23source는 각각의 검사 범위다.

[실제 preview export](validation/v0.1.14/local-preview-build.json)는 dirty0.1.14·ff1171a1/96selectedsource fingerprint와14Web·두ZIP/manifest를 고정한다. raw149,722,063B/150MB 미만·여유277,937B, WebZIP119,083,495B·WindowsZIP146,924,851B다. Windows export는 OS 실행이 아니며 clean release/현재 공개판이라고 부르지 않는다.

[baseline45](validation/v0.1.14/baseline-45-checkpoint.json)는1072.282초 offline 비용·2724deliveryframe/45.4초·raw2728/48kstereo와 정확한 WAV prefix를 확인했다. chargedserial42/contacttick2248/release2224/sharedpause5·HP120→88이고 nominal57/2700 crop 및 끝 원본의 severe left/bottom crop을 보존한다.2700gameplay+24UIframe과 requestedLP3는14초LP1과 별개 입력이다. 첫 after45/pair를 실제 확인했지만 camera의 완전한 전투 구도는 기각했다. camera의 실제 경계·latentstate/feedback 수정은 [별도 제작/검증](CAMERA_COLLISION_FRAMING_SLICE.md)과 사례 70의 제한된 검증 범위로 관리한다.


## 첫 after45: 캡처 성공과 camera 구도 기각

[첫 after45의 실제 pair](validation/v0.1.14/first-after45-rejected-checkpoint.json)는1019.108초·2724deliveryframe/45.4초·actualPCM/WAVprefix·real69.3 contact2248/sharedpause5를 확인했다. 두 take의2724행에서 controls/hero·enemy root/velocity/health/timing 비교가0mismatch이고 receipt payload도 명시된ID/curve/localphysicscounter 제외0mismatch다. 이는 이 두 take의 관측값이며 일반 engine 결정론의 증거는 아니다.

Hero nominal crop이57→0/2700으로 줄었지만 루트가 entry/contact/end의6paired raw원본을 모두 보고 **완전한 전투 camera로는 기각**했다. entry/end는 가파른 topdown·바닥 중심 구도로 nearby enemy가 보이지 않는다. contact는 양쪽에서 읽힌다. [a519 source·4untouchedentry/end원본·기각판정](validation/v0.1.14/rejected-camera-001/review.json)을 보존하고 몸만 들어왔다는 수치로 전체 전투 가독성을 승인하지 않는다.006 model 채택은 유지한다.

다음 camera는 이미 alpha.24/unshaded인 임시 forcefield의 실제 표시/충돌 의미를 분리하는 후보 단계다. 같은 world의 명시 표시된 임시 StaticBody이며 모든 effective StandardMaterial의ALPHA가.25이하인 경우에만 camera query에서 제외하는 조건을 검토한다. actor/weapon의 실제 blocking·wall/shape/visibility/material은 유지해야 한다. opaque-taggednegative/solidwallbehind/실제factory·Hero+enemy동시표시와 기존overhang/zero-time 기준을 새 입력에서 다시 확인해야 하며 당시에는 계획이었다. 이후 구현/native/export는 아래 별도006근거로 확인했고 당시 actualafter45-002는 미승인이었으며 이후 아래 최종 근거로 제한적으로 채택했다.


## 반투명 임시forcefield 정책006의 실제 native/export

[현재7b8c정책006](validation/v0.1.14/current-camera-policy-006.json)은 명시group·동일World·실제single-surface mesh의effective StandardMaterial ALPHA/finite0..25%를 모두 만족하는 임시barrier만 모든camera ray/sphere/sweep에서 제외한다. Sanctuary는 group1행을 빼면 baseline source와 exact이고 기존energygate의alpha.24/unshaded·actor/weapon layer1/shape/material/visibility는 유지한다. 이는 벽을 물리적으로 제거하거나 모든투명geometry를 무시하는 변경이 아니다.

[실제 camera native006](validation/v0.1.14/native-camera-policy-006.json)은 기존solidwall/overhang/windup 기준을 유지하고 actualfactory14group·두viewport Hero+lockedfoe여백·원래playercapsulecast/unfilteredray blocking·opaque/alpha-disabled/untagged/otherWorld negative·뒤의opaquesolidwall을 추가 검사했다.005의692/0은 formatted label `24%-alpha`의strictERROR2개 때문에 기각했고 message-only 수정 뒤006의692/0/ERROR0/exit0·양쪽export를 확인했다. assertion개수만으로005를 성공 처리하지 않는다.

[새preview](validation/v0.1.14/local-preview-build-006.json)는 raw149,726,783B/여유273,217B·WebZIP119,084,890B/WindowsZIP146,926,246B·source96fingerprint38e831...을 별도로 고정한다. 앞선a519/672/export와기각45는 그대로 남긴다. 새dirtypreview는 cleanrelease/실기기 승인이 아니다.

[private staged preflight경계](validation/v0.1.14/staged-camera-preflight-scope.json)는 원래FAILED pipeline을 유지한다. texture metadata640×400과 실제Image/PNG960×600 차이로guard가 실패했지만 원본entry/contact/end를 따로 보고 Hero·feet/blade·세foe가 전방에 보이는지 확인했다. Hero/foe bonefit근사·frozencontroller/AI·recreatedpose라 실제transition/skin/AV 증거가 아니다. cyanwash/끝darkvoid는 남는다. 최종 actualafter45-002는 baseline45와 같은360c6c runner/371058fixture/129e scene·LP3/q1/960×600/45초 정책으로 이후 완료됐으며 아래 실제 결과를 staged이미지로 대체하지 않는다.


## 최종 actual after45-002 채택과 변동의 한계

[최종 actual paired audit](validation/v0.1.14/final45/paired-audit.json)은1050.123초 offline 비용·45.4 logical초/2724 delivery frame/raw2728·48k stereo2,182,400 sample frame·정확한 WAV prefix2,179,200을 고정한다. captured Game78/78은 root96 freeze38e831 subset과 같고 runtime Changed/added/import metadata는0이다. 이후96 source·14 Web·두 ZIP/manifest의 [byte 불변](validation/v0.1.14/final45/source-export-after-capture.json)도 확인했다. 재생 가능한 자체 MP4는 game 밖의 문서 자산이며 Web export 용량에 더하지 않는다.

actual Hero nominal 0/2700과 engaged locked foe0/626의 finite XY/nonbehind를 확인했다. baseline은 Hero57/foe0, 기각001은 Hero0/foe23이므로 body-only 개선만으로 camera를 승인하지 않았다. 실제 locked actor와 독립 projection의 최대 UV 차이는9.45e−8이다. 실제 평가한 foot/toe4+Grip/Tip2의6 point는 각각 Hero2700/foe626에서 finite/inframe였다. [3 selected trace/receipt](validation/v0.1.14/final45/trace-excerpts.json)는 실제 actor identity·root·camera·marker를 연결한다. full mesh/depth occlusion/UI 충돌·발 plant·모든 적의 지속적인 가시성을 승인한 것은 아니다.

ROOT와 독립 검토자는 entry/contact/end의 baseline/최종6 raw 원본에서 Hero 전신·발/검·상대 context·전방 깊이가 유지됨을 확인했다. cyan forcefield wash·chapter banner·먼 적 겹침·끝의 dark outside platform/foreground edge는 남는다. [기각001](validation/v0.1.14/rejected-camera-001/review.json)의 steep body-only 구도와 해당672/export는 보존했다.

같은 controls/timing/health·69.3 contact serial 42/release2224/contact2248/shared pause5/HP88와 receipt의 명시된 field는 일치한다. **최종002는 root trajectory가 동일하지 않다.** 후반 288 distinct 행(foe288/Hero244, section 총532)에서 차이가 났다. 첫 차이는 foe 2437/Hero2481로 contact 후다. 최대 Hero root .030015m/한 foe.956972m이며 원인을 분리하지 못했다. 기각001의0 mismatch를 최종002에 승계하거나 일반 physics 결정론을 주장하지 않는다. 실제 AV의 sample-clock 정합·제공과 전체 1배속 시청·직접 청취·청각적 contact sync 평가는 구분한다.
