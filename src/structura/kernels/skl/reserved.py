"""Identifiers reserved in at least one SKL target (C/C++/CUDA, OpenCL C, WGSL, GLSL).

The front end rejects them so that names are identical on every target (backends bind uniforms by name).
"""

from __future__ import annotations

C_CPP = """auto break case char const continue default do double else enum extern float for goto if inline int long
register restrict return short signed sizeof static struct switch typedef union unsigned void volatile while bool
true false class private protected public template this typename virtual namespace using new delete operator
friend mutable explicit export static_cast const_cast dynamic_cast reinterpret_cast try catch throw
noexcept nullptr constexpr decltype alignas alignof char16_t char32_t thread_local asm uint uchar ushort ulong
half size_t"""
OPENCL = """kernel global local constant private read_only write_only read_write image2d_t image3d_t sampler_t event_t
__kernel __global __local __constant __private"""
WGSL = """alias array atomic bitcast break case const const_assert continue continuing default diagnostic discard else
enable f16 f32 fn for i32 if let loop mat2x2 mat3x3 mat4x4 override ptr requires return sampler struct switch
texture_2d true u32 var vec2 vec3 vec4 while workgroup storage uniform function module handle meta mut self
super target type typedef typeof unless unsafe use where yield abstract as async await become box crate
do dyn enum extern final impl in macro match move mod of pub ref static trait try unsized virtual"""
GLSL = """attribute const uniform varying buffer shared coherent volatile restrict readonly writeonly layout centroid
flat smooth noperspective patch sample subroutine in out inout invariant precise discard return lowp mediump
highp precision input output filter common partition active sizeof cast namespace using main gl_Position
sampler2D image2D atomic_uint dvec2 dvec3 dvec4 ivec2 ivec3 ivec4 uvec2 uvec3 uvec4 bvec2 bvec3 bvec4 mat2 mat3
mat4 vec2 vec3 vec4 float int uint double void bool struct params"""

RESERVED: frozenset[str] = frozenset((C_CPP + " " + OPENCL + " " + WGSL + " " + GLSL).split())
