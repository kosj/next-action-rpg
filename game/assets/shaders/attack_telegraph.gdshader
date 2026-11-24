shader_type spatial;
// Billboarded enemy attack warning glyph. Presentation only: the glyph reads
// the attack's own startup progress and never times or grants a parry.
render_mode unshaded, blend_add, depth_draw_never, depth_test_disabled, cull_disabled, shadows_disabled, fog_disabled;

// 0 at attack start, 1 when the active window opens.
uniform float progress : hint_range(0.0, 1.0) = 0.0;
// 0 = parryable (gold), 1 = unparryable (red).
uniform float danger : hint_range(0.0, 1.0) = 0.0;
uniform vec4 parry_color : source_color = vec4(1.0, 0.76, 0.36, 1.0);
uniform vec4 danger_color : source_color = vec4(1.0, 0.25, 0.16, 1.0);

void vertex() {
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
	MODELVIEW_MATRIX = MODELVIEW_MATRIX * mat4(
		vec4(length(MODEL_MATRIX[0].xyz), 0.0, 0.0, 0.0),
		vec4(0.0, length(MODEL_MATRIX[1].xyz), 0.0, 0.0),
		vec4(0.0, 0.0, length(MODEL_MATRIX[2].xyz), 0.0),
		vec4(0.0, 0.0, 0.0, 1.0));
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	vec2 p = (UV - 0.5) * 2.0;
	// Diamond frame contracts toward the core as the strike approaches.
	float closing = mix(1.0, 0.62, smoothstep(0.0, 1.0, progress));
	float diamond = abs(p.x) + abs(p.y);
	float outer = 1.0 - smoothstep(0.0, 0.06, abs(diamond - closing * 0.92));
	float inner = 1.0 - smoothstep(0.0, 0.05, abs(diamond - 0.38));
	// Vertical rune stroke with a separated dot: an exclamation read at a glance.
	// UV.y grows downward, so the stroke uses negative p.y (upper half).
	float stroke = (1.0 - smoothstep(0.05, 0.09, abs(p.x))) * step(-0.5, p.y) * step(p.y, 0.1);
	float dot_mark = 1.0 - smoothstep(0.07, 0.11, length(p - vec2(0.0, 0.3)));
	float glyph = max(max(outer, inner * 0.55), max(stroke, dot_mark));
	float halo = (1.0 - smoothstep(0.0, 1.0, diamond)) * 0.18;
	// Final 15% of startup: a sharp white-hot cue for the parry/dodge read.
	float cue = smoothstep(0.85, 0.97, progress);
	vec3 base = mix(parry_color.rgb, danger_color.rgb, danger);
	vec3 color = mix(base, vec3(1.0, 0.97, 0.9), cue * 0.75);
	float intensity = (glyph + halo) * mix(0.55, 1.0, progress) * (1.0 + cue * 0.9);
	ALBEDO = color * intensity;
	ALPHA = 1.0;
}
