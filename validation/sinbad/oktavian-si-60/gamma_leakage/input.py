"""Detector-explicit 3-D model of the SINBAD OKTAVIAN Si-60 gamma experiment.

The geometry, materials, D-T source law, detectors, and tally grids are defined
in this file from the detailed benchmark models.  The circular neutron-emission
spot is represented by an equal-area rectangular block spanning the modeled
Ti-T target thickness; see README.md before interpreting C/E results.
"""

import numpy as np

import mcdc

# ======================================================================================
# Benchmark data
# ======================================================================================

# Tabulated D-T source law used by the detailed neutron-analysis model.
# Direction cosine is measured from the deuteron-beam axis (+y).  The same law
# is used here as a fully supported approximation to the gamma-analysis model's
# custom deuteron-transport source routine.
D_T_DIRECTION_COSINES = np.array(
    [
        -1.0000,
        -0.9962,
        -0.9848,
        -0.9659,
        -0.9397,
        -0.9063,
        -0.8660,
        -0.8192,
        -0.7660,
        -0.7071,
        -0.6428,
        -0.5736,
        -0.5000,
        -0.4226,
        -0.3420,
        -0.2588,
        -0.1737,
        -0.0872,
        0.0000,
        0.0872,
        0.1737,
        0.2588,
        0.3420,
        0.4226,
        0.5000,
        0.5736,
        0.6428,
        0.7071,
        0.7660,
        0.8192,
        0.8660,
        0.9063,
        0.9397,
        0.9659,
        0.9848,
        0.9962,
        1.0000,
    ]
)
D_T_RELATIVE_YIELDS = np.array(
    [
        0.8973,
        0.8975,
        0.8980,
        0.8990,
        0.9003,
        0.9019,
        0.9039,
        0.9062,
        0.9089,
        0.9118,
        0.9150,
        0.9185,
        0.9222,
        0.9261,
        0.9302,
        0.9344,
        0.9387,
        0.9431,
        0.9476,
        0.9521,
        0.9566,
        0.9610,
        0.9653,
        0.9695,
        0.9735,
        0.9774,
        0.9810,
        0.9844,
        0.9876,
        0.9904,
        0.9929,
        0.9950,
        0.9968,
        0.9982,
        0.9992,
        0.9998,
        1.0000,
    ]
)
D_T_ENERGIES_MEV = np.array(
    [
        13.36,
        13.365,
        13.37,
        13.385,
        13.4,
        13.425,
        13.45,
        13.49,
        13.53,
        13.58,
        13.62,
        13.67,
        13.71,
        13.8,
        13.88,
        13.92,
        13.97,
        14.04,
        14.1,
        14.165,
        14.23,
        14.32,
        14.4,
        14.44,
        14.48,
        14.54,
        14.6,
        14.65,
        14.7,
        14.74,
        14.78,
        14.81,
        14.84,
        14.86,
        14.88,
        14.885,
        14.89,
    ]
)
SOURCE_DISK_RADIUS_CM = 0.3
SOURCE_BLOCK_HALF_WIDTH_CM = 0.5 * np.sqrt(np.pi) * SOURCE_DISK_RADIUS_CM
SOURCE_BLOCK_THICKNESS_CM = 0.0011

ROOM_TEMPERATURE_K = 293.6

# ======================================================================================
# Helper functions
# ======================================================================================


def material(name, composition):
    """Create a room-temperature material from atomic number densities."""
    return mcdc.Material(
        name=name,
        nuclide_composition=composition,
        temperature=ROOM_TEMPERATURE_K,
    )


def split_natural_element(total_density, abundances):
    """Expand one natural-element density using explicit atom fractions."""
    return {
        nuclide: total_density * fraction for nuclide, fraction in abundances.items()
    }


def plane_along(name, normal, distance):
    """Create a plane normal to a unit vector at its signed distance."""
    return mcdc.Surface.Plane(
        name=name,
        A=normal[0],
        B=normal[1],
        C=normal[2],
        D=-distance,
    )


