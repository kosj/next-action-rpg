# v0.1.9 무음 1배속 모션 비교

2026-11-01 UTC. 실제 임포트한 이전/새 GLB를 같은 카메라·바닥·조명에서
`ActorVisual.pose`와 `SkeletalVisualBridge`로 표시한 **오프라인 표현 fixture**다.
아래 MP4는 정상 논리 시간의 1배속·60fps 파일이며, 연속 재생의 시각 품질을
모델이 검수했다는 뜻은 아니다. 직접 확인한 것은 명시한 정지 raster와
프레임·시계·입력 해시·카메라·종료 결과다. 무음이며 게임 접촉/VFX도 발생시키지 않는다.

| 자료 | 시간·범위 |
| --- | --- |
| [리라 전신 1배속 MP4](hero-1x.mp4) | 1280×720, 60fps, 162프레임·2.7초. idle→charge/hold→charged_heavy→idle |
| [수호병 전신 1배속 MP4](sentinel_melee-1x.mp4) | 1280×720, 60fps, 84프레임·1.4초. idle→heavy_hit→idle |
| [리라 9시점 비교](hero-contact-sheet.png) | 실제 60Hz 정수 프레임의 전신·검·회복 표본. 목표 시점을 정수 프레임으로 반올림한다. |
| [수호병 9시점 비교](sentinel_melee-contact-sheet.png) | 같은 방법의 피격·회수 표본 |
| [팔 확대 정지 비교](hero-arms-static-strip.png) | 실제 피부·장갑, 효과 off. 아래 다섯 subframe pose의 정지 strip이며 1배속 영상이 아니다. |

팔 확대 원본은 MovieMaker의 손실 없는 PNG다. 각각 before/after를 같은 투영으로
표시하며, 전신 시점의 카메라 방향을 유지하고 확대·재중심만 했다.

| charged elapsed | 실제 1280×720 PNG |
| --- | --- |
| 0.4667초 | [01](hero-arms-01.png) |
| 0.4750초 | [02](hero-arms-02.png) |
| 0.4780초 | [03](hero-arms-03.png) |
| 0.4800초 | [04](hero-arms-04.png) |
| 0.4833초 | [05](hero-arms-05.png) |

## 관찰과 승인 범위

선택한 전신 raster에서 새 리라의 큰 장전 실루엣·낮은 다리 자세와 수호병의
피격/회수 차이를 읽을 수 있고, 몸과 검이 화면 안에 있다. 팔 확대에서는 이전/새
모델 모두 forearm/gauntlet 방향이 짧은 구간에 크게 돌아간다. 이번 제작 단위가
그 기존 보상 회전을 제거했다거나 손목 변형을 승인했다는 뜻은 아니다.
바닥은 같은 고정 조명에서 밝게 표시되므로 재질·조명 승인을 위한 자료도 아니다.

이전 진단 배치002는 hero ownerY=0에 production visual offset +0.025m를 더해
명목상 바닥보다 약 25mm 높을 수 있었다. 그 배치는 body-relative 진단으로만
보존했다. 이 배치는 **ownerY=-visual.ground_offset_y**로 실제 캡슐 바닥 배치에
맞췄고, runtime 코드·offset은 바꾸지 않았다. 이것은 평면의 명목 배치 확인이며
terrain IK·모든 vertex의 접지·실제 충돌 승인이 아니다.

fixture는 값 snapshot으로 표현만 구동한다. 리라의 막힘 없는 active lunge
0.576m와 수호병의 0.24초/0.35m recoil을 별도로 처방했으며 `move_and_slide`,
피해·접촉 판정·실제 입력은 실행하지 않는다. 인터랙티브 전투·전체 프레임의 변형,
연속 1배속 시각/AV·청취·실제 목표 기기/GPU 성능·AAA 승인은 **pending**이다.
오프라인으로 생성한 encoded60fps를 실제 게임60fps로 해석하지 않는다.

## 원문과 재현

- [검증·출력 SHA-256·decoded tail proof](verification.json)
- [MovieMaker/ffprobe 원문 메타데이터](capture.json)
- [리라 프레임 원문](hero-frames.json), [수호병 프레임 원문](sentinel_melee-frames.json), [팔 정지 원문](hero-arms-frames.json)
- [격리 프로젝트 설정](fixture-project.json), [고정 촬영 도구/씬 원문](fixture-source/)
- [리라 decoded raw tail](hero-raw-tail.framemd5), [수호병 decoded raw tail](sentinel_melee-raw-tail.framemd5)

각 JSON에는 source path와 GLB·반입 설정·실제 compiled scene·이미지·도구·fixture의
해시가 있다. 배치 중 source를 바꾸지 않았고 모든 profile 후 해시를 대조했다.
raw AVI의 종료 프레임은 실제 decoded pixel hash로 이전 프레임과 같음을 확인한
경우에만 중복으로 기록했다. 마지막 동일 프레임 한 장만 제외했으며 보간이나
속도 변경은 하지 않았다. 원본 대용량 AVI와 이전 배치 진단은 ignored build에 보존한다.

```bash
python tools/render_weight_review.py --output build/art-review/weight-motion/NEW_EMPTY_DIR --capture --arm-strip
```

먼저 현재 프로젝트의 올바른 GLB/import cache가 준비돼 있어야 한다. 기본 실행은
준비만 하며 `--capture`가 실제 로컬 Xorg/MovieMaker를 시작한다. 별도 CPU 슬롯을
확보하고 실행하며, 다른 반입/빌드와 동시에 공유 source cache를 바꾸지 않는다.
원본 game/project.godot를 바꾸지 않는 격리 프로젝트와 TCP가 꺼진 로컬 Xorg를 쓰고
종료 시 프로세스를 정리한다. 실제 renderer는 Mesa llvmpipe이며 VSync 미지원 경고를
원문 로그에 남겼다. 이 환경을 목표 GPU와 동일시하지 않는다.

## 고정한 모델 입력

| source path | SHA-256 |
| --- | --- |
| `game/assets/models/production/lyra_impact_gameplay.glb` | `0aa78c46c0453f8286785ee937ef9388324dc4312bb076f5179934f08e44d57d` |
| `game/assets/models/production/lyra_weight_gameplay.glb` | `27fbed52e1e7011e66f4d0347827db7aa35cb035fbb2dd23df873de752fa1d83` |
| `game/assets/models/production/rune_sword_web.glb` | `68dfaca4a44b6f56bf8025e469bfb4f03270363f0bb0e6dc35e78c05cb165448` |
| `game/assets/models/production/lyra_eyes.glb` | `d7d984fb10637be102a740e91e89316580b33c53d4b6a2cd1055108675ef3ef4` |
| `game/assets/models/production/sentinel_impact_gameplay.glb` | `6180967f4220651f5a9a343109e07bfab5831252c875170d008d17072d09c576` |
| `game/assets/models/production/sentinel_weight_gameplay.glb` | `e7e2b5bd5d5d6dbf0e3ada3fe373c3bb8acbd4918ece0519a2e5c55417d5f619` |
