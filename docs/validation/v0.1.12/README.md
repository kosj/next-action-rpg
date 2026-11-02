# v0.1.12 성역 분위기·원경·바닥 검증

2026-11-02 UTC 최종 로컬 snapshot. baseline은 공개 v0.1.11/`ce120726`이다. [제작 경계](../../ENVIRONMENT_ATMOSPHERE_SLICE.md)에 따라 **001의 전체 분위기를 기각하고002 native 정지 화면을 prototype 범위로 채택했다.002 exact native523/0·Python51·Web/Windows export는 통과했고 실제 브라우저·clean CI·공개/릴리스는 pending**이다. 로컬 build는 dirty0.1.12·ce120 preview이며 이전 판본의 [공개 checkpoint](../v0.1.11/published-verification.json)를 승계하지 않는다.

| gate | 확인할 근거 | 현재 상태 |
| --- | --- | --- |
| 하늘·갑옷 전면 | [공식4source bytes/SHA·호출 경로](sky-renderer-evidence.json), static cubemap/RADIANCE·002 shader와 실제3구도 | native 실제 렌더 오류0·blue/cloud 분리 prototype 채택. 갑옷/기기 비용/AAA 별도 |
| 일관된 원경 | cliff3개 FLOOR_STONE/terrace·crown2개 limestone, shadow/GI OFF·새 texture 없음 | 실제5mesh/5surface/2102tri/6306vertex·safe_geometry true;002 재질 prototype 채택, 형상 한계/성능 별도 |
| 진입/연결 바닥 | PBR slot/실제 normal·1.8m tile/지지면·같은001→002 parameter | 실제7ray 지지/Y≈0 및 PBR3surface 확인·제한적 채택 |
| 권한과 source 보존 | [선택 critical10파일](source-preservation.json), [실제 collision/RNG와 source 차이](paired-capture-checkpoint.json) | canonical160body/178shape rows와 RNG exact·critical10 source bytes 동일. 미측정 vertex payload/모든 미래 동작을 주장하지 않음 |
| 품질 의미 | q0균형: 실제 key shadow ON / q1성능: OFF+근사 grounding; native/Web/DPR scale | native q0 1.0/q1.65 실제 확인; Web/DPR/최종 브라우저 pending |
| source×구도×품질 원본 | [baseline6/0026·기각0013 공개 원본과 근거](atmosphere-review/README.md) | baseline71.293초/002124.046초 오류0·짝 조건 일치. root q0landing/fight/overview+q1fight 직접 검수·제한적 채택 |
| source별 native/Python | [첫520/1](native-first-failure.json)·[001수정523/0](native-corrected-checkpoint.json) 보존, [최종002/66source·닫힌 log](native-final-checkpoint.json) | 최종002 새523/0/exit0/ERROR0·Python51/0/1.522초 |
| Web/Windows export | [실제 로컬 manifest·source 경계·bytes/SHA](local-preview-build.json) | exit0·rawWeb146,599,311B/14files<150MB·두ZIP. actual Windows OS/clean-release 별도 |
| 실제 브라우저 | desktop/mobile 입력·runtime 품질·새 source provenance·저장·재시작·오류 | pending |
| clean CI·공개·릴리스 | PR/main/tag 필수 gates·공개 runtime identity·실제 TLS 다운로드 | pending |
| 실기기·연속 AV·AAA | 목표 기기/GPU·실시간 동작과 청취·대표 구간 전체 아트 판정 | pending |

소프트웨어 native raster의 시간과 목표 GPU의 FPS, raw geometry 추가와 실제 상주/화면 비용, 시각 바닥과 충돌 지지면을 구분한다. 채택은 같은 입력의 실제 원본에 근거하며 후보만 색보정하거나 숫자만으로 성공이라 하지 않는다. source 경계가 바뀌면 촬영 당시와 최종 입력의 양쪽 해시를 남긴다.

공개한 지식 묶음1.4.5는 덮어쓰지 않는다. 다음1.4.6은 원본 카탈로그/근거를 먼저 커밋한 뒤 존재하는 source Git object에 고정하며, 아직 없는 미래 SHA나 미완료 검증을 기록하지 않는다.
