"""Build and launch the SINBAD validation study with Maestro."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

# ======================================================================================
# Bootstrap VVP imports
# ======================================================================================

REPO_DIR = Path(__file__).resolve().parents[2]

if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))


# ======================================================================================
# Load shared VVP configs
# ======================================================================================

from configs.platform_config import PLATFORMS
from configs.util import get_case_walltime
from util import case_directory, load_tasks, output_file

try:
    from configs.user_config import USER_CONFIG
except ImportError:
    USER_CONFIG = {}


# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(description="Launch the MC/DC VVP SINBAD suite.")
parser.add_argument("--platform", default="local", choices=["local"] + list(PLATFORMS))
parser.add_argument("--N_node", type=int, default=1, help="Set the number of nodes.")
parser.add_argument(
    "--walltime",
    type=float,
    default=None,
    help="Set the base walltime in hours; each case scales it by walltime_factor.",
)
args = parser.parse_args()

if args.N_node < 1:
    parser.error("--N_node must be at least one.")
if args.platform == "local" and args.N_node != 1:
    parser.error("Local execution supports only --N_node 1.")


# ======================================================================================
# Paths and tasks
# ======================================================================================

suite_dir = Path(__file__).resolve().parent
task_file = suite_dir / "task.yaml"
run_case = suite_dir / "run_case.py"
study_file = suite_dir / "study.yaml"

task_config, tasks = load_tasks(task_file)


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

    if args.N_node > platform["max_nodes"]:
        parser.error(
            f"--N_node exceeds the {platform['max_nodes']}-node limit for "
            f"{args.platform}."
        )

    account = user_platform_config.get("account")
    queue = user_platform_config.get("queue")
    reservation = user_platform_config.get("reservation")

    if account is None:
        raise ValueError(
            f"Platform '{args.platform}' requires an account. "
            "Create configs/user_config.py from configs/user_config.py.template."
        )


# ======================================================================================
# Build Maestro study
# ======================================================================================

steps = []
case_walltimes = {}
skipped_cases = []

for benchmark, case, task in tasks:
    name = f"{benchmark}/{case}"
    case_dir = case_directory(suite_dir, benchmark, case)
    input_file = case_dir / "input.py"
    N_particle = task["N_particle"]

    if not input_file.is_file():
        raise FileNotFoundError(f"Case input not found: {input_file}")

    if output_file(case_dir, N_particle).is_file():
        skipped_cases.append(name)
        print(f"Skip complete case: {name}")
        continue

    safe_name = name.replace("-", "_").replace("/", "__")
    command = f"{mcdc_python} {run_case} --benchmark {benchmark} --case {case}"
    if not local:
        command += ' --launcher "$(LAUNCHER)"'

    run = {"cmd": command}
    if not local:
        walltime = get_case_walltime(task, platform, args.walltime)
        case_walltimes[name] = walltime
        run.update(
            {
                "nodes": args.N_node,
                "walltime": walltime,
                "procs": args.N_node * cpu_cores,
                "exclusive": True,
            }
        )

    steps.append(
        {
            "name": safe_name,
            "description": f"Run SINBAD case: {name}",
            "run": run,
        }
    )

if not steps:
    print("All configured cases are complete; nothing to launch.")
    raise SystemExit(0)

study = {
    "description": {
        "name": "maestro_run",
        "description": "MC/DC validation - SINBAD suite",
    },
    "env": {"variables": {}},
    "study": steps,
}

if not local:
    batch = {"type": scheduler, "host": platform["host"], "bank": account}
    if queue is not None:
        batch["queue"] = queue
    if reservation is not None:
        batch["reservation"] = reservation
    study["batch"] = batch


# ======================================================================================
# Write and launch the study
# ======================================================================================

with study_file.open("w") as file:
    yaml.dump(study, file, sort_keys=False)

maestro_python = None if local else user_platform_config.get("maestro_python")
environment = os.environ.copy()

if maestro_python is None:
    maestro_command = ["maestro", "run", "study.yaml"]
else:
    maestro_python = Path(maestro_python).expanduser()
    environment["PATH"] = f"{maestro_python.parent}:{environment['PATH']}"
    maestro_command = [
        str(maestro_python),
        "-m",
        "maestrowf.maestro",
        "run",
        "study.yaml",
    ]

subprocess.run(maestro_command, cwd=suite_dir, check=True, env=environment)


# ======================================================================================
# Store launch metadata
# ======================================================================================

maestro_runs = sorted(
    suite_dir.glob("maestro_run_*"), key=lambda path: path.stat().st_mtime
)
if not maestro_runs:
    raise RuntimeError("Maestro did not create a maestro_run_* directory.")

latest_run = maestro_runs[-1]
launch_config = {
    "platform": args.platform,
    "scheduler": "local" if local else scheduler,
    "N_node": args.N_node,
    "N_process": 1 if local else args.N_node * cpu_cores,
    "walltime": args.walltime,
    "case_walltimes": case_walltimes,
    "mcdc_python": mcdc_python,
}

with (latest_run / "launch_config.yaml").open("w") as file:
    yaml.dump(launch_config, file, sort_keys=False)
with (latest_run / "task.yaml").open("w") as file:
    yaml.dump(task_config, file, sort_keys=False)


# ======================================================================================
# Summary
# ======================================================================================

print(f"Platform : {args.platform}")
print(f"Nodes    : {args.N_node}")
print(f"Python   : {mcdc_python}")
print(f"Study    : {study_file}")
if not local:
    print(f"Scheduler: {scheduler}")
    print(f"Account  : {account}")
    print(f"Queue    : {queue}")
    print(f"Reserv.  : {reservation}")
    print("Walltimes:")
    for name, walltime in case_walltimes.items():
        print(f"  {name}: {walltime}")
    print(f"Procs    : {args.N_node * cpu_cores}")
print(f"Cases    : {len(steps)}")
print(f"Skipped  : {len(skipped_cases)}")
