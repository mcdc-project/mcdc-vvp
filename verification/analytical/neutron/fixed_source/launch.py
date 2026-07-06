import argparse
import subprocess
from pathlib import Path


parser = argparse.ArgumentParser(
    description="Generate and launch the Maestro workflow for this verification suite."
)
parser.add_argument(
    "--platform",
    default="local",
    help="Execution platform (e.g., local, dane, lassen, tuolumne).",
)
parser.add_argument(
    "--mpi",
    action="store_true",
    help="Run each MC/DC simulation using MPI.",
)
parser.add_argument(
    "--walltime",
    type=int,
    default=None,
    help="Requested walltime in hours. Defaults to the platform maximum.",
)
args = parser.parse_args()


suite_dir = Path(__file__).resolve().parent


# =============================================================================
# Generate study.yaml
# =============================================================================

command = [
    "python",
    "generate_study.py",
    "--platform",
    args.platform,
]

if args.mpi:
    command.append("--mpi")

if args.walltime is not None:
    command.extend(["--walltime", str(args.walltime)])

subprocess.run(command, cwd=suite_dir, check=True)


# =============================================================================
# Launch Maestro
# =============================================================================

subprocess.run(
    ["maestro", "run", "study.yaml"],
    cwd=suite_dir,
    check=True,
)
