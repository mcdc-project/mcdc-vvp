import argparse
import os
import subprocess
from pathlib import Path

from platform_config import PLATFORMS

try:
    from user_config import USER_CONFIG
except ImportError:
    USER_CONFIG = {}


# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(
    description="Generate and launch the Maestro workflow for this verification suite."
)
parser.add_argument(
    "--platform",
    default="local",
    choices=["local"] + list(PLATFORMS.keys()),
)
parser.add_argument("--mpi", action="store_true")
parser.add_argument("--walltime", type=int, default=None)
args = parser.parse_args()


# ======================================================================================
# Paths
# ======================================================================================

suite_dir = Path(__file__).resolve().parent


# ======================================================================================
# Generate study
# ======================================================================================

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


# ======================================================================================
# Launch Maestro
# ======================================================================================

maestro_python = None

if args.platform != "local":
    maestro_python = USER_CONFIG.get(args.platform, {}).get("maestro_python")

env = os.environ.copy()

if maestro_python is None:
    maestro_command = ["maestro", "run", "study.yaml"]
else:
    maestro_python = Path(maestro_python).expanduser()
    maestro_bin = maestro_python.parent

    env["PATH"] = f"{maestro_bin}:{env['PATH']}"

    maestro_command = [
        str(maestro_python),
        "-m",
        "maestrowf.maestro",
        "run",
        "study.yaml",
    ]

subprocess.run(maestro_command, cwd=suite_dir, check=True, env=env)
