shader_type spatial;
// Presentation-only overlay drawn over an actor's existing surfaces through
// GeometryInstance3D.material_overlay. It never replaces imported materials,
// writes depth or changes the silhouette used by gameplay.
render_mode unshaded, blend_add, depth_draw_never, cull_back, shadows_disabled, fog_disabled;

uniform vec4 flash_color : source_color = vec4(1.0, 0.93, 0.80, 1.0);
uniform float flash : hint_range(0.0, 2.0) = 0.0;
uniform vec4 ember_color : source_color = vec4(1.0, 0.58, 0.22, 1.0);
uniform vec4 rune_color : source_color = vec4(0.47, 0.92, 0.86, 1.0);
// 0 = intact, 1 = fully burnt into rune embers.
uniform float dissolve : hint_range(0.0, 1.0) = 0.0;
uniform float noise_scale = 3.4;

varying vec3 local_position;

float hash13(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}

float value_noise(vec3 p) {
	vec3 cell = floor(p);
	vec3 f = fract(p);
	vec3 u = f * f * (3.0 - 2.0 * f);
	float n000 = hash13(cell);
	float n100 = hash13(cell + vec3(1.0, 0.0, 0.0));
	float n010 = hash13(cell + vec3(0.0, 1.0, 0.0));
	float n110 = hash13(cell + vec3(1.0, 1.0, 0.0));
	float n001 = hash13(cell + vec3(0.0, 0.0, 1.0));
	float n101 = hash13(cell + vec3(1.0, 0.0, 1.0));
	float n011 = hash13(cell + vec3(0.0, 1.0, 1.0));
	float n111 = hash13(cell + vec3(1.0, 1.0, 1.0));
	return mix(mix(mix(n000, n100, u.x), mix(n010, n110, u.x), u.y),
		mix(mix(n001, n101, u.x), mix(n011, n111, u.x), u.y), u.z);
}

void vertex() {
	// Skinned model space keeps the burn pattern attached to the body.
	local_position = VERTEX;
}

void fragment() {
	float facing = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	float rim = pow(1.0 - facing, 2.2);
	vec3 color = flash_color.rgb * flash * (0.32 + 0.68 * rim);
	if (dissolve > 0.0) {
		// Burn front rises from the feet: height bias plus two noise octaves.
		float n = value_noise(local_position * noise_scale) * 0.62
			+ value_noise(local_position * noise_scale * 2.7) * 0.38;
		float field = n * 0.7 + clamp(local_position.y * 0.22, 0.0, 0.3);
		float front = dissolve * 1.15;
		float edge = smoothstep(front - 0.09, front, field) * (1.0 - smoothstep(front, front + 0.025, field));
		float burnt = 1.0 - smoothstep(front - 0.22, front - 0.02, field);
		float fade = 1.0 - smoothstep(0.75, 1.0, dissolve);
		color += ember_color.rgb * edge * 3.2 * fade;
		color += mix(ember_color.rgb, rune_color.rgb, 0.55) * burnt * 0.32 * fade;
		color += rune_color.rgb * rim * 0.35 * dissolve * fade;
	}
	ALBEDO = color;
	// Additive blend: black adds nothing, so a full alpha keeps exact colour.
	ALPHA = 1.0;
}