def box_region(name, x_bounds, y_bounds, z_bounds):
    """Create an axis-aligned rectangular-parallelepiped region."""
    x_min = mcdc.Surface.PlaneX(name=f"{name} x min", x=x_bounds[0])
    x_max = mcdc.Surface.PlaneX(name=f"{name} x max", x=x_bounds[1])
    y_min = mcdc.Surface.PlaneY(name=f"{name} y min", y=y_bounds[0])
    y_max = mcdc.Surface.PlaneY(name=f"{name} y max", y=y_bounds[1])
    z_min = mcdc.Surface.PlaneZ(name=f"{name} z min", z=z_bounds[0])
    z_max = mcdc.Surface.PlaneZ(name=f"{name} z max", z=z_bounds[1])
    return +x_min & -x_max & +y_min & -y_max & +z_min & -z_max


def local_box_region(name, x_bounds, y_bounds, z_bounds, basis):
    """Create a box whose coordinates are projections onto an orthonormal basis."""
    x_axis, y_axis, z_axis = basis
    x_min = plane_along(f"{name} local x min", x_axis, x_bounds[0])
    x_max = plane_along(f"{name} local x max", x_axis, x_bounds[1])
    y_min = plane_along(f"{name} local y min", y_axis, y_bounds[0])
    y_max = plane_along(f"{name} local y max", y_axis, y_bounds[1])
    z_min = plane_along(f"{name} local z min", z_axis, z_bounds[0])
    z_max = plane_along(f"{name} local z max", z_axis, z_bounds[1])
    return +x_min & -x_max & +y_min & -y_max & +z_min & -z_max


def frustum_surface(name, axis, base_distance, length, base_radius, end_radius):
    """Create the infinite cone underlying a coaxial truncated cone."""
    slope = (end_radius - base_radius) / length
    apex_distance = base_distance - base_radius / slope
    apex = axis * apex_distance
    half_angle = np.degrees(np.arctan(abs(slope)))
    return mcdc.Surface.Cone(
        name=name,
        apex=apex,
        axis=axis,
        half_angle=half_angle,
    )


def union(regions):
    """Return the Boolean union of a nonempty sequence of regions."""
    result = regions[0]
    for region in regions[1:]:
        result = result | region
    return result


# ======================================================================================
# Set model
# ======================================================================================

simulation = mcdc.Simulation("SINBAD OKTAVIAN Si-60 gamma-leakage experiment")

# Materials
# The detailed benchmark model specifies atomic densities in atoms/(barn cm).
# Its natural-element carbon and argon entries are expanded here because MC/DC
# consumes isotope tables.  The fractions are the natural abundances used by
# MC/DC; this conversion is documented as a reproducibility item in README.md.
carbon_abundances = {"C12": 0.9894, "C13": 0.0106}
argon_abundances = {"Ar36": 0.003336, "Ar38": 0.000629, "Ar40": 0.996035}

