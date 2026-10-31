# 리라 눈 소켓·안구 국소 파생

2026-10-31. **국소 개선 프리뷰이며 최종 AAA 승인은 pending**이다. 원본 [A89 gameplay 자산](../lyra-gameplay-001/manifest.json)은 보존했다. `source.glb`는 눈 내부 cut9·인접 conform11·안쪽 lid136삼각형을 반영한 몸체이며, `eyes-web.glb`는 별도의 Head-local physical-meter 안구다. runtime 두 파일은 이 보관본과 byte-exact다. `eyes-reference.glb`는 비교용 고밀도 안구이며 게임에는 사용하지 않는다.

원본32,000삼각형 중31,980개 index triple과 원래25,799 attribute rows·전체17,153,208-byte BIN prefix·53본/skin·20클립·node·이미지/텍스처·기존 재질을 그대로 유지했다. [source-audit.json](source-audit.json)은 같은 몸체4cc9와 **이전 안구81331**에 대한 역사 감사다. [refit-delta-audit.json](refit-delta-audit.json)이 최종d7d 안구와 연결하며 양 눈의 rigid center translation만 확인한다. 이를 충돌 승인으로 확대하지 않는다.

[초기 파생](initial-derivation.json)은 당시 runtime A89를 입력한 역사 기록이다. 그 파일의 `source.unchanged`는 제작 당시의 사실이며 현재 runtime도 A89라는 뜻이 아니다. inner-rim-only fit은 주변 기존 face와 새 lid 삼각형을 놓쳐 **기각**했다. [실패 보고서](../../character_polish/rejected_socket_fit/bvh-pose-check.json)는 보존했다. 좌표계 가설은 원본 CPU skin과 실제 Blender 정점의 µm 대조로 배제했다.

[최종 refit](refit.json)은 몸체를 유지하고 왼쪽2.192mm/오른쪽1.050mm만 안구 중심을 뒤로 옮겼다. 모든20클립 exported key+midpoint2,358표본/근접484삼각형에서 최대 cornea를 포함한12.8mm 보수 구면과의 최소 gap은+.551mm다. [실제 GLB 재반입 BVH](bvh-pose-check.json)는 REST·yaw±15°·pitch±10°의5포즈에서0교차쌍이다. 연속적인 모든 포즈의 충돌 보증은 아니다. rim34정점은 Head 약98~99%와 Neck 등의 **혼합 skin**이며 별도 안구만 rigid Head 부착이다.

`studio/`는 실제 재반입한 Web 안구·같은 몸체의 중립 조명 렌더다. 정면·3/4·측면·yaw·pitch에서 국소 형태를 검토했다. 실제 게임 캡처나 최종 피부/머리/표정 승인이 아니다. [표면 오차](surface-error.json)는 Web→고밀도 안구의17,792개 유한 단방향 표본이다. visible-front 최대.017623mm, 전체 최대.722444mm는 더 성긴 가려진 뒤쪽에서 발생했다. 연속 Hausdorff bound나 하드웨어 성능으로 표현하지 않는다.

Body32,288삼각형은 원래 계획한 Web body target32,000을 **288초과**하며 안구3,840은 별도다. 높이1.82m·53본·19상태+RESET·원본 갑옷 웨이트는 유지했다. 목표 삼각형·실기기 성능의 최종 통과로 반올림하지 않는다.

Godot의 Head attachment는 수입 normalization scale만 역보정하며 actor 외부scale를 유지한다. [실제 native 증거](../../../../docs/validation/v0.1.5/character-eyes.json)는 독립 source-world REST anchor·19클립57표본·외부1.25배·같은 프레임 Head·정지·yaw/pitch·해제를 검사한다. 첫 primitive의 COLOR_0 flag가 꺼지는 Godot4.7.2 문제는 [자산 전용 post-import](../../../../game/import/eye_materials.gd)에서 예상3재질/색배열을 검증하고 복제 재질의 색 사용만 켰다. source GLB/이미지는 그대로다. 원본 색·실제 양자화 배열·재질 flag를 함께 검증한다.

이번 단계 새 VARCO 생성/포인트 사용·추가 구매는0이다. 원래 PRIVATE 생성 자산의 사용 근거는 기존 manifest와 [라이선스 검토](../../../../docs/CHARACTER_INTEGRATION.md)에 따른다. 새로운 모션 원본·재배포 권리를 만들었다는 뜻이 아니다. 재현 recipe와 tool SHA는 이 후보의 manifest에서 확인한다. 실제 Web 품질0/1·정상 입력/저장·Windows 실기기·최종 AAA는 각 실행 증거와 별개로 판단한다.
