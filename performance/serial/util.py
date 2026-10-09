"""Shared definitions for serial-performance tasks."""

from pathlib import Path
import sys

import numpy as np

# Make shared performance helpers available when launching from this suite.
REPO_DIR = Path(__file__).resolve().parents[2]
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from performance.metrics import output_complete, tally_score_paths

MODES = ("numba", "python")


def task_modes(task):
    """Return the execution modes enabled for a serial-performance case."""
    modes = tuple(mode for mode in MODES if mode in task)
    if not modes:
        raise ValueError("Each case must define a numba and/or python task block.")
    for mode in modes:
        if not isinstance(task[mode], dict):
            raise ValueError(f"Case {mode} settings must be a mapping.")
    return modes


def particle_counts(logN_min, logN_max, N_task):
    """Return logarithmically spaced particles per batch for a case study."""
    return np.logspace(logN_min, logN_max, N_task, dtype=int)


def task_particle_counts(task, mode):
    """Return the particle counts configured for one execution mode."""
    if mode not in task_modes(task):
        raise ValueError(f"Mode '{mode}' is not enabled for this case.")
    settings = task[mode]
    return particle_counts(
        settings["logN_min"], settings["logN_max"], settings["N_task"]
    )


def output_name(mode, N_particle):
    """Return the case-local output name for one mode and particle count."""
    if mode not in MODES:
        raise ValueError(f"Unsupported execution mode: {mode}")
    return f"output_{mode}_{int(N_particle)}"


def case_outputs_complete(case_dir, task, mode):
    """Return whether all configured outputs exist for one case and mode."""
    case_dir = Path(case_dir)
    return all(
        output_complete(case_dir / f"{output_name(mode, count)}.h5")
        for count in task_particle_counts(task, mode)
    )