tritium_titanium = material(
    "Ti-T target",
    {
        "H3": 1.0076e-1,
        "Ti46": 4.1572e-3,
        "Ti47": 3.7490e-3,
        "Ti48": 3.7148e-2,
        "Ti49": 2.7261e-3,
        "Ti50": 2.6102e-3,
    },
)
copper = material("Copper target backing", {"Cu63": 5.8732e-2, "Cu65": 2.6178e-2})
stainless_steel = material(
    "SUS-304 stainless steel",
    {
        "Cr50": 7.5725e-4,
        "Cr52": 1.4603e-2,
        "Cr53": 1.6558e-3,
        "Cr54": 4.1217e-4,
        "Fe54": 3.4694e-3,
        "Fe56": 5.4462e-2,
        "Fe57": 1.2578e-3,
        "Fe58": 1.6738e-4,
        "Ni58": 5.2553e-3,
        "Ni60": 2.0243e-3,
        "Ni61": 8.7997e-5,
        "Ni62": 2.8057e-4,
        "Ni64": 7.1454e-5,
        "Mn55": 1.7363e-3,
    },
)
air_composition = {
    "N14": 4.3248e-5,
    "N15": 1.5974e-7,
    "O16": 1.0170e-5,
    "O17": 3.8739e-9,
}
air_composition.update(split_natural_element(1.8876e-7, argon_abundances))
air = material("Standard air", air_composition)
iron_composition = {
    "Si28": 3.5705e-4,
    "Si29": 1.8130e-5,
    "Si30": 1.1951e-5,
    "P31": 3.0524e-5,
    "S32": 1.3995e-5,
    "S33": 1.1205e-7,
    "S34": 6.3246e-7,
    "S36": 2.9486e-9,
    "Mn55": 7.6582e-4,
    "Fe54": 4.8830e-3,
    "Fe56": 7.6652e-2,
    "Fe57": 1.7702e-3,
    "Fe58": 2.3559e-4,
}
iron_composition.update(split_natural_element(6.2974e-4, carbon_abundances))
iron = material("Collimator iron", iron_composition)
paraffin_composition = {"H1": 8.2558e-2, "H2": 9.4952e-6}
paraffin_composition.update(split_natural_element(3.9700e-2, carbon_abundances))
paraffin = material("C25H52 paraffin", paraffin_composition)
polyethylene_composition = {"H1": 8.0704e-2}
polyethylene_composition.update(split_natural_element(4.0358e-2, carbon_abundances))
polyethylene = material("Gamma-collimator polyethylene", polyethylene_composition)
heavy_concrete = material(
    "Heavy concrete",
    {
        "H1": 8.8413e-3,
        "H2": 1.0169e-6,
        "O16": 4.7929e-2,
        "O17": 1.1675e-4,
        "Mg24": 1.3758e-3,
        "Mg25": 1.7418e-4,
        "Mg26": 1.9177e-4,
        "Al27": 8.2580e-4,
        "Si28": 5.0487e-3,
        "Si29": 2.5636e-4,
        "Si30": 1.6900e-4,
        "Ca40": 2.5870e-3,
        "Ca42": 1.7266e-5,
        "Ca43": 3.6026e-6,
        "Ca44": 5.5667e-5,
        "Ca46": 1.0674e-7,
        "Ca48": 4.9903e-6,
        "Fe54": 1.1777e-3,
        "Fe56": 1.8487e-2,
        "Fe57": 4.2695e-4,
        "Fe58": 5.6820e-5,
    },
)
ordinary_concrete = material(
    "Ordinary concrete",
    {
        "H1": 6.0889e-3,
        "H2": 7.0030e-7,
        "O16": 4.3305e-2,
        "O17": 1.6496e-5,
        "Na23": 8.9997e-4,
        "Al27": 1.7852e-3,
        "Si28": 1.6034e-2,
        "Si29": 8.1418e-4,
        "Si30": 5.3671e-4,
        "Ca40": 1.8979e-3,
        "Ca42": 1.2667e-5,
        "Ca43": 2.6430e-6,
        "Ca44": 4.0840e-5,
        "Ca46": 7.8312e-8,
        "Ca48": 3.6611e-6,
        "Fe54": 1.9542e-5,
        "Fe56": 3.0677e-4,
        "Fe57": 7.0847e-6,
        "Fe58": 9.4284e-7,
    },
)
lead = material(
    "Gamma-collimator lead",
    {
        "Pb204": 4.6142e-4,
        "Pb206": 7.9429e-3,
        "Pb207": 7.2838e-3,
        "Pb208": 1.7270e-2,
    },
)
stainless_steel_316 = material(
    "Gamma-collimator SUS-316 stainless steel",
    {
        "Si28": 1.5662e-3,
        "Si29": 7.9529e-5,
        "Si30": 5.2426e-5,
        "Cr50": 6.7754e-4,
        "Cr52": 1.3066e-2,
        "Cr53": 1.4815e-3,
        "Cr54": 3.6879e-4,
        "Mn55": 1.7363e-3,
        "Fe54": 3.2697e-3,
        "Fe56": 5.1327e-2,
        "Fe57": 1.1854e-3,
        "Fe58": 1.5775e-4,
        "Ni58": 6.6383e-3,
        "Ni60": 2.5571e-3,
        "Ni61": 1.1115e-4,
        "Ni62": 3.5441e-4,
        "Ni64": 9.0257e-5,
        "Mo92": 1.8443e-4,
        "Mo94": 1.1496e-4,
        "Mo95": 1.9786e-4,
        "Mo96": 2.0730e-4,
        "Mo97": 1.1869e-4,
        "Mo98": 2.9989e-4,
        "Mo100": 1.1968e-4,
    },
)
detector_composition = {"H1": 4.5042e-2, "H2": 5.1805e-6}
detector_composition.update(split_natural_element(5.7890e-2, carbon_abundances))
ne218 = material("NE-218 liquid scintillator", detector_composition)
nai = material(
    "NaI gamma detector crystal",
    {"Na23": 1.474435e-2, "I127": 1.474435e-2},
)
silicon = material(
    "Granular silicon",
    {"Si28": 2.5511e-2, "Si29": 1.2954e-3, "Si30": 8.5391e-4},
)

