import h5py
import matplotlib.pyplot as plt

import numpy as np

import openmc, sys


###############################################################################
# Create multigroup data

# Library data
groups = openmc.mgxs.EnergyGroups(
    group_edges=[1e-5, 0.0635, 10.0, 1.0e2, 1.0e3, 0.5e6, 1.0e6, 20.0e6]
)

# Library data
lib = h5py.File("MGXS-C5G7.h5", "r")


# The setter helper
def set_xs_data(name, mat):
    SigmaC = mat["capture"][:]
    SigmaS = mat["scatter"][:]
    SigmaF = mat["fission"][:]
    nu_p = mat["nu_p"][:]
    nu_d = mat["nu_d"][:]
    chi_p = mat["chi_p"][:]
    chi_d = mat["chi_d"][:]
    speed = mat["speed"][:]
    decay = mat["decay"][:]

    xsdata = openmc.XSdata(name, groups, num_delayed_groups=8)
    xsdata.order = 0

    xsdata.set_inverse_velocity(1.0 / speed)
    xsdata.set_decay_rate(decay)

    SigmaS = SigmaS.transpose()
    SigmaA = SigmaC + SigmaF
    SigmaS_total = np.sum(SigmaS, 1)
    SigmaT = SigmaA + SigmaS_total
    chi_p = chi_p[:, 0]
    chi_d = chi_d.transpose()

    xsdata.set_total(SigmaT)
    xsdata.set_absorption(SigmaA)
    xsdata.set_fission(SigmaF)
    xsdata.set_scatter_matrix(np.expand_dims(SigmaS, 2))

    xsdata.set_prompt_nu_fission(nu_p * SigmaF)
    xsdata.set_delayed_nu_fission(nu_d * SigmaF)
    xsdata.set_chi_prompt(chi_p)
    xsdata.set_chi_delayed(chi_d)

    return xsdata


# Set up the XS data
mg_cross_sections_file = openmc.MGXSLibrary(groups, 8)
mg_cross_sections_file.add_xsdatas(
    [
        set_xs_data("UO2", lib["uo2"]),
        set_xs_data("MOX43", lib["mox43"]),
        set_xs_data("MOX7", lib["mox7"]),
        set_xs_data("MOX87", lib["mox87"]),
        set_xs_data("Guide Tube", lib["gt"]),
        set_xs_data("Fission Chamber", lib["fc"]),
        set_xs_data("Control Rod", lib["cr"]),
        set_xs_data("Moderator", lib["mod"]),
    ]
)
mg_cross_sections_file.export_to_hdf5()

###############################################################################
# Create materials for the problem

# Fuel: UO2
mat_uo2 = openmc.Material(name="UO2")
mat_uo2.set_density("macro", 1.0)
mat_uo2.add_macroscopic(openmc.Macroscopic("UO2"))

# Fuel: MOX 4.3%
mat_mox43 = openmc.Material(name="MOX43")
mat_mox43.set_density("macro", 1.0)
mat_mox43.add_macroscopic(openmc.Macroscopic("MOX43"))

# Fuel: MOX 7%
mat_mox7 = openmc.Material(name="MOX7")
mat_mox7.set_density("macro", 1.0)
mat_mox7.add_macroscopic(openmc.Macroscopic("MOX7"))

# Fuel: MOX 8.7%
mat_mox87 = openmc.Material(name="MOX87")
mat_mox87.set_density("macro", 1.0)
mat_mox87.add_macroscopic(openmc.Macroscopic("MOX87"))

# Guide tube
mat_gt = openmc.Material(name="Guide Tube")
mat_gt.set_density("macro", 1.0)
mat_gt.add_macroscopic(openmc.Macroscopic("Guide Tube"))

# Fission chamber
mat_fc = openmc.Material(name="Fission Chamber")
mat_fc.set_density("macro", 1.0)
mat_fc.add_macroscopic(openmc.Macroscopic("Fission Chamber"))

