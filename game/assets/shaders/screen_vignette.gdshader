shader_type canvas_item;
// Cheap full-screen overlay: no screen read. Low-health heartbeat, hurt edge
// flash and the cool rim of Rune Haste are pure alpha-blended gradients.

uniform float low_health : hint_range(0.0, 1.0) = 0.0;
uniform float pulse : hint_range(0.0, 1.0) = 0.0;
uniform float hurt : hint_range(0.0, 1.0) = 0.0;
uniform float haste : hint_range(0.0, 1.0) = 0.0;
uniform vec2 aspect = vec2(1.6, 1.0);

void fragment() {
	vec2 p = (UV - 0.5) * aspect;
	float radial = length(p) / length(aspect * 0.5);
	float edge = smoothstep(0.42, 1.02, radial);
	float tight = smoothstep(0.62, 1.05, radial);
	vec3 color = vec3(0.0);
	float alpha = 0.0;
	// Heartbeat: a dark red edge that thickens with each beat.
	float low_edge = smoothstep(0.36, 1.0, radial);
	float beat = low_health * (0.55 + 0.45 * pulse);
	float low_alpha = low_edge * beat * 0.85;
	color += vec3(0.5, 0.02, 0.04) * low_alpha;
	alpha += low_alpha;
	// Hurt: brief brighter red rim.
	float hurt_alpha = tight * hurt * 0.55;
	color += vec3(0.85, 0.08, 0.06) * hurt_alpha;
	alpha += hurt_alpha;
	// Haste: cold cyan frame that reads even with screen effects disabled.
	float haste_alpha = edge * haste * 0.34;
	color += vec3(0.1, 0.55, 0.62) * haste_alpha;
	alpha += haste_alpha;
	alpha = clamp(alpha, 0.0, 0.85);
	COLOR = vec4(alpha > 0.0001 ? color / alpha : vec3(0.0), alpha);
}
