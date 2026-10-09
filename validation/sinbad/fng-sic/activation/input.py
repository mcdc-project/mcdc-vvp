"""Detector-explicit model of the SINBAD FNG SiC activation experiment."""

import numpy as np

import mcdc

# ======================================================================================
# Benchmark data
# ======================================================================================

detector_depths_cm = [10.41, 25.65, 40.89, 56.13]

AVOGADRO_BARN_CM = 0.602214076

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


def atomic_density(mass_density, mass_fraction, atomic_weight):
    """Convert a mass fraction and density to atoms/(barn cm)."""
    return AVOGADRO_BARN_CM * mass_density * mass_fraction / atomic_weight


# ======================================================================================
# Materials
# ======================================================================================

simulation = mcdc.Simulation("SINBAD FNG SiC activation experiment")

# The supplied MCNP mass fractions do not sum exactly to one; MCNP normalizes
# them internally, so the explicit number densities below do the same.
sic_mass_fractions = {
    "C12": 0.3047 * 0.9893,
    "C13": 0.3047 * 0.0107,
    "Si28": 0.627994,
    "Si29": 0.031798,
    "Si30": 0.0211079,
    "B10": 0.0003762,
    "B11": 0.0015238,
    "Al27": 0.00079,
    "Fe56": 0.00014,
}
sic_atomic_weights = {
    "C12": 12.0,
    "C13": 13.0034,
    "Si28": 27.9769,
    "Si29": 28.9765,
    "Si30": 29.9738,
    "B10": 10.0129,
    "B11": 11.0093,
    "Al27": 26.9815,
    "Fe56": 55.9349,
}
normalization = sum(sic_mass_fractions.values())
sic = mcdc.Material(
    name="SiC assembly",
    nuclide_composition={
        nuclide: atomic_density(
            3.158, fraction / normalization, sic_atomic_weights[nuclide]
        )
        for nuclide, fraction in sic_mass_fractions.items()
    },
    temperature=293.6,
)
aluminum = mcdc.Material(
    name="Aluminum activation holder",
    nuclide_composition={"Al27": atomic_density(2.70, 1.0, 26.9815)},
    temperature=293.6,
)
copper = mcdc.Material(
    name="Copper target backing",
    nuclide_composition={
        "Cu63": atomic_density(8.94, 0.69, 62.9296),
        "Cu65": atomic_density(8.94, 0.31, 64.9278),
    },
    temperature=293.6,
)
water = mcdc.Material(
    name="Target cooling water",
    element_composition={
        "H": atomic_density(1.0, 0.1119, 1.008),
        "O": atomic_density(1.0, 0.8881, 15.999),
    },
    temperature=293.6,
)
steel = mcdc.Material(
    name="Target stainless steel",
    element_composition={
        "Fe": atomic_density(7.954, 0.695, 55.845),
        "Cr": atomic_density(7.954, 0.152, 51.996),
        "Ni": atomic_density(7.954, 0.107, 58.693),
        "Mo": atomic_density(7.954, 0.0212, 95.95),
        "C": atomic_density(7.954, 0.0004, 12.011),
    },
    temperature=293.6,
)

# ======================================================================================
# Geometry
# ======================================================================================

x_min = mcdc.Surface.PlaneX(x=-22.86, boundary_condition="vacuum")
x_max = mcdc.Surface.PlaneX(x=22.86, boundary_condition="vacuum")
y_world_min = mcdc.Surface.PlaneY(y=-10.0, boundary_condition="vacuum")
y_front = mcdc.Surface.PlaneY(y=5.3)
y_back = mcdc.Surface.PlaneY(y=76.42, boundary_condition="vacuum")
z_min = mcdc.Surface.PlaneZ(z=-22.86, boundary_condition="vacuum")
z_max = mcdc.Surface.PlaneZ(z=22.86, boundary_condition="vacuum")

world_region = +x_min & -x_max & +y_world_min & -y_back & +z_min & -z_max
block_region = +x_min & -x_max & +y_front & -y_back & +z_min & -z_max

