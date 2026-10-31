# 첫 courtyard · 고정 카메라 장면 검수

2026-10-31, Godot 4.7.2의 실제 Game·RuneCamera를 별도 복사 프로젝트에서 Web Compatibility로 내보내고 Chromium SwiftShader에서 촬영했습니다. 생성 이미지나 콘셉트가 아닙니다. **최종 웨이트 보정 이전 리라 a89… / 수호병 214… 파일을 사용한 장면 검사이며, 최종 gameplay QA·AAA 품질 승인이 아닙니다.**

- [기본 플레이 카메라 구도](balanced-inspection.png): 플레이어 `(0, 0.15, -25)`, yaw `0`, pitch `-0.18`, 수직 FOV `56°`.
- [기둥 가까이 구도](detail-inspection.png): 플레이어 `(11, 0.15, -42)`, yaw `-0.7`, 나머지 카메라 설정 동일.

[검수용 fixture](scene-inspection-fixture.gd.txt)는 실제 첫 encounter를 생성하고 HUD를 숨긴 뒤 두 물리 프레임 이후 장면을 정지합니다. 플레이어 Y를 `0.15`에 고정했으므로 이 화면으로 실제 이동·낙하·발 접지·공격 타이밍을 승인하지 않습니다. fixture는 게임 원본이나 배포 프로젝트에 추가하지 않았습니다.

[장면 감사](scene-audit.json)는 기존 178개 충돌체의 형상·전역 변환·layer/mask·disabled 상태와 최종 공유 RNG 상태가 기존 Git 원본과 정확히 같음을 확인합니다. 새 장식에는 PhysicsBody와 CollisionShape가 없습니다. 추가 장식의 논리적 수는 404개 인스턴스·12,400삼각형·9개 surface batch이며 GPU 드로콜·FPS 실측값은 아닙니다.

바닥은 40×40m PlaneMesh와 1.8m 물리 반복 크기의 PBR 재질을 사용합니다. 새 벽/돌은 2m 세계 좌표 triplanar를, 가장자리 토양은 2m UV와 vertex alpha를 사용합니다. 첫 바닥 시각 높이 `Y0.005`, 기존 기단/문 잠금/카메라 충돌을 보존했습니다. 조명은 sky 반사·중립적인 warm key/cool fill·먼 배경 안개를 사용하며 Web에서 제공되지 않는 SSAO/SSR/볼류메트릭 효과에 의존하지 않습니다.

[manifest](inspection-manifest.json)에 원본 코드·재질·텍스처·실제 사용 runtime GLB·이미지의 SHA-256과 크기, 카메라 설정, 별도 검사 패키지 크기를 보관합니다. [브라우저 콘솔](web-inspection-console.json)은 오류 없이 두 검사 구도의 준비를 기록합니다. 별도 검사 패키지의 용량을 최종 배포 패키지 용량으로 재사용하지 않습니다.

실제 화면에서 바닥과 재질 분리·그림자·큰 배경 구도는 개선됐습니다. 큰 아치의 단순한 형상/마모 부족, 먼 방의 블록아웃, 풍경·초목·상세 조형과 캐릭터 최종 품질은 AAA 목표까지 남은 제작 범위입니다.
