"""Offsets of the per-pass configuration buffer 'cfg' (float32), shared by the host and the kernels."""

EYE, FORWARD, RIGHT, UP = 0, 3, 6, 9
TAN_HALF, ASPECT, APERTURE, FOCUS = 12, 13, 14, 15
BACKGROUND, EPS = 16, 19
SUN_DIR, SUN_COS, SUN_IRRADIANCE, AO_DIST = 20, 23, 24, 27
SKY_TOP, CLAMP = 28, 31
SKY_BOTTOM = 32
LIGHT_POS, SHADOWS = 36, 39  # classic: point light position, 1 = cast shadows
CAUSTIC_ALPHA = 40  # path: GGX alpha floor after a rough bounce (0 = full caustics)
BACKDROP_SKY = 41  # 1: camera rays that miss see the environment instead of the background colour
N_LIGHTS = 42  # number of records in light_f (path: next-event estimation for each)
CAM_TYPE, ORTHO_HALF, FISHEYE_FOV = 43, 44, 45  # 0 perspective, 1 orthographic, 2 spherical, 3 fisheye
ENV_ON, ENV_W, ENV_H, ENV_ROT, ENV_SCALE = 46, 47, 48, 49, 50  # environment map (render/environment.py)
N_EMITTERS = 51  # emissive primitives sampled as lights (render/emitters.py)
FILTER_ON, FILTER_RADIUS = 52, 53  # filter importance sampling (render/filters.py); 0 = box jitter
BLADES, BLADE_ROT = 54, 55  # polygonal aperture (bokeh): blade count (< 3: a round disc), rotation in radians
FOG_DENSITY, FOG_FALLOFF, FOG_BASE, FOG_COLOR = 56, 57, 58, 59  # kernels/fog.py; density 0 = no fog
PHOTONS_ON, PHOTON_RADIUS, PHOTON_TABLE = 62, 63, 64  # caustic photon map (kernels/photons.py); 0 = off
PHOTON_CENTRE, PHOTON_EXTENT, PHOTON_COUNT = 65, 68, 69  # photon emission: scene bounding sphere, photon count
SEQUENCE = 70  # 0: hashed random numbers; 1: Halton (rotated per pixel) for the pixel, lens and first bounce
DIFFUSE_BOUNCES, GLOSSY_BOUNCES, TRANSMISSION_BOUNCES = 71, 72, 73  # path: per-lobe limits (huge = none)
AO_DIRECT = 74  # ao: 1 adds direct light from the sun and the declared lights
CFG_SIZE = 80
FILTER_BASE = CFG_SIZE  # cfg[FILTER_BASE:] holds the filter table when FILTER_ON (render/filters.py)
FILTER_TABLE, FILTER_SIGNS = 256, 256  # FILTER_TABLE + 1 inverse-CDF offsets, then the signs

# The film 'accum' (float32 × FILM_F per pixel): RGB sum, weight sum, then the same for the even-numbered
# samples only. The two halves give the adaptive sampler its per-pixel error estimate (render/film.py).
FILM_F = 8

# Photons: the tracing pass writes PHOTON_OUT floats per photon (position, flux, direction towards where it
# came from, 1 = stored); the photon map 'photon_f' is a hash table of (start, count) pairs, PHOTON_TABLE of
# them, followed by the photons sorted by cell, PHOTON_F floats each (position, flux, direction).
PHOTON_OUT, PHOTON_F = 10, 9

CAMERA_TYPES = {"perspective": 0, "orthographic": 1, "spherical": 2, "fisheye": 3}

# Light records 'light_f' (float32 × LIGHT_F per light; packed by render/lights.py)
LIGHT_F = 16
L_TYPE, L_POS, L_RADIUS, L_INTENSITY, L_DIR, L_COS_OUTER, L_COS_INNER = 0, 1, 4, 5, 8, 11, 12
L_EDGE_V = 13  # rect: second half-edge (the first is stored at L_DIR); L_RADIUS holds the area
LIGHT_TYPES = {"point": 0, "sphere": 1, "spot": 2, "rect": 3}

INTEGRATOR_PREVIEW, INTEGRATOR_AO, INTEGRATOR_PATH, INTEGRATOR_CLASSIC = 0, 1, 2, 3

# Emitter records 'emit_f' (float32 × EMIT_F per emissive primitive; packed by render/emitters.py)
EMIT_F = 24
NO_EMITTER = 0xFFFFFFFF
E_KIND, E_PRIM, E_RADIANCE, E_AREA, E_SELECT, E_GEO = 0, 1, 2, 5, 6, 8  # kinds: 0 sphere, 1 box, 2 triangle

# Material records 'mat_f' (float32 × MAT_F per material; packed by render/materials.py)
MAT_F = 32
M_BASE, M_BASE_STATE = 0, 3  # rgb linear, 1 = use the instance colour
M_METALLIC, M_ROUGHNESS, M_SPECULAR, M_IOR = 4, 5, 6, 7
M_TRANSMISSION, M_TRANS_ROUGHNESS, M_COAT, M_COAT_ROUGHNESS = 8, 9, 10, 11
M_EMISSION, M_EMISSION_STATE = 12, 15  # rgb × strength (linear), 1 = instance colour × strength
M_OPACITY = 16  # < 0: instance alpha
M_ATTENUATION, M_ATTENUATION_DIST = 17, 20
M_LEGACY_AMBIENT, M_LEGACY_DIFFUSE, M_LEGACY_SPECULAR, M_LEGACY_REFLECTION = 21, 22, 23, 24
M_MODEL, M_THIN, M_ANISOTROPY, M_ANISO_ROTATION = 25, 26, 27, 28
M_EMISSION_STRENGTH = 29
