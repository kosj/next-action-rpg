# v0.1.4 캐릭터 프리뷰 검증

Godot4.7.2·Blender4.3.2에서 실제32k리라/22k수호병을검수했습니다. 최종입력SHA와43개독립검사/오류0은 `production-summary.json`, 전체게임268개/실패0과Web·Windows내보내기는 `local-build.log`입니다. 최종Hero의충전끝장전hold가의미있는몸/검이동을유지하고1.3초까지고정됨도확인했습니다. 이전잘못된clip은같은검사에서정확히1개실패했으며 `production-charge-before-fix.json`에원인관찰을남깁니다.

`local-web-initial/`은실제새게임UI·품질0/1·safe1회베기/손변화·근접수호병·기존전투·완전종료/재시작을모두통과한294.774초의개발export검사입니다. **이실행은마지막charge/finger데이터보정전모델을사용했습니다.** 동일19/9상태구조와게임/QA코드가동작했음을확인한자료이며, 최종GLB와공개배포의정확커밋검증은해당CI가별도로수행합니다. 같은모델데이터검증으로표시하지않습니다.

최종source·recipe·동작/접지/그립검수근거는 `art_source/production/candidates/lyra-gameplay-001/`와 `sentinel-gameplay-001/`입니다. 소프트웨어WebGL과자동구조/좌표검사는목표GPU성능·Windows실기기·최종AAA아트승인이아닙니다.


## 후속 아트·전환·오디오 판본

[최신 빌드 요약](art-quality-build-summary.json)과 [실제 전체 로그](art-quality-build.log)는 PBR·장면 구도·80ms 전환·오디오 종료 수정을 포함한 통합305개/실패0, 오류·경고0, Web·Windows 내보내기 정상 종료를 기록합니다. 웹 원시합계141,912,072bytes로150MB 예산을 지켰습니다. 로컬 빌드번호는 `0.1.4 · 1b8d95b9`이며 커밋 전 변경이 포함됩니다. 이후 정확한 공개 커밋 검증은 GitHub CI와 구분합니다.

[전환 표본](transition-polish.json)과 [집중27개 검사](transition-polish-runtime.log)는 실제53본·손·칼끝의 위치 튐과 phase/clock/우선 상태를 확인합니다. [불변 트랙 제거 진단](transition-import-diagnostic.log)에 따른 두 production import 정책도 보존합니다. [오디오 집중9개](audio-lifecycle-focused.log)와 [실제 playback 소멸 조건](audio-lifecycle.json)은 고정 대기 대신 참조 해제를 확인하며 stale callback·반복 중지·명시적 재개를 검사합니다. 이 집중 검사들을 전체305개에 더한 합계로 표시하지 않습니다.

[첫 방 실제 고정 카메라 검사](courtyard/README.md)는 별도 복사 fixture의 구도·PBR·조명 자료입니다. [전체 key/midpoint 변형 검토](../../../art_source/production/character_actions/deformation_review/README.md)는 원본의 불량과 자동 수선 기각을 기록합니다. 수선된 GLB는 채택하지 않았으며 원본 runtime A89/214를 유지합니다. [AAA 기준](../../AAA_ART_QUALITY.md)의 얼굴·손·갑옷/의상·접촉·실제 목표 GPU 항목은 계속 미승인입니다.
