# 성역 분위기의 같은 장면 비교

2026-11-02 UTC. 공개 v0.1.11/ce120726의 baseline001과 v0.1.12 후보002를 같은 실제 Game·production Hero/Sentinel·HUD, prescribed idle pose와 camera로 비교했다. **후보002는 하늘·원경 재질·진입 바닥의 native 정지 화면을 prototype 범위에서 채택했다. AAA·실시간 모션/AV·Web/DPR raster·목표 기기 성능 승인은 아니다.**

| 같은 조건 | baseline001 | 채택 후보002 |
| --- | --- | --- |
| landing · 균형 q0 | [원본](baseline-001/landing-q0.png) | [원본](candidate-002/landing-q0.png) |
| fight · 균형 q0 | [원본](baseline-001/fight-q0.png) | [원본](candidate-002/fight-q0.png) |
| overview · 균형 q0 | [원본](baseline-001/overview-q0.png) | [원본](candidate-002/overview-q0.png) |
| landing · 성능 q1 | [원본](baseline-001/landing-q1.png) | [원본](candidate-002/landing-q1.png) |
| fight · 성능 q1 | [원본](baseline-001/fight-q1.png) | [원본](candidate-002/fight-q1.png) |
| overview · 성능 q1 | [원본](baseline-001/overview-q1.png) | [원본](candidate-002/overview-q1.png) |

루트 검수자는002의 q0 landing/fight/overview와 q1 fight를 직접 보고 파란 clear sky와 구름 분리, 밝은 벽돌 커튼처럼 보이지 않는 어두운 지질 재질, 진입 PBR·limestone/gold 세부·HUD/고리/배우 실루엣을 확인했다. 조명 담당자는6장 전체, 원경 담당자는 landing-q0/fight-q0/overview-q1도 별도로 확인했다.128 radiance의 부드러운 구름, 반복되는 limestone fins, 평평한 절벽 형상, primitive NPC/crystal, 어두운 platform void는 남아 있다.

q0은 균형 모드이며 실제 주광 그림자 ON/native scale1.0이다. q1은 성능 모드이며 실제 주광 그림자 OFF/native scale.65와 유한 근사 grounding을 사용한다. native q0의1.0은 Web 기본.8/DPR 정책의 검증이 아니다. 실제 그림자와 근사 ellipse를 동일한 물리적 발 접촉 품질로 표시하지 않는다.

## 기각한001과 수정 범위

루트는001의 q0 landing/fight/overview를 직접 검수해 진입 PBR만 제한적으로 채택했다. 전체 분위기는 옆 절벽이 밝은 벽돌 커튼처럼 읽히고 교전 구도의 clear sky가 gray/teal로 남아 미채택했다. [기각 landing](rejected-001/landing-q0.png)·[fight](rejected-001/fight-q0.png)·[overview](rejected-001/overview-q0.png)와 [판정](rejected-001/review.json)을 보존한다. 공개 폴더에는 직접 본3원본과6장 전체 해시/보고서를, 로컬 capture에는6원본 전체를 유지한다.001의 실행 오류가 없었다는 사실과 시각적 미채택을 구분한다.

002는 cliff/strata/far ridge를 기존 불규칙 FLOOR_STONE PBR과 어둡고 차가운 색·6~9m world-triplanar로 바꾸고 terrace/crown limestone을 유지했다. 하늘은 clear blue와 cloud coverage/따뜻한 혼합을 조정했다. [정확한 source diff](source-delta-from-001.patch)와 [construction 함수10개의 동일 해시](backdrop-construction-source-comparison.json)를 남긴다. 두 후보의 실제5mesh/5surface/2102triangle/6306stored vertex, AABB·shadow flag와 진입 바닥 parameter가 같다.001 fixture에서 실제 vertex payload hash는 수집하지 않았으므로 별도의 측정된 vertex-buffer 해시 일치를 주장하지 않는다.

## 실행과 권한 보존

baseline은71.293초,001은64.353초,002는124.046초에 캡처를 마쳤고 모두 엔진 오류0·source 입력 불변·모든 프로세스 종료를 확인했다. Godot4.7.2 OpenGL Compatibility/Mesa llvmpipe의 촬영 시간은 목표 GPU FPS나 성능 회귀 판정이 아니다. V-Sync 변경을 지원하지 않는 driver 경고는 원래 결과에 보존했다.

세 촬영의 실제 static collision canonical rows는160body/178shape로 정확히 같고 fingerprint와 Sanctuary RNG 상태도 같다.6개 구도의 camera·배우 위치/표현·native scale도 일치한다. 이는 통제한 같은 staging 지점의 관찰이며 모든 미래 RNG 동작이나 정상 spawn 물리를 증명하지 않는다. Game/actor/camera callback을 멈추고 nominal grounded checkpoint로 맞춘 landing을 정상 입력으로 관찰한 spawn이라고 부르지 않는다.

[짝 조건 원장](paired-baseline-comparison.json), [종합 checkpoint](../paired-capture-checkpoint.json), [파일 bytes/SHA 원장](archive-manifest.json)을 연결한다. source/capture/runtime inventory와 canonical collision rows는 각 폴더에 보존한다. 공개 `scene-review.json`은 실제 report에서 local cache 경로와 worktree 목록만 생략한 subset이고 raw report bytes/SHA를 `curation`에 남겼다. 원본 PNG는 리사이즈·색보정하지 않았다.

native 계약의 [첫520/1 실패](../native-first-failure.json)와 [001 수정 후523/0](../native-corrected-checkpoint.json)은 역사적 입력으로 남는다.002 색/재질 source는 [별도의 최종 native523/0·Python51](../native-final-checkpoint.json)과 [Web/Windows export](../local-preview-build.json)로 다시 확인했다. 브라우저·clean CI·공개 gate는 [판본별 검증](../README.md)에서 pending으로 둔다.
