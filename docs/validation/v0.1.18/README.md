# v0.1.18 검사 스킬 VFX

같은 링을 사용하던 세 기술을 전방 청록 초승달, 보라/청록 회전 검기, 금빛 낙하 검으로 구분했다. 피해·범위·룬 비용·공격 시간은 유지하고, 확정 접촉의 색·카메라 pulse·심판의 저역 타격음을 연결했다.

- [이전 실제 게임 영상](media/skills-before-logical1x.mp4) · [수정 후 실제 게임 영상](media/skills-after-logical1x.mp4)
- [섬광](media/skill-1-active.png) · [폭풍](media/skill-2-active.png) · [심판](media/skill-3-active.png)
- [소스·원본 미디어 SHA·발동/수명 근거](technical-visual.json) · [구현 계약](../../SKILL_VFX_SLICE.md)

영상은 실제 native Game을 논리60Hz/1배속으로 기록했다. 기술 비교를 위해 각 스킬 전에 룬100을 보충한 **기술 캡처**이며, 정상 자원 획득·실제 적중의 증거가 아니다. 이전 영상은840gameplay frames, 수정 후는 같은840예산 안에서 세 기술의 실제 회복·효과 소멸·마지막 발동 후90tick을 확인한394frames다. 동일 tick/phase를 비교하며 영상 전체 길이가 같거나 실시간60fps로 실행되었다고 주장하지 않는다. 개발 캡처의 옛 preview build label과 최종 배포 버전 확인은 분리한다.

첫 두 섬광 후보는 긴 전방 날이 뒤 카메라에서 몸과 기존 흰 궤적에 가려져 기각했다. [기각한 화면](media/rejected-dash-before-crescent.png)을 남겼다. 세 번째 후보의 큰 전방 초승달은 실제 준비/활성/후반/회수 PNG에서 방향·양옆 끝·캐릭터 가독성을 확인해 프로토타입으로 채택했다. 심판은 가드·손잡이를 추가해 광창과 검의 형태를 구분했다.

[최종 native·export](final-native-export.json): 실제 벽/이동 잔상 검사를 포함한913검사/0실패·엔진ERROR0, Web/Windows export 성공, raw Web149,918,911bytes. [초기 진단](initial-native.json)과 구분한다. 정상 입력 gameplay·모바일/공개 주소·릴리스 결과는 해당 source와 산출물에서 따로 검증한다. 연속 직접 시청/청취, 실제 Android/iOS/Windows GPU 성능과 AAA 최종 아트 승인은 남는다.

[정상 자원 획득 gameplay](normal-gameplay.json) · [실제 게임 영상](media/skills-normal-earned-logical1x.mp4): 룬 보충 없이 실제 UI/키·패링·두 전투 구역 이동으로 세 기술을 각각 한 번 사용하고 회복/연출 종료를 확인했다. 실제 접촉은 심판3회(각150), 섬광3회(각65)다. 폭풍은 첫 구역의 적이 쓰러진 후 발동해 이 take에서는 빗나갔다. 모든 기술의 실제 접촉은 별도 native 회귀에서 확인하며 이 영상의 범위를 확대하지 않는다.1256gameplay frames의 논리1배속 기록이고 인간 플레이·실시간60fps·난이도/밸런스 승인이 아니다.
