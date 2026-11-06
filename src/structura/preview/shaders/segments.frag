#version 330
#include "gbuffer_out.glsl"
in vec4 v_color;
flat in uint v_id;

void main() {
    write_gbuffer(v_color.rgb, v_color.a, vec3(0.0, 0.0, 1.0), v_id);
}
