shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled;

// A finite low-quality grounding approximation, not a projected light shadow.
uniform float opacity : hint_range(0.0, 0.3) = 0.0;

void fragment() {
	vec2 point = UV * 2.0 - 1.0;
	float radius_squared = dot(point, point);
	float feather = 1.0 - smoothstep(0.45, 1.0, radius_squared);
	ALBEDO = vec3(0.0);
	ALPHA = opacity * exp(-2.8 * radius_squared) * feather;
}
