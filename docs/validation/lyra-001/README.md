# 리라 후보의 실제 Godot 반입 검증

2026-10-30, Godot 4.7.2 stable의 독립 임시 프로젝트에서 [실제 GLB](../../../art_source/production/candidates/lyra-001/lyra-locomotion.glb)를 반입했습니다. [결과](godot-import.json)는 원본 SHA와 53본·스킨 바인딩·4클립·CPU-skinned REST 높이/바닥·AnimationTree 수동 샘플링을 기록합니다. 모델의 raw mesh AABB는 스킨 inverse bind와 스켈레톤 변환을 반영하지 않으므로 실제 REST 크기 판정에 사용하지 않습니다.

`idle`·`walk`·`run`의 import loop mode는 모두 `NONE`입니다. 루프 이음새·발 접지·방향/그립·BoneMap·동적 root motion·전체 구간 변형·실제 GPU 화면 품질과 성능은 합격으로 표시하지 않습니다. 전투 6클립이 없으므로 기본 9모션 계약도 충족하지 않습니다.

검증 스크립트는 이 후보에 고정한 감사용 fixture이며 일반 리타겟 도구가 아닙니다. 재현할 때 `GODOT_BIN`은 `tools/toolchain.json`의 엔진을 가리켜야 합니다. 저장소 루트에서 다음을 실행합니다. 기존 게임이나 사용자의 저장 파일은 열지 않습니다.

```bash
RUNEFALL_AUDIT_DIR=$(mktemp -d /tmp/runefall-lyra-audit.XXXXXX)
cp art_source/production/candidates/lyra-001/lyra-locomotion.glb "$RUNEFALL_AUDIT_DIR/candidate.glb"
cp docs/validation/lyra-001/audit.gd "$RUNEFALL_AUDIT_DIR/audit.gd"
cat > "$RUNEFALL_AUDIT_DIR/project.godot" <<'EOF'
config_version=5
[application]
config/name="RUNEFALL isolated candidate audit"
[rendering]
renderer/rendering_method="gl_compatibility"
EOF
XDG_DATA_HOME="$RUNEFALL_AUDIT_DIR/data" XDG_CACHE_HOME="$RUNEFALL_AUDIT_DIR/cache" XDG_CONFIG_HOME="$RUNEFALL_AUDIT_DIR/config" "$GODOT_BIN" --headless --path "$RUNEFALL_AUDIT_DIR" --editor --import
XDG_DATA_HOME="$RUNEFALL_AUDIT_DIR/data" XDG_CACHE_HOME="$RUNEFALL_AUDIT_DIR/cache" XDG_CONFIG_HOME="$RUNEFALL_AUDIT_DIR/config" "$GODOT_BIN" --headless --path "$RUNEFALL_AUDIT_DIR" --script res://audit.gd
```

생성한 임시 디렉터리의 `audit-result.json`, 프로세스 종료 코드와 오류 로그를 함께 확인합니다. JSON이 있다고 성공으로 판정하지 않습니다.
