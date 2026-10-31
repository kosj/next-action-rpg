# Web shader-cache 후보의 공식 소스 근거

확인일: 2026-10-31. **공식 소스 분기는 verified, 실제33키 내용·성능 효과·설정 채택은 pending**이다. 이 폴더는 private 진단 자료이며 저장소 소스를 바꾸지 않았다.

Godot4.7.2-stable의 관측 short SHA `ed1daf0bf`와 태그는 모두 **ed1daf0bf001b61586d9930840f2f1394092c079**로 확인했다. Emscripten은 공식4.0.19의 **08e2de1031913e4ba7963b1c56f35f036a7d4d56**를 고정 참조한다. 해당 IDBFS 알고리즘은 현재 generated `index.js`의 remote cursor/reconcile과 같다. 실제 export template의 SDK 버전이4.0.19라는 주장은 하지 않는다.

## 실제 분기

- [기본 등록](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/servers/rendering/rendering_server.cpp#L3690-L3694)은 `enabled=true`다. 이 등록 원본 전체에 `shader_cache/enabled.web` 등록은 없다.
- [GLES 초기화](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/drivers/gles3/rasterizer_gles3.cpp#L336-L365)는 기본 `user://shader_cache`를 만든 뒤 enabled를 확인한다. false이면 non-editor cache 경로를 비워 per-shader 설정을 생략한다.
- [ShaderGLES3 초기화](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/drivers/gles3/shader_gles3.cpp#L774-L805)는 cache 경로가 있을 때 shader 이름과 hash 디렉터리를 만든다.
- 같은 파일의 [load547–550](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/drivers/gles3/shader_gles3.cpp#L547-L550), [save633–637](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/drivers/gles3/shader_gles3.cpp#L633-L637)는 `WEB_ENABLED`에서 GPU program-binary cache를 사용하지 않는다. [compile703–719](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/drivers/gles3/shader_gles3.cpp#L703-L719)는 cache load가 false이면 항상 실제 variant를 컴파일하므로 이 동작은 유지된다.
- [OS_Web74–89](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/platform/web/os_web.cpp#L74-L89)와 [GodotFS191–205](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/platform/web/js/libs/library_godot_os.js#L191-L205)는 다음 loop의 비동기 sync 경로다. [Emscripten197–224](https://github.com/emscripten-core/emscripten/blob/08e2de1031913e4ba7963b1c56f35f036a7d4d56/src/lib/libidbfs.js#L197-L224)는 timestamp cursor를 직렬 진행한 다음 reconcile을 수행한다.

후보는 **`rendering/shader_compiler/shader_cache/enabled.web=false` 한 설정**이다. fresh profile에서 불필요한 하위 디렉터리를 만들지 않을 수 있다. 최상위 `shader_cache`는 enabled 확인 전에 만들어지므로 남는다. **기존 persistent 디렉터리는 자동 삭제되지 않는다.** 33키가 실제로 이 디렉터리인지 먼저 읽기 전용으로 확인해야 한다.

이 후보는 이미지·화질·render scale·그림자·조명·재질·shader source/실제 compilation·브라우저 WebGL cache·저장 schema/rotation·자동 sync를 변경하지 않는다. 타임아웃 증가나 QA phase 완화, force sync를 제안하지 않는다. 실제30초 primary commit·품질0/1·완전 재시작 검증의 통과는 아직 주장하지 않는다. cursor마다 반드시1frame을 기다린다는 브라우저 스케줄 보장도 없다.

## 해시

[official-source.json](official-source.json)에6개 전체 원문의 UTF-8 bytes·SHA-256·Git blob SHA-1·고정 URL·관련 줄과 발췌를 보관했다. SHA-1/SHA-256 known vector를 검사했고, 모든 원문에서 재계산한 Git blob ID가 GitHub의 blob ID와 일치했다. 원문 전체를 이 문서에 복제하지 않았다.

