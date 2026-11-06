#version 330
#include "common.glsl"
#include "gbuffer_out.glsl"
in vec3 v_pos;
flat in vec3 v_center;
flat in float v_radius;
in vec4 v_color;
flat in uint v_id;

void main() {
    vec3 ro = u_ortho == 1 ? vec3(v_pos.xy, 0.0) : vec3(0.0);
    vec3 rd = u_ortho == 1 ? vec3(0.0, 0.0, -1.0) : normalize(v_pos);
    vec3 oc = ro - v_center;
    float b = dot(oc, rd);
    float disc = b * b - (dot(oc, oc) - v_radius * v_radius);
    if (disc < 0.0) discard;
    float t = -b - sqrt(disc);
    vec3 p = ro + rd * t;
    vec4 clip = u_proj * vec4(p, 1.0);
    gl_FragDepth = 0.5 * (clip.z / clip.w) + 0.5;
    write_gbuffer(v_color.rgb, v_color.a, (p - v_center) / v_radius, v_id);
}
