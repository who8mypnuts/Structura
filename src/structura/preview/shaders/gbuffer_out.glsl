// Fragment outputs of the geometry pipelines.
//  * default: G-buffer (linear albedo + alpha, view-space normal, instance id = row + 1; 0 = background);
//  * OIT_ACCUM / OIT_REVEAL: weighted blended order-independent transparency (McGuire & Bavoil 2013) in
//    two passes, because GL 3.3 has no per-attachment blend functions.
#if defined(OIT_ACCUM) || defined(OIT_REVEAL)
uniform vec3 u_key_dir;   // view space
#ifdef OIT_ACCUM
layout(location = 0) out vec4 o_accum;
#else
layout(location = 0) out vec4 o_reveal;
#endif

void write_gbuffer(vec3 albedo, float alpha, vec3 n_view, uint id) {
#ifdef OIT_ACCUM
    vec3 n = normalize(n_view);
    vec3 c = albedo * (0.45 + 0.55 * max(dot(n, u_key_dir), 0.0)) + vec3(0.08) * pow(max(n.z, 0.0), 16.0);
    float z = gl_FragCoord.z;
    float w = clamp(pow(min(1.0, alpha * 10.0) + 0.01, 3.0) * 1e8 * pow(1.0 - z * 0.9, 3.0), 1e-2, 3e3);
    o_accum = vec4(c * alpha, alpha) * w;
#else
    o_reveal = vec4(alpha);
#endif
}
#else
layout(location = 0) out vec4 o_albedo;
layout(location = 1) out vec4 o_normal;
layout(location = 2) out uint o_id;     // opaque surface (lighting)
layout(location = 3) out uint o_pick;   // front-most surface including see-through ones (picking, outline)

void write_gbuffer(vec3 albedo, float alpha, vec3 n_view, uint id) {
    o_albedo = vec4(albedo, alpha);
    o_normal = vec4(normalize(n_view), 1.0);
    o_id = id;
    o_pick = id;
}
#endif
