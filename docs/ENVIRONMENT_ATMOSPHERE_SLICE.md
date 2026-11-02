# v0.1.12 성역의 하늘·배경·바닥 시각 완성도

2026-11-02 UTC 최종 로컬 snapshot. 시작점은 공개 v0.1.11의 `ce1207269922d50edfc725a5aba728d32f8989f3`다. [이전 공개 검증](validation/v0.1.11/published-verification.json)은 그 판본의 PR/main/tag·실제 공개 실행·다운로드 무결성을 확인했다. **001 전체 분위기를 기각한 뒤 수정한002를 native 정지 화면의 prototype 범위에서 채택했다.002 exact native523/0·Python51·Web/Windows export를 통과했고 브라우저·clean CI·공개/릴리스·실기기·AAA는 pending이다.**

## 개선할 실제 화면

v0.1.11의 제한적 조명 채택 후에도 낮은 전투 카메라에서 중립색 지평선이 넓고 갑옷 전면이 어두우며, 공간 바깥이 단순한 블록 형태로 남았다. 진입 지점과 연결 바닥의 시각적 마감도 courtyard의 PBR과 이어지지 않았다. 이번에는 이 네 영역을 하나의 공간으로 읽히도록 다듬는다.

- 하늘과 조명: 실제 renderer의 sky gradient·horizon·ambient/reflection 경로를 읽고 전투 카메라에서 하늘색과 원경 깊이를 확인한다. 갑옷 전면이 보이면서 밝은 돌·금속이 날아가지 않는지 같은 재질/몸체로 비교한다. getter의 색이나 에너지 수치만으로 채택하지 않는다.
- 원경: ruins/cliffs의 실루엣·높이·색과 안개를 맞춰 외곽을 구성한다. 표시 전용 mesh는 기존 이동·전투·support ray의 충돌 권한을 추가하지 않는다. 시각 전용이어도 화면 가림·그림자·노드/표면 비용은 실제로 확인한다.
- 진입/연결 바닥: 기존 지지면을 보존한 PBR visual skin을 구성한다. 재질 단위·반복 크기·roughness·normal·깊이 겹침과 courtyard 연결을 확인한다. 화면상의 바닥 덧입힘과 실제 collision surface가 다르다는 사실을 기록한다.
- 보존 범위: 품질0균형/실제 그림자 ON과 품질1성능/실제 그림자 OFF·근사 ellipse의 의미를 유지한다. 원본 배우/무기/모션·전투 판정·이동·카메라·저장·입력·RNG는 이 제작 단위의 변경 대상으로 삼지 않는다. 보존 여부는 source inventory와 실제 회귀/물리 검사로 확인한다.

## 검증 방법

[현재 엔진](../tools/toolchain.json)은 Godot4.7.2다. 이전 [renderer 원장](validation/v0.1.11/renderer-evidence.json)의 지원 사실과 새 sky/material source 해석을 구분한다. 새 공식 원문은 영구 URL·판본·bytes/SHA·읽은 구간으로 남긴다. 고정 source의 수식 해석, 실제 runtime 설정, 원본 raster에서 보인 결과는 각각의 근거다.

[새 sky 공식 근거](validation/v0.1.12/sky-renderer-evidence.json)는4개 원문의 bytes/SHA와 실제 GLES3 호출 경로를 보존한다. 기존 ProceduralSky는 `pow(1−EYEDIR.y, .6/curve)`로 horizon을 혼합하므로 낮은 카메라에서 curve가 커지면 중립색 띠가 넓어질 수 있다. 새 [sky shader 후보](../game/assets/shaders/sanctuary_sky.gdshader)는 cubemap pass에서 정적인 하늘/구름을 계산하고 배경에서는 `RADIANCE`를 샘플링하는 공식 recipe를 사용한다. 시간·카메라 위치 입력을 쓰지 않고 실제 주광 transform의+Z에서 태양 방향을 맞춘다. 이 설계는002의 실제 native 렌더에서 오류 없이 사용됐고 색·구름 분리를 prototype 범위로 채택했다.128 radiance/QUALITY에도 초기 cube bake/filter 비용과 세부 손실의 tradeoff가 있으며 비용0이나 목표 GPU 성능으로 기록하지 않는다.

baseline과 후보는 서로 독립된 실제 Game 프로젝트로 비교한다. landing·fight·overview 각각의 q0/q1에서 실제 몸체·포즈·카메라·해상도·HUD를 맞춰 원본 PNG를 보존한다. landing은 진입 공간, fight는 적/발/검/전투 가독성, overview는 원경 실루엣과 공간 연결을 확인하는 서로 다른 구도다. 정해진 pose와 멈춘 callback을 사용하는 controlled scene-view를 정상 입력이나 목표 기기 FPS로 바꾸어 해석하지 않는다. 모드 전후와 source 전후를 섞지 않는다.

시각 전용 배경과 바닥은 collision node/RID·ray support·actor transform·카메라의 실제 가림과 품질별 draw/shadow 비용을 함께 다룬다. 원경을 추가했다는 사실이나 재질 파일 크기만으로 게임 완성도를 승인하지 않는다. 실패 후보·단일 변수 수정·고정 source·같은 장면의 원본을 보존하고 악화가 남으면 기각한다.

## 현재 상태

