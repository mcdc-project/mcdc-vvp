from pathlib import Path
import re
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

if len(sys.argv) != 3:
    raise SystemExit("Usage: python plot.py OUTPUT SINBAD_INPUTS")

output_file = sys.argv[1]
sinbad_inputs = Path(sys.argv[2])

# ======================================================================================
# Experimental data
# ======================================================================================

DETECTOR_CENTER_DISTANCE_CM = 1097.45
DETECTOR_RADIUS_CM = 6.35
DETECTOR_LENGTH_CM = 5.1
VALIDATION_ENERGY_MIN_MEV = 3.0288
VALIDATION_ENERGY_MAX_MEV = 13.574

lines = (sinbad_inputs / "oksi-exp.md").read_text().splitlines()
table_start = next(
    index for index, line in enumerate(lines) if line.startswith("### Table 3")
)

float_pattern = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?")
rows = []
for line in lines[table_start + 1 :]:
    values = float_pattern.findall(line)
    if len(values) == 4:
        rows.append([float(value) for value in values])
    elif rows:
        break

experiment = np.asarray(sorted(rows))
exp_lower, exp_upper, exp_lethargy, exp_sdev_lethargy = experiment.T
selected = (exp_lower >= VALIDATION_ENERGY_MIN_MEV) & (
    exp_upper <= VALIDATION_ENERGY_MAX_MEV
)
exp_lower = exp_lower[selected]
exp_upper = exp_upper[selected]
exp_lethargy = exp_lethargy[selected]
exp_sdev_lethargy = exp_sdev_lethargy[selected]
energy_edges = np.append(exp_lower, exp_upper[-1])

# ======================================================================================
# MC/DC result
# ======================================================================================

with h5py.File(output_file, "r") as output:
    tally = output["tallies/neutron_detector_flux_energy"]
    tally_energy_edges = tally["grid/energy"][:] * 1.0e-6
    detector_flux = np.asarray(tally["flux/mean"][:]).squeeze()
    detector_flux_sdev = np.asarray(tally["flux/sdev"][:]).squeeze()
    number_batches = int(output["settings/N_batch"][()])

tally_bins = np.flatnonzero(
    (tally_energy_edges[:-1] >= VALIDATION_ENERGY_MIN_MEV)
    & (tally_energy_edges[1:] <= VALIDATION_ENERGY_MAX_MEV)
)
first_bin = tally_bins[0]
last_bin = tally_bins[-1] + 1
selected_tally_edges = tally_energy_edges[first_bin : last_bin + 1]
if not np.allclose(selected_tally_edges, energy_edges):
    raise ValueError("MC/DC tally grid does not match the selected experimental bins")

detector_flux = detector_flux[first_bin:last_bin]
detector_flux_sdev = detector_flux_sdev[first_bin:last_bin]

# ======================================================================================
# Spectrum normalization and statistics
# ======================================================================================

# The experiment reports leakage per unit lethargy. Recover each bin integral,
# then divide by its energy width so the stair-plot area equals that integral.
energy_width = np.diff(energy_edges)
lethargy_width = np.log(energy_edges[1:] / energy_edges[:-1])

experimental_integral = exp_lethargy * lethargy_width
experimental_integral_sdev = exp_sdev_lethargy * lethargy_width
experimental = experimental_integral / energy_width
experimental_sdev = experimental_integral_sdev / energy_width

# MC/DC scores track length per source neutron in the finite detector cell.
# Divide by the detector volume for cell-averaged scalar flux, then apply the
# benchmark's 4*pi*R^2 far-field conversion to total-equivalent leakage.
detector_volume = np.pi * DETECTOR_RADIUS_CM**2 * DETECTOR_LENGTH_CM
leakage_factor = 4.0 * np.pi * DETECTOR_CENTER_DISTANCE_CM**2 / detector_volume
calculated_integral = detector_flux * leakage_factor
calculated_integral_sdev = detector_flux_sdev * leakage_factor
calculated = calculated_integral / energy_width
calculated_sdev = calculated_integral_sdev / energy_width

# The experiment band is its published binwise 1-sigma counting uncertainty.
# The MC/DC band is a two-sided, Student-t-corrected 95% confidence interval.
confidence_multiplier = t.ppf(0.975, number_batches - 1)
calculated_lower = np.maximum(calculated - confidence_multiplier * calculated_sdev, 0.0)
calculated_upper = calculated + confidence_multiplier * calculated_sdev
experimental_lower = np.maximum(experimental - experimental_sdev, 0.0)
experimental_upper = experimental + experimental_sdev

ratio = calculated / experimental
ratio_half_width = confidence_multiplier * calculated_sdev / experimental
positive = np.isfinite(ratio) & (ratio > 0.0)
ratio_lower = np.where(
    positive,
    np.maximum(ratio - ratio_half_width, np.finfo(float).tiny),
    np.nan,
)
ratio_upper = np.where(positive, ratio + ratio_half_width, np.nan)

# The geometric mean summarizes multiplicative C/E bias. The RMS of the
# relative MC/DC standard errors summarizes binwise Monte Carlo convergence;
# it is not the uncertainty of the geometric mean.
geometric_mean = np.exp(np.mean(np.log(ratio[positive])))
relative_standard_error = calculated_sdev[positive] / calculated[positive]
rms_standard_error = np.sqrt(np.mean(relative_standard_error**2))

# ======================================================================================
# Plot
# ======================================================================================

fig, (ax_spectrum, ax_ratio) = plt.subplots(
    2,
    1,
    figsize=(5, 5),
    sharex=True,
    gridspec_kw={"height_ratios": [2.2, 1.0]},
)

ax_spectrum.stairs(
    experimental,
    energy_edges,
    color="tab:red",
    linewidth=1.25,
    label="Experiment (1σ)",
)
ax_spectrum.stairs(
    experimental_upper,
    energy_edges,
    baseline=experimental_lower,
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
ax_spectrum.set_ylim(
    0.0,
    1.08 * max(np.max(experimental_upper), np.max(calculated_upper)),
)
ax_spectrum.set_ylabel("[MeV$^{-1}$ source neutron$^{-1}$]")
ax_spectrum.set_title("OKTAVIAN Si-60 — Neutron leakage")
handles, labels = ax_spectrum.get_legend_handles_labels()
ax_spectrum.legend(handles[::-1], labels[::-1], fontsize="x-small")

experimental_relative_sdev = experimental_sdev / experimental
ax_ratio.stairs(
    1.0 + experimental_relative_sdev,
    energy_edges,
    baseline=np.maximum(1.0 - experimental_relative_sdev, 0.0),
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
    f"Geometric mean: {geometric_mean:.3f}\n" f"RMS of SE: {rms_standard_error:.2f}",
    transform=ax_ratio.transAxes,
    horizontalalignment="right",
    verticalalignment="top",
    fontsize="x-small",
)

ratio_exponent = max(1, int(np.ceil(np.max(np.abs(np.log2(ratio[positive]))))))
ax_ratio.set_ylim(2.0**-ratio_exponent, 2.0**ratio_exponent)
ratio_ticks = 2.0 ** np.arange(-ratio_exponent, ratio_exponent + 1)
ax_ratio.set_yticks(ratio_ticks, labels=[f"{value:g}" for value in ratio_ticks])
ax_ratio.set_xlim(VALIDATION_ENERGY_MIN_MEV, VALIDATION_ENERGY_MAX_MEV)

for axis in (ax_spectrum, ax_ratio):
    axis.grid(which="both", alpha=0.22)

fig.tight_layout()
fig.savefig("neutron_leakage.png", dpi=200)
plt.close(fig)
