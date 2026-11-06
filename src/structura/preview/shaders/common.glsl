// Shared declarations for the preview engine's geometry shaders (GLSL 3.30 core).
uniform mat4 u_view;
uniform mat4 u_proj;
uniform vec2 u_viewport;   // pixels
uniform int u_ortho;       // 1: orthographic projection (also the shadow pass)

mat4 instance_matrix(vec4 r0, vec4 r1, vec4 r2) {
    return transpose(mat4(r0, r1, r2, vec4(0.0, 0.0, 0.0, 1.0)));
}

// Cofactor of the linear part: transforms normals, stays finite for flat (singular) instances.
vec3 normal_to_world(mat4 m, vec3 n) {
    vec3 a = m[0].xyz, b = m[1].xyz, c = m[2].xyz;
    mat3 cof = mat3(cross(b, c), cross(c, a), cross(a, b));
    vec3 w = cof * n;
    float len = length(w);
    return len > 1e-20 ? w / len : vec3(0.0, 0.0, 1.0);
}

vec3 srgb_to_linear(vec3 c) {
    return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}
