#version 330
#include "common.glsl"
in vec3 in_pos;
in vec3 in_normal;
in vec4 i_r0;
in vec4 i_r1;
in vec4 i_r2;
in vec4 i_color;
in uint i_id;
out vec3 v_normal;
out vec4 v_color;
flat out uint v_id;

void main() {
    mat4 m = instance_matrix(i_r0, i_r1, i_r2);
    vec4 view = u_view * (m * vec4(in_pos, 1.0));
    v_normal = mat3(u_view) * normal_to_world(m, in_normal);
    v_color = vec4(srgb_to_linear(i_color.rgb), i_color.a);
    v_id = i_id;
    gl_Position = u_proj * view;
}
