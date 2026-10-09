"""Geometry and source model for the SINBAD RFNC compound photon experiment.

The benchmark observable is a photon spectrum. MC/DC does not yet transport
neutron-induced photons, so this input stops before defining a tally or running.
"""

import sys

import numpy as np

import mcdc

# ======================================================================================
# Run selection and benchmark data
# ======================================================================================

sample_name = sys.argv[1] if len(sys.argv) == 2 else None
sample_names = {
    "h2o-sphere",
    "sio2-sphere",
    "sio2-back-hemisphere",
    "nacl-sphere",
    "nacl-back-hemisphere",
}
if sample_name not in sample_names:
    raise SystemExit(
        "Usage: python input.py {h2o-sphere|sio2-sphere|"
        "sio2-back-hemisphere|nacl-sphere|nacl-back-hemisphere}"
    )

AVOGADRO_BARN_CM = 0.602214076
SHELL_VOLUME_CM3 = 4.0 / 3.0 * np.pi * (10.0**3 - 5.0**3)
sample_density = {
    "h2o": 3600.0 / SHELL_VOLUME_CM3,
    "sio2": 5340.0 / SHELL_VOLUME_CM3,
    "nacl": 5130.0 / SHELL_VOLUME_CM3,
}


def molecular_number_density(mass_density, molar_mass):
    """Return molecules/(barn cm) from density and molar mass."""
    return AVOGADRO_BARN_CM * mass_density / molar_mass


# ======================================================================================
# Materials
# ======================================================================================

simulation = mcdc.Simulation(f"SINBAD RFNC {sample_name}")

h2o_molecules = molecular_number_density(sample_density["h2o"], 18.0153)
h2o = mcdc.Material(
    name="H2O sample",
    element_composition={"H": 2.0 * h2o_molecules, "O": h2o_molecules},
    temperature=293.6,
)
sio2_molecules = molecular_number_density(sample_density["sio2"], 60.0843)
sio2 = mcdc.Material(
    name="SiO2 sample",
    element_composition={"Si": sio2_molecules, "O": 2.0 * sio2_molecules},
    temperature=293.6,
)
nacl_molecules = molecular_number_density(sample_density["nacl"], 58.4428)
nacl = mcdc.Material(
    name="NaCl sample",
    element_composition={"Na": nacl_molecules, "Cl": nacl_molecules},
    temperature=293.6,
)
sample_material = {"h2o": h2o, "sio2": sio2, "nacl": nacl}[sample_name.split("-")[0]]

copper = mcdc.Material(
    name="Copper target and container",
    element_composition={"Cu": molecular_number_density(8.94, 63.546)},
    temperature=293.6,
)
water = mcdc.Material(
    name="Target cooling water",
    element_composition={
        "H": 2.0 * molecular_number_density(1.0, 18.0153),
        "O": molecular_number_density(1.0, 18.0153),
    },
    temperature=293.6,
)
steel = mcdc.Material(
    name="Steel target shell and delay rod",
    element_composition={"Fe": molecular_number_density(7.8, 55.845)},
    temperature=293.6,
)
stilbene_molecules = molecular_number_density(1.16, 180.25)
stilbene = mcdc.Material(
    name="Stilbene detector",
    element_composition={
        "C": 14.0 * stilbene_molecules,
        "H": 12.0 * stilbene_molecules,
    },
    temperature=293.6,
)

# ======================================================================================
# Geometry
# ======================================================================================

container_inner_inside = mcdc.Surface.Sphere(radius=4.96)
sample_inner = mcdc.Surface.Sphere(radius=5.0)
sample_outer = mcdc.Surface.Sphere(radius=10.0)
container_outer = mcdc.Surface.Sphere(radius=10.04)
back_hemisphere_plane = mcdc.Surface.PlaneZ(z=0.0)
world = mcdc.Surface.Sphere(radius=860.0, boundary_condition="vacuum")

sample_region = +sample_inner & -sample_outer
if sample_name.endswith("back-hemisphere"):
    # The back hemisphere is the half away from the +z detector direction.
    sample_region = sample_region & -back_hemisphere_plane

inner_container_region = +container_inner_inside & -sample_inner
outer_container_region = +sample_outer & -container_outer

# Principal layers of the target unit along the detector (+z) axis.
source_plane = mcdc.Surface.PlaneZ(z=0.001)
copper_back = mcdc.Surface.PlaneZ(z=0.30)
water_back = mcdc.Surface.PlaneZ(z=0.45)
steel_back = mcdc.Surface.PlaneZ(z=0.50)
copper_radius = mcdc.Surface.CylinderZ(radius=1.20)
water_radius = mcdc.Surface.CylinderZ(radius=1.35)
steel_radius = mcdc.Surface.CylinderZ(radius=1.40)
target_copper_region = +source_plane & -copper_back & -copper_radius
target_water_region = +copper_back & -water_back & -water_radius
target_steel_region = +water_back & -steel_back & -steel_radius

rod_front = mcdc.Surface.PlaneZ(z=15.0)
rod_back = mcdc.Surface.PlaneZ(z=55.0)
rod_radius = mcdc.Surface.CylinderZ(radius=1.5)
rod_region = +rod_front & -rod_back & -rod_radius

detector_front = mcdc.Surface.PlaneZ(z=847.0)
detector_back = mcdc.Surface.PlaneZ(z=853.0)
detector_radius = mcdc.Surface.CylinderZ(radius=3.0)
detector_region = +detector_front & -detector_back & -detector_radius

material_region = (
    sample_region
    | inner_container_region
    | outer_container_region
    | target_copper_region
    | target_water_region
    | target_steel_region
    | rod_region
    | detector_region
)

sample_cell = mcdc.Cell(
    name="Compound sample", region=sample_region, fill=sample_material
)
detector_cell = mcdc.Cell(
    name="Stilbene detector", region=detector_region, fill=stilbene
)
simulation.set_model(
    [
        mcdc.Cell(
            name="Inner copper container", region=inner_container_region, fill=copper
        ),
        sample_cell,
        mcdc.Cell(
            name="Outer copper container", region=outer_container_region, fill=copper
        ),
        mcdc.Cell(
            name="Copper target backing", region=target_copper_region, fill=copper
        ),
        mcdc.Cell(name="Target cooling water", region=target_water_region, fill=water),
        mcdc.Cell(name="Target steel shell", region=target_steel_region, fill=steel),
        mcdc.Cell(name="Steel neutron-delay rod", region=rod_region, fill=steel),
        detector_cell,
        mcdc.Cell(name="Experimental air and void", region=-world & ~material_region),
    ]
)

# ======================================================================================
# Prescribed computational source
# ======================================================================================

simulation.set_sources(
    [
        mcdc.Source(
            name="Prescribed 14 MeV source",
            position=[0.0, 0.0, 0.0],
            isotropic=True,
            energy=14.0e6,
        )
    ]
)

# The benchmark observable is the neutron-induced photon spectrum at the
# remote stilbene detector. Defining a neutron-only diagnostic here would not
# represent that measured quantity, so stop explicitly until the required
# coupled physics and photon tally are available.
raise NotImplementedError(
    "The RFNC photon-spectrum case requires neutron-induced photon production, "
    "photon transport, and a photon tally, which MC/DC does not yet provide."
)
