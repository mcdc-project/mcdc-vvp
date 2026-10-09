"""Detector-explicit model of the SINBAD FNG/TUD SiC spectral experiment."""

import numpy as np

import mcdc

# ======================================================================================
# Benchmark data
# ======================================================================================

DETECTOR_LABEL = "P3"
DETECTOR_DEPTH_CM = 43.18
SOURCE_ENERGY_POINTS = 72

# The duplicated 6.502 MeV boundary in the migrated experimental table is
# restored to 6.603 MeV from the surrounding regular sequence.
EXPERIMENT_ENERGY_EDGES_MEV = np.array(
    [
        0.999,
        1.036,
        1.107,
        1.178,
        1.249,
        1.322,
        1.394,
        1.468,
        1.543,
        1.618,
        1.693,
        1.769,
        1.845,
        1.922,
        2.000,
        2.079,
        2.158,
        2.236,
        2.317,
        2.397,
        2.478,
        2.559,
        2.641,
        2.724,
        2.807,
        2.890,
        2.974,
        3.059,
        3.144,
        3.229,
        3.315,
        3.402,
        3.489,
        3.576,
        3.664,
        3.752,
        3.841,
        3.930,
        4.020,
        4.109,
        4.200,
        4.292,
        4.383,
        4.475,
        4.566,
        4.659,
        4.753,
        4.846,
        4.941,
        5.035,
        5.130,
        5.225,
        5.321,
        5.417,
        5.513,
        5.611,
        5.708,
        5.806,
        5.904,
        6.003,
        6.101,
        6.201,
        6.301,
        6.401,
        6.502,
        6.603,
        6.704,
        6.806,
        6.907,
        7.011,
        7.114,
        7.216,
        7.320,
        7.425,
        7.529,
        7.633,
        7.739,
        7.845,
        7.951,
        8.056,
        8.164,
        8.271,
        8.378,
        8.486,
        8.595,
        8.704,
        8.813,
        8.921,
        9.031,
        9.142,
        9.252,
        9.363,
        9.474,
        9.585,
        9.698,
        9.809,
        9.922,
        10.04,
        10.15,
        10.26,
        10.38,
        10.49,
        10.61,
        10.72,
        10.84,
        10.95,
        11.07,
        11.18,
        11.30,
        11.42,
        11.54,
        11.65,
        11.77,
        11.89,
        12.01,
        12.13,
        12.25,
        12.37,
        12.49,
        12.61,
        12.73,
        12.85,
        12.97,
        13.10,
        13.22,
        13.34,
        13.46,
        13.59,
        13.71,
        13.84,
        13.96,
        14.08,
        14.21,
        14.34,
        14.46,
        14.59,
        14.71,
        14.84,
        14.97,
        15.10,
        15.22,
    ]
)