첫 [원경 source 후보](../game/scripts/world/sanctuary_backdrop.gd)는5개 병합 ArrayMesh와 기존 limestone의 복제 재질을 사용하며, 새 텍스처를 추가하지 않는다. world-triplanar stone의 반복 크기를2~5m로 두고 먼 geometry의 shadow/GI는 끈다. source는 고정된 저작 profile과 비충돌·비navigation·비light 정책을 선언한다. 수정 후 실제 native는5mesh/2102triangle/6306stored vertex와 transformed geometry 경계·tree 계약을 확인했다. 화면과 목표 기기 비용은 별도다.

[첫 native520/1](validation/v0.1.12/native-first-failure.json)은 유효한 unindexed ArrayMesh의 `ARRAY_INDEX`가 null인데 fixture가 `PackedInt32Array`로 바로 대입해 실패했다. 상세 원경 report에도 같은 가정이 있어 수정했다. null index를 빈 배열로 처리하고 unindexed triangle은 vertex 수에서 계산하며 geometry/재질은 바꾸지 않았다. 이 수정은 전체 재실행의 성공을 뜻하지 않는다.

그 뒤 [실제 전체 재실행523/0](validation/v0.1.12/native-corrected-checkpoint.json)을 확인했다.66개 frozen source의 현재 해시를 직접 대조했고, 기존 외곽 장식45개 숨김·실제 주광과 unit sun 방향 일치·진입/연결/courtyard7개 지지 ray의 Y≈0을 검증했다. 이는 새 native 계약의 통과이며 아직 후보 원본 raster·full build·브라우저·성능 승인은 아니다.

후보001의 실제6장은64.353초/exit0/엔진 오류0으로 촬영됐다. 같은 baseline과 camera·배우/표현·native scale을 맞췄고 static collision160body/178shape의 canonical rows와 RNG 상태도 일치했다. 그러나 루트 검수자는 q0 landing/fight/overview를 직접 보고 옆 절벽이 거대한 밝은 벽돌 커튼처럼 보이며 교전 구도의 맑은 하늘이 여전히 gray/teal로 읽힌다는 이유로 전체 분위기를 채택하지 않았다. 진입 바닥의 PBR만 제한적으로 채택했다. [기각 원본3장과6장 전체 해시/source](validation/v0.1.12/atmosphere-review/rejected-001/review.json)를 남긴다. 이는 엔진 실행 실패와 다른 판정이다.

후보002는 절벽/strata/먼 ridge의 재질을 기존의 불규칙한 FLOOR_STONE PBR과 어둡고 차가운 색으로 바꾸고, terrace/crown의 limestone을 유지했다. sky는 파란 clear 영역을 강화하고 넓은 구름/보편적인 따뜻한 혼합을 줄였다. [source diff·원본과 짝 조건](validation/v0.1.12/atmosphere-review/README.md)은 동일한 camera/배우 표현/scale·static collision canonical rows/RNG와001→002의10개 construction 함수 source, 실제 count/AABB/그림자 flag 보존을 연결한다.001에 vertex payload hash는 없었으므로 독립적으로 측정된 vertex-buffer 해시 일치를 주장하지 않는다.

002 원본6장은124.046초/exit0/엔진 오류0으로 촬영됐다. 루트는 q0 landing/fight/overview와 q1 fight를 직접 보고 blue/cloud 분리와 어두운 지질 재질, PBR·HUD/고리·배우 실루엣을 prototype 범위로 채택했다. 구름의128 해상도/부드러운 경계·반복 fins·평평한 cliff·primitive NPC/crystal·어두운 platform void는 남았다. 촬영 시간은 목표 GPU FPS가 아니다.

[최종002 native/build](validation/v0.1.12/native-final-checkpoint.json)는66개 frozen source 일치와 새523/0, Python51/0을 확인했다. [로컬 export](validation/v0.1.12/local-preview-build.json)는 raw Web146,599,311B/14files<150MB와 Web/Windows ZIP을 확인했다. dirty0.1.12·ce120 preview이며 clean CI나 공개/릴리스 artifact로 표시하지 않는다. Windows export는 실제 Windows 실행과 다르다. [선택한 critical10파일](validation/v0.1.12/source-preservation.json)은 ce120 baseline과 bytes가 같다.

baseline의 landing/fight/overview×q0/q1 원본6장은71.293초에 실제 캡처됐고 엔진 오류 없이 모든 프로세스가 종료됐다. baseline은 ce120726의 실제 앱0.1.11이며, 기존 fight/overview4장은 v0.1.11 최종002와 byte 단위로 같다. landing은 grounded checkpoint에서 실제 RuneCamera를 unlocked 상태로 둔 추가 구도다. 이는 새 후보의 채택이나 정상 입력 검증이 아니다.

[v0.1.12 검증 현황](validation/v0.1.12/README.md)의 각 gate는 실제 결과로만 갱신한다. 새 native 계약과 원본 raster 채택, Python/Web/Windows export, 실제 브라우저 입력/품질/저장/재시작, clean CI·공개·릴리스를 각각 확인한다. 이전508검사나 공개 모바일1010.102초의 성공을 이 판본에 복사하지 않는다.

AAA 최종 아트·실제 Windows/Android/iOS/Safari/GPU·모션/연속 AV 검수는 별도다. 이번 원경과 바닥 마감만으로 얼굴·손·변형·머리카락·발 접촉·완성된 세계 전체가 승인되지 않는다.
