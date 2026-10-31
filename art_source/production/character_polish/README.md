# 캐릭터 국소 개선 자료

2026-10-31의 흉갑 웨이트·리라 눈·검 궤적 검토를 보관한다. **AAA 승인 상태는 `pending`**이다. 변경 범위·반려 이유·남은 검사는 [캐릭터 개선 기록](../../../docs/CHARACTER_POLISH.md), 전체 승인 조건은 [AAA 기준](../../../docs/AAA_ART_QUALITY.md)을 따른다.

| 자료 | 용도와 판정 |
| --- | --- |
| [weight_review](weight_review/README.md) | 원래 4-slot support를 유지한 작은 흉갑 영역 최적화. 개선 효과가 작아 리라·수호병 모두 불채택. normalized 최종안은 메모리 평가이며 새 GLB·PNG·시각 합격 없음 |
| [rejected_eye_inlays/decision.json](rejected_eye_inlays/decision.json) | 평면에 가까운 별도 눈 삽입의 불채택 기록. REST 근접 스튜디오 렌더이며 게임 캡처가 아님. 비관통 수치만으로 채택하지 않음 |
| [rejected_socket_fit/bvh-pose-check.json](rejected_socket_fit/bvh-pose-check.json) | 첫 소켓 fit의 실제 재반입 교차 실패. 안쪽 rim만 확인해 주변 몸체 교차를 놓친 증거이며 좌표계 문제로 재해석하지 않음 |
| [최종 소켓 후보](../candidates/lyra-eye-sockets-001/refit.json) | 몸체 `4cc9…`를 유지하고 두 안구 중심만 안쪽으로 2.192mm·1.050mm 이동. 최종 Web 안구는 `d7d984…`. 국소 형상·native 기술 반입 개선을 프리뷰에 채택 |
| [rejected_socket_fit/bvh-pose-check.json](rejected_socket_fit/bvh-pose-check.json) | 첫 inner-rim-only fit의 실제 주변 면 교차. 전체 표면 refit으로 대체한 실패 기록 |
| [rejected_eye_palette/decision.json](rejected_eye_palette/decision.json) | RGB만 변경한 대안1개. 실제 Web PCK 적용은 확인했으나 가시적 개선이 작아 불채택; d7d 유지 |
| [blade_trail_review](blade_trail_review/README.md) | 실제 Game 첫 방·RuneCamera의 정지 Web fixture 비교. ADD 프리뷰 유지, MIX는 대비 저하로 불채택. 눈 소켓 몸체 적용 전 판본 |

`blade_trail_review`는 선택한 원본 PNG 3장과 fixture·로그·판정·해시를 보관한다. 전체 on/off 비교 이미지와 MIX PNG는 원래 ignored build에만 있으며, 파일이 없는 캡처를 이 폴더에 보관한 것으로 표시하지 않는다. [archive.json](blade_trail_review/archive.json)의 파일 크기·SHA와 [review.json](blade_trail_review/review.json)의 전체 캡처 해시를 구분한다.

눈 소켓은 [제작 도구](../../../tools/derive_character_eye_sockets.py)로 원본의 눈 안쪽만 절단하고 rim·벽·곡면 안구를 별도 파생했다. 최종 [몸체·Web 안구](../candidates/lyra-eye-sockets-001/refit-delta-audit.json)는 runtime과 일치한다. [과거 source-audit](../candidates/lyra-eye-sockets-001/source-audit.json)은 이전 `81331…` 안구의 검사이므로 최종 결과로 바꾸지 않았고, 별도 delta audit이 최종 안구를 연결한다. [최종 BVH](../candidates/lyra-eye-sockets-001/bvh-pose-check.json)는 실제 재반입 5개 Head 포즈의 교차쌍 0개, refit의 2,358시점 검사는 cornea 포함 12.8mm 보수적 구에서 최소 +0.551mm 여유를 기록한다. 유한 표본을 연속 접촉·AAA 승인으로 확대하지 않는다.

최종 몸체·안구·궤적의 [native 통합 345검사](../../../docs/validation/v0.1.5/native.log)와 [눈 집중 21검사](../../../docs/validation/v0.1.5/eyes-native.log)는 실패 0개다. [character-eyes.json](../../../docs/validation/v0.1.5/character-eyes.json)에 입력 해시·눈 전용 재질 반입 수정·범위를 기록했다. 몸체 32,288삼각형은 계획된 Web 몸체 예산을 288개 넘으며 별도 안구 3,840개가 추가된다. 실제 Web 두 품질의 최종 화면·일반 gameplay QA·export·공개 배포와 목표 하드웨어 성능은 이 기록 시점에 `pending`이다.

반복 시 원본/후보 해시와 같은 edge·포즈·카메라·조명을 고정한다. 원래 가장 나쁜 부분의 개선 외에 새 악화, 얼굴·손·갑옷·발 접촉을 확인한다. 원본 파일을 덮어쓰지 않고 새 출력에서 비교하며, 구조·유한 수치 표본·스튜디오 렌더·실제 게임·목표 하드웨어 결과를 각각 기록한다.

실제 Web의 두 품질·Head 표본과 색상 대안의 비교는 [reference](../../../docs/validation/v0.1.5/eyes-web-reference/review.json)·[palette](../../../docs/validation/v0.1.5/eyes-web-palette/review.json)에 보관했다. 정지 장면·같은 화면 비교의 범위이며 정상 플레이/저장·실기기·최종 AAA로 확대하지 않는다.