# Control rod
mat_cr = openmc.Material(name="Control Rod")
mat_cr.set_density("macro", 1.0)
mat_cr.add_macroscopic(openmc.Macroscopic("Control Rod"))

# Moderator
mat_mod = openmc.Material(name="Moderator")
mat_mod.set_density("macro", 1.0)
mat_mod.add_macroscopic(openmc.Macroscopic("Moderator"))

# Instantiate a Materials collection and export to XML
materials_file = openmc.Materials(
    [mat_uo2, mat_mox43, mat_mox7, mat_mox87, mat_gt, mat_fc, mat_cr, mat_mod]
)
materials_file.cross_sections = "mgxs.h5"
materials_file.export_to_xml()

colors = {
    mat_uo2: "red",
    mat_mox43: "orange",
    mat_mox7: "brown",
    mat_mox87: "yellow",
    mat_gt: "gray",
    mat_fc: "silver",
    mat_cr: "green",
    mat_mod: "blue",
}

###############################################################################
# Problem specifications

# Reactor geometry sizes
pitch = 1.26
radius = 0.54
core_height = 128.52
reflector_thickness = 21.42

# Control rod banks fractions
#   All out: 0.0
#   All in : 1.0
cr1 = np.array([1.0, 1.0, 0.89, 1.0])
cr1_t = np.array([0.0, 10.0, 15.0, 15.0 + 1.0 - cr1[-2]])

cr2 = np.array([1.0, 1.0, 0.0, 0.0, 0.8])
cr2_t = np.array([0.0, 5.0, 10.0, 15.0, 15.8])

cr3 = np.array([0.75, 0.75, 1.0])
cr3_t = np.array([0.0, 15.0, 15.25])

cr4 = np.array([1.0, 1.0, 0.5, 0.5, 1.0])
cr4_t = np.array(
    [0.0, 5.0, 5.0 + (cr4[1] - cr4[2]) / 2 * 10, 15.0, 15.0 + 1.0 - cr4[-2]]
)

# Tips of the control rod banks
cr1_bottom = core_height * (0.5 - cr1)
cr2_bottom = core_height * (0.5 - cr2)
cr3_bottom = core_height * (0.5 - cr3)
cr4_bottom = core_height * (0.5 - cr4)
cr1_top = cr1_bottom + core_height
cr2_top = cr2_bottom + core_height
cr3_top = cr3_bottom + core_height
cr4_top = cr4_bottom + core_height

# Durations of the moving tips
cr1_durations = cr1_t[1:] - cr1_t[:-1]
cr2_durations = cr2_t[1:] - cr2_t[:-1]
cr3_durations = cr3_t[1:] - cr3_t[:-1]
cr4_durations = cr4_t[1:] - cr4_t[:-1]

# Velocities of the moving tips
cr1_velocities = np.zeros((len(cr1) - 1, 3))
cr2_velocities = np.zeros((len(cr2) - 1, 3))
cr3_velocities = np.zeros((len(cr3) - 1, 3))
cr4_velocities = np.zeros((len(cr4) - 1, 3))
cr1_velocities[:, 2] = (cr1_top[1:] - cr1_top[:-1]) / cr1_durations
cr2_velocities[:, 2] = (cr2_top[1:] - cr2_top[:-1]) / cr2_durations
cr3_velocities[:, 2] = (cr3_top[1:] - cr3_top[:-1]) / cr3_durations
cr4_velocities[:, 2] = (cr4_top[1:] - cr4_top[:-1]) / cr4_durations

###############################################################################
# Pin cells

