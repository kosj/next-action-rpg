# v0.1.14 막힌 전투 카메라의 구도와 경로 검증

2026-11-02 UTC. [baseline14의 실제 decoded crop](validation/v0.1.14/baseline-14/README.md)과 [baseline45의57/2700 nominal crop](validation/v0.1.14/baseline-45-checkpoint.json)을 보존한다. camera004 source `a5198c6b4515e0c17381879aa5ffd14ecc44ba1601b3982addc1fe578265f813`는 **native에서는 제한적으로 통과했으나 실제 첫 after45의 완전한 전투 구도에서 기각**했다. 후속7b8c source는 별도 native 692/0·export와 actual after45-002에서 ROOT+독립 검토자의 첫 방 전투 가독성 prototype 채택을 확인했다. [최종 checkpoint](validation/v0.1.14/final45/checkpoint.json)와 [전후 AV/6원본](validation/v0.1.14/gameplay-comparison/README.md)을 제공한다. clean CI/browser/공개·릴리스·연속 시청/직접 청취·실기기/AAA는 pending이다. 사례 70의 verified는 이 제한된 관측·절차 범위다.

## 실제 gate·focus lag와 몸의 투영

[실제 native camera 보고서](validation/v0.1.14/native-camera-collision.json)는 닫힌 gate 뒤로 boom이 짧아지고 일반 sprint의 look focus가 늦는 조건을 재현한다. 같은 actual Camera3D에서 focus recenter만으로 짧은 boom의 머리/발이 들어오지 않는 witness를 보존한다. 몸의 nominal base/head/옆 radius와 실제 portrait/landscape viewport를 투영해 기존 전투 여백을 확인한다. evaluated skin·칼끝 전체·UI 가림을 모두 만족한다는 뜻이 아니다.

막혔을 때 fresh hero focus를 사용하고 bounded 최소 높이를 구한다. pivot→candidate ray, 현재 camera→candidate ray, near-radius **swept sphere**와 endpoint overlap을 함께 검사한다. endpoint나 pivot ray만 비어 있어도 위로 이동하는 길이 overhang을 통과하면 거부한다. 안전한 bounded fit이 없으면 `no_clear_bounded_fit`을 남기며 wall authority를 유지한다. 무조건 높은 곳으로 뛰어넘거나 FOV를 넓혀 가리지 않는다.

## followbase와 feedback을 분리한다

카메라의 latent followbase를 wall-resolved·un-kicked 위치로 따로 sync한다. obstruction height 보정이나 contact shake/kick를 다음 follow target에 누적하면 zero-delta 반복에도 떠오르는 windup이 생길 수 있다. native003에서 landscape/portrait 두 조건이 실제 실패했고 동일 기준으로004를 고쳤다. free composition·기존 feedback·lock recovery·zero-time stable state·overhang거부를 각각 확인한다.

yaw/input·baseFOV/feedback·피해·actorphysics·환경 collision은 유지한다. 그러나 latentbase 동기화가 바뀌므로 analytic 같은XZ 의도와 실제 이후 X/Z history의 byte동일은 다르다. runtime bitidentity를 주장하지 않는다. 같은 input policy에서도 실제AI/충돌 trajectory가 달라질 수 있으며 source/native·실제영상을 각각 대조한다.

## 검증 범위

[닫힌 native672/0/exit0·실패 원장](validation/v0.1.14/native-attempts-and-current.json)은 baseline loader의 editor-only context 실패와 실제 latent state 오류를 분리한다. 독립 GLTF100Hz originalcontrol은 baseline를 engine에서 재현하기 위한 장치이며 현재 production500Hz+100Hz posthook은 유지한다. 실제 source96/export map과 두ZIP은 [preview](validation/v0.1.14/local-preview-build.json)에 연결한다.

첫 after45 actual pair는 아래와 같이 확인하고 기각했다. 후속006의 source/native/export는 아래처럼 별도 확인했다. 실제after45-002는 이후 아래 최종 근거로 확인했다. realinputbrowser·연속시청/청취·실기기는 아직 없다. 단순한 낮은 crop count나 nominal body fit도 전체 skin·칼끝/적·오버행 모든환경·AAA를 승인하지 않는다.


## body-only fit의 실제 실패와 다음 후보 경계

