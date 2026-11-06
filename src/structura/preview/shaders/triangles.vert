#version 330
#include "common.glsl"
in vec3 in_pos;
in vec3 in_normal;
in vec4 in_color;
in uint in_id;
out vec3 v_normal;
out vec4 v_color;
flat out uint v_id;

void main() {
    vec4 view = u_view * vec4(in_pos, 1.0);
    v_normal = mat3(u_view) * in_normal;
    v_color = vec4(srgb_to_linear(in_color.rgb), in_color.a);
    v_id = in_id;
    gl_Position = u_proj * view;
}
