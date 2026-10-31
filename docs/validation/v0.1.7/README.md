# Web 캐시와 저장소 순회 검증

v0.1.6의 실제 모바일 full 검사는 [PR CI](https://github.com/kosj/next-action-rpg/actions/runs/41208818257)에서821.980초·오류0으로 통과했다. 같은 source tree의 main/tag 첫 배포에서는 품질0 primary를30초 안에 관찰하지 못했고 배포/릴리스는 차단됐다. 이 실패를 성공으로 바꾸거나 숨기지 않는다.

- [main 첫 실행](https://github.com/kosj/next-action-rpg/actions/runs/41210719087/attempts/1):1027.110초·오류0·quality0 durable미관측.
- [tag 첫 실행](https://github.com/kosj/next-action-rpg/actions/runs/41210755726/attempts/1):1032.097초·오류0·같은 실패.
- `main-attempt1/`·`tag-attempt1/`: 실제 다운로드 artifact의 결과·timeout 관찰·메모리 파일·오류 원문. ZIP CRC도 확인했다.
- `before-userfs.json`: actualWeb0.1.6·3085c189/Godot4.7.2 새 프로필, 실제 새 여정을 시작한 뒤 readonly metadata만 조사했다. 33키 중29개가0byte 셰이더 캐시 디렉터리다.69.872초·오류0·browser/server종료·원본 export불변을 확인했다.
- `official-source.json`·`.md`: Godot ed1daf0bf001b61586d9930840f2f1394092c079의 기본 enabled·Web load/save 미지원·디렉터리 생성·실제 compile 경로와 Emscripten 참고 구현의 직렬 cursor를 고정 출처·원문 해시로 검증했다. Emscripten 참고 판본을 실제 엔진 SDK 판본으로 주장하지 않는다.

- `after-userfs.json`·`after-provenance.json`·`key-comparison.json`: 같은 실제Web/footer에서 설정 한 줄만 바꾼 fresh 프로필이5키·상위cache1개·67.148초·오류0이었다. 하위28디렉터리 생성을 막은 것을 확인했다. 원본manifest는이전ZIP의자료임을명시하고 실제exporthash를별도기록한다. `export-html.diff`는PCK64bytes증가에따른fileSizes갱신만이며JS/WASM/DOM/화질은유지한다.

- `after-settings/`: 원래15초UI/30초primary 조건의 actual settings-focus471.265초·오류0. 품질1→0→1 primary는각6.339/10.663/4.899초였고 세화면·실제Button-start스크롤·완전브라우저재시작·primary복원과PNG raster를 확인했다. 게임 상태 쓰기·강제sync·관찰값 캐싱이나제한확대는없다. 전체전투/입력여정과최종배포승인은아니다.
- 같은기존커밋의main단독재시도도품질0primary30초에서실패했다. 동시실행만의원인으로주장하지않는다. 해당결과도`main-attempt2/`에보존한다.

최종v0.1.7 build/fullmobile/public 검증은 진행 중이다. 기존 profile의 데이터/디렉터리를 삭제하지 않으며 fresh-key 개선을 기존 profile 개선으로 승계하지 않는다. [원칙과 남은 범위](../../WEB_USERFS_CACHE.md), 확정 후 [PR #8의 실제 배포 결과](https://github.com/kosj/next-action-rpg/pull/8)를 참조한다.
