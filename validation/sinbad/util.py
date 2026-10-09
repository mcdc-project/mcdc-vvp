"""Shared configuration helpers for the SINBAD validation suite."""

import math
from pathlib import Path

import yaml

SINBAD_PACKAGE_TOKENS = {
    "oktavian-si-60": "oktav_si",
    "fng-tud-sic": "tud_sic",
}

RUNNABLE_CASES = {
    "oktavian-si-60": {"neutron_leakage"},
    "fng-tud-sic": {"p1", "p2", "p3", "p4"},
}


def load_tasks(task_file):
    """Load and validate the benchmark/case particle-count mapping."""
    task_file = Path(task_file)
    with task_file.open("r") as file:
        configured = yaml.safe_load(file)

    if not isinstance(configured, dict) or not configured:
        raise ValueError(f"Task configuration must be a nonempty mapping: {task_file}")

    tasks = []
    for benchmark, cases in configured.items():
        if not isinstance(benchmark, str) or not benchmark:
            raise ValueError("Every benchmark name must be a nonempty string.")
        if benchmark not in RUNNABLE_CASES:
            raise ValueError(f"Benchmark '{benchmark}' is not runnable in this suite.")
        if not isinstance(cases, dict) or not cases:
            raise ValueError(f"Benchmark '{benchmark}' must contain at least one case.")

        for case, task in cases.items():
            if not isinstance(case, str) or not case:
                raise ValueError("Every case name must be a nonempty string.")
            if case not in RUNNABLE_CASES[benchmark]:
                raise ValueError(
                    f"Case '{benchmark}/{case}' is not runnable in this suite."
                )
            if not isinstance(task, dict):
                raise ValueError(
                    f"Task '{benchmark}/{case}' must define N_particle and "
                    "walltime_factor."
                )

            N_particle = task.get("N_particle")
            if (
                isinstance(N_particle, bool)
                or not isinstance(N_particle, int)
                or N_particle <= 0
            ):
                raise ValueError(
                    f"Particle count for '{benchmark}/{case}' must be a positive integer."
                )

            walltime_factor = task.get("walltime_factor")
            if (
                isinstance(walltime_factor, bool)
                or not isinstance(walltime_factor, (int, float))
                or not math.isfinite(walltime_factor)
                or walltime_factor <= 0.0
            ):
                raise ValueError(
                    f"Walltime factor for '{benchmark}/{case}' must be positive."
                )

            tasks.append((benchmark, case, task))

    return configured, tasks


def case_directory(suite_dir, benchmark, case):
    """Return the directory containing one benchmark case."""
    return Path(suite_dir) / benchmark / case


def output_file(case_dir, N_particle):
    """Return the expected output path for one configured case."""
    return Path(case_dir) / f"output_{N_particle}.h5"


def resolve_sinbad_inputs(sinbad_root, benchmark):
    """Locate the licensed input directory for a supported benchmark."""
    sinbad_root = Path(sinbad_root).expanduser().resolve()
    if not sinbad_root.is_dir():
        raise FileNotFoundError(f"SINBAD repository not found: {sinbad_root}")

    token = SINBAD_PACKAGE_TOKENS.get(benchmark)
    if token is None:
        raise ValueError(f"No SINBAD package mapping is defined for '{benchmark}'.")

    matches = sorted(sinbad_root.glob(f"*{token}*/00_Report/10_Inputs"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected one '{token}' package below {sinbad_root}, found {len(matches)}."
        )
    return matches[0]


def plot_arguments(output, sinbad_inputs):
    """Return the positional arguments used by every runnable case plot."""
    return [str(output), str(sinbad_inputs)]
