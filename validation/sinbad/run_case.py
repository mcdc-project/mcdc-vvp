"""Run one configured SINBAD validation case."""

import argparse
import subprocess
import sys
from pathlib import Path

from util import case_directory, load_tasks, output_file

# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(description="Run one MC/DC VVP SINBAD case.")
parser.add_argument("--benchmark", required=True, help="SINBAD benchmark directory.")
parser.add_argument(
    "--case", required=True, help="Case directory within the benchmark."
)
parser.add_argument("--task-file", default="task.yaml")
parser.add_argument(
    "--launcher",
    default="",
    help="Process launch command supplied by Maestro.",
)
args = parser.parse_args()


# ======================================================================================
# Paths and task definition
# ======================================================================================

suite_dir = Path(__file__).resolve().parent
task_file = suite_dir / args.task_file
case_dir = case_directory(suite_dir, args.benchmark, args.case)

configured, _ = load_tasks(task_file)
if args.benchmark not in configured or args.case not in configured[args.benchmark]:
    raise ValueError(
        f"Case '{args.benchmark}/{args.case}' is not listed in {task_file}."
    )
if not (case_dir / "input.py").is_file():
    raise FileNotFoundError(f"Case input not found: {case_dir / 'input.py'}")

task = configured[args.benchmark][args.case]
N_particle = task["N_particle"]
output = f"output_{N_particle}"
expected_output = output_file(case_dir, N_particle)

if expected_output.is_file():
    print(f"Skip existing output: {args.benchmark}/{args.case}, N={N_particle}")
    raise SystemExit(0)


# ======================================================================================
# Run case
# ======================================================================================

command = (
    f"{args.launcher} {sys.executable} input.py "
    "--mode=numba "
    f"--N_particle={N_particle} "
    f"--output={output} "
    "--no-progress_bar "
    "--caching"
).strip()

print("=" * 80)
print(f"Benchmark           : {args.benchmark}")
print(f"Case                : {args.case}")
print(f"Particles per batch : {N_particle}")
print(f"Python              : {sys.executable}")
print(f"Command             : {command}")
print("=" * 80)

subprocess.run(command, shell=True, cwd=case_dir, check=True)
