#version 330
#include "common.glsl"
// Ray-cast sphere impostors: one camera-facing quad per instance (docs/08 §4).
uniform float u_fixed_radius;  // > 0: dots (world units)
in vec2 in_corner;             // (±1, ±1)
in vec4 i_r0;
in vec4 i_r1;
in vec4 i_r2;
in vec4 i_color;
in uint i_id;
out vec3 v_pos;                // view-space point on the billboard
flat out vec3 v_center;
flat out float v_radius;
out vec4 v_color;
flat out uint v_id;

void main() {
    mat4 m = instance_matrix(i_r0, i_r1, i_r2);
    vec3 c = (u_view * (m * vec4(0.5, 0.5, 0.5, 1.0))).xyz;
    float r = u_fixed_radius > 0.0 ? u_fixed_radius : 0.5 * length(m[2].xyz);
    float d = length(c);
    float grow = (u_ortho == 1 || d <= r * 1.01) ? 1.0 : d / sqrt(d * d - r * r);
    vec3 q = c + vec3(in_corner * r * grow * 1.05, 0.0);  // silhouette-covering quad at the centre depth
    vec3 p = q + vec3(0.0, 0.0, r);                        // ortho: simply move it in front of the sphere
    if (u_ortho == 0) p = (c.z + r < -1e-3) ? q * ((c.z + r) / c.z) : q;  // perspective: same projection
    v_pos = p;
    v_center = c;
    v_radius = r;
    v_color = vec4(srgb_to_linear(i_color.rgb), i_color.a);
    v_id = i_id;
    gl_Position = u_proj * vec4(p, 1.0);
}
