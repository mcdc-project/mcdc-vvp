from pathlib import Path
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ======================================================================================
# Inputs
# ======================================================================================

if len(sys.argv) != 2:
    raise SystemExit("Usage: python plot.py SINBAD_INPUTS")

sinbad_inputs = Path(sys.argv[1])

# ======================================================================================
# Experimental data
# ======================================================================================

lines = (sinbad_inputs / "oksi-exp.md").read_text().splitlines()
table_start = next(
    index for index, line in enumerate(lines) if line.startswith("### Table 5")
)

float_pattern = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?")
rows = []
for line in lines[table_start + 1 :]:
    values = float_pattern.findall(line)
    if len(values) == 4:
        rows.append([float(value) for value in values])
    elif rows:
        break

experiment = np.asarray(rows)
energy_lower, energy_upper, spectrum, uncertainty = experiment.T
energy_edges = np.append(energy_lower, energy_upper[-1])

# ======================================================================================
# Plot
# ======================================================================================

# The benchmark supplies a combined binwise uncertainty that includes source
# normalization, response-matrix, and counting contributions.  It does not
# document a distributional interpretation, so the band is labeled as the
# reported uncertainty rather than converted to a confidence interval.
lower = np.maximum(spectrum - uncertainty, 0.0)
upper = spectrum + uncertainty

fig, ax = plt.subplots(figsize=(5, 3.6))
ax.stairs(
    spectrum,
    energy_edges,
    color="tab:red",
    linewidth=1.25,
    label="Experiment",
)
ax.stairs(
    upper,
    energy_edges,
    baseline=lower,
    fill=True,
    color="tab:red",
    alpha=0.17,
    linewidth=0.0,
    label="Reported uncertainty",
)
ax.set_xlim(energy_edges[0], energy_edges[-1])
ax.set_ylim(0.0, 1.08 * np.max(upper))
ax.set_xlabel("Photon energy [MeV]")
ax.set_ylabel("[MeV$^{-1}$ source neutron$^{-1}$]")
ax.set_title("OKTAVIAN Si-60 — Gamma leakage")
ax.grid(alpha=0.22)
ax.legend(fontsize="x-small")
fig.tight_layout()
fig.savefig("gamma-leakage-experiment.png", dpi=200)
plt.close(fig)