# Surfaces
cy = openmc.ZCylinder(x0=0.0, y0=0.0, r=radius)
# Control rod top and bottom tips
z1_top = openmc.ZPlane(z0=cr1_top[0], surface_id=9911)
z1_bottom = openmc.ZPlane(z0=cr1_bottom[0], surface_id=9910)
z2_top = openmc.ZPlane(z0=cr2_top[0], surface_id=9921)
z2_bottom = openmc.ZPlane(z0=cr2_bottom[0], surface_id=9920)
z3_top = openmc.ZPlane(z0=cr3_top[0], surface_id=9931)
z3_bottom = openmc.ZPlane(z0=cr3_bottom[0], surface_id=9930)
z4_top = openmc.ZPlane(z0=cr4_top[0], surface_id=9941)
z4_bottom = openmc.ZPlane(z0=cr4_bottom[0], surface_id=9940)
# Fuel top
#   (Bottom is bounded by the universe cell)
zf = openmc.ZPlane(z0=0.5 * core_height)

# Move the control rods' tips
z1_top.move(cr1_velocities, cr1_durations)
z1_bottom.move(cr1_velocities, cr1_durations)
z2_top.move(cr2_velocities, cr2_durations)
z2_bottom.move(cr2_velocities, cr2_durations)
z3_top.move(cr3_velocities, cr3_durations)
z3_bottom.move(cr3_velocities, cr3_durations)
z4_top.move(cr4_velocities, cr4_durations)
z4_bottom.move(cr4_velocities, cr4_durations)

# Fission chamber pin
fc = openmc.Cell(region=-cy, fill=mat_fc)
mod_fc = openmc.Cell(region=+cy, fill=mat_mod)
fission_chamber = openmc.Universe(cells=[fc, mod_fc])

# Fuel rods
uo2 = openmc.Cell(region=-cy & -zf, fill=mat_uo2)
mox4 = openmc.Cell(region=-cy & -zf, fill=mat_mox43)
mox7 = openmc.Cell(region=-cy & -zf, fill=mat_mox7)
mox8 = openmc.Cell(region=-cy & -zf, fill=mat_mox87)
mod_uo2 = openmc.Cell(region=+cy, fill=mat_mod)
mod_mox4 = openmc.Cell(region=+cy, fill=mat_mod)
mod_mox7 = openmc.Cell(region=+cy, fill=mat_mod)
mod_mox8 = openmc.Cell(region=+cy, fill=mat_mod)
moda_uo2 = openmc.Cell(region=-cy & +zf, fill=mat_mod)  # Water above pin
moda_mox4 = openmc.Cell(region=-cy & +zf, fill=mat_mod)  # Water above pin
moda_mox7 = openmc.Cell(region=-cy & +zf, fill=mat_mod)  # Water above pin
moda_mox8 = openmc.Cell(region=-cy & +zf, fill=mat_mod)  # Water above pin
fuel_uo2 = openmc.Universe(cells=[uo2, mod_uo2, moda_uo2])
fuel_mox43 = openmc.Universe(cells=[mox4, mod_mox4, moda_mox4])
fuel_mox7 = openmc.Universe(cells=[mox7, mod_mox7, moda_mox7])
fuel_mox87 = openmc.Universe(cells=[mox8, mod_mox8, moda_mox8])

# Control rods and guide tubes
cr1 = openmc.Cell(region=-cy & +z1_bottom & -z1_top, fill=mat_cr)
gt1_lower = openmc.Cell(region=-cy & -z1_bottom, fill=mat_gt)
gt1_upper = openmc.Cell(region=-cy & +z1_top, fill=mat_gt)
#
cr2 = openmc.Cell(region=-cy & +z2_bottom & -z2_top, fill=mat_cr)
gt2_lower = openmc.Cell(region=-cy & -z2_bottom, fill=mat_gt)
gt2_upper = openmc.Cell(region=-cy & +z2_top, fill=mat_gt)
#
cr3 = openmc.Cell(region=-cy & +z3_bottom & -z3_top, fill=mat_cr)
gt3_lower = openmc.Cell(region=-cy & -z3_bottom, fill=mat_gt)
gt3_upper = openmc.Cell(region=-cy & +z3_top, fill=mat_gt)
#
cr4 = openmc.Cell(region=-cy & +z4_bottom & -z4_top, fill=mat_cr)
gt4_lower = openmc.Cell(region=-cy & -z4_bottom, fill=mat_gt)
gt4_upper = openmc.Cell(region=-cy & +z4_top, fill=mat_gt)
#
mod_cr1 = openmc.Cell(region=+cy, fill=mat_mod)
mod_cr2 = openmc.Cell(region=+cy, fill=mat_mod)
mod_cr3 = openmc.Cell(region=+cy, fill=mat_mod)
mod_cr4 = openmc.Cell(region=+cy, fill=mat_mod)
#
control_rod1 = openmc.Universe(cells=[cr1, gt1_lower, gt1_upper, mod_cr1])
control_rod2 = openmc.Universe(cells=[cr2, gt2_lower, gt2_upper, mod_cr2])
control_rod3 = openmc.Universe(cells=[cr3, gt3_lower, gt3_upper, mod_cr3])
control_rod4 = openmc.Universe(cells=[cr4, gt4_lower, gt4_upper, mod_cr4])

