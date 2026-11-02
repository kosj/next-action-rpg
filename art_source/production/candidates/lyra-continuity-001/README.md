# 후보006: prototype 범위 채택·native와 실제 입력 기록

현재 source는 `source-006-guarded.glb`(`14e5069a…`)다. ROOT가 동일 bytes를 런타임에 설치하고 native692/0·Web/Windows export·실제 입력의45초 첫 전투 기록을 확인했다. 현재 결과는 [검증 기록](../../../../docs/validation/v0.1.14/README.md)과 [전후 영상](../../../../docs/validation/v0.1.14/gameplay-comparison/README.md)에서 범위를 구분한다. 과거 pending 저작 보고서는 생성 당시 상태로 보존한다. **전체 피부·연속1x AV·하드웨어·AAA 승인은 없다.**

006은005의 새 자유손 위치·팔꿈치 경로를 그대로 두고, freephase wrist만 실제 idle-grasp local에서 실제 bind/rest local로 quintic blend한다. 원본 idle/start/end grasp, 오른손/검, body/feet, 다른150채널·18클립·정적 geometry/rest/weights/maps는 그대로다. 원본의 in-action 왼손 key를 보존하는 수정이라고 주장하지 않는다.

전53본60/120Hz·모든key/mid 각속도 최대1363.726°/s는 기존2700°/s 이내다. 새 `source-006-guarded.targets.json`과 실제 GLB의 hand 위치 최대1.051mm는 기존3mm 이내다. 각clip의 원본hand key와399/429/401mm, 방향52/57/52°까지 달라지는 의도적 재저작이며 source-idle grasp는 정확히 돌아온다.

ROOT와 별도 실제4장 검수는 `.33` 노출된 underarm old/new 및 `.25` front old/new의 prototype 방향을 채택했다. 낮은 counterguard·어깨·펴진 wrist가 읽히며 선택뷰에 명백한 background hole/needle은 보이지 않았다. 어두운 underarm fabric/crease/shadow는 남아 있고,127개edge의1mm이상 envelope 악화와 최악+15.814mm를 합격으로 지우지 않았다. 같은 `.33` pose의 해당 edge 길이는 old36.889mm→new56.538mm다.

`studio-006-actual-broad/`는 실제4fd geometry를 원래68df root/markers/PBR material과 합성해 ActorVisual과 같은 구성으로 촬영했다. 4장 실제marker는 raw source와 grip0.000360mm/tip0.001361mm 이내로 맞는다. 기존 `studio-006-first/`6장은 **old slim blade를 쓴 body/wrist 증거**다. 원본 report·사진·구도는 바꾸지 않고 `studio-weapon-scope-correction.json`으로 용도를 바로잡았다.

실제 broadblade에 대한 유한 raw LBS active hand-vertex 최소거리는 blade188.838mm/hilt68.386mm, 보수적 전체손삼각형 edge bound는144.125/23.673mm다. source/PI/25mm/socket 변환은 adoption 전601a chargedLUT의181점에서 grip0.037mm/tip0.288mm 오차로 보정했다. ROOT의 LUT metadata-only source핀 변경8946…은 byte역치환으로601a 원문을 복원한다. 샘플/시간·모든비metadata byte는 그대로다. 유한 표면 거리로 연속 무교차나 실제 Game카메라의2D읽힘을 승인하지 않는다.

최초006실패는 quintic roundoff가 strict slerp factor 범위를 미세하게 넘은 것으로, graft 전에 GLB가 없었다. 실제 snapshot·로그를 보존했다. 현재 helper는 polynomial 결과가1e−12 이상의 유의한 범위초과이면 실패하고 roundoff만[0,1]로 반환한다. 유효한 초기retry와guarded결과 GLB bytes는 같아 중복파일을 `006-duplicate-storage-receipt.json`으로 정리했다.2700/3mm 기준은 바꾸지 않았다.