# Source data derived from Tables 1 and 2 of the benchmark description. The
# conditional-energy moments and limits retain the source broadening without
# reproducing the package's complete licensed table.
SOURCE_MU = np.array(
    [
        -1.0,
        -0.9848,
        -0.9397,
        -0.8660,
        -0.7660,
        -0.6428,
        -0.5000,
        -0.3420,
        -0.1736,
        0.0,
        0.1736,
        0.3420,
        0.5000,
        0.6428,
        0.7660,
        0.8660,
        0.9397,
        0.9848,
        1.0,
    ]
)
SOURCE_RELATIVE_YIELD = np.array(
    [
        0.94764,
        0.94842,
        0.95073,
        0.95452,
        0.95969,
        0.96609,
        0.97354,
        0.98184,
        0.99075,
        1.0,
        1.00932,
        1.01842,
        1.02701,
        1.03484,
        1.04162,
        1.04715,
        1.05124,
        1.05374,
        1.05459,
    ]
)
SOURCE_ENERGY_MEAN_MEV = np.array(
    [
        13.400467,
        13.410745,
        13.441326,
        13.491435,
        13.559799,
        13.644701,
        13.743911,
        13.854659,
        13.973984,
        14.098240,
        14.223929,
        14.347116,
        14.463896,
        14.570440,
        14.663136,
        14.738881,
        14.794992,
        14.829467,
        14.841075,
    ]
)
SOURCE_ENERGY_SDEV_MEV = np.array(
    [
        0.127568,
        0.125442,
        0.119136,
        0.108800,
        0.094644,
        0.076997,
        0.056262,
        0.033039,
        0.008445,
        0.019234,
        0.045991,
        0.072529,
        0.097857,
        0.121102,
        0.141427,
        0.158088,
        0.170452,
        0.178078,
        0.180652,
    ]
)
SOURCE_ENERGY_MIN_MEV = np.array(
    [
        13.1490,
        13.1635,
        13.2067,
        13.2774,
        13.3740,
        13.4941,
        13.6347,
        13.7918,
        13.9613,
        14.0531,
        14.0985,
        14.1427,
        14.1843,
        14.2220,
        14.2546,
        14.2811,
        14.3007,
        14.3127,
        14.3167,
    ]
)
SOURCE_ENERGY_MAX_MEV = np.array(
    [
        13.7943,
        13.7982,
        13.8098,
        13.8287,
        13.8544,
        13.8862,
        13.9231,
        13.9640,
        14.0078,
        14.1384,
        14.3176,
        14.4936,
        14.6607,
        14.8134,
        14.9464,
        15.0552,
        15.1358,
        15.1854,
        15.2021,
    ]
)

# ======================================================================================
# Materials
# ======================================================================================

simulation = mcdc.Simulation(f"SINBAD FNG/TUD SiC detector {DETECTOR_LABEL}")

# Number densities are those in the supplied MCNP input, in atoms/(barn cm).
sic = mcdc.Material(
    name="SiC assembly",
    nuclide_composition={
        "C12": 4.89e-2,
        "Si28": 4.67e-2,
        "B10": 2.00e-5,
        "B11": 8.03e-5,
        "Fe54": 1.98e-7,
        "Fe56": 3.12e-6,
        "Fe57": 7.49e-8,
        "Fe58": 9.54e-9,
        "Al27": 5.36e-5,
    },
    temperature=293.6,
)
source_air = mcdc.Material(
    name="Source-side air",
    nuclide_composition={
        "N14": 4.614e-5 * 0.788903,
        "O16": 4.614e-5 * 0.211097,
    },
    temperature=293.6,
)
detector_clearance_air = mcdc.Material(
    name="Detector-clearance air",
    nuclide_composition={"N14": 3.969077e-5, "O16": 1.062057e-5},
    temperature=293.6,
)
ne213 = mcdc.Material(
    name="NE213 active scintillator",
    nuclide_composition={"H1": 4.820e-2, "C12": 3.976e-2},
    temperature=293.6,
)
polyethylene = mcdc.Material(
    name="Polyethylene light guide",
    nuclide_composition={"H1": 8.08e-2, "C12": 4.03e-2},
    temperature=293.6,
)

# ======================================================================================
# Geometry
# ======================================================================================

# Coordinate y follows the source and measurement axis.
x_min = mcdc.Surface.PlaneX(x=-22.85, boundary_condition="vacuum")
x_max = mcdc.Surface.PlaneX(x=22.85, boundary_condition="vacuum")
y_world_min = mcdc.Surface.PlaneY(y=-10.0, boundary_condition="vacuum")
y_front = mcdc.Surface.PlaneY(y=5.3)
y_back = mcdc.Surface.PlaneY(y=76.4, boundary_condition="vacuum")
z_min = mcdc.Surface.PlaneZ(z=-22.85, boundary_condition="vacuum")
z_max = mcdc.Surface.PlaneZ(z=22.85, boundary_condition="vacuum")

detector_center_y = 5.3 + DETECTOR_DEPTH_CM
detector_radius = mcdc.Surface.CylinderZ(
    name="NE213 radius", center=[0.0, detector_center_y], radius=1.91
)
clearance_radius = mcdc.Surface.CylinderZ(
    name="Detector insertion clearance",
    center=[0.0, detector_center_y],
    radius=2.5,
)
detector_bottom = mcdc.Surface.PlaneZ(z=-1.91)
detector_top = mcdc.Surface.PlaneZ(z=1.91)

