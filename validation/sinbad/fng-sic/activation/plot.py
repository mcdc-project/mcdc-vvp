import sys

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import t

# ======================================================================================
# Inputs
# ======================================================================================

if len(sys.argv) != 2:
    raise SystemExit("Usage: python plot.py OUTPUT")

output_file = sys.argv[1]
depths = [10.41, 25.65, 40.89, 56.13]

# The activation calculation uses an 18 mm-diameter disk, 1 mm thick at P1
# and P2 and 2 mm thick at P3 and P4.
detector_volumes = np.pi * 0.9**2 * np.array([0.10, 0.10, 0.20, 0.20])

# ======================================================================================
# Detector spectra
# ======================================================================================

fig, axes = plt.subplots(2, 2, figsize=(8, 6), sharex=True, sharey=True)

with h5py.File(output_file, "r") as output:
    number_batches = int(output["settings/N_batch"][()])
    confidence_multiplier = t.ppf(0.975, number_batches - 1)

    for index, (ax, depth, volume) in enumerate(
        zip(axes.flat, depths, detector_volumes), start=1
    ):
        tally = output[f"tallies/detector_flux_p{index}"]
        energy_edges = tally["grid/energy"][:] * 1.0e-6
        energy_width = np.diff(energy_edges)
        spectrum = np.asarray(tally["flux/mean"][:]).squeeze() / volume / energy_width
        spectrum_sdev = (
            np.asarray(tally["flux/sdev"][:]).squeeze() / volume / energy_width
        )
        lower = np.maximum(
            spectrum - confidence_multiplier * spectrum_sdev,
            np.finfo(float).tiny,
        )
        upper = spectrum + confidence_multiplier * spectrum_sdev

        ax.stairs(spectrum, energy_edges, color="tab:blue", linewidth=1.1)
        ax.stairs(
            upper,
            energy_edges,
            baseline=lower,
            fill=True,
            color="tab:blue",
            alpha=0.17,
            linewidth=0.0,
        )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"P{index} — {depth:.2f} cm")

for ax in axes[-1, :]:
    ax.set_xlabel("Neutron energy [MeV]")
for ax in axes[:, 0]:
    ax.set_ylabel("[MeV$^{-1}$ cm$^{-2}$ source neutron$^{-1}$]")

fig.suptitle("FNG SiC activation spectra — response-folding input (95% CI)")
fig.tight_layout()
fig.savefig("neutron-spectra.png", dpi=300)
plt.close(fig)
