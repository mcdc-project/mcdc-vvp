import matplotlib.pyplot as plt
import h5py
import sys

from reference import reference

# Reference solution
output = sys.argv[1]

# Load results
with h5py.File(output, "r") as f:
    z = f["tallies/mesh_tally_0/grid/z"][:]
    dz = z[1:] - z[:-1]
    z_mid = 0.5 * (z[:-1] + z[1:])
    I = len(z) - 1

    phi = f["tallies/mesh_tally_0/flux/mean"][:]
    phi_sd = f["tallies/mesh_tally_0/flux/sdev"][:]

# Normalize
phi, phi_sd = phi / dz, phi_sd / dz
z_ref, phi_ref = reference()

# Flux - spatial average
plt.plot(z_mid, phi, "-b", label="MC")
plt.fill_between(z_mid, phi - phi_sd, phi + phi_sd, alpha=0.2, color="b")
plt.plot(z_ref, phi_ref, "-r", label="Reference")
plt.xlabel(r"$z$, cm")
plt.ylabel("Flux")
plt.grid()
plt.legend()
plt.title(r"$\bar{\phi}_i$")
plt.savefig("scalar_flux.png", dpi=300)
plt.show()