###############################################################################
# Fuel lattices

# UO2 lattice 1
u = fuel_uo2
c = control_rod1
f = fission_chamber
lattice_1 = openmc.RectLattice()
lattice_1.pitch = (pitch, pitch)
lattice_1.lower_left = (-pitch * 17 / 2, -pitch * 17 / 2)
lattice_1.universes = np.array(
    [
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, u, u, c, u, u, c, u, u, c, u, u, u, u, u],
        [u, u, u, c, u, u, u, u, u, u, u, u, u, c, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, c, u, u, c, u, u, c, u, u, c, u, u, c, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, c, u, u, c, u, u, f, u, u, c, u, u, c, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, c, u, u, c, u, u, c, u, u, c, u, u, c, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, c, u, u, u, u, u, u, u, u, u, c, u, u, u],
        [u, u, u, u, u, c, u, u, c, u, u, c, u, u, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
    ]
)

# MOX lattice 2
l = fuel_mox43
m = fuel_mox7
n = fuel_mox87
c = control_rod2
f = fission_chamber
lattice_2 = openmc.RectLattice()
lattice_2.pitch = (pitch, pitch)
lattice_2.lower_left = (-pitch * 17 / 2, -pitch * 17 / 2)
lattice_2.universes = np.array(
    [
        [l, l, l, l, l, l, l, l, l, l, l, l, l, l, l, l, l],
        [l, m, m, m, m, m, m, m, m, m, m, m, m, m, m, m, l],
        [l, m, m, m, m, c, m, m, c, m, m, c, m, m, m, m, l],
        [l, m, m, c, m, n, n, n, n, n, n, n, m, c, m, m, l],
        [l, m, m, m, n, n, n, n, n, n, n, n, n, m, m, m, l],
        [l, m, c, n, n, c, n, n, c, n, n, c, n, n, c, m, l],
        [l, m, m, n, n, n, n, n, n, n, n, n, n, n, m, m, l],
        [l, m, m, n, n, n, n, n, n, n, n, n, n, n, m, m, l],
        [l, m, c, n, n, c, n, n, f, n, n, c, n, n, c, m, l],
        [l, m, m, n, n, n, n, n, n, n, n, n, n, n, m, m, l],
        [l, m, m, n, n, n, n, n, n, n, n, n, n, n, m, m, l],
        [l, m, c, n, n, c, n, n, c, n, n, c, n, n, c, m, l],
        [l, m, m, m, n, n, n, n, n, n, n, n, n, m, m, m, l],
        [l, m, m, c, m, n, n, n, n, n, n, n, m, c, m, m, l],
        [l, m, m, m, m, c, m, m, c, m, m, c, m, m, m, m, l],
        [l, m, m, m, m, m, m, m, m, m, m, m, m, m, m, m, l],
        [l, l, l, l, l, l, l, l, l, l, l, l, l, l, l, l, l],
    ]
)

