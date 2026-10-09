import numpy as np
import mcdc

simulation = mcdc.Simulation("Time-dependent Kobayashi dog-leg with fission")

# ======================================================================================
# Set model
# ======================================================================================
# Based on Kobayashi dog-leg benchmark problem
# (PNE 2001, https://doi.org/10.1016/S0149-1970(01)00007-5)

# Set materials
m = mcdc.Material.multigroup(
    capture=np.array([0.05]),
    scatter=np.array([[0.05]]),
)
m_void = mcdc.Material.multigroup(
    capture=np.array([5e-5]),
    scatter=np.array([[5e-5]]),
)
m_fuel = mcdc.Material.multigroup(
    scatter=np.array([[0.05]]),
    fission=np.array([0.05]),
    nu_p=np.array([2.5]),
)

# Set surfaces
sx1 = mcdc.Surface.PlaneX(x=0.0, boundary_condition="reflective")
sx2 = mcdc.Surface.PlaneX(x=10.0)
sx3 = mcdc.Surface.PlaneX(x=30.0)
sx4 = mcdc.Surface.PlaneX(x=40.0)
sx5 = mcdc.Surface.PlaneX(x=60.0, boundary_condition="vacuum")
sy1 = mcdc.Surface.PlaneY(y=0.0, boundary_condition="reflective")
sy2 = mcdc.Surface.PlaneY(y=10.0)
sy3 = mcdc.Surface.PlaneY(y=50.0)
sy4 = mcdc.Surface.PlaneY(y=60.0)
sy5 = mcdc.Surface.PlaneY(y=90.0)
sy6 = mcdc.Surface.PlaneY(y=100.0, boundary_condition="vacuum")
sz1 = mcdc.Surface.PlaneZ(z=0.0, boundary_condition="reflective")
sz2 = mcdc.Surface.PlaneZ(z=10.0)
sz3 = mcdc.Surface.PlaneZ(z=30.0)
sz4 = mcdc.Surface.PlaneZ(z=40.0)
sz5 = mcdc.Surface.PlaneZ(z=60.0, boundary_condition="vacuum")

# Set cells

## Source
source_region = +sx1 & -sx2 & +sy1 & -sy2 & +sz1 & -sz2
source_cell = mcdc.Cell(region=source_region, fill=m)

## Void channel
channel_1 = +sx1 & -sx2 & +sy2 & -sy3 & +sz1 & -sz2
channel_2 = +sx1 & -sx3 & +sy3 & -sy4 & +sz1 & -sz2
channel_3 = +sx3 & -sx4 & +sy3 & -sy4 & +sz2 & -sz3
channel_4 = +sx3 & -sx4 & +sy3 & -sy5 & +sz3 & -sz4
void_channel = channel_1 | channel_2 | channel_3 | channel_4
void_cell = mcdc.Cell(region=void_channel, fill=m_void)

# Fuel
fuel_region = +sx3 & -sx4 & +sy3 & -sy4 & +sz1 & -sz2
fuel_cell = mcdc.Cell(region=fuel_region, fill=m_fuel)

# Detector
detector_region = +sx3 & -sx4 & +sy5 & -sy6 & +sz3 & -sz4
detector_cell = mcdc.Cell(region=detector_region, fill=m)

# Shield
box = +sx1 & -sx5 & +sy1 & -sy6 & +sz1 & -sz5
shield_cell = mcdc.Cell(
    region=box & ~void_channel & ~source_region & ~fuel_region & ~detector_region,
    fill=m,
)

simulation.set_model([source_cell, void_cell, fuel_cell, detector_cell, shield_cell])

# ======================================================================================
# Set source
# ======================================================================================
# The source pulses in t=[0, 50]

source = mcdc.Source(
    x=[0.0, 10.0],
    y=[0.0, 10.0],
    z=[0.0, 10.0],
    isotropic=True,
    energy=0,
    time=[0.0, 50.0],
)
simulation.set_sources([source])

# ======================================================================================
# Set tallies, settings, techniques, and run MC/DC
# ======================================================================================

# Tallies
time_grid = np.linspace(0.0, 500.0, 501)
detector_tally = mcdc.Tally(
    name="detector", cell=detector_cell, scores=["capture"], time=time_grid
)
simulation.set_tallies([detector_tally])

# Settings
simulation.settings.N_particle = 100
simulation.settings.N_batch = 30

# Techniques
simulation.technique.implicit_capture()

# Run
if __name__ == "__main__":
    simulation.run()
