# v0.1.15 강한 대검 동작과 확정 타격 표현

2026-11-03 UTC 갱신. 시작점은 공개 v0.1.14의 `87fcefdd9a7e24f575e9d1b2df2e9273da29a8ab`다. 사용자가 지적한 소극적인 동작·이펙트를 개선하기 위해 **일반 강공격과 차지·완충 강타를 함께** 다룬다. source-006 몸체와 새 칼날 곡선을 finite studio 검토 뒤 native QA용으로 선택했다. 첫 native707검사/3실패는 보존했고, source 경로와 독립 payload 가드를 고친 뒤714검사/0실패·ERROR0·양쪽 export를 확인했다. 실제 Game의 두14초 pipeline·PCM/접촉 감사와 원본의 루트/독립 finite 검토를 마쳤으며, 준비 자세·큰 궤적을 prototype 개선으로 채택했다. 연속 시청·직접 청취·full skin·AAA는 pending이다. 이전 판본의 통과를 새 v0.1.15 검증으로 쓰지 않는다.

## 동작의 차이를 먼저 만든다

루트가 baseline의 일반 heavy 첫 active 원본과 light3 원본을 비교했을 때, 둘 다 수평의 한 손 베기로 거의 같게 읽혔다. 이 관찰은 동작을 구분할 이유이며 아직 끝나지 않은 baseline14 전체의 시각·AV 승인과 다르다. 이펙트나 소리만 키워 일반 강공격의 차이를 만들었다고 표시하지 않는다.

새 charge/charged/heavy 세 clip은 머리 위 양손 준비와 전신의 힘 전달을 중심으로 저작한다. 일반 heavy는 별도의 양손 동작으로 startup/active/recovery .32/.22/.32초를 유지하고, motor는 phase별0/3.2/0으로 active 동안 .704m 이동하도록 검토한다. 기존 약2m의 glide와 새 목표를 구분하며 실제 이동은 native physics·충돌과 게임 입력으로 다시 확인한다.

완충 강타는 피해69.3·startup/active/recovery .34/.18/.54초·active-only .576m 이동을 유지하는 방향이다. 다만 새 geometry의 실제 칼날 접촉 시점은 달라질 수 있다. 원래 접촉 phase를 억지로 맞추기 위해 피해 구간을 늦추거나 hilt 쪽 판정을 넓히지 않는다. 새 강공격에도 실제 source의 Grip/Tip에서 구한 물리 LUT가 필요하며, 곡선 데이터·resource pin·source SHA를 함께 연결한다. 계획값을 아직 반입한 runtime 값으로 기록하지 않는다.

## 몸체·곡선·이동의 권한을 구분한다

[이전 연속 동작 제작](COMBAT_CONTINUITY_SLICE.md)의006 light는 모든 channel을 보존한다. 새 whole GLB SHA는 바뀌더라도14e5 계보의 세 light와 보호한 clip/channel·rest/weights/maps가 같은지 별도로 대조한다. clip 이름이 같다는 사실이나 새 파일의 구조 통과만으로 이를 보증하지 않는다. 실제 import의53본 회전2700deg/s·손/Grip/Tip3mm 기준도 유지한다.

