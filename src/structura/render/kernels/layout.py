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
CFG_SIZE = 48

CAMERA_TYPES = {"perspective": 0, "orthographic": 1, "spherical": 2, "fisheye": 3}

# Light records 'light_f' (float32 × LIGHT_F per light; packed by render/lights.py)
LIGHT_F = 16
L_TYPE, L_POS, L_RADIUS, L_INTENSITY, L_DIR, L_COS_OUTER, L_COS_INNER = 0, 1, 4, 5, 8, 11, 12
LIGHT_TYPES = {"point": 0, "sphere": 1, "spot": 2}

INTEGRATOR_PREVIEW, INTEGRATOR_AO, INTEGRATOR_PATH, INTEGRATOR_CLASSIC = 0, 1, 2, 3

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
