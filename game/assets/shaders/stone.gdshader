shader_type spatial;
varying vec3 world_pos;
uniform vec4 stone_color : source_color = vec4(0.19, 0.25, 0.26, 1.0);

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void vertex() { world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }
void fragment() {
    vec2 p = world_pos.xz;
    vec2 tile = floor(p / 2.0);
    float variation = hash(tile);
    vec2 edges = abs(fract(p / 2.0) - 0.5);
    float seam = smoothstep(0.478, 0.495, max(edges.x, edges.y));
    float grain = hash(floor(p * 35.0));
    ALBEDO = stone_color.rgb * (0.77 + variation * 0.35 + grain * 0.06) * (1.0 - seam * 0.5);
    ROUGHNESS = 0.82;
}
