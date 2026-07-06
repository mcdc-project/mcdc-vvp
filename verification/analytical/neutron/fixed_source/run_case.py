import argparse
import subprocess
from pathlib import Path

import numpy as np
import yaml


parser = argparse.ArgumentParser(
    description="Run one MC/DC VVP suite_A verification case."
)
parser.add_argument("--name", required=True, help="Verification case name.")
parser.add_argument("--task-file", default="task.yaml")
parser.add_argument(
    "--mpi",
    default="",
    help="MPI launch command supplied by Maestro, e.g. 'srun -n 112'.",
)
args = parser.parse_args()


suite_dir = Path(__file__).resolve().parent
case_dir = suite_dir / "cases" / args.name
task_file = suite_dir / args.task_file

if not case_dir.is_dir():
    raise FileNotFoundError(f"Case directory not found: {case_dir}")

with task_file.open("r") as f:
    tasks = yaml.safe_load(f)

if args.name not in tasks:
    raise ValueError(f"Case '{args.name}' is not listed in {task_file}")

task = tasks[args.name]
particle_counts = np.logspace(
    task["logN_min"],
    task["logN_max"],
    task["N_task"],
    dtype=int,
)

for N_particle in particle_counts:
    N_particle = int(N_particle)
    output = f"output_{N_particle}"
    output_file = case_dir / f"{output}.h5"

    if output_file.is_file():
        print(f"Skip (output exists): {args.name}, N={N_particle}")
        continue

    command = (
        f"{args.mpi} python input.py "
        f"--mode=numba "
        f"--N_particle={N_particle} "
        f"--output={output} "
        "--no-progress_bar "
        "--caching"
    ).strip()

    print("=" * 80)
    print(f"Case      : {args.name}")
    print(f"N_particle: {N_particle}")
    print(f"Command   : {command}")
    print("=" * 80)

    subprocess.run(command, shell=True, cwd=case_dir, check=True)
