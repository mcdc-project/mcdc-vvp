"""Process a completed SINBAD validation Maestro study."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from util import (
    case_directory,
    load_tasks,
    output_file,
    plot_arguments,
    resolve_sinbad_inputs,
)

# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(description="Process the MC/DC VVP SINBAD suite.")
parser.add_argument(
    "sinbad_root",
    help="Path containing the locally available licensed SINBAD repositories.",
)
parser.add_argument(
    "maestro_run",
    nargs="?",
    default=None,
    help="Maestro run directory; defaults to the latest maestro_run_*.",
)
args = parser.parse_args()


# ======================================================================================
# Paths
# ======================================================================================

suite_dir = Path(__file__).resolve().parent
sinbad_root = Path(args.sinbad_root).expanduser()

if args.maestro_run is None:
    maestro_runs = sorted(
        suite_dir.glob("maestro_run_*"), key=lambda path: path.stat().st_mtime
    )
    if not maestro_runs:
        raise FileNotFoundError("No maestro_run_* directory found.")
    maestro_run = maestro_runs[-1]
else:
    maestro_run = Path(args.maestro_run).expanduser()
    if not maestro_run.is_absolute():
        maestro_run = suite_dir / maestro_run

launch_config_file = maestro_run / "launch_config.yaml"
task_file = maestro_run / "task.yaml"

if not launch_config_file.is_file():
    raise FileNotFoundError(f"Launch config not found: {launch_config_file}")
if not task_file.is_file():
    raise FileNotFoundError(f"Task config not found: {task_file}")


# ======================================================================================
# Load configuration and prepare results
# ======================================================================================

with launch_config_file.open("r") as file:
    launch_config = yaml.safe_load(file)

_, tasks = load_tasks(task_file)

results_dir = suite_dir / "results"
if results_dir.is_dir():
    shutil.rmtree(results_dir)
results_dir.mkdir(parents=True)

shutil.copy2(launch_config_file, results_dir / "launch_config.yaml")
shutil.copy2(task_file, results_dir / "task.yaml")


# ======================================================================================
# Process cases
# ======================================================================================

for benchmark, case, task in tasks:
    name = f"{benchmark}/{case}"
    case_dir = case_directory(suite_dir, benchmark, case)
    plot_script = case_dir / "plot.py"
    N_particle = task["N_particle"]
    output = output_file(case_dir, N_particle)

    if not plot_script.is_file():
        raise FileNotFoundError(f"Case plot script not found: {plot_script}")
    if not output.is_file():
        raise FileNotFoundError(f"Case output not found: {output}")

    for pattern in ("*.png", "*.gif"):
        for figure in case_dir.glob(pattern):
            figure.unlink()

    sinbad_inputs = resolve_sinbad_inputs(sinbad_root, benchmark)

    command = [sys.executable, str(plot_script)]
    command.extend(plot_arguments(output, sinbad_inputs))

    print(f"Processing {name}")
    subprocess.run(command, cwd=case_dir, check=True)

    figures = [
        figure
        for pattern in ("*.png", "*.gif")
        for figure in sorted(case_dir.glob(pattern))
    ]
    if not figures:
        raise RuntimeError(f"No figure was generated for {name}.")

    destination = results_dir / benchmark / case
    destination.mkdir(parents=True, exist_ok=True)
    for figure in figures:
        figure.replace(destination / figure.name)


# ======================================================================================
# Summary
# ======================================================================================

print()
print(f"Maestro run: {maestro_run}")
print(f"Platform   : {launch_config['platform']}")
print(f"Nodes      : {launch_config['N_node']}")
print(f"Processes  : {launch_config['N_process']}")
print(f"Cases      : {len(tasks)}")
print(f"Results    : {results_dir}")
print("Processing complete.")