# Surfaces and regions
# Sample, source-target assembly, and reentrant beam duct.  The coordinate
# system follows the detailed benchmark model, with the deuteron beam along +y.
target_front = mcdc.Surface.PlaneY(name="Target front", y=0.0)
target_back = mcdc.Surface.PlaneY(name="Target back", y=0.0011)
backing_back = mcdc.Surface.PlaneY(name="Copper backing back", y=0.0211)
tube_cap_end = mcdc.Surface.PlaneY(name="Beam-tube cap end", y=0.1211)
tube_start = mcdc.Surface.PlaneY(name="Beam-tube upstream end", y=-200.0)
target_radius = mcdc.Surface.CylinderY(name="Target radius", radius=1.5)
tube_inner = mcdc.Surface.CylinderY(name="Beam-tube inner radius", radius=1.5)
tube_outer = mcdc.Surface.CylinderY(name="Beam-tube outer radius", radius=1.6)
duct_inner = mcdc.Surface.CylinderY(name="Beam-duct inner radius", radius=5.55)
duct_outer = mcdc.Surface.CylinderY(name="Beam-duct outer radius", radius=5.75)
cavity_inner = mcdc.Surface.Sphere(name="Central cavity", radius=10.0)
inner_vessel_outer = mcdc.Surface.Sphere(name="Inner vessel outer surface", radius=10.2)
silicon_outer = mcdc.Surface.Sphere(name="Silicon outer surface", radius=30.0)
vessel_outer = mcdc.Surface.Sphere(name="Outer vessel surface", radius=30.5)

target_region = +target_front & -target_back & -target_radius
backing_region = +target_back & -backing_back & -target_radius
beam_tube_region = (+backing_back & -tube_cap_end & -tube_outer) | (
    -tube_outer & +tube_inner & -backing_back & +tube_start
)
beam_duct_air_region = (
    -target_front & -duct_inner & +cavity_inner & -vessel_outer & ~beam_tube_region
)
inner_vessel_region = (
    (+cavity_inner & -inner_vessel_outer & +duct_inner & -target_front)
    | (+cavity_inner & -inner_vessel_outer & +target_front)
    | (+duct_inner & -duct_outer & +cavity_inner & -vessel_outer & -target_front)
)
sample_region = (
    +inner_vessel_outer
    & -silicon_outer
    & ~beam_tube_region
    & ~beam_duct_air_region
    & ~inner_vessel_region
)
outer_vessel_region = (
    +silicon_outer
    & -vessel_outer
    & ~beam_tube_region
    & ~beam_duct_air_region
    & ~inner_vessel_region
)

# The neutron and gamma detector line is 55 degrees from +y.  These are the
# local axes encoded by the detailed models' transformation card.  The complete
# gamma-analysis configuration is used below: its NaI collimator occupies the
# space assigned to the alternative iron/paraffin pre-collimator in the
# neutron-only model, while retaining the main neutron collimator, housing, and
# NE-218 detector.
angle = np.deg2rad(55.0)
local_x = np.array([0.0, 0.0, 1.0])
local_y = np.array([-np.sin(angle), np.cos(angle), 0.0])
local_z = np.cross(local_x, local_y)
detector_basis = (local_x, local_y, local_z)

