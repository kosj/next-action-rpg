# v0.1.14 전투 연속 동작·카메라 검증

2026-11-02 UTC.006 guarded/broad blade 원본과 최종 actual after45-002를 ROOT+독립 검토자가 보고 **첫 방 전투 가독성의 prototype 개선을 채택**했다. native 692/0/ERROR0·실제 raw149,726,783B/양쪽 export·45.4초 mixer AV/PCM을 확인했다. **dirty0.1.14ff1171 preview이며 clean CI/browser/public/release·전체 연속 시청/직접 청취/full skin/하드웨어/AAA는 pending**이다. 이전 기각 source/native/export와 당시 pending 기록은 역사적 범위로 남긴다. [실제 전후 영상·6원본](gameplay-comparison/README.md)·[최종 checkpoint](final45/checkpoint.json)·[최종 actual pair](final45/paired-audit.json)를 먼저 확인한다.

| 근거 | 현재 범위 |
| --- | --- |
|[006adoption/source보존](source-adoption-and-preservation.json)|runtime14e5·6atlas/import/GLBimport불변·curve8946metadata inverse601a exact|
|[실제 native light](native-light-continuity.json)|새target3mm/53bones2700deg/s 안·원래control·right/grip/tip/joins; 전체skin/AV아님|
|[camera native](native-camera-collision.json)|actualgate/focuslag/portrait-landscape/bodyfit/overhang/latentfollow/feedback; actual첫raster completecomposition기각|
|[실패→최종672](native-attempts-and-current.json)|001type/002autoloadexit0stderr기각/003624·3실패 보존.004672/0/오류0/cleanup|
|[실제preview](local-preview-build.json)|dirty0.1.14ff1171,raw149722063/여유277937·양쪽export. WindowsOS실행별도|
|[source96/exportfreeze](local-runtime-source-freeze.json),[package](local-runtime-package.json)|선택96source/14Web/두ZIP·MD5·예산; cleanGit/공개판아님|
|[baseline14LP1](baseline-14/README.md)|actualdecoded3crop원본/trace/PCM·역사적runner6e970521|
|[baseline45LP3](baseline-45-checkpoint.json)|2724delivery45.4s/raw2728/실제mixer·contact/nominal57crop. 첫after45/pair완료·camera기각|

[연속전투 제작](../../COMBAT_CONTINUITY_SLICE.md)·[별도camera제작](../../CAMERA_COLLISION_FRAMING_SLICE.md)·[알려진후보/isolated관측/원본audio근거](draft-known-findings.json)를 분리한다.001~004 기각·005newtarget/sharpwrist·006검토 과정은 보존한다.006slim검6원본은 body/wrist범위이며 이후 actualbroad4원본의 판단과 섞지 않는다. isolatedobserver success는 Game/과거timeout 원인 증거가 아니다.

[첫 actualafter45checkpoint](first-after45-rejected-checkpoint.json)와 [ROOT기각·a519source/4untouched원본](rejected-camera-001/review.json)은 pipeline/body57→0과 적이 사라지는 구도 실패를 함께 보존한다.006model채택은 유지한다. 다음반투명forcefield조건 camera후보의새검증은 아직없다.


| 현재후속006 근거 | 확인한범위 |
| --- | --- |
|[정책/005실패→006692](current-camera-policy-006.json)|tag+sameWorld+actualsingleSurfaceStandardMaterialALPHAfinite0..25%; group1행외Sanctuary보존.005strictERROR2기각|
|[실제camera006](native-camera-policy-006.json)|기존solidwall/overhang/windup 유지·새20assertion/14factorygroup·양viewportHero+lockedfoe/원래physicalblocking/negative/solidwallbehind|
|[preview006](local-preview-build-006.json),[package006](local-runtime-package-006.json),[freeze96](local-runtime-source-freeze-006.json)|actualraw149726783/여유273217·양쪽export;dirtypreview/after45-browserpending|
|[staged실패와별도원본관찰](staged-camera-preflight-scope.json)|metadata640400실패유지/actualPNG960600·근사bonepose·continuedvalidationonly. 실제45대체아님|

최종actualafter45-002는이후[실제근거](final45/checkpoint.json)로제한적prototype채택했다. 이전a519first45는기각상태로유지한다.


최종Hero0/2700/실제engagedfoe0/626과평가된foot/toe/Grip/Tip6point의finite/inframe을확인했다. 이는depthocclusion/wholemesh/UI·발plant·모든적의항상가시성승인이아니다. 입력/타이밍/health/contactpayload는일치하지만후반 288distinct행/532section행에서actorroot가달랐다(최대Hero.030015m/foe.956972m,contact이후/원인미분리). 기각001의0mismatch를최종에승계하지않는다. [사후source96/export불변](final45/source-export-after-capture.json)과실제기능·hardware판정은분리한다.
