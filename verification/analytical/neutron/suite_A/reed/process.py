import numpy as np
import h5py
import sys

sys.path.append("../")
import tool

# Cases run
N_min = int(sys.argv[1])
N_max = int(sys.argv[2])
N = int(sys.argv[3])
N_particle_list = np.logspace(N_min, N_max, N)

# Reference solution
data = np.load("reference.npz")
phi_ref = data["phi"]

# Error containers
error = np.zeros(len(N_particle_list))
error_max = np.zeros(len(N_particle_list))

# Calculate error
for k, N_particle in enumerate(N_particle_list):
    # Get results
    with h5py.File("output_%i.h5" % (int(N_particle)), "r") as f:
        z = f["tallies/mesh_tally_0/grid/z"][:]
        dz = z[1:] - z[:-1]
        phi = f["tallies/mesh_tally_0/flux/mean"][:]

    # Normalize
    phi = phi / dz

    # Get error
    error[k] = tool.rerror(phi, phi_ref)
    error_max[k] = tool.rerror_max(phi, phi_ref)


# Plot
tool.plot_convergence("reed_flux", N_particle_list, error, error_max)