# MOX lattice 3
l = fuel_mox43
m = fuel_mox7
n = fuel_mox87
c = control_rod3
f = fission_chamber
lattice_3 = openmc.RectLattice()
lattice_3.pitch = (pitch, pitch)
lattice_3.lower_left = (-pitch * 17 / 2, -pitch * 17 / 2)
lattice_3.universes = np.array(
    [
        [l, l, l, l, l, l, l, l, l, l, l, l, l, l, l, l, l],
        [l, m, m, m, m, m, m, m, m, m, m, m, m, m, m, m, l],
        [l, m, m, m, m, c, m, m, c, m, m, c, m, m, m, m, l],
        [l, m, m, c, m, n, n, n, n, n, n, n, m, c, m, m, l],
        [l, m, m, m, n, n, n, n, n, n, n, n, n, m, m, m, l],
        [l, m, c, n, n, c, n, n, c, n, n, c, n, n, c, m, l],
        [l, m, m, n, n, n, n, n, n, n, n, n, n, n, m, m, l],
        [l, m, m, n, n, n, n, n, n, n, n, n, n, n, m, m, l],
        [l, m, c, n, n, c, n, n, f, n, n, c, n, n, c, m, l],
        [l, m, m, n, n, n, n, n, n, n, n, n, n, n, m, m, l],
        [l, m, m, n, n, n, n, n, n, n, n, n, n, n, m, m, l],
        [l, m, c, n, n, c, n, n, c, n, n, c, n, n, c, m, l],
        [l, m, m, m, n, n, n, n, n, n, n, n, n, m, m, m, l],
        [l, m, m, c, m, n, n, n, n, n, n, n, m, c, m, m, l],
        [l, m, m, m, m, c, m, m, c, m, m, c, m, m, m, m, l],
        [l, m, m, m, m, m, m, m, m, m, m, m, m, m, m, m, l],
        [l, l, l, l, l, l, l, l, l, l, l, l, l, l, l, l, l],
    ]
)

# UO2 lattice 4
u = fuel_uo2
c = control_rod4
f = fission_chamber
lattice_4 = openmc.RectLattice()
lattice_4.pitch = (pitch, pitch)
lattice_4.lower_left = (-pitch * 17 / 2, -pitch * 17 / 2)
lattice_4.universes = np.array(
    [
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, u, u, c, u, u, c, u, u, c, u, u, u, u, u],
        [u, u, u, c, u, u, u, u, u, u, u, u, u, c, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, c, u, u, c, u, u, c, u, u, c, u, u, c, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, c, u, u, c, u, u, f, u, u, c, u, u, c, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, c, u, u, c, u, u, c, u, u, c, u, u, c, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, c, u, u, u, u, u, u, u, u, u, c, u, u, u],
        [u, u, u, u, u, c, u, u, c, u, u, c, u, u, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
        [u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u, u],
    ]
)

###############################################################################
# Assemblies and core

# Surfaces
x0 = openmc.XPlane(x0=0.0, boundary_type="reflective")
x1 = openmc.XPlane(x0=pitch * 17)
x2 = openmc.XPlane(x0=pitch * 17 * 2)
x3 = openmc.XPlane(x0=pitch * 17 * 3, boundary_type="vacuum")

y0 = openmc.YPlane(y0=-pitch * 17 * 3, boundary_type="vacuum")
y1 = openmc.YPlane(y0=-pitch * 17 * 2)
y2 = openmc.YPlane(y0=-pitch * 17)
y3 = openmc.YPlane(y0=0.0, boundary_type="reflective")

z0 = openmc.ZPlane(z0=-(core_height / 2 + reflector_thickness), boundary_type="vacuum")
z1 = openmc.ZPlane(z0=-(core_height / 2))
z2 = openmc.ZPlane(z0=(core_height / 2 + reflector_thickness), boundary_type="vacuum")

# Assembly cells
center = np.array([pitch * 17 / 2, -pitch * 17 / 2, 0.0])
assembly_1 = openmc.Cell(region=+x0 & -x1 & +y2 & -y3 & +z1 & -z2, fill=lattice_1)
assembly_1.translation = center

