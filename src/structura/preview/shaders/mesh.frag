#version 330
#include "gbuffer_out.glsl"
in vec3 v_normal;
in vec4 v_color;
flat in uint v_id;

void main() {
    vec3 n = gl_FrontFacing ? v_normal : -v_normal;
    write_gbuffer(v_color.rgb, v_color.a, n, v_id);
}
