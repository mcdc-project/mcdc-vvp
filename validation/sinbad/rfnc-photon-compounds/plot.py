from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ======================================================================================
# Input and experimental data
# ======================================================================================

if len(sys.argv) != 2:
    raise SystemExit("Usage: python plot.py SINBAD_INPUTS")

sinbad_inputs = Path(sys.argv[1])
data = np.loadtxt(sinbad_inputs / "tab2res.txt", skiprows=6)
energy_lower = data[:, 1]
energy_upper = data[:, 2]
energy_edges = np.append(energy_lower, energy_upper[-1])
spectra = data[:, 3:].T

labels = [
    "H₂O sphere",
    "SiO₂ sphere",
    "SiO₂ back hemisphere",
    "NaCl sphere",
    "NaCl back hemisphere",
]

# The package gives a 12% combined uncertainty for absolute measurements, not
# binwise standard deviations or a covariance matrix. The bands below display
# that reported combined uncertainty without assigning it a Gaussian meaning.
relative_uncertainty = 0.12

# ======================================================================================
# Plot
# ======================================================================================

fig, axes = plt.subplots(3, 2, figsize=(8, 8), sharex=True)

for ax, label, spectrum in zip(axes.flat, labels, spectra):
    ax.stairs(spectrum, energy_edges, color="tab:red", linewidth=1.1)
    ax.stairs(
        spectrum * (1.0 + relative_uncertainty),
        energy_edges,
        baseline=np.maximum(spectrum * (1.0 - relative_uncertainty), 0.0),
        fill=True,
        color="tab:red",
        alpha=0.17,
        linewidth=0.0,
    )
    ax.set_title(label)
    ax.set_yscale("log")

axes.flat[-1].axis("off")
for ax in axes[-1, :1]:
    ax.set_xlabel("Photon energy [MeV]")
axes[1, 1].set_xlabel("Photon energy [MeV]")
for ax in axes[:, 0]:
    ax.set_ylabel("photons / 100,000 source neutrons")

fig.suptitle("RFNC measured photon spectra — reported 12% combined uncertainty")
fig.tight_layout()
fig.savefig("experimental-photon-spectra.png", dpi=300)
plt.close(fig)