inner_frustum = frustum_surface(
    "Inner collimator frustum", local_y, 550.0, 550.0, 18.5, 7.0
)
outer_frustum = frustum_surface(
    "Outer collimator frustum", local_y, 550.0, 550.0, 18.5, 12.0
)
shield_box_20 = box_region(
    "Shield box 20", (-773.55, -713.55), (370.0, 700.0), (-150.0, 150.0)
)
shield_box_21 = box_region(
    "Shield box 21", (-853.55, -773.55), (335.0, 524.0), (-150.0, 150.0)
)
shield_box_22 = box_region(
    "Shield box 22", (-853.55, -773.55), (-200.0, 800.0), (-150.0, 150.0)
)
housing_front = mcdc.Surface.PlaneX(name="Housing global-x front", x=-853.55)
housing_local_front = plane_along("Housing local-y front", local_y, 1070.0)
housing_box_25 = local_box_region(
    "Housing box 25", (-40.0, 40.0), (1070.0, 1130.0), (-40.0, 40.0), detector_basis
)
housing_box_26 = local_box_region(
    "Housing box 26", (-36.0, 36.0), (1074.0, 1126.0), (-36.0, 36.0), detector_basis
)
housing_box_27 = local_box_region(
    "Housing box 27", (-32.0, 32.0), (1078.0, 1122.0), (-32.0, 32.0), detector_basis
)
detector_front = plane_along("NE-218 front", local_y, 1094.9)
detector_back = plane_along("NE-218 back", local_y, 1100.0)
detector_radius = mcdc.Surface.Cylinder(name="NE-218 radius", axis=local_y, radius=6.35)
nai_collimator_435 = plane_along("Gamma collimator 435 cm", local_y, 435.0)
nai_collimator_440 = plane_along("Gamma collimator 440 cm", local_y, 440.0)
nai_collimator_485 = plane_along("Gamma collimator 485 cm", local_y, 485.0)
nai_collimator_545 = plane_along("Gamma collimator 545 cm", local_y, 545.0)
nai_collimator_560 = plane_along("Gamma collimator 560 cm", local_y, 560.0)
nai_detector_front = plane_along("NaI detector front", local_y, 580.0)
nai_detector_back = plane_along("NaI detector back", local_y, 587.1)
nai_collimator_655 = plane_along("Gamma collimator 655 cm", local_y, 655.0)
nai_detector_radius = mcdc.Surface.Cylinder(
    name="NaI detector radius", axis=local_y, radius=3.81
)
nai_lead_inner = mcdc.Surface.Cylinder(
    name="NaI lead inner radius", axis=local_y, radius=4.0
)
nai_lead_outer = mcdc.Surface.Cylinder(
    name="NaI lead outer radius", axis=local_y, radius=6.0
)
nai_concrete_inner = mcdc.Surface.Cylinder(
    name="NaI concrete inner radius", axis=local_y, radius=42.0
)
nai_polyethylene_inner = mcdc.Surface.Cylinder(
    name="NaI polyethylene inner radius", axis=local_y, radius=25.0
)
nai_collimator_outer = mcdc.Surface.Cylinder(
    name="NaI collimator outer radius", axis=local_y, radius=50.0
)
nai_inner_frustum = frustum_surface(
    "NaI inner collimator frustum", local_y, 0.0, 545.0, 60.0, 4.0
)
nai_outer_frustum = frustum_surface(
    "NaI outer collimator frustum", local_y, 0.0, 545.0, 60.0, 6.0
)

collimator_iron_region = shield_box_20 & +inner_frustum & -outer_frustum
collimator_heavy_region = shield_box_20 & +outer_frustum
upstream_heavy_region = shield_box_21
ordinary_shield_region = shield_box_22 & ~shield_box_21 & +inner_frustum
downstream_iron_region = (
    +inner_frustum & -outer_frustum & -housing_front & -housing_local_front
)
paraffin_housing_region = (
    housing_box_25 & ~housing_box_26 & +inner_frustum & -housing_front
)
concrete_housing_region = housing_box_26 & ~housing_box_27 & +inner_frustum
detector_region = +detector_front & -detector_back & -detector_radius
nai_detector_region = +nai_detector_front & -nai_detector_back & -nai_detector_radius
nai_polyethylene_region = (
    +nai_collimator_435
    & -nai_collimator_545
    & +nai_polyethylene_inner
    & -nai_collimator_outer
)
nai_concrete_region = (
    -nai_detector_front
    & +nai_collimator_560
    & +nai_concrete_inner
    & -nai_collimator_outer
) | (
    +nai_collimator_440
    & -nai_collimator_485
    & +nai_outer_frustum
    & -nai_polyethylene_inner
)
nai_paraffin_region = (
    -nai_collimator_545
    & +nai_collimator_485
    & +nai_outer_frustum
    & -nai_polyethylene_inner
) | (
    -nai_collimator_outer
    & -nai_collimator_655
    & +nai_collimator_560
    & ~nai_concrete_region
    & +nai_lead_outer
)
nai_lead_region = (
    +nai_collimator_545 & -nai_collimator_655 & +nai_lead_inner & -nai_lead_outer
) | (
    +nai_inner_frustum & -nai_outer_frustum & +nai_collimator_435 & -nai_collimator_545
)
nai_stainless_steel_region = (
    -nai_collimator_560 & +nai_collimator_545 & -nai_collimator_outer & +nai_lead_outer
) | (
    +nai_collimator_435
    & -nai_collimator_440
    & +nai_outer_frustum
    & -nai_polyethylene_inner
)