world_region = +x_min & -x_max & +y_world_min & -y_back & +z_min & -z_max
block_region = +x_min & -x_max & +y_front & -y_back & +z_min & -z_max
insertion_region = -clearance_radius & +detector_bottom & -z_max
active_region = -detector_radius & +detector_bottom & -detector_top
light_guide_region = -detector_radius & +detector_top & -z_max
clearance_region = +detector_radius & -clearance_radius & +detector_bottom & -z_max

source_side_air = mcdc.Cell(
    name="Source-side air", region=world_region & ~block_region, fill=source_air
)
sic_block = mcdc.Cell(
    name="SiC block", region=block_region & ~insertion_region, fill=sic
)
detector_cell = mcdc.Cell(name="NE213 active volume", region=active_region, fill=ne213)
light_guide_cell = mcdc.Cell(
    name="Polyethylene light guide", region=light_guide_region, fill=polyethylene
)
clearance_cell = mcdc.Cell(
    name="Detector clearance", region=clearance_region, fill=detector_clearance_air
)
simulation.set_model(
    [source_side_air, sic_block, detector_cell, light_guide_cell, clearance_cell]
)

# ======================================================================================
# Correlated D-T source
# ======================================================================================

# At each of the 19 benchmark polar-cosine nodes, reconstruct a 72-point
# conditional energy PDF from the derived support, mean, and standard deviation.
# MC/DC samples the piecewise-linear angular PDF and uses unit-base interpolation
# between the neighboring conditional energy PDFs.
source_energy_fraction = np.linspace(0.0, 1.0, SOURCE_ENERGY_POINTS)
source_energy_grid_mev = (
    SOURCE_ENERGY_MIN_MEV[:, None]
    + source_energy_fraction * (SOURCE_ENERGY_MAX_MEV - SOURCE_ENERGY_MIN_MEV)[:, None]
)
source_energy_pdf = np.exp(
    -0.5
    * (
        (source_energy_grid_mev - SOURCE_ENERGY_MEAN_MEV[:, None])
        / SOURCE_ENERGY_SDEV_MEV[:, None]
    )
    ** 2
)
source_energy_at_polar_cosine = np.stack(
    [source_energy_grid_mev * 1.0e6, source_energy_pdf / 1.0e6], axis=1
)

source = mcdc.Source(
    name="D-T neutron source",
    position=[0.0, 0.0, 0.0],
    direction=[0.0, 1.0, 0.0],
    polar_cosine=(SOURCE_MU, SOURCE_RELATIVE_YIELD),
    azimuthal=[0.0, 2.0 * np.pi],
    energy_at_polar_cosine=source_energy_at_polar_cosine,
)
simulation.set_sources([source])

# ======================================================================================
# Tally, settings, and run
# ======================================================================================

detector_flux = mcdc.Tally(
    name="neutron_detector_flux_energy",
    cell=detector_cell,
    particle_type="neutron",
    energy=EXPERIMENT_ENERGY_EDGES_MEV * 1.0e6,
    scores=["flux"],
)
simulation.set_tallies([detector_flux])

# Neutrons below the measured range are strongly rouletted rather than
# terminated. A unit-weight neutron survives with probability 1.0e-7 and is
# reweighted by its reciprocal upon survival.
low_energy_survival_probability = 1.0e-7
low_energy_target_weight = 1.0 / low_energy_survival_probability
weight_windows = np.array(
    [
        [
            low_energy_target_weight,
            low_energy_target_weight,
            low_energy_target_weight,
        ],
        [0.5, 1.0, 2.0],
    ]
)
simulation.technique.weight_windows(
    weight_windows,
    energy=np.array([0.0, EXPERIMENT_ENERGY_EDGES_MEV[0] * 1.0e6, np.inf]),
)

simulation.settings.N_particle = 1_000_000
simulation.settings.N_batch = 30
simulation.settings.output_name = "output"

simulation.run()
