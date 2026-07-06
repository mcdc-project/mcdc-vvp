import openmc
import numpy as np
import h5py, sys

# ===========================================================================
# Set Library
# ===========================================================================

SigmaC = 1.0 / 3.0
SigmaF = 1.0 / 3.0
nu = 2.3
SigmaA = SigmaC + SigmaF
SigmaS = 1.0 / 3.0
SigmaT = SigmaA + SigmaS
v = 1.0

m1_SigmaT = 50.0
m2_SigmaT = 5.0
m3_SigmaT = 0.0
m4_SigmaT = 1.0

m1_SigmaA = 50.0
m2_SigmaA = 5.0
m3_SigmaA = 0.0
m4_SigmaA = 0.1

m1_SigmaS = m1_SigmaT - m1_SigmaA
m2_SigmaS = m2_SigmaT - m2_SigmaA
m3_SigmaS = m3_SigmaT - m3_SigmaA
m4_SigmaS = m4_SigmaT - m4_SigmaA

groups = openmc.mgxs.EnergyGroups([0.0, 2e7])

m1 = openmc.XSdata("m1", groups)
m2 = openmc.XSdata("m2", groups)
m3 = openmc.XSdata("m3", groups)
m4 = openmc.XSdata("m4", groups)

m1.order = 0
m2.order = 0
m3.order = 0
m4.order = 0

m1.set_total([m1_SigmaT], temperature=294.0)
m2.set_total([m2_SigmaT], temperature=294.0)
m3.set_total([m3_SigmaT], temperature=294.0)
m4.set_total([m4_SigmaT], temperature=294.0)

m1.set_absorption([m1_SigmaA], temperature=294.0)
m2.set_absorption([m2_SigmaA], temperature=294.0)
m3.set_absorption([m3_SigmaA], temperature=294.0)
m4.set_absorption([m4_SigmaA], temperature=294.0)

m1.set_scatter_matrix(np.ones((1, 1, 1)) * m1_SigmaS, temperature=294.0)
m2.set_scatter_matrix(np.ones((1, 1, 1)) * m2_SigmaS, temperature=294.0)
m3.set_scatter_matrix(np.ones((1, 1, 1)) * m3_SigmaS, temperature=294.0)
m4.set_scatter_matrix(np.ones((1, 1, 1)) * m4_SigmaS, temperature=294.0)

mg_cross_sections_file = openmc.MGXSLibrary(groups)
mg_cross_sections_file.add_xsdata(m1)
mg_cross_sections_file.add_xsdata(m2)
mg_cross_sections_file.add_xsdata(m3)
mg_cross_sections_file.add_xsdata(m4)
mg_cross_sections_file.export_to_hdf5("mgxs.h5")

# ===========================================================================
# Exporting to OpenMC materials.xml file
# ===========================================================================

materials = {}
materials["m1"] = openmc.Material(name="m1")
materials["m1"].set_density("macro", 1.0)
materials["m1"].add_macroscopic("m1")

materials["m2"] = openmc.Material(name="m2")
materials["m2"].set_density("macro", 1.0)
materials["m2"].add_macroscopic("m2")

materials["m3"] = openmc.Material(name="m3")
materials["m3"].set_density("macro", 1.0)
materials["m3"].add_macroscopic("m3")

materials["m4"] = openmc.Material(name="m4")
materials["m4"].set_density("macro", 1.0)
materials["m4"].add_macroscopic("m4")

materials_file = openmc.Materials(materials.values())
materials_file.cross_sections = "mgxs.h5"
materials_file.export_to_xml()

# ===========================================================================
# Exporting to OpenMC geometry.xml file
# ===========================================================================

# Instantiate ZCylinder surfaces
s1 = openmc.XPlane(x0=0.0, boundary_type="reflective")
s2 = openmc.XPlane(x0=2.0)
s3 = openmc.XPlane(x0=3.0)
s4 = openmc.XPlane(x0=5.0)
s5 = openmc.XPlane(x0=8.0, boundary_type="vacuum")

# Instantiate Cells
c1 = openmc.Cell()
c2 = openmc.Cell()
c3 = openmc.Cell()
c4 = openmc.Cell()
# Use surface half-spaces to define regions
c1.region = +s1 & -s2
c2.region = +s2 & -s3
c3.region = +s3 & -s4
c4.region = +s4 & -s5
# Register Materials with Cells
c1.fill = materials["m1"]
c2.fill = materials["m2"]
c3.fill = materials["m3"]
c4.fill = materials["m4"]

# Instantiate Universes
root = openmc.Universe(universe_id=0, name="root universe", cells=[c1, c2, c3, c4])

# Instantiate a Geometry, register the root Universe, and export to XML
geometry = openmc.Geometry(root)
geometry.export_to_xml()

# ===========================================================================
# Exporting to OpenMC settings.xml file
# ===========================================================================

# Instantiate a Settings object, set all runtime parameters, and export to XML
settings_file = openmc.Settings()
settings_file.run_mode = "fixed source"
settings_file.particles = 1000000000
settings_file.batches = 30
settings_file.output = {"tallies": False}
settings_file.energy_mode = "multi-group"

# Define source
src1 = openmc.IndependentSource()
src2 = openmc.IndependentSource()
#
src1.space = openmc.stats.CartesianIndependent(
    x=openmc.stats.Uniform(0.0, 2.0),
    y=openmc.stats.Discrete([0.0], [1.0]),
    z=openmc.stats.Discrete([0.0], [1.0]),
)
src2.space = openmc.stats.CartesianIndependent(
    x=openmc.stats.Uniform(5.0, 6.0),
    y=openmc.stats.Discrete([0.0], [1.0]),
    z=openmc.stats.Discrete([0.0], [1.0]),
)
#
src1.angle = openmc.stats.Isotropic()
src2.angle = openmc.stats.Isotropic()
#
src1.strength = 50.0 / 50.5
src2.strength = 0.5 / 50.5

settings_file.source = [src1, src2]
settings_file.export_to_xml()


# ===========================================================================
# Exporting to OpenMC tallies.xml file
# ===========================================================================

# Create a mesh filter that can be used in a tally
mesh = openmc.RectilinearMesh()
mesh.x_grid = np.linspace(0.0, 8.0, 81)
mesh.y_grid = np.linspace(-1e15, 1e15, 2)
mesh.z_grid = np.linspace(-1e15, 1e15, 2)
mesh_filter = openmc.MeshFilter(mesh)

# Now use the mesh filter in a tally and indicate what scores are desired
tally1 = openmc.Tally(name="flux")
tally1.estimator = "tracklength"
tally1.filters = [mesh_filter]
tally1.scores = ["flux"]

# Instantiate a Tallies collection and export to XML
tallies = openmc.Tallies([tally1])
tallies.export_to_xml()