[첫 after45 실제 pair](validation/v0.1.14/first-after45-rejected-checkpoint.json)는57→0/2700 nominal Hero crop을 확인했다. 루트는6paired entry/contact/end 원본을 모두 보고 entry/end의 과도한 topdown·바닥 중심·적 부재를 기각했다. [a519 snapshot·전후4원본](validation/v0.1.14/rejected-camera-001/review.json)을 그대로 보존한다. native672/0과 실제 export의 source 범위를 새 camera 성공으로 바꾸지 않는다. 최적화한 body-only 지표가 전체 전투 가독성을 대표하지 못한 사례다.

다음 source 후보는 실제 Sanctuary의 이미 반투명한 임시forcefield만 구분한다. 명시적으로 표시된 StaticBody·같은world·실제effective StandardMaterial의ALPHA mode/alpha≤.25 조건을 모두 만족할 때만 **모든cameraquery**에서 동일하게 제외하는 계획이다. actor/weapon physics·opaquegeometry·shape·material/visibility를 바꾸지 않고 normalboom이 기존translucentbarrier를 통과하게 한다. 표시만 있는opaquebody·다른world·뒤의solidwall은 제외하지 않아야 한다.

factory연결/actorweaponphysicalblocking/material불변·Hero+enemy구도·opaque-taggednegative/solidwallbehind와 기존solidwall/overhang/sweptvolume/zero-time 검사를 새 source에서 실행해야 한다. 이 내용은 당시 작업 방향이었다. 아래 현재006에서 구현/native/export를 별도로 확인했고 actualafter45-002는 이후 아래 최종 근거로 확인했다.


## 현재정책006: 물리벽과 camera가림의 제한적 분리

[새source와정책](validation/v0.1.14/current-camera-policy-006.json)은 camera SHA7b8c7c9d...·Sanctuary1553ecfe...을 고정한다. actualsingle-surface mesh/effective StandardMaterial3D의ALPHA mode·finite0≤alpha≤.25, explicittemporarybodytag·sameWorld를 모두 확인해 공통exclude list를 모든camera ray/sphere/sweep에 전달한다. 실제기존barrier는alpha.24이며 Sanctuary의새group1행 외sourcebyte는baseline과 같다.

[actualnative006](validation/v0.1.14/native-camera-policy-006.json)은 새20assertion으로factory14barrier group, landscape/portrait 양쪽Hero+lockedfoe 여백, playercapsulecast/unfilteredray의원래physicalblocking·opaque/disabledalpha/untagged/otherWorldnegative·solidwallbehind를 검증했다. 기존solidwall/overhang/zero-time assertions는 완화하지 않았다.005는692/0이라도 formattedmessage의ERROR2개로strict기각했고006는message-only수정뒤692/0/ERROR0/exit0이다.

새[previewsource96/export](validation/v0.1.14/local-preview-build-006.json)는 과거a519/672와별개다. staged원본은 전방Hero/세foe가보여 continuedvalidation에만허용했으며 pipeline의metadata-size 실패와 실제PNGdimensions·근사bonefit을 [별도](validation/v0.1.14/staged-camera-preflight-scope.json)로남겼다. settledsnap은 controller/AI/transition/skin/45초 proof가 아니다. 실제after45-002·최종pair구도는 이후 아래 범위로 채택했다. 입력browser·연속시청/청취·하드웨어/AAA는pending이다.


## actual45 최종 구도 판정

[actual002](validation/v0.1.14/final45/paired-audit.json)의 nominal Hero0/2700·실제 engaged foe0/626은 finite XY/nonbehind 검사다. 네 foot/toe와 두 weapon marker도 각각 Hero2700/foe626에서 모두 finite/inframe이고, independent locked actor UV 차이는 최대9.45e−8이다. 루트+독립 검토자는 실제6 paired entry/contact/end 원본에서 body/feet/blade·상대 context·전방 깊이를 보고 prototype 개선을 채택했다. body만 녹색이던001의 Hero0/foe23 기각과 구분한다.

marker containment는 depth occlusion/whole mesh/UI overlap·발 plant·모든 foe의 지속적인 가시성을 보장하지 않는다. cyan field wash/banner/겹침/dark outside platform은 남는다. 최종002의 후반 288 distinct 행에서 나타난 root 변동(최대 Hero .030015m/foe.956972m)은 contact 이후이며 원인을 분리하지 못했다. 같은 controls/timing/health/contact payload와 전체 physics 동일을 구분한다. source96/export byte 불변은 기능·하드웨어 보증과도 다르다. 새 browser/clean CI/공개·릴리스·전체 연속 시청/청취/AAA는 source snapshot에서 pending이다.
