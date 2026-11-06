#version 330
// Average of the accumulated jittered frames, encoded to sRGB for the display.
uniform sampler2D u_accum;
uniform float u_inv_count;
in vec2 v_uv;
out vec4 o_color;

void main() {
    vec3 c = clamp(texture(u_accum, v_uv).rgb * u_inv_count, 0.0, 1.0);
    o_color = vec4(mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c)), 1.0);
}
