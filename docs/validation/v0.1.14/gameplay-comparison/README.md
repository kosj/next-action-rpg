# 실제 45초 전투 전후 AV와 구도

2026-11-02 UTC. 루트와 독립 검토자가 실제 entry/contact/end 원본을 보고 **첫 방 전투 가독성의 프로토타입 개선을 채택**했다. 최종 after는 002이며 [기각 camera001](../rejected-camera-001/review.json)은 별도 기록이다. 참고 게임 매체를 재배포하지 않고 우리 게임 원본만 제공한다.

| take | 재생/다운로드 | 실제 입력 |
| --- | --- | --- |
| before | [before-logical1x.mp4](before-logical1x.mp4) ·27,007,720B | 공개 v0.1.13 `ff1171a1` archive에서 캡처한 baseline |
| 최종 after002 | [after-logical1x.mp4](after-logical1x.mp4) ·26,696,765B | dirty v0.1.14·ff1171a1 preview. clean CI/release 캡처 아님 |

각각 45초 gameplay + UI .4초로,2724 delivery frame/45.4초·logical1x다.60fps encoding은 목표 GPU60fps가 아니다. 실제 48kHz stereo mixer audio와 정확한 WAV PCM prefix를 보존했으며 MP4는 AAC lossy delivery다. 추가 음악·속도/시간 보간은 넣지 않았다. 영상을 제공했다는 사실은 제작자가1배속 전체를 시청하거나 직접 청취했다는 뜻이 아니다. 해당 품질 판정은 pending이다. 큰 매체는 game 밖에 두어 Web export 예산에 포함되지 않는다.

| event/movie frame | before 원본 | final after002 원본 |
| --- | --- | --- |
| entry2097 | [before](before-entry.png) | [after](after-entry.png) |
| contact2247 | [before](before-contact.png) | [after](after-contact.png) |
| end2723 | [before](before-end.png) | [after](after-end.png) |

6장은 raw MJPEG의 full960×600 decode를 그대로 복사했다. [source/decode 원장](source-decode-provenance.json)과 [원본 bytes/SHA](media-manifest.json)는 변환하지 않은 파일을 고정한다. 실제 Hero crop57→0/2700과 engaged locked foe0/626을 확인했다. foot/toe4+Grip/Tip2의6 marker도 각각 Hero2700/foe626에서 finite/inframe였다. 이는 깊이에 따른 가림·전체 mesh·UI 충돌·발 plant·모든 적의 지속적인 가시성을 보장하지 않는다. cyan forcefield wash·banner·겹치는 적·끝의 dark void/foreground edge는 남는다.

입력 controls/timing/health/contact69.3·serial42/release2224/contact2248/shared pause5는 일치한다. 그러나 후반 288개 distinct 행에서 root 위치가 달랐다(foe288/Hero244 section row=532). 첫 차이는 foe 2437/Hero2481로 contact 이후이며, 최대 Hero .030015m/foe.956972m다. 원인은 분리하지 못했다. 따라서 physics 동일이나 일반 결정론을 주장하지 않는다. 이전 기각001의0 mismatch는 그 take에만 해당한다.

[최종 checkpoint](../final45/checkpoint.json)·[actual paired audit](../final45/paired-audit.json)·[실제 trace/receipt 발췌](../final45/trace-excerpts.json)를 연결한다. clean CI/browser/공개/릴리스·전체 motion/skin/직접 청취·목표 하드웨어/AAA는 이 source snapshot에서 pending이다.