재저작은 새 빈 출력 경로로 실행한다.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/blender -b --factory-startup --python-exit-code 1 --python tools/author_continuity_actions.py -- --recipe art_source/production/character_actions/lyra-continuity-neutral.json --output /workspace/.runefall-task/combat-continuity-polish/reproduced-006.glb
```

현재 근거는 `semantic-review.json`, `raw-preservation-006.json`, `rates-all-schedules-006.json`, `hand-target-review-006.json`, `skin-lbs-006.json`, `hand-weapon-clearance-006.json`, `weapon-frame-calibration-006.json`, `independent006-actual-broad-review.md`, `root-adoption-006.json`이다. 아래005/004내용은 각 검토 당시의 역사다.

---

# 후보005: 자유 왼팔 counterguard 재저작

현재 `source-005.glb`(`2b2732b0…`)를 추가 검증 중이며 **런타임은 원본 f2ed 그대로**다. 001–004는 거절했고 004의 숫자 통과도 실제 높은 팔꿈치 자세를 정당화하지 않았다.

005는 원본 왼손 world key를 그대로 보존하는 수정이 아니다. 자유 왼손을 몸에 동행하는 낮은 counterguard로 다시 저작했다. 원본 key와 위치399/429/401mm, 방향100/106/101°까지 달라진다. 원본 idle/start/end grasp, 오른손/검, body/feet, 다른150채널·18클립과 geometry/rest/skin/weights/maps는 보존한다.

새 독립 semantic target은 `source-005.targets.json`에 key와 midpoint351개로 기록했다. 실제 decoded GLB와 최대1.051mm 차이로3mm 기준 안에 있다. 전53본60/120Hz·key/mid 각속도 최대1363.726°/s는 기존2700°/s 안에 있다. 이것은 실제 Godot나 AAA 품질의 합격이 아니다.

Root가 실제 L2 .13/.25 front/opposite4장을 확인해 낮은 counterguard를 추가 검증 대상으로 채택했다. 그러나 free wrist가 처져 보인다. 원인은 idle의 무기-grasp wrist-local이 실제 bind/rest 중립과64.274° 다르기 때문이다. 다음006은005 손 위치·팔꿈치를 유지하고 freephase에 손목만 실제 bind 방향으로 blend하도록 승인됐지만 아직 생성하지 않았다.

피부127edges는 원본 envelope보다1mm 이상 악화한다. 최악 L2 .330s thorax/armpit 혼합edge의 +15.814mm는 아직 실제 raster 검수 전이다. 이 edge에는 Hand 가중치가 없어 손목만 바꾸는006이 이를 해결한다고 주장하지 않는다.

실제 runtime broadblade geometry와 production socket을 사용한 유한 raw LBS 거리는 L2 .25에서 hand-vertex→blade234.976mm/hilt221.102mm다. 이 수치는 같은 프레임의 보수적 손삼각형 edge bound와 함께 보고했다. socket/scale/PI/25mm 변환은 unchangedcharged91LUT의181key/mid에서 grip0.037mm/tip0.288mm 오차로 독립 보정했다. 연속 intersection-free, 실제 게임카메라의2D읽힘, 회수 grasp 접촉이나 AAA를 합격 처리하지 않는다.

005 근거는 `semantic-review.json`, `raw-preservation-005.json`, `rates-all-schedules-005.json`, `hand-target-review-005.json`, `skin-lbs-005.json`, `hand-weapon-clearance-005.json`, `weapon-frame-calibration-005.json`, `studio-005-first/`다. 아래는 거절한004의 역사다.

---

# 리라 일반 3연격 연속성 후보

`source-004.glb`(`9f0d00ac…`)는 높은 팔꿈치·늘어진 전완·올라간 견갑 갑옷의 실제 포즈가 나빠 **아트 채택에서 거절했다.** 런타임에 반입하지 않았다. 다음005는 자유 왼손 target 자체를 낮은 counterguard로 다시 저작한다. 원본은 `../lyra-fury-001/source.glb`(`f2edbd37…`)이고, 초기 세 실패 후보와 실제 저작 도구·레시피 스냅샷도 보존했다.

원본 light_1/2/3은 고정 pole이 팔 축을 통과하면서 왼쪽 상완·전완·손목이 급회전했다. 새 후보는 가슴 기준 elbow-plane parallel transport와 각 팔 뼈 축의 최소회전, 부드러운 endpoint 축회전 보정을 쓴다. light_2의 45° load-plane 편향은 의도적인 새 팔꿈치 자세다. 이 envelope의 미분은 경계에서 연속이지만, glTF의 전체 관절 속도가 연속이라는 뜻은 아니다.

| 실제 raw FK | 원본 | 후보004 |
| --- | ---: | ---: |
| light_1, 60Hz 최대 local 회전 | 152.030° | 38.652° |
| light_2, 60Hz 최대 local 회전 | 155.451° | 39.575° |
| light_3, 60Hz 최대 local 회전 | 133.459° | 29.800° |
| 3클립 전체 key/mid 최대 각속도 | 원본 branch 급회전 | 2594.187°/s |

원본100Hz world hand key 위치·방향은 float32 오차 범위에서 보존한다. 오른손/검, body/feet, 다른150채널, 다른18클립, 원본 BIN prefix와 정적 geometry/rest/skin/weights/maps 선언은 그대로다. 왼손의 원본 FK midpoint pop은 보존 대상이 아니다. world key 사이 선형 목표에 대한 최대 오차가38.194/73.298/37.952mm에서3.742/3.657/1.993mm로 줄었다. 오른손 midpoint는 원본과 정확히 같다.

팔꿈치 경로는 새로 저작했다. light_2는 후보003과 최대169.842mm, 원본과 최대415.415mm 다르다. light_1/3도 원본 branch의 반대편 경로와347.813/353.041mm 다르다. 원본 손 목표와 각 key의 상완/전완 길이를 지키는 다른 IK 해이며, 해부학적 자연스러움은 별도 검수가 필요하다.

피부에는 실제 tradeoff가 있다. 351개 key+midpoint의 팔 영역23,800edges 중345개는 원본 envelope보다1mm 이상 늘어났다. 최악은 light_2 .250s의 왼쪽 어깨–상완 edge로 +14.851mm 악화했다. 전체 최대 확장은36.863mm로 같고 p99는1.618→1.552이지만 이 요약으로 국소 결함을 합격 처리하지 않는다. 최소 삼각형 면적비도 .001323→.000772로 악화했다. `skin-lbs-004.json`과 실제 같은 카메라 raster를 함께 검토해야 한다.

현재 raw 수치는 사전2700°/s 기준 안에 있다. Godot 실제 import/양손·검/전환, 실제 게임1x 영상·소리, 연속 피부/접촉/충돌, 성능/기기, AAA 품질은 아직 승인되지 않았다. 원본 charge/charged_heavy와91점 blade curve 값·시간에는 변화가 없다.

재현은 저장소 루트에서 새 빈 출력 경로로 실행한다.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/blender -b --factory-startup --python tools/author_continuity_actions.py -- --recipe art_source/production/character_actions/lyra-continuity.json --output /workspace/.runefall-task/combat-continuity-polish/reproduced.glb
```

원본/후보 SHA, 실제 저작 도구·레시피, 정적 보존, 손/idle join, raw 회전, 피부 증거를 각각 분리했다. 실패 수치는 `rejected-motion-summary.json`에 기록했다.

유한 hand/weapon 거리와 socket 보정은 다음 read-only CLI로 재계산할 수 있다. 실제 source/geometry/config SHA가 결과에 기록되며 Blender/Godot/네트워크를 호출하지 않는다.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 art_source/production/candidates/lyra-continuity-001/hand_weapon_clearance.py --body art_source/production/candidates/lyra-continuity-001/source-005.glb --output /tmp/lyra-clearance.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 art_source/production/candidates/lyra-continuity-001/calibrate_weapon_frame.py --body art_source/production/candidates/lyra-continuity-001/source-005.glb --output /tmp/lyra-socket-calibration.json
```
