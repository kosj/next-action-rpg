shader_type spatial;
// Billboarded enemy health/poise plate. Values are written by presentation
// code only; the quad has no collision and never affects combat state.
render_mode unshaded, blend_mix, depth_draw_never, depth_test_disabled, cull_disabled, shadows_disabled, fog_disabled;

uniform float health : hint_range(0.0, 1.0) = 1.0;
// Delayed "chip" that trails the real health after damage.
uniform float trail : hint_range(0.0, 1.0) = 1.0;
uniform float poise : hint_range(0.0, 1.0) = 0.0;
uniform float flash : hint_range(0.0, 1.0) = 0.0;
uniform float opacity : hint_range(0.0, 1.0) = 1.0;
uniform vec4 fill_color : source_color = vec4(0.86, 0.38, 0.29, 1.0);
uniform vec4 fill_low_color : source_color = vec4(0.62, 0.16, 0.13, 1.0);
uniform vec4 trail_color : source_color = vec4(1.0, 0.88, 0.62, 1.0);
uniform vec4 poise_color : source_color = vec4(1.0, 0.74, 0.32, 1.0);
uniform vec4 frame_color : source_color = vec4(0.78, 0.67, 0.47, 1.0);
uniform float aspect = 9.0;

void vertex() {
	// Same camera-facing basis as BaseMaterial3D BILLBOARD_ENABLED, keeping
	// the plate's own scale.
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
	MODELVIEW_MATRIX = MODELVIEW_MATRIX * mat4(
		vec4(length(MODEL_MATRIX[0].xyz), 0.0, 0.0, 0.0),
		vec4(0.0, length(MODEL_MATRIX[1].xyz), 0.0, 0.0),
		vec4(0.0, 0.0, length(MODEL_MATRIX[2].xyz), 0.0),
		vec4(0.0, 0.0, 0.0, 1.0));
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	vec2 uv = UV;
	// Slanted plate: a short parallelogram reads as a forged blade, not a UI rect.
	float x = uv.x + (uv.y - 0.5) * 0.035;
	float border_x = 0.012;
	float border_y = border_x * aspect;
	bool outside = x < 0.0 || x > 1.0;
	bool frame = x < border_x || x > 1.0 - border_x || uv.y < border_y || uv.y > 1.0 - border_y;
	float bar_bottom = poise > 0.001 ? 0.66 : 1.0 - border_y;
	vec3 color = vec3(0.025, 0.045, 0.05);
	float alpha = 0.82;
	if (!frame && uv.y < bar_bottom) {
		float sx = (x - border_x) / (1.0 - 2.0 * border_x);
		if (sx <= health) {
			float shade = 0.82 + 0.18 * (1.0 - smoothstep(0.15, 0.6, uv.y));
			color = mix(fill_low_color.rgb, fill_color.rgb, smoothstep(0.0, 0.55, health)) * shade;
			color = mix(color, vec3(1.0), flash * 0.65);
		} else if (sx <= trail) {
			color = trail_color.rgb;
		}
	} else if (!frame) {
		// Poise strip below health. It fills as stagger damage accumulates.
		float sx = (x - border_x) / (1.0 - 2.0 * border_x);
		color = sx <= poise ? poise_color.rgb * (0.75 + 0.25 * poise) : vec3(0.05, 0.04, 0.03);
	} else {
		color = frame_color.rgb * 0.75;
	}
	if (outside) {
		alpha = 0.0;
	}
	ALBEDO = color;
	ALPHA = alpha * opacity;
}
