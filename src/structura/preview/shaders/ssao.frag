#version 330
// Screen-space ambient occlusion, hemisphere kernel around the G-buffer normal (rendered at half resolution).
#include "view_pos.glsl"
uniform sampler2D u_normal;
uniform mat4 u_proj;
uniform float u_radius;        // view-space units
uniform vec3 u_kernel[16];
in vec2 v_uv;
out float o_ao;

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

void main() {
    if (texture(u_depth, v_uv).r >= 1.0) { o_ao = 1.0; return; }
    vec3 p = view_position(v_uv);
    vec3 n = normalize(texture(u_normal, v_uv).xyz);
    float a = hash12(gl_FragCoord.xy) * 6.2831853;
    vec3 rv = vec3(cos(a), sin(a), 0.0);
    vec3 t = normalize(rv - n * dot(rv, n) + vec3(1e-4));
    mat3 tbn = mat3(t, cross(n, t), n);
    float occlusion = 0.0;
    for (int i = 0; i < 16; ++i) {
        vec3 s = p + tbn * u_kernel[i] * u_radius;
        vec4 o = u_proj * vec4(s, 1.0);
        vec2 suv = o.xy / o.w * 0.5 + 0.5;
        float scene_z = view_position(suv).z;
        float range = smoothstep(0.0, 1.0, u_radius / max(abs(p.z - scene_z), 1e-6));
        occlusion += (scene_z >= s.z + 0.02 * u_radius ? 1.0 : 0.0) * range;
    }
    o_ao = 1.0 - occlusion / 16.0;
}
