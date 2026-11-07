shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;

// No TIME: the owning effect samples the authoritative attack clock, including
// the first confirmed contact sample and subsequent hit stop.
uniform vec4 tint : source_color = vec4(0.08, 0.62, 1.0, 1.0);
uniform vec4 hot_tint : source_color = vec4(0.60, 0.94, 1.0, 1.0);
uniform float effect_age = 0.0;
uniform float opacity : hint_range(0.0, 1.0) = 0.0;
uniform float energy = 1.2;
uniform int pattern = 0;

void fragment() {
	float across = abs(UV.y * 2.0 - 1.0);
	float edge = 1.0 - smoothstep(0.58, 1.0, across);
	float core = exp(-across * across * 32.0);
	float flow = 0.78 + 0.22 * sin(UV.x * 19.0 - effect_age * 12.0);
	float ends = smoothstep(0.0, 0.055, UV.x) * (1.0 - smoothstep(0.91, 1.0, UV.x));
	float mask = edge * ends * flow;
	if (pattern == 1) {
		// Broken glyph strips: strong lines, no opaque circular floor fill.
		mask = edge * (0.72 + 0.28 * sin(UV.x * 9.0 + effect_age * 5.0));
		core *= 0.22;
	} else if (pattern == 2) {
		// Small faceted motes retain a colored body instead of white points.
		mask = 0.78;
		core = 0.08;
	} else if (pattern == 3) {
		mask = edge * ends * (0.32 + 0.68 * pow(max(0.0, sin(UV.x * 12.0 - effect_age * 9.0)), 2.0));
		core *= 0.35;
	}
	vec3 color = mix(tint.rgb, hot_tint.rgb, core * 0.64) * energy;
	ALBEDO = color;
	EMISSION = color;
	ALPHA = clamp(mask * opacity * tint.a, 0.0, 0.78);
}
