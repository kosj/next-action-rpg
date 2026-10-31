# 캐릭터 국소 개선과 검수 범위

기준일: **2026-10-31**. 이번 작업은 기존 리라·수호병의 국소 변형, 리라의 눈 형상, 검 궤적의 표현을 개선하는 제작 단계다. **최종 AAA 아트 승인은 `pending`**이다. [승인 기준](AAA_ART_QUALITY.md)과 [현재 캐릭터 반입](CHARACTER_INTEGRATION.md)을 함께 적용한다.

## 이번 작업의 판단

| 대상 | 실제로 한 작업 | 현재 판단과 근거 |
| --- | --- | --- |
| 흉갑 웨이트 | 원래 네 joint 슬롯을 유지한 작은 영역의 제약 최적화. exported key와 midpoint를 원본과 비교 | **불채택**. 목표 edge 개선이 리라 0.365mm·수호병 0.515mm에 그쳤다. 갑옷 변형을 해결하지 못했고 원본 웨이트를 유지했다. [검수 기록](../art_source/production/character_polish/weight_review/README.md) |
| 평면에 가까운 눈 삽입 | 원본 얼굴을 유지하며 별도 눈 표면을 맞추고 동일 스튜디오 카메라로 재반입 비교 | **불채택**. 선명한 동공도 얕은 눈꺼풀 위의 그래픽 삽입처럼 보였다. 거리·비관통 수치가 형태 품질을 보장하지 않았다. [결정](../art_source/production/character_polish/rejected_eye_inlays/decision.json) |
| 눈 소켓·안구 | 원본의 그려진 눈 안쪽 삼각형을 국소 절단하고 안쪽 rim·소켓 벽과 곡면 안구를 제작. 교차가 남은 첫 fit을 반려하고 안구 중심만 안쪽으로 재배치 | **국소 형상·native 기술 반입 개선을 프리뷰에 채택**. 최종 몸체·Web 안구가 runtime과 일치하며 통합 native 검사를 통과했다. 실제 Web 화면과 최종 AAA 승인은 별도 범위다. [고정 후보](../art_source/production/candidates/lyra-eye-sockets-001/refit.json) |
| 검 궤적 | 실제 표시된 검의 grip/tip 이력을 짧은 world-space ribbon으로 표현. 같은 포즈·카메라에서 on/off와 ADD/MIX 비교 | **ADD 프리뷰 유지, MIX 불채택**. MIX는 밝은 돌 위에서 대비를 낮췄다. 실제 속도의 교전 가독성은 아직 별도 검수 대상이다. [Web 비교](../art_source/production/character_polish/blade_trail_review/README.md) |

웨이트 실험의 초기 raw-unit solver 실패는 수선 불가능의 증거가 아니다. 같은 물리 조건을 정규화하자 solver는 종료했지만 개선 효과가 작았다. 리라 결과의 엄밀한 0.25mm 상한 초과와 수호병의 추가 면적 압축도 [원본 보고서](../art_source/production/character_polish/weight_review/README.md)에 보존했다. 최종 normalized 제안은 메모리에서만 평가했으며, 새 GLB·렌더나 시각 합격은 없다.

## 눈 후보의 변경 계약

[소켓 제작 도구](../tools/derive_character_eye_sockets.py)는 원본 GLB를 보존하고 새 파일에만 변경한다. 눈 안쪽의 그려진 표면을 제거하고, 경계에 연속된 안쪽 rim·벽을 만든 뒤 그 뒤에 곡률이 있는 안구를 둔다. 기존 몸 전체를 재생성하거나 눈 위에 불투명 그림을 추가하는 방식으로 처리하지 않는다. 원본 attribute row, 눈 바깥 삼각형, 기존 재질·스킨·애니메이션의 보존 범위는 파생 보고서와 해시로 확인해야 한다.

안구는 Head의 REST rigid-local 좌표와 identity root를 계약으로 사용한다. 런타임의 [ActorVisual](../game/scripts/actors/actor_visual.gd)은 `eye_socket`·`eye_model`을 두고 최종 Head 본 표본 뒤 attachment를 갱신한다. [최종 눈 native 보고서](validation/v0.1.5/character-eyes.json)는 실제 19개 gameplay 클립의 57표본에서 같은 프레임의 Head 추종, REST 앵커·단위·외부 변환·보간·hit pause를 확인한다. 이는 얼굴의 모든 접촉·변형을 승인하는 검사가 아니다.

