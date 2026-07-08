import argparse
import os
import subprocess
from pathlib import Path

import yaml


# ======================================================================================
# Bootstrap VVP imports
# ======================================================================================

import sys

REPO_DIR = Path(__file__).resolve().parents[4]

if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))


# ======================================================================================
# Load shared VVP configs
# ======================================================================================

from configs.platform_config import PLATFORMS  # noqa: E402

try:
    from configs.user_config import USER_CONFIG  # noqa: E402
except ImportError:
    USER_CONFIG = {}


# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(
    description="Launch the MC/DC VVP analytical neutron fixed-source suite."
)
parser.add_argument("--platform", default="local", choices=["local"] + list(PLATFORMS))
parser.add_argument("--mpi", action="store_true")
parser.add_argument("--walltime", type=int, default=None)
parser.add_argument("--rewrite", action="store_true")
args = parser.parse_args()

if args.mpi and args.platform == "local":
    parser.error("--mpi requires a cluster platform. Specify --platform <platform>.")


# ======================================================================================
# Paths
# ======================================================================================

suite_dir = Path(__file__).resolve().parent
task_file = suite_dir / "task.yaml"
run_case = suite_dir / "run_case.py"
study_file = suite_dir / "study.yaml"


# ======================================================================================
# Platform settings
# ======================================================================================

local = args.platform == "local"
user_platform_config = USER_CONFIG.get(args.platform, {})

mcdc_python = user_platform_config.get("mcdc_python")

if mcdc_python is None:
    mcdc_python = sys.executable
else:
    mcdc_python = str(Path(mcdc_python).expanduser())

if not local:
    platform = PLATFORMS[args.platform]
    scheduler = platform["scheduler"]
    cpu_cores = platform["cpu_cores_per_node"]

    walltime_hours = (
        platform["max_walltime_hours"]
        if args.walltime is None
        else min(args.walltime, platform["max_walltime_hours"])
    )
    walltime = platform["walltime_format"].format(hours=walltime_hours)

    account = user_platform_config.get("account")
    queue = user_platform_config.get("queue")
    reservation = user_platform_config.get("reservation")

    if account is None:
        raise ValueError(
            f"Platform '{args.platform}' requires an account. "
            "Create configs/user_config.py from configs/user_config.py.template."
        )


# ======================================================================================
# Load tasks
# ======================================================================================

with task_file.open("r") as f:
    tasks = yaml.safe_load(f)


# ======================================================================================
# Build Maestro study
# ======================================================================================

steps = []

for case_name in tasks:
    safe_case_name = case_name.replace("-", "_")

    command = f"{mcdc_python} {run_case} --name {case_name}"

    if args.mpi:
        command += ' --mpi "$(LAUNCHER)"'

    if args.rewrite:
        command += " --rewrite"

    run = {"cmd": command}

    if not local:
        run["nodes"] = 1
        run["walltime"] = walltime

        if args.mpi:
            run["procs"] = cpu_cores
            run["exclusive"] = True
        else:
            run["procs"] = 1

    steps.append(
        {
            "name": safe_case_name,
            "description": f"Run case: {case_name}",
            "run": run,
        }
    )

study = {
    "description": {
        "name": "maestro_run",
        "description": "MC/DC verification - analytical neutron - fixed-source suite",
    },
    "env": {
        "variables": {},
    },
    "study": steps,
}

if not local:
    batch = {
        "type": scheduler,
        "host": platform["host"],
        "bank": account,
    }

    if queue is not None:
        batch["queue"] = queue

    if reservation is not None:
        batch["reservation"] = reservation

    study["batch"] = batch


# ======================================================================================
# Write Maestro study
# ======================================================================================

with study_file.open("w") as f:
    yaml.dump(study, f, sort_keys=False)


# ======================================================================================
# Launch Maestro
# ======================================================================================

maestro_python = None

if not local:
    maestro_python = user_platform_config.get("maestro_python")

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


# ======================================================================================
# Store launch metadata
# ======================================================================================

maestro_runs = sorted(
    suite_dir.glob("maestro_run_*"),
    key=lambda path: path.stat().st_mtime,
)

if not maestro_runs:
    raise RuntimeError("Maestro did not create a maestro_run_* directory.")

latest_run = maestro_runs[-1]

launch_config = {
    "platform": args.platform,
    "mpi": args.mpi,
    "walltime": args.walltime,
    "rewrite": args.rewrite,
}

with (latest_run / "launch_config.yaml").open("w") as f:
    yaml.dump(launch_config, f, sort_keys=False)

with task_file.open("r") as f:
    task_config = yaml.safe_load(f)

with (latest_run / "task.yaml").open("w") as f:
    yaml.dump(task_config, f, sort_keys=False)


# ======================================================================================
# Summary
# ======================================================================================

print(f"Platform : {args.platform}")
print(f"MPI      : {args.mpi}")
print(f"Rewrite  : {args.rewrite}")
print(f"Python   : {mcdc_python}")
print(f"Study    : {study_file}")

if not local:
    print(f"Scheduler: {scheduler}")
    print(f"Account  : {account}")
    print(f"Queue    : {queue}")
    print(f"Reserv.  : {reservation}")
    print(f"Walltime : {walltime}")
    print(f"Nodes    : 1")
    print(f"Procs    : {cpu_cores if args.mpi else 1}")

print(f"Cases    : {len(steps)}")
