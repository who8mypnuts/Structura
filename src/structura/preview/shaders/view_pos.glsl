// Reconstruct a view-space position from the depth buffer.
uniform sampler2D u_depth;
uniform mat4 u_inv_proj;

vec3 view_position(vec2 uv) {
    float d = texture(u_depth, uv).r;
    vec4 v = u_inv_proj * vec4(uv * 2.0 - 1.0, d * 2.0 - 1.0, 1.0);
    return v.xyz / v.w;
}
