# 실제 baseline14-002 checkpoint

2026-11-02 UTC. 공개 baseline `ff1171a1`을 고정한 **기존 LP1** scripted native take다. runner SHA `6e97052114085fca5e9f45b149a22bf5a87f92ac8e2b654c876ef33559123fdc`와 [원본 capture](capture.json)·[checkpoint](checkpoint.json)·입력/전체 frames bytes/SHA를 보존한다. 현재 LP3 runner 실행으로 재해석하지 않는다.

physical960×600/source1440×900·q1의840gameplay+24UIframe,864deliveryframe/14.4초다. raw868frame의48kHz stereo PCM과 delivery864×800sample의 정확한 WAV prefix를 [원본 AV검증](av-verification.json)에 고정했다. MP4 AAC는 lossy이며 exact PCM은 AVI/WAV에 남는다. 큰 AV와 전체7.9MB trace는 복제하지 않고 retained original hash로 연결했다.870.559초는 offline 비용이며 실시간FPS가 아니다.

세 light·charged whiff·실제69.3 hurtbox contact/serial6/tick570/sharedpause5frame을 관측했다. audio attackID/point가 receipt와 맞고 PCM은 nonzero다. Audio API 자체에 serial이 없다는 경계와 혼합된 ambience/voices를 유지한다. HeroHP120→88, heal input1회/실제consume0회다. [정확한4trace행419/421/570/864와receipt](trace-excerpts.json), [post-take감사](post-take-audit.json)를 보존한다. 기존 runtime bytes는 불변이나 새 fixture UID가 생겼으므로 whole project file-set equality는 false다.

## 실제 decoded crop 원본

[frame provenance](decoded-frame-provenance.json)의 MJPEG AVI에서 decode한 full960×600 원본이다. viewport PNG와 같은 byte라는 뜻은 아니며 crop/resize/retouch/보간하지 않았다.

| movie frame / physics tick | 원본 | 관찰 |
| --- | --- | --- |
|418 /419|[decoded01](decoded-01.png)|입구에서 Hero 오른쪽 몸이 심하게 잘림|
|420 /421|[decoded02](decoded-02.png)|발이 아래 frame 밖|
|863 /864|[decoded03](decoded-03.png)|끝의 발이 아래 frame 밖|

nominal projection31/840도 frame 밖이다. 이는 이미 해결한 physical writer aspect mismatch와 별개인 production-camera 구도 문제이며 원인을 collision/clamp로 확정하지 않는다. 성공한 원본 캡처와 잘린 구도는 함께 보존한다. 선택 still은 연속시청·직접청취·hardware/AAA 승인이 아니고 새006 runtime/camera fix/native/export는 아직 없다.