# Cells
regions_and_fills = [
    ("Ti-T target", target_region, tritium_titanium),
    ("Copper target backing", backing_region, copper),
    ("Stainless-steel beam tube", beam_tube_region, stainless_steel),
    ("Air-filled reentrant beam duct", beam_duct_air_region, air),
    ("Inner vessel and duct wall", inner_vessel_region, stainless_steel),
    ("Granular silicon pile", sample_region, silicon),
    ("Outer stainless-steel vessel", outer_vessel_region, stainless_steel),
    ("Gamma-collimator polyethylene", nai_polyethylene_region, polyethylene),
    ("Gamma-collimator paraffin", nai_paraffin_region, paraffin),
    ("Iron main collimator", collimator_iron_region, iron),
    ("Main heavy-concrete shield", collimator_heavy_region, heavy_concrete),
    ("Upstream heavy-concrete shield", upstream_heavy_region, heavy_concrete),
    ("Ordinary-concrete shield", ordinary_shield_region, ordinary_concrete),
    ("Downstream iron collimator", downstream_iron_region, iron),
    ("Paraffin detector housing", paraffin_housing_region, paraffin),
    ("Concrete detector housing", concrete_housing_region, heavy_concrete),
    ("Gamma-collimator lead", nai_lead_region, lead),
    (
        "Gamma-collimator stainless steel",
        nai_stainless_steel_region,
        stainless_steel_316,
    ),
    ("Gamma-collimator concrete", nai_concrete_region, ordinary_concrete),
    ("NaI gamma detector", nai_detector_region, nai),
    ("NE-218 detector", detector_region, ne218),
]
cells = [
    mcdc.Cell(name=name, region=region, fill=fill)
    for name, region, fill in regions_and_fills
]
nai_detector_cell = cells[-2]

problem_boundary = mcdc.Surface.Sphere(
    name="Problem boundary", radius=2000.0, boundary_condition="vacuum"
)
occupied_region = union([region for _, region, _ in regions_and_fills])
cells.append(
    mcdc.Cell(
        name="Atmosphere and central cavity",
        region=-problem_boundary & ~occupied_region,
        fill=air,
    )
)
simulation.set_model(cells)

# ======================================================================================
# Set source
# ======================================================================================

# Sample the piecewise-linear angular density and obtain the neutron
# energy by interpolation over the same direction-cosine interval.  This
# preserves its deterministic energy-angle correlation.  It intentionally does
# not reproduce the detailed gamma-analysis model's deuteron-transport source.
# The equal-area square source footprint preserves the supplied disk area; its
# finite y interval spans the complete 0.0011 cm modeled Ti-T target thickness.
source = mcdc.Source(
    name="D-T neutron source",
    x=[-SOURCE_BLOCK_HALF_WIDTH_CM, SOURCE_BLOCK_HALF_WIDTH_CM],
    y=[0.0, SOURCE_BLOCK_THICKNESS_CM],
    z=[-SOURCE_BLOCK_HALF_WIDTH_CM, SOURCE_BLOCK_HALF_WIDTH_CM],
    direction=[0.0, 1.0, 0.0],
    polar_cosine=(D_T_DIRECTION_COSINES, D_T_RELATIVE_YIELDS),
    azimuthal=[0.0, 2.0 * np.pi],
    energy_at_polar_cosine=D_T_ENERGIES_MEV * 1.0e6,
)
simulation.set_sources([source])

# ======================================================================================
# Set tallies, settings, and run MC/DC
# ======================================================================================

# The benchmark observable is the neutron-induced photon spectrum in the NaI
# detector.  MC/DC does not yet support coupled neutron-photon production and
# photon transport, so defining a neutron tally here would not represent the
# measured quantity.  Keep the complete experiment-specific geometry and
# neutron source above ready for the photon-transport implementation, but stop
# explicitly instead of producing a misleading validation result.
raise NotImplementedError(
    "The OKTAVIAN gamma-leakage case requires neutron-induced photon "
    "production, photon transport, and a photon tally, which MC/DC does not "
    "yet provide."
)
