#version 330
// Deferred lighting (docs/08 §5): hemisphere ambient × AO + key light × shadow + specular; view transform.
#include "view_pos.glsl"
uniform sampler2D u_albedo;
uniform sampler2D u_normal;
uniform usampler2D u_id;
uniform usampler2D u_pick;
uniform sampler2D u_ao;
uniform sampler2D u_shadow;
uniform mat4 u_view_to_light;   // view space → light clip space
uniform mat4 u_view_to_world;
uniform vec3 u_key_dir;          // view space, towards the light
uniform vec3 u_key_color;
uniform vec3 u_sky;
uniform vec3 u_ground;
uniform vec3 u_bg_top;           // linear
uniform vec3 u_bg_bottom;
uniform int u_look;              // 0 studio, 1 legacy, 2 clay, 3 flat, 4 technical
uniform int u_effects;           // bit 0: AO, bit 1: shadows
uniform float u_exposure;
uniform uint u_selected;         // id + 1, 0 = none
uniform vec3 u_select_color;    // linear
uniform usampler2D u_highlight;  // one texel per SceneIR row, non-zero = highlighted (provenance hover)
uniform int u_highlight_on;
uniform sampler2D u_oit_accum;
uniform sampler2D u_oit_reveal;
uniform int u_oit;              // 1: blend the transparent layer
uniform int u_grid;             // 1: the ground grid
uniform vec4 u_grid_plane;      // world: height of the plane, centre x, centre z, fade radius
uniform float u_grid_step;      // world units between minor lines (major: ×10)
uniform vec3 u_grid_color;      // linear
in vec2 v_uv;
out vec4 o_color;

float shadow_at(vec3 p_view, vec3 n) {
    if ((u_effects & 2) == 0) return 1.0;
    vec4 l = u_view_to_light * vec4(p_view + n * 0.002 * length(p_view), 1.0);
    vec3 s = l.xyz / l.w * 0.5 + 0.5;
    if (any(lessThan(s.xy, vec2(0.0))) || any(greaterThan(s.xy, vec2(1.0)))) return 1.0;
    vec2 texel = 1.0 / vec2(textureSize(u_shadow, 0));
    float lit = 0.0;
    for (int x = -1; x <= 1; ++x)
        for (int y = -1; y <= 1; ++y)
            lit += s.z - 0.0015 <= texture(u_shadow, s.xy + vec2(x, y) * texel).r ? 1.0 : 0.0;
    return lit / 9.0;
}

vec3 tonemap(vec3 c) {
    c *= exp2(u_exposure);
    return c / (1.0 + 0.15 * c);   // gentle shoulder; keeps mid tones
}

bool outline() {
    if (u_selected == 0u) return false;
    ivec2 px = ivec2(gl_FragCoord.xy);
    uint here = texelFetch(u_pick, px, 0).r;
    bool inside = here == u_selected;
    for (int i = 0; i < 4; ++i) {
        ivec2 o = ivec2(i == 0 ? 1 : (i == 1 ? -1 : 0), i == 2 ? 1 : (i == 3 ? -1 : 0)) * 2;
        if ((texelFetch(u_pick, px + o, 0).r == u_selected) != inside) return true;
    }
    return false;
}

bool highlighted() {
    if (u_highlight_on == 0) return false;
    uint id = texelFetch(u_pick, ivec2(gl_FragCoord.xy), 0).r;
    if (id == 0u) return false;
    int row = int(id) - 1;
    int width = textureSize(u_highlight, 0).x;
    return texelFetch(u_highlight, ivec2(row % width, row / width), 0).r != 0u;
}

// Anti-aliased grid lines on the ground plane, hidden behind the structure; rgb + coverage.
float grid_lines(vec2 c) {
    vec2 g = abs(fract(c - 0.5) - 0.5) / max(fwidth(c), vec2(1e-6));
    return 1.0 - min(min(g.x, g.y), 1.0);
}

