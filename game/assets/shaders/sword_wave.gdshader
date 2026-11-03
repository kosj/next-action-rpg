shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never;

// World-space crescent surfaces keep their existing prism geometry. Default
// depth testing remains enabled; transparent layers never occlude each other.
// Animation has one owner: the paused/inherited physics clock from the node.
uniform float wave_width = 2.0;
uniform float curvature = 0.34;
uniform float prism_depth = 0.24;
uniform float wave_age = 0.0;
uniform float wave_fade : hint_range(0.0, 1.0) = 1.0;
uniform int energy_layer = 0; // 0: volume, 1: narrow white core, 2: short wake.
varying vec3 local_point;

void vertex() {
	local_point = VERTEX;
}

void fragment() {
	float across = local_point.x * 2.0 / max(wave_width, 0.001);
	float behind = max(0.0, local_point.z-curvature*across*across);
	float edge = 1.0-smoothstep(0.72, 1.12, abs(across));
	float vertical = exp(-pow(local_point.y/0.085, 2.0));
	float flow = sin(local_point.x*20.0+behind*49.0-wave_age*22.0
		+sin(local_point.x*11.0+wave_age*9.0)*0.8);
	float wisp = pow(0.5+0.5*flow, 3.0);
	vec3 cyan = vec3(0.055, 0.60, 1.0);
	vec3 white = vec3(0.88, 0.98, 1.0);
	vec3 energy = cyan;
	float opacity = 0.0;
	if (energy_layer == 0) {
		// The visible volume has soft height/depth edges. Its rear face is
		// deliberately faint, so it reads as flowing energy rather than a slab.
		float front = exp(-behind*13.0);
		float narrow_core = exp(-pow(behind/0.038, 2.0))
			*exp(-pow(local_point.y/0.045, 2.0));
		opacity = (0.035+front*0.15)*vertical*edge*(0.65+0.35*wisp);
		energy = mix(cyan, white, narrow_core*0.8)*1.25;
	} else if (energy_layer == 1) {
		// This existing thin face/ridge becomes the white leading filament.
		// Additive, non-depth-writing surfaces expose it through the volume
		// without moving a vertex in front of the authoritative leading limit.
		float core = exp(-pow(behind/0.043, 2.0));
		float core_height = exp(-pow(local_point.y/0.032, 2.0));
		opacity = core*core_height*edge*(0.75+0.15*wisp);
		energy = mix(vec3(0.32, 0.88, 1.0), white, core)*2.1;
	} else {
		// Existing finite 0.32m wake: sparse filaments taper to zero at its
		// rear boundary, with no screen texture, particles or vertex expansion.
		float tail = 1.0-smoothstep(prism_depth, prism_depth+0.32, behind);
		float filament = pow(0.5+0.5*sin(local_point.x*29.0+behind*35.0
			-wave_age*18.0+sin(local_point.x*9.0)*1.3), 6.0);
		opacity = tail*tail*edge*(0.025+0.12*filament);
		energy = vec3(0.045, 0.40, 0.78);
	}
	ALBEDO = vec3(0.0);
	EMISSION = energy;
	ALPHA = clamp(opacity*wave_fade, 0.0, 0.9);
}
