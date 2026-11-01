# Fury007 선택 피부 검토

기존 `27fbed52`와 후보 `f2edbd37`의 같은 카메라·조명·원본 피부를 비교했다. 선택한 12개 정지 화면과 원시 LBS 표본 범위에서는 새 뚜렷한 붕괴·가시·찢김이 보이지 않아 **실제 게임 검증을 위한 후보로 잠정 채택**했다. 전체 피부·관통·연속 1배속 AV·실기기·AAA 승인이 아니다.

- [장전 .296 이전](charge-0296-before-left.png) / [이후](charge-0296-after-left.png): 새 국소 최대 악화 부위인 왼팔꿈치의 안감·가운틀릿을 확인했다. 정면 비교도 검토했으며 원문 해시를 review.json에 보존한다.
- [베기 .441 이전 반대쪽](stroke-0441-before-opposite.png) / [이후](stroke-0441-after-opposite.png): 앞쪽에서 가려지는 전완을 확인했다.
- [새 베기 .450 정면](stroke-0450-after-front.png), [새 베기 .354 정면](stroke-0354-after-front.png): .354는 기하 예측 접촉 부근의 정지 포즈이며 실제 입력·명중 캡처가 아니다.

새 왼팔꿈치 안감은 더 펴지고 crease가 보인다. 검토한 각도에서는 새 뚜렷한 붕괴나 candy-wrapper를 보지 못했다. 주먹 감김·갑옷 접촉·전체 시각 품질은 미완료다. 비교에는 양쪽 모두 원래 중립 룬검을 사용했으며, 새 넓은 칼날의 실제 가독성·충격은 별도 production gameplay에서 검증한다.

원시 LBS는 팔/손/어깨 influence가 있는 primitive0의 1,712개 charge·charged 키/중간 시점을 비교했다. 지역 최대 extension은53.06→34.08mm로 줄었지만, 같은 edge envelope가1mm 넘게 악화된 edge는2,054개다. 최악은 charge .296의 LeftArm/LeftForeArm 경계: old−14.61mm→new+17.95mm, 차이+32.55mm다. 이 결과를 숨기거나 글로벌 개선으로 국소 합격을 대신하지 않는다. 유한 표본·지역 선택이며 피부 관통·천 물리·해부학 승인도 아니다.

[판정·카메라·선택 PNG 해시](review.json), [전체 수치 원문](skin-lbs-audit.json), [읽기 전용 재현 코드](skin_lbs_audit.py). 공개 PNG6장은 렌더 원본을 byte-exact 복사했고, 전체12장 원본은 ignored build에 보존했다.

```bash
mkdir -p build/art-review
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python3 art_source/production/candidates/lyra-fury-001/skin-review/skin_lbs_audit.py game/assets/models/production/lyra_weight_gameplay.glb game/assets/models/production/lyra_fury_gameplay.glb build/art-review/fury-skin-repeat.json
```

선택 Python 아트 의존성과 별도 CPU 슬롯이 필요하다. 원본 자산·웨이트·리그를 수정하지 않는다.
