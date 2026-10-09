from pathlib import Path
import re
import sys

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
import numpy as np
from scipy.stats import t

# ======================================================================================
# Inputs
# ======================================================================================

if len(sys.argv) != 3:
    raise SystemExit("Usage: python plot.py OUTPUT SINBAD_INPUTS")

output_file = sys.argv[1]
sinbad_inputs = Path(sys.argv[2])
POSITION_INDEX = 1
POSITION_LABEL = "P2 — 27.94 cm"

# ======================================================================================
# Experimental neutron spectra
# ======================================================================================

lines = (sinbad_inputs / "tudsic-e.md").read_text().splitlines()
table_start = next(
    index for index, line in enumerate(lines) if line.startswith("### Table 3")
)
float_pattern = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?")

first_edge = None
rows = []
for line in lines[table_start + 1 :]:
    values = [float(value) for value in float_pattern.findall(line)]
    if len(values) == 1 and first_edge is None and 0.9 < values[0] < 1.1:
        first_edge = values[0]
    elif len(values) == 5 and first_edge is not None:
        rows.append(values)
    elif rows and line.strip() == "```":
        break

experiment = np.asarray(rows)
energy_edges = np.append(first_edge, experiment[:, 0])
nonincreasing = np.flatnonzero(np.diff(energy_edges) <= 0.0)
for index in nonincreasing:
    energy_edges[index + 1] = 0.5 * (energy_edges[index] + energy_edges[index + 2])
experimental = experiment[:, 1:].T

energy_midpoints = 0.5 * (energy_edges[:-1] + energy_edges[1:])
experimental_relative_sdev = np.empty_like(experimental)
experimental_relative_sdev[:, energy_midpoints < 5.0] = 0.04
middle = (energy_midpoints >= 5.0) & (energy_midpoints < 10.0)
experimental_relative_sdev[:, middle] = 0.05
experimental_relative_sdev[:, energy_midpoints >= 10.0] = 0.04
experimental_relative_sdev[2, energy_midpoints >= 10.0] = 0.03
experimental_sdev = experimental * experimental_relative_sdev

# ======================================================================================
# MC/DC results, statistics, and plots
# ======================================================================================

detector_volume = np.pi * 1.91**2 * 3.82
energy_width = np.diff(energy_edges)

with h5py.File(output_file, "r") as output:
    tally = output["tallies/neutron_detector_flux_energy"]
    tally_edges = tally["grid/energy"][:] * 1.0e-6
    calculated = np.asarray(tally["flux/mean"][:]).squeeze()
    calculated_sdev = np.asarray(tally["flux/sdev"][:]).squeeze()
    number_batches = int(output["settings/N_batch"][()])

if not np.allclose(tally_edges, energy_edges):
    raise ValueError(f"{output_file}: tally grid does not match the experiment")

calculated = calculated / detector_volume / energy_width
calculated_sdev = calculated_sdev / detector_volume / energy_width
confidence_multiplier = t.ppf(0.975, number_batches - 1)
calculated_lower = np.maximum(calculated - confidence_multiplier * calculated_sdev, 0.0)
calculated_upper = calculated + confidence_multiplier * calculated_sdev

exp = experimental[POSITION_INDEX]
exp_sdev = experimental_sdev[POSITION_INDEX]
ratio = calculated / exp
ratio_half_width = confidence_multiplier * calculated_sdev / exp
positive = np.isfinite(ratio) & (ratio > 0.0)
ratio_lower = np.where(
    positive,
    np.maximum(ratio - ratio_half_width, np.finfo(float).tiny),
    np.nan,
)
ratio_upper = np.where(positive, ratio + ratio_half_width, np.nan)

geometric_mean = np.exp(np.mean(np.log(ratio[positive])))
relative_standard_error = calculated_sdev[positive] / calculated[positive]
rms_standard_error = np.sqrt(np.mean(relative_standard_error**2))

fig, (ax_spectrum, ax_ratio) = plt.subplots(
    2,
    1,
    figsize=(5, 5),
    sharex=True,
    gridspec_kw={"height_ratios": [2.2, 1.0]},
)

ax_spectrum.stairs(
    exp, energy_edges, color="tab:red", linewidth=1.25, label="Experiment (1σ)"
)
ax_spectrum.stairs(
    exp + exp_sdev,
    energy_edges,
    baseline=np.maximum(exp - exp_sdev, 0.0),
    fill=True,
    color="tab:red",
    alpha=0.17,
    linewidth=0.0,
)
ax_spectrum.stairs(
    calculated,
    energy_edges,
    color="tab:blue",
    linewidth=1.25,
    label="MC/DC (95% CI)",
)
ax_spectrum.stairs(
    calculated_upper,
    energy_edges,
    baseline=calculated_lower,
    fill=True,
    color="tab:blue",
    alpha=0.17,
    linewidth=0.0,
)
ax_spectrum.set_ylabel("[MeV$^{-1}$ cm$^{-2}$ source neutron$^{-1}$]")
ax_spectrum.set_title(f"FNG/TUD SiC — {POSITION_LABEL}")
handles, labels = ax_spectrum.get_legend_handles_labels()
ax_spectrum.legend(handles[::-1], labels[::-1], fontsize="x-small")

exp_relative_sdev = exp_sdev / exp
ax_ratio.stairs(
    1.0 + exp_relative_sdev,
    energy_edges,
    baseline=np.maximum(1.0 - exp_relative_sdev, 0.0),
    fill=True,
    color="tab:red",
    alpha=0.17,
    linewidth=0.0,
)
ax_ratio.stairs(ratio, energy_edges, color="tab:blue", linewidth=1.25)
ax_ratio.stairs(
    ratio_upper,
    energy_edges,
    baseline=ratio_lower,
    fill=True,
    color="tab:blue",
    alpha=0.17,
    linewidth=0.0,
)
ax_ratio.axhline(1.0, color="black", linewidth=0.85)
ax_ratio.set_yscale("log", base=2)
ax_ratio.set_ylabel("C/E")
ax_ratio.set_xlabel("Neutron energy [MeV]")
ax_ratio.text(
    0.98,
    0.95,
    f"Geometric mean: {geometric_mean:.3f}\nRMS of SE: {rms_standard_error:.2f}",
    transform=ax_ratio.transAxes,
    horizontalalignment="right",
    verticalalignment="top",
    fontsize="x-small",
)

ratio_exponent = max(1, int(np.ceil(np.max(np.abs(np.log2(ratio[positive]))))))
ax_ratio.set_ylim(2.0**-ratio_exponent, 2.0**ratio_exponent)
ax_ratio.set_yticks(2.0 ** np.arange(-ratio_exponent, ratio_exponent + 1))
ax_ratio.yaxis.set_major_formatter(FormatStrFormatter("%g"))
ax_ratio.set_xlim(energy_edges[0], energy_edges[-1])

fig.tight_layout()
fig.savefig("neutron_spectrum.png", dpi=300)
plt.close(fig)