vec4 grid(uint id) {
    vec2 ndc = v_uv * 2.0 - 1.0;
    vec4 a = u_inv_proj * vec4(ndc, -1.0, 1.0);
    vec4 b = u_inv_proj * vec4(ndc, 1.0, 1.0);
    vec3 near_v = a.xyz / a.w, far_v = b.xyz / b.w;
    vec3 o = (u_view_to_world * vec4(near_v, 1.0)).xyz;
    vec3 d = (u_view_to_world * vec4(far_v - near_v, 0.0)).xyz;
    if (abs(d.y) < 1e-12) return vec4(0.0);
    float t = (u_grid_plane.x - o.y) / d.y;
    if (t <= 0.0) return vec4(0.0);
    vec3 p = o + d * t;
    if (id != 0u && -(near_v + (far_v - near_v) * t).z > -view_position(v_uv).z) return vec4(0.0);
    vec2 c = p.xz / u_grid_step;
    float line = max(grid_lines(c) * 0.3, grid_lines(c / 10.0) * 0.75);
    float fade = 1.0 - smoothstep(0.4, 1.0, length(p.xz - u_grid_plane.yz) / u_grid_plane.w);
    fade *= smoothstep(0.0, 0.15, abs(normalize(d).y));  // no moiré at the horizon
    return vec4(u_grid_color, line * fade);
}

// Technical look: dark lines where the depth or the normal jumps (object edges and creases).
float edge() {
    ivec2 px = ivec2(gl_FragCoord.xy);
    vec3 n = texelFetch(u_normal, px, 0).xyz;
    float z = view_position(v_uv).z;
    float e = 0.0;
    vec2 texel = 1.0 / vec2(textureSize(u_normal, 0));
    for (int i = 0; i < 4; ++i) {
        ivec2 o = ivec2(i == 0 ? 1 : (i == 1 ? -1 : 0), i == 2 ? 1 : (i == 3 ? -1 : 0));
        vec3 m = texelFetch(u_normal, px + o, 0).xyz;
        float zo = view_position(v_uv + vec2(o) * texel).z;
        e = max(e, max(1.0 - dot(n, m), 0.0) * 2.0);
        e = max(e, abs(zo - z) / max(abs(z), 1e-6) * 40.0);
    }
    return clamp(e, 0.0, 1.0);
}

vec3 shade(vec3 albedo, vec3 n, vec3 p) {
    float ao = (u_effects & 1) != 0 ? texture(u_ao, v_uv).r : 1.0;
    if (u_look == 3) return albedo;
    if (u_look == 4) return albedo * (0.8 + 0.2 * max(dot(n, normalize(-p)), 0.0));
    vec3 base = u_look == 2 ? vec3(0.72) : albedo;
    if (u_look == 1) {                                  // legacy: headlight Phong, no AO or shadows
        vec3 v = normalize(-p);
        float d = max(dot(n, v), 0.0);
        return base * (0.35 + 0.65 * d) + vec3(0.25) * pow(max(dot(reflect(-v, n), v), 0.0), 30.0);
    }
    vec3 n_world = mat3(u_view_to_world) * n;
    vec3 ambient = mix(u_ground, u_sky, n_world.y * 0.5 + 0.5) * ao;
    float sh = shadow_at(p, n);
    float ndl = max(dot(n, u_key_dir), 0.0);
    vec3 h = normalize(u_key_dir + normalize(-p));
    float spec = pow(max(dot(n, h), 0.0), 64.0) * 0.18 * sh * ndl;
    return base * (ambient + u_key_color * ndl * sh * mix(0.6, 1.0, ao)) + vec3(spec);
}

void main() {
    uint id = texture(u_id, v_uv).r;
    vec3 color;
    if (id == 0u) {
        color = mix(u_bg_bottom, u_bg_top, v_uv.y);
    } else {
        vec4 albedo = texture(u_albedo, v_uv);
        vec3 n = normalize(texture(u_normal, v_uv).xyz);
        color = tonemap(shade(albedo.rgb, n, view_position(v_uv)));
        if (u_look == 4) color = mix(color, vec3(0.0), edge() * 0.85);
    }
    if (u_grid == 1) {
        vec4 g = grid(id);
        color = mix(color, g.rgb, g.a);
    }
    if (u_oit == 1) {
        vec4 accum = texture(u_oit_accum, v_uv);
        float reveal = texture(u_oit_reveal, v_uv).r;
        if (reveal < 0.999) color = mix(tonemap(accum.rgb / max(accum.a, 1e-5)), color, reveal);
    }
    if (highlighted()) color = mix(color, u_select_color, 0.45);
    if (outline()) color = u_select_color;
    o_color = vec4(color, 1.0);   // linear, display-referred; present.frag encodes
}
