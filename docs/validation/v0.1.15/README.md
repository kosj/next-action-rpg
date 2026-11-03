# v0.1.15 대검 동작·이펙트 검증

2026-11-03 UTC. 공개 v0.1.14 `87fcefdd9a7e24f575e9d1b2df2e9273da29a8ab`와 새 후보를 비교했다. 일반 강공격은 작은 수평 베기에서 양손 머리 위 준비·내려베기로 바뀌었고, 실제 칼날 경로를 따르는 더 큰 fan이 보인다. 루트와 독립 검토자가 실제 원본을 직접 보고 **제한된 prototype 개선으로 채택**했다. 연속 시청·직접 청취·전체 skin·실기기·AAA 승인은 별도다.

| 근거 | 확인 범위 |
| --- | --- |
| [제작과 한계](../../DECISIVE_SWORD_SLICE.md) | 변경 이유·공식 문서·모션/판정/시각 권한 |
| [선택006](selected-candidate-pre-native.json) | 18개 기존 clip/channel·static 의미 보존, 새 곡선91/111 sample, raw2700deg/s·marker3mm·sole10mm 기준 |
| [native002와 preview](native-and-preview-002.json) | 714검사/0실패·ERROR0·양쪽 export; 첫707/3실패 보존 |
| [107개 소스 고정](runtime-source-freeze-002.json) | 실제 소스와14개 Web 파일·ZIP. 촬영 후 exact readback 동일 |
| [실제 Game 최종 감사](actual-game-final.json) | 같은 include-heavy policy의 before/after14·접촉/이동/PCM·finite 시각 검토 |
| [독립 원본 검토](independent-actual-game-review.md) | 머리 위 준비·큰 궤적은 채택; flat fan·겹침·어깨/손목·전체 리듬은 남음 |
| [live-reference 정리](live-reference-compaction.json) | 독립11 guard·core 의미/byte 보존. source 감소와 Web 증가를 구분 |
| [공식 문서·audio preflight](source-and-audio-preflight.json) | 기존9WAV byte 동일·baked lead .20/.28초·gain-only 변경·offline headroom |

전후 영상은 [이전](media/before-combat-logical1x-av.mp4)과 [개선 후](media/after-combat-logical1x-av.mp4)다. 각14.4초이며 engine 원본 PCM을 사용한 logical1x/60Hz 인코딩이다. q1 성능 모드·960×600·소프트웨어 raster의 scripted input이므로 사람 플레이나 목표 GPU60fps 측정이 아니다. [원본 파일 해시](media/manifest.json)와 [이전 일반 강공격](media/before-ordinary-heavy-active.png)·[개선 후](media/after-ordinary-heavy-active.png), [이전 접촉+2](media/before-charged-contact-plus2.png)·[개선 후](media/after-charged-contact-plus2.png)를 보관한다.

실제 일반 heavy 이동은2.091251→.7039995m이며 준비 중 glide를 없애고 active 구간만 이동했다. 완충 강타는 실제69.3 피해1회·공유 pause5tick·HP120→88이며 접촉은610→621tick으로 자연스럽게 달라졌다. 입력 policy가 같아도 world 위치·카메라·AI·접촉 시간은 같다고 가정하지 않는다. 양쪽 ordinary heavy/charged whiff는 피해를 만들지 않았다.

actual feet/toes/grip과 모든 공격의 blade tip sample은 프레임 안이었다. 이후 같은 dodge 동작에서 tip만 좌측으로 벗어난 표본은 baseline3→after5tick이다. nominal Hero/locked foe 검사가 전체 mesh·가림·UI 승인을 뜻하지 않는다. charged .262초 근처1191개 edge의 악화와 최대+18.438mm 같은-edge skin 위험도 남는다.

raw PCM694,400 sample frame과 전달 WAV691,200의 exact prefix/48k stereo·영상864frame/14.4초를 확인했고 clipping은0이었다. 기존 quiet lead에 player delay를 더하지 않았다. 실제 mix와 보존 검사는 직접 청취나 지각 타격감 승인과 다르다.

q0는 균형/shadow ON/Web 기본.8, q1은 성능/shadow OFF/.65다. impact 내부에서 뒤집혀 있던 particle 예산만 수정했다. 현재 dirty preview raw Web149,791,667B/150MB·여유208,333B로 v14보다63,348B 늘었다. source GLB 감소를 Web 절감으로 표시하지 않는다. clean CI·브라우저·공개 runtime·릴리스는 이 source 기록 시점에 pending이며 실제 결과는 해당 PR/Actions에서 확인한다. Windows export와 Windows OS 실행도 구분한다.
