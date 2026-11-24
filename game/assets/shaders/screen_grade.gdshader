shader_type canvas_item;
// Short-lived screen-read grade. The owning node is hidden unless Rune Haste
// or an impact pulse is active, so idle frames do not copy the screen.

uniform sampler2D screen_texture : hint_screen_texture, filter_linear, repeat_disable;
uniform float haste : hint_range(0.0, 1.0) = 0.0;
uniform float impact : hint_range(0.0, 1.0) = 0.0;
uniform vec2 impact_center = vec2(0.5, 0.5);
// 0 performance: a single tap; 1 balanced: chromatic split and radial taps.
uniform float detail : hint_range(0.0, 1.0) = 1.0;

vec3 sample_scene(vec2 uv) {
	return texture(screen_texture, clamp(uv, vec2(0.001), vec2(0.999))).rgb;
}

void fragment() {
	vec2 uv = SCREEN_UV;
	vec3 color = sample_scene(uv);
	if (detail > 0.5) {
		if (impact > 0.001) {
			// Radial zoom blur toward the confirmed contact on screen.
			vec2 toward = impact_center - uv;
			vec3 sum = color;
			// The contact area stays sharp; blur grows toward the frame edge.
			float reach = smoothstep(0.08, 0.5, length(toward * vec2(1.6, 1.0)));
			float strength = impact * 0.034 * reach;
			for (int i = 1; i <= 5; i++) {
				sum += sample_scene(uv + toward * strength * float(i) / 5.0);
			}
			color = sum / 6.0;
		}
		if (haste > 0.001) {
			// Edge-weighted chromatic split for the slowed-time read.
			vec2 offset = (uv - 0.5) * 0.006 * haste;
			color.r = mix(color.r, sample_scene(uv + offset).r, 0.85);
			color.b = mix(color.b, sample_scene(uv - offset).b, 0.85);
		}
	}
	float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
	vec3 graded = mix(color, vec3(luma), 0.55 * haste);
	graded *= mix(vec3(1.0), vec3(0.82, 1.02, 1.08), haste);
	graded = mix(graded, graded * 1.06 + 0.02, impact * 0.5);
	COLOR = vec4(graded, 1.0);
}
