# 게임용 캐릭터 동작 저작

리라 19개·수호병 9개 상태와 각각 RESET을 Blender 4.3.2에서 새로 저작합니다. 입력 GLB에서는 메시·재질·53본 REST/skin만 사용하고 기존 Action을 모두 삭제합니다. stock 키를 복사하거나 시간 축만 줄이지 않습니다. `tools/author_character_actions.py`의 전신 포즈/손 IK와 `tools/character_gait.py`의 다리 IK를 사용하며 모든 본의 위치·회전·스케일을 100Hz로 기록합니다.

입력과 설정:

| 캐릭터 | 원본 후보 | 저작 설정 | 축약 검증 |
|---|---|---|---|
| 리라 | `../candidates/lyra-web-001/motion-library.glb` | [lyra.json](lyra.json) | [lyra-authoring-summary.json](lyra-authoring-summary.json) |
| 수호병 | `../candidates/sentinel-web-001/locomotion.glb` | [sentinel.json](sentinel.json) | [sentinel-authoring-summary.json](sentinel-authoring-summary.json) |

저장소 루트에서 검증된 Blender 실행 파일로 다음 명령을 실행합니다. 출력 GLB와 `.authoring.json`은 기존 파일을 덮어쓰지 않으므로 재현할 때 새 출력 경로를 사용합니다.

```bash
blender -b --factory-startup --python tools/author_character_actions.py -- \
  --source art_source/production/candidates/lyra-web-001/motion-library.glb \
  --recipe art_source/production/character_actions/lyra.json \
  --output build/art-candidates/character-integration/reproduction/lyra-gameplay.glb

blender -b --factory-startup --python tools/author_character_actions.py -- \
  --source art_source/production/candidates/sentinel-web-001/locomotion.glb \
  --recipe art_source/production/character_actions/sentinel.json \
  --output build/art-candidates/character-integration/reproduction/sentinel-gameplay.glb
```

원본 SHA, 53본 역할, topology와 상속 규칙을 검사하고 원본 해시를 종료 전에 다시 확인합니다. 내보낸 GLB의 실제 클립 이름·개수·길이·skin·내장 리소스를 검증한 뒤 새 파일로 게시합니다. 기존 출력 거부와 변조된 본 역할 거부의 재현 결과는 [author-tool-guard-validation.json](author-tool-guard-validation.json)에 있습니다.

## 게임 시간과 이동

리라 `light_1/2/3`의 길이는 각각 0.52/0.52/0.70초이며 active 창은 0.13–0.30/0.13–0.30/0.18–0.40초입니다. 해당 창에서 실제 검 방향이 게임 `AttackData`의 −arc/2에서 +arc/2로 진행하도록 손의 세계 IK를 저작합니다. `heavy`, `skill_1/2/3`, `charge`, `dodge`, `parry`, `hit`, `heal`, `death`도 개별 동작입니다. 구체적 창과 내보낸 부동소수 길이는 축약 검증을 참조합니다.

`charge`는 0.65초에 준비 포즈에 도달하고 입력을 계속 잡고 있으면 그 마지막 포즈를 유지합니다. 초기 pulse 초안의 끝 포즈 복귀를 수정했고, 실제 GLB의 소켓 상승·수평 Root 고정·다른 19개 클립 샘플 불변을 [charge-hold-validation.json](charge-hold-validation.json)에 기록했습니다.

리라 전방/후방/횡이동은 6.4m/s·0.48초, 달리기는 8.5m/s·0.40초 기준입니다. 수호병 이동은 3.6m/s·0.70초입니다. 후방/횡이동은 발의 세계 목표와 골반·가슴 반대 회전을 사용하며 캐릭터 전체를 돌려 전방 걸음으로 바꾸지 않습니다. 이동 루프의 끝 포즈는 시작과 같고, 실제 skinned sole 정점의 stance 속도를 코드 이동 기준으로 측정합니다. glTF 루프 메타데이터에 의존하지 않으며 런타임은 검증된 루프의 복제 Animation 리소스에만 loop flag를 지정합니다.

이 GLB에는 무기나 게임 이동·피해·충돌 트랙이 없습니다. 게임이 움직임과 판정 시간을 소유하고 스킨은 해당 시각의 포즈만 표시합니다. Root는 고정이며 전투 중 Hips의 수평 이동도 없습니다. `skill_2/3`의 넓은 피해 반경은 룬 VFX 표현으로, 검 길이의 물리적 접촉 범위를 뜻하지 않습니다.

## 손과 무기 계약

무기의 정규 blade 축은 +Y입니다. RightHand 소켓의 단위 기저 열은 `(0,0,1), (-1,0,0), (0,-1,0)`이고 리라 물리 offset은 `(0.055,0.10,-0.060)m`입니다. 수호병 offset은 이 값을 `1.95/1.82`배 합니다. 런타임 무기 자식의 scale과 local offset은 보고서의 실제 rig uniform scale로 나눠야 합니다. 기존 wrapper scale을 그대로 무기에 상속하면 크기와 위치가 달라집니다.

손가락 curl은 [grip-recipe-selection.json](grip-recipe-selection.json)의 실제 메시 비교로 캐릭터별로 선택했습니다. 리라는 `[.65,1.35,1.40]`, 손 형상이 다른 수호병은 `[.20,1.10,1.40]`을 사용합니다. 수호병의 선택 동작에서 같은 curl을 공유했을 때의 약 10.8mm 겹침을 약 0.09mm로 줄였으며, 접촉 없이 손을 벌린 후보는 제외했습니다. 리라 미리보기에서 허용한 국부 손/자루 겹침은 약 2.5mm이며 모든 행동에 같은 검수 그립을 유지합니다. 손가락별 형상·웨이트 수정은 남아 있습니다. 이 값은 최종 해부학적 그립 승인이나 전체 프레임의 접촉 합격을 뜻하지 않습니다.

## 검증 범위

축약 검증의 구조·클립 시간·원본 불변·IK reach clamp·루프·접지 수치는 실제 Bpy 평가 결과입니다. 전체 프레임별 결과는 `build/art-candidates/character-integration/{lyra,sentinel}-gameplay.authoring.json`에 있습니다. 메시 edge stretch는 실제 길이 2mm 이상인 edge를 10Hz와 끝점에서 측정한 수치이며 자동 품질 승인 기준으로 사용하지 않습니다. 독립 Godot 감사와 실제 화면 검수는 캐릭터 반입 문서 및 후보 manifest에서 별도로 추적합니다.

현재 결과는 절차적으로 저작한 플레이 가능한 아트 미리보기입니다. 임의의 이동 위상에서 행동으로 전환하거나 동작을 취소할 때 crossfade가 없어 포즈가 튈 수 있습니다. 최종 손·의상 변형, 얼굴/재질·조명, 애니메이션 polish, 플랫폼별 성능 및 AAA 수준 승인도 별도 작업입니다.
