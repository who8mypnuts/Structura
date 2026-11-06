#version 330
// Add the current frame into the accumulation buffer (additive blending is enabled by the host).
uniform sampler2D u_source;
in vec2 v_uv;
out vec4 o_color;

void main() {
    o_color = texture(u_source, v_uv);
}