assembly_2 = openmc.Cell(region=+x1 & -x2 & +y2 & -y3 & +z1 & -z2, fill=lattice_2)
assembly_2.translation = assembly_1.translation + np.array([pitch * 17, 0.0, 0.0])

assembly_3 = openmc.Cell(region=+x0 & -x1 & +y1 & -y2 & +z1 & -z2, fill=lattice_3)
assembly_3.translation = center
assembly_3.translation = assembly_2.translation + np.array(
    [-pitch * 17, -pitch * 17, 0.0]
)

assembly_4 = openmc.Cell(region=+x1 & -x2 & +y1 & -y2 & +z1 & -z2, fill=lattice_4)
assembly_4.translation = assembly_3.translation + np.array([pitch * 17, 0.0, 0.0])

# Bottom reflector cell
reflector_bottom = openmc.Cell(region=+x0 & -x3 & +y0 & -y3 & +z0 & -z1, fill=mat_mod)

# Side reflectors
reflector_south = openmc.Cell(region=+x0 & -x3 & +y0 & -y1 & +z1 & -z2, fill=mat_mod)
reflector_east = openmc.Cell(region=+x2 & -x3 & +y1 & -y3 & +z1 & -z2, fill=mat_mod)

# Root universe
root_universe = openmc.Universe(
    universe_id=0,
    cells=[
        assembly_1,
        assembly_2,
        assembly_3,
        assembly_4,
        reflector_bottom,
        reflector_south,
        reflector_east,
    ],
)

# Create a geometry with the two cells and export to XML
geometry = openmc.Geometry(root_universe)
geometry.export_to_xml()

###############################################################################
# Define problem settings

# Instantiate a Settings object, set all runtime parameters, and export to XML
settings = openmc.Settings()
settings.run_mode = "fixed source"
settings.energy_mode = "multi-group"
settings.batches = 30
settings.particles = int(sys.argv[1])
settings.cutoff = {"time_neutron": 20}

# Create an initial uniform spatial source distribution over fissionable zones
space = openmc.stats.CartesianIndependent(
    x=openmc.stats.Uniform(
        pitch * 17 * 3 / 2 - pitch / 2, pitch * 17 * 3 / 2 + pitch / 2
    ),
    y=openmc.stats.Uniform(
        -pitch * 17 * 3 / 2 - pitch / 2, -pitch * 17 * 3 / 2 + pitch / 2
    ),
    z=openmc.stats.Uniform(-core_height / 2, core_height / 2),
)
energy = openmc.stats.Discrete([1.4e7], [1.0])
time = openmc.stats.Uniform(0.0, 15.0)
settings.source = openmc.IndependentSource(space=space, time=time, energy=energy)
settings.output = {"tallies": False}
settings.export_to_xml()

###############################################################################
# Define tallies

Nt = 200
Nx = 17 * 2
Ny = 17 * 2
Nz = 17 * 6

# Create a mesh that will be used for tallying
mesh = openmc.RectilinearMesh()
mesh.x_grid = np.linspace(0.0, pitch * 17 * 2, Nx + 1)
mesh.y_grid = np.linspace(-pitch * 17 * 2, 0.0, Ny + 1)
mesh.z_grid = np.linspace(-core_height / 2, core_height / 2, Nz + 1)
time = np.linspace(0.0, 20.0, Nt + 1)

# Create a mesh filter that can be used in a tally
time_filter = openmc.TimeFilter(time)
time_mesh_filter = openmc.TimedMeshFilter(mesh, time)

# Now use the mesh filter in a tally and indicate what scores are desired
mesh_tally = openmc.Tally(name="pincell fission")
mesh_tally.filters = [time_mesh_filter]
mesh_tally.estimator = "tracklength"
mesh_tally.scores = ["fission"]

# Instantiate a Tallies collection and export to XML
tallies = openmc.Tallies([mesh_tally])
tallies.export_to_xml()
