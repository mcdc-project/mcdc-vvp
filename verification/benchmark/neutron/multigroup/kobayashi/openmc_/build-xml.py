import numpy as np

import openmc


###############################################################################
# Create materials for the problem

# Instantiate some Macroscopic Data
shield_data = openmc.Macroscopic("Shield")
void_data = openmc.Macroscopic("Void")

# Instantiate some Materials and register the appropriate Macroscopic objects
shield = openmc.Material(name="Shield")
shield.set_density("macro", 1.0)
shield.add_macroscopic(shield_data)

void = openmc.Material(name="Void")
void.set_density("macro", 1.0)
void.add_macroscopic(void_data)

# Instantiate a Materials collection and export to XML
materials_file = openmc.Materials([shield, void])
materials_file.cross_sections = "mgxs.h5"
materials_file.export_to_xml()

###############################################################################
# Define problem geometry

# Create surfaces
sx1 = openmc.XPlane(0.0, boundary_type="reflective")
sx2 = openmc.XPlane(10.0)
sx3 = openmc.XPlane(30.0)
sx4 = openmc.XPlane(40.0)
sx5 = openmc.XPlane(60.0, boundary_type="vacuum")
sy1 = openmc.YPlane(0.0, boundary_type="reflective")
sy2 = openmc.YPlane(10.0)
sy3 = openmc.YPlane(50.0)
sy4 = openmc.YPlane(60.0)
sy5 = openmc.YPlane(100.0, boundary_type="vacuum")
sz1 = openmc.ZPlane(0.0, boundary_type="reflective")
sz2 = openmc.ZPlane(10.0)
sz3 = openmc.ZPlane(30.0)
sz4 = openmc.ZPlane(40.0)
sz5 = openmc.ZPlane(60.0, boundary_type="vacuum")

# Instantiate Cells
# Soruce
S1 = openmc.Cell(region=+sx1 & -sx2 & +sy1 & -sy2 & +sz1 & -sz2, fill=shield)
# Voids
V1 = openmc.Cell(region=+sx1 & -sx2 & +sy2 & -sy3 & +sz1 & -sz2, fill=void)
V2 = openmc.Cell(region=+sx1 & -sx3 & +sy3 & -sy4 & +sz1 & -sz2, fill=void)
V3 = openmc.Cell(region=+sx3 & -sx4 & +sy3 & -sy4 & +sz1 & -sz3, fill=void)
V4 = openmc.Cell(region=+sx3 & -sx4 & +sy3 & -sy5 & +sz3 & -sz4, fill=void)
# Shield
Sh1 = openmc.Cell(region=+sx1 & -sx3 & +sy1 & -sy5 & +sz2 & -sz5, fill=shield)
Sh2 = openmc.Cell(region=+sx2 & -sx5 & +sy1 & -sy3 & +sz1 & -sz2, fill=shield)
Sh3 = openmc.Cell(region=+sx3 & -sx5 & +sy1 & -sy3 & +sz2 & -sz5, fill=shield)
Sh4 = openmc.Cell(region=+sx3 & -sx5 & +sy4 & -sy5 & +sz1 & -sz3, fill=shield)
Sh5 = openmc.Cell(region=+sx4 & -sx5 & +sy4 & -sy5 & +sz3 & -sz5, fill=shield)
Sh6 = openmc.Cell(region=+sx4 & -sx5 & +sy3 & -sy4 & +sz1 & -sz5, fill=shield)
Sh7 = openmc.Cell(region=+sx3 & -sx4 & +sy3 & -sy5 & +sz4 & -sz5, fill=shield)
Sh8 = openmc.Cell(region=+sx1 & -sx3 & +sy4 & -sy5 & +sz1 & -sz2, fill=shield)

# Create a geometry with the two cells and export to XML
geometry = openmc.Geometry([S1, V1, V2, V3, V4, Sh1, Sh2, Sh3, Sh4, Sh5, Sh6, Sh7, Sh8])
geometry.export_to_xml()

###############################################################################
# Define problem settings

# Instantiate a Settings object, set all runtime parameters, and export to XML
settings = openmc.Settings()
settings.run_mode = "fixed source"
settings.energy_mode = "multi-group"
settings.batches = 30
settings.particles = 100000000
settings.cutoff = {"time_neutron": 200}

# Create an initial uniform spatial source distribution over fissionable zones
lower_left = (0.0, 0.0, 0.0)
upper_right = (10.0, 10.0, 10.0)
space = openmc.stats.Box((0.0, 0.0, 0.0), (10.0, 10.0, 10.0))
time = openmc.stats.Uniform(0.0, 50.0)
energy = openmc.stats.Discrete([1.0], [1.0])
settings.source = openmc.IndependentSource(space=space, time=time, energy=energy)
settings.output = {"tallies": False}
settings.export_to_xml()

###############################################################################
# Define tallies

# Create a mesh that will be used for tallying
mesh = openmc.RectilinearMesh()
mesh.x_grid = np.linspace(0.0, 60.0, 61)
mesh.y_grid = np.linspace(0.0, 100.0, 101)
mesh.z_grid = np.linspace(0.0, 60.0, 61)
time = np.linspace(0.0, 200.0, 101)

# Create a mesh filter that can be used in a tally
time_mesh_filter = openmc.TimedMeshFilter(mesh, time)
time_filter = openmc.TimeFilter(time)

# Now use the mesh filter in a tally and indicate what scores are desired
mesh_tally = openmc.Tally(name="flux")
mesh_tally.filters = [time_mesh_filter]
mesh_tally.estimator = "tracklength"
mesh_tally.scores = ["flux"]

density_tally = openmc.Tally(name="density")
density_tally.filters = [time_filter]
density_tally.estimator = "tracklength"
density_tally.scores = ["inverse-velocity"]

# Instantiate a Tallies collection and export to XML
tallies = openmc.Tallies([mesh_tally, density_tally])
tallies.export_to_xml()