# Principal target layers immediately downstream of the Ti-T source plane.
target_copper_back = mcdc.Surface.PlaneY(y=0.10)
target_water_back = mcdc.Surface.PlaneY(y=0.20)
target_steel_back = mcdc.Surface.PlaneY(y=0.35)
source_plane = mcdc.Surface.PlaneY(y=0.001)
copper_radius = mcdc.Surface.CylinderY(radius=1.5)
water_radius = mcdc.Surface.CylinderY(radius=1.7)
steel_radius = mcdc.Surface.CylinderY(radius=1.8)
copper_region = +source_plane & -target_copper_back & -copper_radius
water_region = +target_copper_back & -target_water_back & -water_radius
steel_region = +target_water_back & -target_steel_back & -steel_radius
target_region = copper_region | water_region | steel_region

detector_regions = []
detector_cells = []
for index, depth in enumerate(detector_depths_cm):
    thickness = 0.10 if index < 2 else 0.20
    center = 5.3 + depth
    front = mcdc.Surface.PlaneY(y=center - 0.5 * thickness)
    back = mcdc.Surface.PlaneY(y=center + 0.5 * thickness)
    radius = mcdc.Surface.CylinderY(radius=0.9)
    region = +front & -back & -radius
    detector_regions.append(region)
    detector_cells.append(
        mcdc.Cell(
            name=f"Activation foil P{index + 1}",
            region=region,
            fill=aluminum,
        )
    )

all_detectors = detector_regions[0]
for region in detector_regions[1:]:
    all_detectors = all_detectors | region

cells = [
    mcdc.Cell(
        name="Source-side air", region=world_region & ~block_region & ~target_region
    ),
    mcdc.Cell(name="Copper target backing", region=copper_region, fill=copper),
    mcdc.Cell(name="Target cooling water", region=water_region, fill=water),
    mcdc.Cell(name="Target steel shell", region=steel_region, fill=steel),
    mcdc.Cell(name="SiC block", region=block_region & ~all_detectors, fill=sic),
    *detector_cells,
]
simulation.set_model(cells)

# ======================================================================================
# Correlated finite D-T source
# ======================================================================================

source_mu_edges = np.empty(SOURCE_MU.size + 1)
source_mu_edges[0] = -1.0
source_mu_edges[-1] = 1.0
source_mu_edges[1:-1] = 0.5 * (SOURCE_MU[:-1] + SOURCE_MU[1:])
source_half_width = 0.5 * np.sqrt(np.pi) * 0.7

sources = []
for index in range(SOURCE_MU.size):
    energy_mev = np.linspace(
        SOURCE_ENERGY_MIN_MEV[index], SOURCE_ENERGY_MAX_MEV[index], 44
    )
    energy_pdf = np.exp(
        -0.5
        * ((energy_mev - SOURCE_ENERGY_MEAN_MEV[index]) / SOURCE_ENERGY_SDEV_MEV[index])
        ** 2
    )
    mu_lower = source_mu_edges[index]
    mu_upper = source_mu_edges[index + 1]
    sources.append(
        mcdc.Source(
            name=f"D-T angular interval {index + 1}",
            x=[-source_half_width, source_half_width],
            y=[0.0, 0.001],
            z=[-source_half_width, source_half_width],
            direction=[0.0, 1.0, 0.0],
            polar_cosine=[mu_lower, mu_upper],
            azimuthal=[0.0, 2.0 * np.pi],
            energy=np.array([energy_mev * 1.0e6, energy_pdf / 1.0e6]),
            probability=SOURCE_RELATIVE_YIELD[index] * (mu_upper - mu_lower),
        )
    )
simulation.set_sources(sources)

# ======================================================================================
# Tallies, settings, and run
# ======================================================================================

energy = np.geomspace(1.0e-5, 20.0e6, 301)
tallies = []
for index, detector_cell in enumerate(detector_cells):
    tallies.append(
        mcdc.Tally(
            name=f"detector_flux_p{index + 1}",
            cell=detector_cell,
            particle_type="neutron",
            energy=energy,
            scores=["flux"],
        )
    )
simulation.set_tallies(tallies)

simulation.settings.N_particle = 1_000_000
simulation.settings.N_batch = 30
simulation.settings.output_name = "output"

simulation.run()