첫 socket-001 fit은 안쪽 rim만 확인해 주변 얼굴 삼각형과 안구의 교차를 놓쳤다. [반려한 실제 재반입 검사](../art_source/production/character_polish/rejected_socket_fit/bvh-pose-check.json)를 보존했다. 이 실패를 좌표계 착시로 설명하거나 비관통으로 바꾸지 않는다. 이후 몸체와 attachment basis는 유지하고, 두 안구 중심만 source world -Z 방향으로 각각 **2.192mm·1.050mm** 옮겼다.

[최종 refit](../art_source/production/candidates/lyra-eye-sockets-001/refit.json)은 20클립의 exported key/midpoint **2,358시점·주변 몸체 484삼각형**을 cornea 최대 돌출을 포함한 **반지름 12.8mm의 보수적 구**로 검사했다. 최소 여유는 **+0.551mm**다. [최종 실제 GLB 재반입 BVH](../art_source/production/candidates/lyra-eye-sockets-001/bvh-pose-check.json)는 REST·yaw ±15°·pitch ±10°의 5개 Head 포즈에서 교차쌍 0개를 기록했다. 모두 유한 표본이며 연속 동작 전체의 접촉·시각 승인을 대신하지 않는다.

[source-audit](../art_source/production/candidates/lyra-eye-sockets-001/source-audit.json)은 이전 안구 `81331…`로 수행한 **과거** 몸체 보존 검사다. 이를 최종 안구 검사로 덮어쓰지 않았다. [refit-delta-audit](../art_source/production/candidates/lyra-eye-sockets-001/refit-delta-audit.json)이 같은 몸체 `4cc9…`와 최종 Web 안구 `d7d984…`를 연결하며, 안구의 변경이 중심 평행이동뿐이고 indices·normal·색·topology·attachment가 같음을 확인한다. 보관된 [몸체](../art_source/production/candidates/lyra-eye-sockets-001/source.glb)와 [Web 안구](../art_source/production/candidates/lyra-eye-sockets-001/eyes-web.glb)는 실제 runtime 파일과 일치한다.

Godot 4.7.2의 실제 반입에서 첫 primitive의 `COLOR_0` 재질 flag가 꺼지는 문제도 발견했다. [눈 전용 post-import](../game/import/eye_materials.gd)로 해당 안구의 세 PBR 재질만 vertex color를 사용하게 했으며 원본 GLB는 변경하지 않았다. [집중 검사 로그](validation/v0.1.5/eyes-native.log)는 세 flag와 원본의 흰색이 아닌 색 표본을 8-bit 채널 정밀도 안에서 확인한다.

몸체는 **32,288삼각형**으로 계획된 Web 몸체 32,000보다 **288개 초과**한다. 별도 안구 **3,840개**를 합치면 장비 전 36,128개다. 이 수치를 경량화·프레임 성능 합격으로 기록하지 않으며 추가 예산 조정과 실제 하드웨어 측정이 남아 있다.

실제 Game 조명·재질에서도 [6구도×품질0/1 Web12장](validation/v0.1.5/eyes-web-reference/review.json)을 확인했다.317.962초·오류0, 세 색상 사용 flag와 Head 소켓 오차0이 유지됐다. 큰 어두운 동공·주변부와 강한 응시는 아직 남는다. 홍채/동공 RGB만 바꾼 후보는 [같은4화면 비교](validation/v0.1.5/eyes-web-palette/review.json)에서 개선이 미미해 기각했다. 실제 Web PCK 색 적용도 독립 확인하여 오래된 cache를 원인으로 돌리지 않았다. 위치·노멀·인덱스·재질을 그대로 둔 시도였으며 최종 안구는 d7d를 유지한다.

## 검 궤적의 표현 계약과 실제 Web 증거

[BladeTrail](../game/scripts/actors/blade_trail.gd)은 실제 표시된 검의 grip/tip을 표본화한다. 피해 판정·검 길이·게임의 공격창은 기존 코드가 소유한다. 궤적은 현재 공격의 반열린 active 구간에서만 이력을 추가하고 0.12초 동안 사라진다. hit pause는 형상과 나이를 고정하며 공격 변경·시점 이동·epoch·우선 행동·큰 위치 불연속에서 이전 이력을 끊는다. ADD, depth test 유지, depth write·그림자 비활성화가 현재 표현 설정이다.

