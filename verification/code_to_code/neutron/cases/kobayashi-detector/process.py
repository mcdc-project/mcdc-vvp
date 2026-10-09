"""Process the Kobayashi detector particle-count study with archived OpenMC results."""

import argparse
import sys
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np

SUITE_DIR = Path(__file__).resolve().parents[2]
if str(SUITE_DIR) not in sys.path:
    sys.path.insert(0, str(SUITE_DIR))

from util import (
    comparison_reference,
    load_openmc_tally,
    particle_counts,
    plot_convergence,
    relative_difference_metrics,
    require_reference_files,
)


def load_mcdc_results(path):
    """Read time-integrated capture per source particle in each detector bin."""
    with h5py.File(path, "r") as f:
        capture = np.asarray(f["tallies/detector/capture/mean"][()]).reshape(-1)
        time = f["tallies/detector/grid/time"][:]
        N_batch = int(f["settings/N_batch"][()])
    if capture.shape != (len(time) - 1,) or np.any(np.diff(time) <= 0):
        raise ValueError(f"Invalid detector history or time grid in {path}")
    return capture, time, N_batch


def load_openmc_results(path):
    """Read the single-score detector capture tally and its time edges."""
    capture = load_openmc_tally(path, "detector")
    with h5py.File(path, "r") as f:
        tallies = f["tallies"]
        for key, tally in tallies.items():
            if not key.startswith("tally ") or "name" not in tally:
                continue
            name = tally["name"][()]
            if isinstance(name, bytes):
                name = name.decode()
            if name != "detector":
                continue
            scores = [
                s.decode() if isinstance(s, bytes) else s
                for s in np.asarray(tally["score_bins"][()]).reshape(-1)
            ]
            if scores != ["(n,gamma)"]:
                raise ValueError("OpenMC detector must have only the (n,gamma) score.")
            for filter_id in np.asarray(tally["filters"][()]).reshape(-1):
                filter_group = tallies[f"filters/filter {int(filter_id)}"]
                kind = filter_group["type"][()]
                if kind in (b"time", "time"):
                    bins = filter_group["bins"][:]
                    if bins.ndim == 2:
                        if bins.shape[1] != 2 or not np.array_equal(
                            bins[:-1, 1], bins[1:, 0]
                        ):
                            raise ValueError("OpenMC time bins must be contiguous.")
                        time = np.r_[bins[:, 0], bins[-1, 1]]
                    else:
                        time = bins
                    if capture.shape != (len(time) - 1,):
                        raise ValueError(
                            "OpenMC detector must have one value per time bin."
                        )
                    return capture, time
    raise ValueError(f"OpenMC detector has no time filter in {path}")


def check_time_grid(expected, actual):
    """Prevent comparisons between different time discretizations."""
    if not np.array_equal(expected, actual):
        raise ValueError("All MC/DC and OpenMC detector time grids must match.")


def plot_history(time, histories, labels, ylabel, filename):
    """Plot bin-integrated detector responses without spatial animation."""
    fig, ax = plt.subplots()
    for history, label in zip(histories, labels):
        ax.stairs(history, time, label=label)
    ax.set_xlabel("Time")
    ax.set_ylabel(ylabel)
    ax.grid()
    ax.legend()
    fig.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    """Process every particle-count task and generate the convergence figure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logN_min", type=float)
    parser.add_argument("logN_max", type=float)
    parser.add_argument("N_task", type=int)
    args = parser.parse_args()

    case_dir = Path(__file__).resolve().parent
    N_particle = particle_counts(args.logN_min, args.logN_max, args.N_task)
    reference_files = require_reference_files(case_dir, args.N_task)
    mcdc_reference, time, N_batch = load_mcdc_results(
        case_dir / f"output_{int(N_particle[-1])}.h5"
    )
    openmc_reference, openmc_time = load_openmc_results(reference_files[-1])
    check_time_grid(time, openmc_time)
    reference = comparison_reference(mcdc_reference, openmc_reference)
    plot_history(
        time,
        [reference],
        ["Fixed comparison reference"],
        "Detector capture per source particle per time bin",
        "reference_capture.png",
    )

    difference_l2 = np.zeros(args.N_task)
    difference_max = np.zeros(args.N_task)
    for index, (count, reference_file) in enumerate(zip(N_particle, reference_files)):
        capture, current_time, current_N_batch = load_mcdc_results(
            case_dir / f"output_{int(count)}.h5"
        )
        openmc_capture, openmc_time = load_openmc_results(reference_file)
        check_time_grid(time, current_time)
        check_time_grid(time, openmc_time)
        if current_N_batch != N_batch:
            raise ValueError("All MC/DC outputs must use the same number of batches.")
        difference_l2[index], difference_max[index] = relative_difference_metrics(
            reference, capture, openmc_capture
        )
    plot_convergence("capture", N_particle * N_batch, difference_l2, difference_max)


if __name__ == "__main__":
    main()
