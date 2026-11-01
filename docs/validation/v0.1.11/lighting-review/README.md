# 실제 courtyard 조명 비교

2026-11-01 UTC. 공개 v0.1.10의 baseline001과 v0.1.11 후보002를 같은 실제 `main.tscn`, production Hero/Sentinel, idle 포즈, camera,1280×720, 실제 HUD로 비교했다. **후보002는 이 정지 장면의 조명 개선 범위에서 채택했다. AAA·전투 모션·연속 AV·Web raster·실기기 성능 승인은 아니다.**

| 조건 | baseline001 원본 | 채택 후보002 원본 |
| --- | --- | --- |
| 전투 카메라 · 균형 q0 | [fight-q0](baseline-001/fight-q0.png) | [fight-q0](candidate-002/fight-q0.png) |
| overview · 균형 q0 | [overview-q0](baseline-001/overview-q0.png) | [overview-q0](candidate-002/overview-q0.png) |
| 전투 카메라 · 성능 q1 | [fight-q1](baseline-001/fight-q1.png) | [fight-q1](candidate-002/fight-q1.png) |
| overview · 성능 q1 | [overview-q1](baseline-001/overview-q1.png) | [overview-q1](candidate-002/overview-q1.png) |

q0은 균형 모드이며 실제 주광 그림자 ON, native scale1.0이다. q1은 성능 모드이며 실제 주광 그림자 OFF, native scale.65다. 새 q1 후보에서는 지면 ray를 사용하는 근사 ellipse4개가 불투명도.21로 표시됐다. 고품질/저품질 숫자가 뒤집힌 결함은 없다. native q0 화면은 Web 기본 scale.8이나 모바일 DPR 보정 화면을 증명하지 않는다.

루트 검수자는 후보002의 q0 전투 화면을 직접 보고 규칙적인 바닥 격자가 사라지고 바닥·금속 세부가 유지됨을 확인했다. q1 전투 화면도 직접 보고 배우 아래의 유한 근사 접지와 예상된 낮은 해상도를 확인해 두 모드를 prototype 범위에서 채택했다. 조명 담당 검수자는 q0 전투/overview에서 발·접지 인상과 방향성 세부도 확인했다. 두 q1 원본은 후보001과 byte 단위로 같다. 따뜻한 석재와 밝은 구조물의 구분을 조정했지만 평평한 중립색 하늘, 어두운 갑옷 전면, 단순한 건축 형태는 남아 있다. 상세한 움직이는 발 그림자 품질을 승인한 결과는 아니다.

## 기각한 후보와 수정

후보001의 q0에서는 촘촘하고 규칙적인 바닥 줄무늬가 나타났다. [기각 원본](rejected-001/original-png/fight-q0.png)과 [기각 기록](rejected-001/review.json)을 보존한다. q1에서는 해당 격자가 없었으므로 실제 그림자 경로를 먼저 확인했다. shadow acne가 의심되어 후보002에서는 주광의 normal bias만1.1→2.0으로 복구했다. 두 후보의 runtime source inventory 차이가 이 변경뿐임을 대조했고 실제 q0 격자가 사라졌다. 조명 변경 전체를 성공으로 간주하지 않고 새 결함을 별도 원본으로 남긴 사례다.

## 실행과 원본 경계

baseline은64.096초, 최종 후보002는53.105초의 실제 캡처를 완료했고 엔진 오류는 없었으며 프로세스는 모두 종료됐다. renderer는 Godot4.7.2 OpenGL Compatibility, adapter는 Mesa llvmpipe다. 캡처 시간은 목표 기기 FPS가 아니다. V-Sync를 변경할 수 없다는 Xorg/driver 경고는 원래 기록에 남아 있다. baseline runner의 version probe에서 private XDG 설정 전 Fontconfig cache 경고가 발생했으며 이는 게임 엔진 오류가 아니다. runner의 환경/검사 보강은 있었지만 fixture bytes는 두 촬영에서 같다.

실제 Game/actor/camera callback을 멈추고 정해진 배우 위치와 idle pose를 사용했다. 실제 HUD를 표시했지만 정상 메뉴 입력이나 교전 입력을 재현한 take는 아니다. 원본 PNG를 색보정·리사이즈하지 않았다. [짝 조건](paired-baseline-comparison.json)은 camera·배우 위치·native scale과 원본 해시를 연결하고, [종합 checkpoint](../paired-capture-checkpoint.json)는 runtime light/environment·근사 grounding과 채택 범위를 기록한다. [파일 원장](archive-manifest.json)은 공개 파일 bytes/SHA를 고정한다.

baseline과 후보 폴더의 `scene-review.json`은 실제 shot 데이터를 유지한 공개 subset이다. 로컬 cache 경로와 worktree 목록만 생략했고 raw report의 bytes/SHA를 `curation`에 보존했다. `source-inputs.json`, `capture-inputs.json`, `runtime-inputs.json`은 촬영 시점의 source inventory다. 첫 native508은 역사적 기록으로 남기고 이후 source를 [최종 native508/0](../native-final-checkpoint.json)으로 다시 검사했다. [최상위 검증 현황](../README.md)의 브라우저·배포 gate는 별도다.

촬영002 뒤 관측용 Game/HUD/ActorVisual telemetry가 추가됐다. [촬영·최종 source 경계](../post-capture-telemetry.json)는 바뀐3파일의 양쪽 bytes/SHA와 동일한 Sanctuary/GroundingShadow/shader3파일을 대조한다. 원본002가 최종 HUD source 전체와 정확히 같은 입력으로 촬영됐다는 뜻은 아니다. 이 원본의 제한된 시각 판정과 최종 source의 native/브라우저 실행 검증을 구분한다.
