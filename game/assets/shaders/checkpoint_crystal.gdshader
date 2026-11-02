shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

// One convex front-face shell over an opaque core. This is an authored crystal
// impression, not physical refraction. No screen/depth textures, TIME or glow.
uniform vec3 deep_tint : source_color = vec3(0.035, 0.23, 0.24);
uniform vec3 edge_tint : source_color = vec3(0.25, 0.65, 0.58);
uniform vec3 rune_tint : source_color = vec3(0.41, 0.83, 0.70);

float segment_distance(vec2 p, vec2 a, vec2 b) {
	vec2 edge = b-a;
	float along = clamp(dot(p-a,edge)/dot(edge,edge),0.0,1.0);
	return length(p-a-edge*along);
}

float rune_distance(vec2 p) {
	// Deliberately broad angular carving: one central stem with forked arms,
	// diamond shoulder and lower cross-stroke, rather than high-frequency noise.
	float d = segment_distance(p,vec2(0.50,0.25),vec2(0.50,0.76));
	d = min(d,segment_distance(p,vec2(0.50,0.73),vec2(0.29,0.58)));
	d = min(d,segment_distance(p,vec2(0.50,0.73),vec2(0.71,0.58)));
	d = min(d,segment_distance(p,vec2(0.29,0.58),vec2(0.50,0.45)));
	d = min(d,segment_distance(p,vec2(0.71,0.58),vec2(0.50,0.45)));
	d = min(d,segment_distance(p,vec2(0.33,0.35),vec2(0.67,0.35)));
	return d;
}

void fragment() {
	float fresnel = pow(1.0-clamp(dot(normalize(NORMAL),normalize(VIEW)),0.0,1.0),3.0);
	float distance_to_rune = rune_distance(UV);
	float carving = 1.0-smoothstep(0.012,0.026,distance_to_rune);
	float recess = 1.0-smoothstep(0.026,0.045,distance_to_rune);
	float interior = exp(-pow((UV.y-0.53)*3.1,2.0));
	vec3 mineral = mix(deep_tint,edge_tint,0.12+fresnel*0.48)*COLOR.rgb;
	ALBEDO = mix(mineral*(1.0-recess*0.35),rune_tint,carving*0.52);
	METALLIC = 0.12;
	SPECULAR = 0.58;
	ROUGHNESS = mix(0.23,0.42,recess);
	EMISSION = deep_tint*interior*0.12+edge_tint*fresnel*0.16+rune_tint*carving*0.68;
	// The bounded alpha preserves facet colour and leaves the real core visible.
	// Transparent sorting/overlap is an actual-camera acceptance gate.
	ALPHA = clamp(0.58+fresnel*0.17+carving*0.14,0.58,0.88);
}
