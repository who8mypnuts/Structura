#version 330
// 4×4 box blur of the half-resolution AO (hides the rotation-noise pattern).
uniform sampler2D u_source;
in vec2 v_uv;
out float o_value;

void main() {
    vec2 texel = 1.0 / vec2(textureSize(u_source, 0));
    float sum = 0.0;
    for (int x = -2; x < 2; ++x)
        for (int y = -2; y < 2; ++y)
            sum += texture(u_source, v_uv + (vec2(x, y) + 0.5) * texel).r;
    o_value = sum / 16.0;
}
