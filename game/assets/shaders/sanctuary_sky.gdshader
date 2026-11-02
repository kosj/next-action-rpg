shader_type sky;
render_mode use_debanding;

// Authored static atmosphere. Noise runs only while the radiance cube is baked;
// the visible background samples that cube. No clock or camera-position input.
uniform vec3 zenith_color : source_color = vec3(0.10, 0.27, 0.50);
uniform vec3 horizon_color : source_color = vec3(0.22, 0.43, 0.66);
uniform vec3 horizon_warmth : source_color = vec3(0.69, 0.66, 0.58);
uniform vec3 cloud_light : source_color = vec3(0.80, 0.79, 0.73);
uniform vec3 cloud_shadow : source_color = vec3(0.24, 0.37, 0.51);
uniform vec3 ground_color : source_color = vec3(0.10, 0.15, 0.18);
// Set once from SanctuaryKey's actual local +Z, the direction toward the sun.
uniform vec3 sun_direction = vec3(-0.552, 0.669, 0.497);
uniform float sky_energy : hint_range(0.1, 2.0) = 0.90;
uniform float cloud_coverage : hint_range(0.0, 1.0) = 0.42;

float hash_sky(vec2 p) {
	vec3 q = fract(vec3(p.x, p.y, p.x) * 0.1031);
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

float noise_sky(vec2 p) {
	vec2 cell = floor(p);
	vec2 f = fract(p);
	vec2 w = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash_sky(cell), hash_sky(cell + vec2(1.0, 0.0)), w.x),
		mix(hash_sky(cell + vec2(0.0, 1.0)), hash_sky(cell + vec2(1.0)), w.x), w.y);
}

float cloud_field(vec2 p) {
	// Four fixed octaves, evaluated once per cube texel rather than per frame.
	return noise_sky(p) * 0.58
		+ noise_sky(p * 2.03 + vec2(17.1, 3.7)) * 0.25
		+ noise_sky(p * 4.11 + vec2(4.8, 11.2)) * 0.12
		+ noise_sky(p * 8.21 + vec2(8.4, 6.3)) * 0.05;
}

vec3 sanctuary_atmosphere(vec3 direction) {
	float height = max(direction.y, 0.0);
	float sunward = max(dot(direction, normalize(sun_direction)), 0.0);
	// The blue transition starts immediately above a narrow warm horizon.
	vec3 clear_sky = mix(horizon_color, zenith_color, pow(height, 0.42));
	float horizon_band = pow(1.0 - height, 18.0);
	clear_sky = mix(clear_sky, horizon_warmth, horizon_band * (0.10 + 0.56 * pow(sunward, 4.0)));
	clear_sky += vec3(0.25, 0.19, 0.10) * pow(sunward, 32.0);
	// A continuous projected dome avoids a longitude seam. Broad low clouds
	// remain readable in the low fight camera; higher wisps break their outline.
	vec2 p = direction.xz / (height + 0.38);
	float lower_field = cloud_field(p * 2.1 + vec2(6.3, -2.4));
	float higher_field = cloud_field(p * vec2(4.2, 1.8) + vec2(-8.1, 5.7));
	float lower_cloud = smoothstep(0.54, 0.72, lower_field + cloud_coverage * 0.12);
	float higher_cloud = smoothstep(0.57, 0.78, higher_field) * 0.42;
	float cloud_band = smoothstep(0.015, 0.09, height) * (1.0 - smoothstep(0.65, 0.95, height));
	float clouds = max(lower_cloud, higher_cloud) * cloud_band;
	float lit_edge = clamp((lower_field - 0.45) * 2.0 + sunward * 0.40, 0.0, 1.0);
	vec3 cloud_color = mix(cloud_shadow, cloud_light, 0.46 + lit_edge * 0.54);
	cloud_color += vec3(0.09, 0.055, 0.015) * pow(sunward, 8.0);
	vec3 upper = mix(clear_sky, cloud_color, clouds * 0.88);
	vec3 lower = mix(ground_color, horizon_color * 0.62, pow(1.0 + min(direction.y, 0.0), 12.0));
	return mix(lower, upper, smoothstep(-0.025, 0.015, direction.y)) * sky_energy;
}

void sky() {
	if (AT_CUBEMAP_PASS) {
		COLOR = sanctuary_atmosphere(EYEDIR);
	} else {
		COLOR = texture(RADIANCE, EYEDIR).rgb;
	}
}