보관한 Web 비교는 **실제 Game 첫 방과 RuneCamera를 사용한 고정·정지 fixture**다. Godot 4.7.2 Web GL Compatibility, Chromium SwiftShader, 1440×900, quality0에서 light_1의 실제 marker 이력을 60Hz로 표본화한 뒤 0.18/0.24초를 고정했다. detail 샷은 의도적으로 카메라를 가까이 옮겼다. on/off 각 쌍의 카메라·포즈·조명·품질은 같지만 라이브 입력 교전이나 목표 GPU 성능 검사는 아니다.

공개 보관본에는 [실제 플레이 카메라 ADD](../art_source/production/character_polish/blade_trail_review/01-game-trail-024.png), [근접 ADD](../art_source/production/character_polish/blade_trail_review/05-detail-trail-018.png), [같은 근접 샷의 궤적 off](../art_source/production/character_polish/blade_trail_review/06-detail-no-trail-018.png)가 있다. 나머지 비교 이미지와 MIX 이미지는 ignored build에만 남고 [보고서](../art_source/production/character_polish/blade_trail_review/review.json)·[MIX 판정](../art_source/production/character_polish/blade_trail_review/mix/review.json)·[보관 해시](../art_source/production/character_polish/blade_trail_review/archive.json)로 범위를 구분한다. 이 캡처는 눈 소켓 몸체 채택 이전 판본이다.

ADD도 밝은 돌 위에서는 옅어지고 뒤쪽 플레이 카메라의 0.24초 포즈는 edge-on이라 약하게 보인다. MIX는 그 대비를 더 낮춰 기각했다. 큰 부채꼴로 가리거나 공격창을 늘리는 대신, 실제 교전에서 적 예고·몸·칼과 겹치는 구간을 확인해 원거리 끝의 대비를 다듬어야 한다.

## 아직 남은 품질과 최종 통합

현재 v0.1.5 작업 판본은 최종 `4cc9…` 몸체·`d7d984…` 안구와 검 궤적을 포함해 [native 통합 345검사·실패 0](validation/v0.1.5/native.log), [눈 집중 21검사·실패 0](validation/v0.1.5/eyes-native.log)을 확인했다. [입력 해시와 범위](validation/v0.1.5/character-eyes.json), [실제 blade-marker 궤적 검사](validation/v0.1.5/blade-trail.json)를 보관했다. native 보고서 생성 당시의 입력을 구현 커밋 `c6be1dce`에 고정했다. 두 품질의 정지 Web12장·317.962초와 [정상 플레이/영구 저장/완전 재시작](validation/v0.1.5/local-web-final/README.md)471.812초·오류0을 확인했다. Web/Windows export와 실제 ZIP CRC·SHA·실행 파일/라이선스도 통과했다. 공개 main/tag의 CI·Pages 실행과 Windows 실기기·최종 AAA는 별도 범위다.

- 얼굴: 눈꺼풀 두께·소켓 깊이·안구 접촉, 정면/사선/측면과 Head 포즈, 피부·입·코의 근접 재질, 실제 게임 시선·표정 범위.
- 머리·의상: 덩어리처럼 보이는 머리카락의 실루엣·가닥·표면, 의상 소유권과 충돌, 갑옷 plate 경계·어깨/흉갑의 찢기는 변형.
- 손·전투: 손가락·손목·그립의 형태와 검 접촉, 모든 모션·교차 전환의 관통, 공격 발디딤과 이동 발 접촉·미끄러짐.
- 장면·VFX: 같은 최종 자산의 실제 1배속 교전, 취소·hit pause·다수 적·UI/예고와 궤적의 가독성, Web 품질0/1과 Windows의 같은 구도.
- 성능: GPU/CPU·OS·렌더 경로·해상도를 명시한 목표 하드웨어의 프레임 시간·메모리·로딩. SwiftShader 정지 캡처나 headless 통과를 실기기 합격으로 기록하지 않는다.

제작 산출물·반려 증거의 위치는 [character_polish 보관 안내](../art_source/production/character_polish/README.md)에 연결한다. 원본 수치·해시는 각 보고서를 원본으로 사용하고, 다음 판본의 통과를 이전 판본에 소급하지 않는다.
