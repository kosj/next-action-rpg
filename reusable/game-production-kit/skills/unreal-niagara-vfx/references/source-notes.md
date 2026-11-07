# Unreal VFX 출처·버전·확인 범위

조사일 **2026-11-07 UTC**. 열람한 Epic 문서는 대체로 UE5.8 제목을 표시한다. 본문에는5.2/5.4의 도입 설명도 남아 있으므로 제목만으로 설치본 기능·실험 상태·API 호환성을 확정하지 않는다. 아래는 문서 조사이며 새 Unreal 프로젝트에서 실행한 근거가 아니다.

## 지정 참고 자료

[RedefineFX The Witcher 강좌 소개](https://redefinefx.com/witcher/)의 공개 소개/목차를 참고한다. 앞선 조사에서 소개·목차를 확인했고 강의실의 전체20개 영상·자막·제공 프로젝트는 시청/실습하지 않았다. 여기의 절차·예시는 독립 작성한 실무 종합이며 해당 강의의 정확한 그래프·파라미터로 귀속하지 않는다. 공개 무료 소개를 원본 자료/자산의 재배포 허가로 해석하지 않는다.

## Epic 공식 문서

| 출처 | 스킬에 사용하는 범위 |
| --- | --- |
| [Niagara Overview](https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-niagara-effects-for-unreal-engine) | System/Emitter/Module/Parameter와 stack/renderer의 역할 구분. 오래된4.27 overview URL 대신 현재 UE5 문서를 열람했다. |
| [Niagara Renderers](https://dev.epicgames.com/documentation/en-us/unreal-engine/render-module-reference-for-niagara-effects-in-unreal-engine) | sprite·ribbon·mesh 등의 표시 후보와 binding·component/light 비용을 대조한다. 선택한 renderer의 실제 자료형/기능은 설치본에서 검증한다. |
| [Niagara Fluids](https://dev.epicgames.com/documentation/en-us/unreal-engine/niagara-fluids-in-unreal-engine) | plugin 기반 유체와 template, 무거운 효과의 베이크 대안을 확인했다. |
| [Fluids Quick Start](https://dev.epicgames.com/documentation/en-us/unreal-engine/niagara-fluids-quick-start-guide-for-unreal-engine) | plugin/template·domain/resolution·source/control의 역할을 참고한다. tutorial의 특정 tag/수치/Beta 문장을 모든 시스템·현재 설치본에 일반화하지 않는다. |
| [Flipbook Baker](https://dev.epicgames.com/documentation/en-us/unreal-engine/niagara-flipbook-baker-quick-start-guide-in-unreal-engine) | 촬영 시간/카메라·정수 grid·sprite Sub UV·alpha를 대조한다. 스킬에는 원본 tutorial의 고정 수치를 필수값으로 복제하지 않는다. |
| [Caching and Reusing](https://dev.epicgames.com/documentation/en-us/unreal-engine/caching-and-reusing-your-system) | Sim Cache·Sequencer·User Parameters의 범위. point와 grid의 temporal 처리 차이를 확인하고 cache와 atlas를 구분한다. |
| [Sim Cache API](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/Niagara/UNiagaraSimCache), [Ribbon API](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/Niagara/UNiagaraRibbonRendererProperties) | 캐시의 선택 attribute와 캡처 경로, ribbon ID/link order·표시 자료의 경계를 대조했다. 빠른 무기 표본 누락은 tessellation만으로 복원되지 않는다는 것은 자체 엔지니어링 판단이다. |
| [Spawn System at Location](https://dev.epicgames.com/documentation/en-us/unreal-engine/BlueprintAPI/Niagara/SpawnSystematLocation), [Spawn System Attached](https://dev.epicgames.com/documentation/en-us/unreal-engine/BlueprintAPI/Niagara/SpawnSystemAttached) | spawn/attachment·auto activation·pooling·반환 component 입력을 확인했다. 비활성 생성→입력→활성화는 이를 이용한 자체 통합 권고다. |
| [Scalability and Best Practices](https://dev.epicgames.com/documentation/en-us/unreal-engine/scalability-and-best-practices-for-niagara) | instance/emitter CPU 비용, Effect Types·pooling·bounds·warmup·품질별 선택을 조사했다. 모든 프로젝트의 최적 설정이나 특정 experimental 기능의 현재 출하 상태로 쓰지 않는다. |
| [Niagara Debugger](https://dev.epicgames.com/documentation/en-us/unreal-engine/niagara-debugger-for-unreal-engine) | Debug HUD·FX Outliner·Performance와 실제 활성 객체/비용 관찰을 위한 도구. debugger speed/pause는 gameplay 시간과 별도다. |

## 적용 전에 확인할 것

실제 엔진/plugin 버전과 상태, RHI·기기·목표 빌드, 자료형·소켓/단위·동결 정책, graph의 pin과 asset reference를 확인한다. 특히 GPU 결과의 gameplay readback/네트워크 권한, pool·Auto Destroy 수명, cache의 attribute·재생 제약은 사용하는 구현에서 시험한다.

이 스킬에는 `.uasset`, `.uproject`, 실제 bake/cook/package 결과가 포함되지 않는다. 템플릿의 runtime·성능·시각/음향·AAA 상태는 모두 `pending`이며 패키지의 문서/무결성 검사로 이를 승격하지 않는다.

## 공개 제작글을 이용한 후속 보강

2026-11-07 추가 조사에서는 [제작 실험 노트](redefinefx-production-lab.md)에 연결한 RedefineFX의 유리 파괴 제작기·Magic 소개·Pyro/Liquids 업데이트·MCP 소개 본문을 읽었다. 목차 밖의 공개 기술 설명을 확인한 범위다. 출처의 사실과 자체적인 증상 진단/튜닝/반증 기준은 구분한다. 전체 영상·유료 강의·원본 프로젝트를 열람한 것으로 바꾸지 않으며 새 효과의 실행은 여전히 pending이다.
