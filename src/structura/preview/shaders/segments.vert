#version 330
#include "common.glsl"
// Screen-space thick segments generated from gl_VertexID (docs/08 §4):
// u_mode 0 = 'line' (one edge through the unit cube's x axis), 1 = 'grid' (the 12 cube edges).
uniform int u_mode;
uniform float u_width;         // pixels
in vec4 i_r0;
in vec4 i_r1;
in vec4 i_r2;
in vec4 i_color;
in uint i_id;
out vec4 v_color;
flat out uint v_id;

const vec3 EDGE_A[12] = vec3[](vec3(0,0,0), vec3(0,1,0), vec3(0,0,1), vec3(0,1,1), vec3(0,0,0), vec3(1,0,0),
                               vec3(0,0,1), vec3(1,0,1), vec3(0,0,0), vec3(1,0,0), vec3(0,1,0), vec3(1,1,0));
const vec3 EDGE_B[12] = vec3[](vec3(1,0,0), vec3(1,1,0), vec3(1,0,1), vec3(1,1,1), vec3(0,1,0), vec3(1,1,0),
                               vec3(0,1,1), vec3(1,1,1), vec3(0,0,1), vec3(1,0,1), vec3(0,1,1), vec3(1,1,1));
const vec2 CORNER[6] = vec2[](vec2(0,-1), vec2(1,-1), vec2(1,1), vec2(0,-1), vec2(1,1), vec2(0,1));

void main() {
    int edge = gl_VertexID / 6;
    vec2 corner = CORNER[gl_VertexID % 6];
    vec3 a = u_mode == 0 ? vec3(0.0, 0.5, 0.5) : EDGE_A[edge];
    vec3 b = u_mode == 0 ? vec3(1.0, 0.5, 0.5) : EDGE_B[edge];
    mat4 m = instance_matrix(i_r0, i_r1, i_r2);
    vec4 ca = u_proj * (u_view * (m * vec4(a, 1.0)));
    vec4 cb = u_proj * (u_view * (m * vec4(b, 1.0)));
    vec2 sa = ca.xy / ca.w, sb = cb.xy / cb.w;
    vec2 dir = (sb - sa) * u_viewport;
    vec2 nrm = length(dir) > 1e-6 ? normalize(vec2(-dir.y, dir.x)) : vec2(0.0, 1.0);
    vec4 clip = mix(ca, cb, corner.x);
    clip.xy += nrm * corner.y * u_width / u_viewport * clip.w;
    v_color = vec4(srgb_to_linear(i_color.rgb), i_color.a);
    v_id = i_id;
    gl_Position = clip;
}