[공식4.7 AnimationTree 문서](https://github.com/godotengine/godot-docs/blob/4.7/tutorials/animation/animation_tree.rst)는 AnimationTree가 AnimationPlayer의 애니메이션을 사용한다는 점, Bone Rest/RESET을 기준으로 한 blend와 root-motion 추출을 설명한다. 이것이 현재 프로젝트의 motor·물리·판정 권한을 자동으로 바꾸지는 않는다. 몸의 저작 경로, 실제 collision root 이동, 시각 blend·hitpause·회수 상태를 따로 검증한다. 공식 원문의 조회 날짜·해시는 [source 원장](validation/v0.1.15/source-and-audio-preflight.json)에 남긴다.

## 칼날의 움직임과 확정 접촉을 강화한다

새 trail은 실제 blade marker history를 사용하는3-band fan을 검토한다. contact cut/core/spall을 포함한5개 표시 그룹과 동시 effect8개 한도를 선언하고, 새 source·실제 geometry·수명·깊이·q0/q1 가독성으로 확인한다. 이 숫자나 source 구현만으로 화면의 강도·품질·성능을 승인하지 않는다. 빗맞힘은 확정 접촉 burst나 피해를 만들지 않아야 한다.

카메라는 짧고 빠른 pulse를 목표로 duration .22초·charged .13/heavy .075의 bounded profile을 검토한다. 확정 contact의 방향·시점과 연결하고 기존 yaw/input·실제 피해·wall authority를 유지한다. 더 큰 shake가 적 예고·발/검·상대의 읽힘을 가리지 않는지 실제 입력 장면에서 평가한다. 새 clip·VFX·camera는 각자 통과한 뒤 같은 접촉의 AV에서 함께 검수해야 한다.

## 품질 index의 실제 의미와 impact 예산 수정

[실제 품질 적용 코드](../game/scripts/game.gd)의 q0는 균형 모드다. key shadow가 켜지고 Web 기본 render scale은 .8이다. q1은 성능 모드로 key shadow를 끄고 .65를 사용한다. 모바일 DPR 보정은 이 값에서 별도로 적용한다. 새 baseline14와 후보는 모두 q1 성능 모드로 비교하며 과거 q1 원본을 균형 모드로 다시 이름 붙이지 않는다.

반면 baseline impact effect는 q0 spark를10으로 제한하면서 q1에는 charged18과 더 큰 debris/dust 예산을 주고 있었다. 이는 전역 UI/그림자 모드 역전이 아니라 **impact source 내부 예산이 실제 품질 의미와 반대로 배치된 문제**다. 새 예산은 q0 균형의 spark/debris/dust24/8/3, q1 성능의10/3/1과 triangle 상한160/80을 명시적으로 검토한다. 기존 동시 effect8개 한도는 별도다. source·실제 배열·양쪽 품질의 원본으로 확인하기 전에는 새 예산 검증을 통과했다고 기록하지 않는다. [preflight 원장](validation/v0.1.15/source-and-audio-preflight.json)에 source 관찰과 승인된 변경 방향을 구분한다.

## whoosh의 기존 quiet lead를 먼저 읽는다

기존 swing_heavy PCM에는 .20초, swing_charged에는 .28초의 quiet lead가 이미 들어 있다. attack-start playback과 PCM의 첫 nonzero·envelope peak·실제 release/contact 시계를 대조하기 전에 player delay를 추가하면 지연을 이중으로 만들 수 있다. 새 timer나 비동기 재생 지연을 채택한 것은 아니다. hitpause 동안 presentation clock과 audio mixer clock도 같은 방식으로 정지한다고 가정하지 않는다.

[실제 source·offline mix 확인](validation/v0.1.15/source-and-audio-preflight.json)에서는 기존9개 WAV가 baseline과 byte/SHA 동일함을 확인했다. gain을 바꾼 offline peak는 light .1304747/heavy .2348027/charged .3013669/blocked .1233589이며 .8 아래다. 이는 recipe의 PCM 합성 측정이지 실제 Game의 ambience·여러 타격 동시 mix·직접 청취 결과가 아니다.

[공식4.7 audio buses 문서](https://github.com/godotengine/godot-docs/blob/4.7/tutorials/audio/audio_buses.rst)는 master clipping을 피해야 함을 설명하며 Web의 Sample 재생에서는 bus effects에 제한이 있다고 명시한다. Stream 전환과 latency의 조건도 별도다. 현재 작업은 새 limiter/bus 효과·재생 방식 변경을 검증하거나 채택한 것이 아니다. 실제 Game PCM·contact 보고서·소리의 지각 강도·환경/모바일 재생을 다시 확인해야 한다.

## 새 baseline과 후보의 검증 순서

새 baseline14는 `87fcefdd` archive에서 ordinary heavy를 명시적으로 포함한 입력으로 완료했고, 후보 after14의 캡처 pipeline도 종료됐다. 상세 post-take 감사와 최종 시각 판정은 별도다. 예전14초나45초 take는 입력 policy가 달라 이 baseline의 대체물이 아니다. 이후 후보도 같은 `--include-heavy` policy와 실제 조건으로 비교한다. scripted native 입력·logical1x/60Hz encoding은 사람의 플레이·목표GPU60fps가 아니다.

먼저 raw 보존·새 clip과 LUT·실제 import/physics·이동·접촉·pause를 검증한다. 다음 실제 원본에서 일반 heavy와 light3의 차이, 완충 준비/방출/회복, 발과 양손·검·피격자·VFX·camera·원본 mixer PCM을 함께 본다. 실제 입력/AI 궤적은 달라질 수 있으므로 contact·타이밍·health와 위치 변동을 따로 기록한다. raw/native와 실제 Game의 제한된 관측은 아래 근거로 확인했다. desktop/mobile·cleanCI/Pages/release·전체 연속 시청/직접 청취·실기기/AAA는 source 기록 시점에 pending이다.


## 선택006의 raw 보존과 finite pose 판단

[선택 후보 근거](validation/v0.1.15/selected-candidate-pre-native.json)는 source006 SHA `9bb9025621c7aec3690c47a35e0d6946b322f9b4f73f736a10696d1170071a9f`·19,648,124B를 고정한다. 원래14e5 몸체25,059,960B를 보존하고 charge/charged/heavy만 새로 저작했다. 나머지17개 gameplay+RESET의18개 clip, 세 light의 각159 channel과 static payload는 의미·실제 참조 데이터가 같다. compaction 뒤 accessor/view 주소와 BIN 배치는 다르므로 원래 BIN prefix가 같다고 표시하지 않는다.

raw53본 local/global·key/midpoint·60/120Hz 최대 속도는 charge614.812/charged1905.879/heavy1578.302deg/s로2700 아래다. actual Grip/Tip와 Blender 재반입 LUT의 최대 오차는 charged .619mm/heavy .428mm 이내로3mm 기준을 유지한다. active key/midpoint의 기존 front sole 기준140점은 charged2.224mm/heavy2.424mm로10mm 아래다. leg weight를 포함한 넓은 ankle ROI의 약40mm 진단도 보존하며 이를 기존 sole gate나 실제 controller footplant 승인으로 바꾸지 않는다.

피부의 같은 edge1191개는1mm 이상 악화했고 전체 최대 extension은38.618→45.012mm다. RightShoulder/RightArm 근처의 charged .262초에는 같은 edge의 envelope가18.438mm 악화했다. 이 수치와 관절·손목·손가락/compact through-pose·가림 한계는 남는다. 루트와 독립 검토자는 실제 broad blade/hilt/PBR의8개 finite 원본에서 일반 heavy의 양손 머리 위 준비와 charged 높이 대비를 보고 **native prototype 방향만 채택**했다. 전체 skin·연속 motion/AV·AAA 승인이 아니다.

일반 heavy 비교의 camera/lights는 각 source의 명목 root를 따라 old .64m/new0m로 달랐다. actor-relative pose 비교이며 동일 world camera·footplant 증거가 아니다. raw charged tip은 시작2.688m→끝 .157m/path5.034m이고, 이전은2.169m→.347m/path3.430m였다. heavy는2.673m→.180m/path4.879m다. 더 큰 궤적은 실제 접촉·물리·시각 검토를 대신하지 않는다.

## live-reference compaction과 runtime 경로

[손실 없는 live-data 정리](validation/v0.1.15/live-reference-compaction.json)는 원래14e5 GLB를 별도 private 출력으로25,059,960→19,647,964B로 줄였다.5,411,996B는 dead accessor/view/BIN을 정리한 **source container 절감**이다. 모든21 clip과 static 의미·참조 byte를 보존했고, stride/sparse/morph/skin/image/sampler와 잘못된 입력·덮어쓰기/정리 guard의 독립 Python11검사를 통과했다. 이 실험 자체의 source 절감과 달리, 이후 전체 Web은 실제63,348B 증가했다. compaction만의 분리된 PCK 기여량이나 증가 원인을 측정·분리했다고 주장하지 않는다.

저장 주소를 다시 매핑한 뒤에는 파일 prefix 대신 실제 mesh attributes/index·rest/node/skin/inverse bind·weights·material/image payload의 독립 서명을 검사해야 한다. 이는 보호 기준 완화가 아니라 container와 의미 계약을 분리하는 일이다. 첫 native707/3실패는 새 curve의 source 파일명/주소와 옛 eye-fit BIN prefix 가드에서 나왔다. 모션 physics 실패로 일반화하지 않지만 전체 native 성공으로도 표시하지 않는다. 이후 독립 native static payload 검증과 재검사는 아래002 근거로 통과했다.

runtime 곡선은 charged378be01c.../heavy3fc023d2...로 고정했다. candidate의91/111 sample과 수치·나머지 byte는 같고, `asset_path`만 canonical runtime 경로로 치환했다. 역치환으로 candidate 전체 SHA가 복원되는 [경로 적응 근거](validation/v0.1.15/selected-candidate-pre-native.json)를 남긴다. 이는 새 geometry를 옛 곡선으로 바꾼 것이 아니며 contact timing을 완화한 것도 아니다.

후보001 twist 퇴화,002 arm reach1.9mm,003 heavy leg reach11.8mm,004 export 설정의 action 병합,005 LUT action-name suffix 실패는 [기각 원장](../art_source/production/candidates/lyra-decisive-001/rejected-attempts.json)에 보존했다. target/export/name 처리를 고쳤으며 기존 reach/속도/marker/sole 한도를 늘리지 않았다.005와006 GLB는 같은 pose/byte이고 마지막 처리는 정확한 action-name postfix와 보고서 완성에 관한 것이다.


## 현재 native002·export와 실제 Web 용량

[실제 native/preview002](validation/v0.1.15/native-and-preview-002.json)는714검사/0실패·exit0·ERROR0과 양쪽 export를 고정한다. 기존707/3실패는 지우지 않았다. curve의 canonical `asset_path`만 고쳤으며91/111 sample과 나머지 수치 byte는 같다. 새 eye 가드는 옛 BIN prefix 대신 실제 live body view payload를 독립적으로 읽는다. 원본4cc9 SHA를 엄격하게 고정하고 position·PNG·inverse bind의 실제 byte를 각각 변형한 negative3개도 거부했다. 원본과 runtime의 live SHA26cc76e6…가 같지만 이는 animation/dead storage를 제외한 core body/rest/texture 범위이며 전체 skin 승인이 아니다.

ordinary heavy는 실제 반입87 key·LUT111 sample에서 Tip .440671mm/Grip .079162mm/chord .368776mm를 확인했다. 명목 LeftFoot drift는 .015525mm다. 실제 ordinary miss는 active .704m로 끝났고 반입된 점을 사용한 물리 probe는 준비 중 피해 없이42를1회 적용했다. charged는 Tip .635382mm/Grip .114715mm·명목 LeftFoot .015378mm를 확인했다. 실제 controller/접촉의 구체적 native 검사와 새 Game 입력 영상·terrain footplant·시각/청취 승인은 구분한다.

현재 dirty0.1.15·87 preview의 raw Web은149,791,667B/14파일로150MB 미만이며 여유208,333B다. WebZIP119,129,172B·WindowsZIP146,970,528B와 [107 source freeze](validation/v0.1.15/runtime-source-freeze-002.json)를 남긴다. 최종 Web은 실제 v14 비교에서63,348B 늘었다. 새 GLB source가5,411,836B 작아졌다는 사실을 Web 절감으로 해석하지 않으며, payload를 조사하지 않고 PCK가 커진 원인도 추측하지 않는다. 원래14e5를 변경 없이 정리한 private compactor 실험의5,411,996B 절감과 새 동작006의 net source 차이는 다른 값이다.

새 after14 Game 캡처 pipeline과 post-take 감사·peer/루트 finite 검토를 마쳤다. [최종 근거](validation/v0.1.15/actual-game-final.json)와 [전후 원본 영상](validation/v0.1.15/README.md)에 접촉·이동·PCM·보이는 개선과 한계를 남겼다. 큰 머리 위 준비와 fan은 개선됐지만 flat한 fan·어깨/손목·전체 리듬/청취는 별도다. desktop/mobile·CI/공개/릴리스·전체 연속 시청/직접 청취·full skin/실기기/AAA도 pending이다.


## 실제14초 캡처 종료와 아직 남은 판정

[현재 pipeline readback](validation/v0.1.15/actual-game-pipeline-preliminary.json)은 before와 after 모두864 delivery frame/14.4초·raw868 frame·48kHz stereo694,400 sample frame·정확한 WAV prefix691,200을 보고한다. 추가 음악·시간 보간 없이 출력했고 engine ERROR0·audio resource release·프로세스 종료를 확인했다. wall 시간은 before471.042초/after327.144초이며 실시간FPS가 아니다.

baseline contact610/release586과 후보 contact621/release595는 다르다. 후보의 실제 완충 접촉은1회69.3·shared pause5 frame·HP120→88이며, ordinary heavy active13 sample/일반 heavy whiff·charged whiff도 기록됐다. heal input1회/실제 소비0회·parry 성공0회는 그대로 남긴다. 입력 policy를 맞췄다는 사실과 실제 AI 궤적·접촉 시각의 동일성을 구분한다.

루트는 일반 heavy 첫 active와 contact04의 실제 전후 원본을 직접 보고 overhead/fan의 차이가 명확하다고 보고했다. 이 예비 관찰 뒤 [실제 최종 감사](validation/v0.1.15/actual-game-final.json)와 독립 finite 원본 검토에서 제한된 준비/궤적 개선을 채택했다. 이14초 촬영은 skill 수정 전107 source 범위로 보존한다. raw PCM 보존·logical1x 영상 출력은 전체 연속 시청·직접 청취·AAA 승인이 아니다.


실제 ordinary heavy의 root travel은2.091251→.7039995m이며 준비 중 glide는0이다. 완충 강타는 release595/contact621에69.3을1회 적용하고 양쪽pause5tick을 유지했다. 기존 접촉610과 같게 retime하지 않았다. 12개 paired raw 원본과 native 일반heavy 첫active/접촉 원본을 직접 검토했다. 당시 Hero/feet/상대는 읽히며 모든 공격 tip sample이 프레임 안이었다. 이후 unchanged dodge에서는 tip만5tick 좌측으로 벗어나 baseline3tick보다 늘었다. 전체 mesh/UI containment 승인이 아니다.


## full mobile에서 발견한 스킬의 heavy profile 상속 회귀

[실제 실패와 수정 경계](validation/v0.1.15/skill-inheritance-failure-and-fix.json)는 새 일반 heavy의 물리 곡선이 기존 스킬 생성 코드까지 흘러간 문제를 보존한다. 수정 전 `RunePlayer.use_skill()`은 `HEAVY.duplicate()`로 데이터를 만든 뒤 skill startup/active를 .16/.35초로 바꿨다. 그러나 새 heavy의 physical blade flag와 .32/.22초 curve는 그대로 상속했다. 실제 스킬을 실행하자 곡선의 시간 계약과 AttackData가 불일치해 fail-closed로 거부됐다. 이 가드를 완화하거나 heavy LUT를 스킬 시간에 맞춰 바꾸는 것이 해결책은 아니다.

수정 전 CI run41575785813의 native714/0·desktop423.370초·charged302.326초는 통과했다. PR16의 run #72에서 full mobile1383.425초는 journey와 restart에 도달했지만 마지막 `assert not qa.errors`에서 실패했다. 앞선 `hold_heavy_dodge_parry_heal_skill` 단계의 실제 curve timing 오류가 남아 있었기 때문이다. timeout이나 환경 실패가 아니다. 앞선 제한된 통과를 전체 게임 승인으로 확대할 수 없음을 보여 준다. root는 `AttackData.new()`로 스킬 데이터를 독립 생성하고 기존 명시적 스킬 값을 적용했다. [새 native735/0](validation/v0.1.15/native-and-preview-skillfix-003.json)에서 실제 세 스킬의 물리 피해·범위·룬 비용·중복 방지·돌진을 확인했다. 수정 뒤 clean CI와 공개 실행은 별도 pending이다.

기존14초 after trace864행에는 light/ordinary heavy/charged만 있으며 `skill_` attack 행은0이다. 따라서 기존 몸체9bb·LUT·모션/VFX의 finite 판정은 그 관측 범위에서 남지만, 스킬 수정 후 whole-Game byte 증거나 새 native/모바일 통과가 되지는 않는다. 다른106/107 runtime source의 보존 주장과 수정한 player의 새 전체 검증을 구분한다. 실패 원본과 새 수정 결과를 각각 고정한 뒤 상태를 갱신한다.

실제 `08-skill-one` readback은 skill1의 startup .16/active .35/duration .79를 기록했고 active speed는3.200000286이었다. inherited `phase_lunge=true`가 원래 skill1의 lunge13보다 heavy의 active_lunge3.2를 우선시킨 별도 이동 상속 문제와도 일치한다. 이 이동 관찰을 곡선 거부 assertion의 직접 원인과 섞지 않는다. 실패 artifact는 실제11,261,897B·API/다운로드SHA/ZIP CRC를 확인했고, restart 상태를 봤다는 사실은 오류 없는 full-mobile 통과가 아니다. 수정 native735/0은 후속 근거로 통과했다. 새 전체 browser/CI·공개 검증은 별도 pending이다.


최신 skillfix003 preview는735/0·ERROR0, Web raw149,791,651B·여유208,349B와 Windows export를 확인했다. 새 native21검사를 담은 실제 player skill fixture를 source roster에 추가해108개로 고정했다. 이전107개 중 player와 checker를 고치고 combat regression을 추가한 의도적인 계보다. body9bb/곡선·무기·VFX·camera/audio 파일 SHA는 그대로다.
