"""Build and launch the MC/DC parallel-performance study with Maestro."""

import argparse
import os
import shlex
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
from util import (
    NODE_COUNTS,
    WALLTIME_BASE_HOURS,
    case_directory,
    platform_resources,
    task_output_complete,
    performance_tasks,
)

try:
    from configs.user_config import USER_CONFIG
except ImportError:
    USER_CONFIG = {}


# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(
    description="Launch the MC/DC parallel-performance suite."
)
parser.add_argument("--platform", choices=PLATFORMS, default="dane")
parser.add_argument(
    "--N_node_max",
    type=int,
    choices=NODE_COUNTS,
    default=64,
    help="Largest power-of-two node count to include.",
)
parser.add_argument(
    "--dry_run",
    action="store_true",
    help="Write the platform-specific study file without submitting it.",
)
args = parser.parse_args()


# ======================================================================================
# Paths and platform settings
# ======================================================================================

suite_dir = Path(__file__).resolve().parent
task_file = suite_dir / "task.yaml"
run_case = suite_dir / "run_case.py"
study_file = suite_dir / f"study_{args.platform}.yaml"
platform = PLATFORMS[args.platform]
resources = platform_resources(args.platform)
user_platform_config = USER_CONFIG.get(args.platform, {})

if args.N_node_max > platform["max_nodes"]:
    parser.error(
        f"--N_node_max exceeds the {platform['max_nodes']}-node limit for "
        f"{args.platform}."
    )

mcdc_python = user_platform_config.get("mcdc_python")
if mcdc_python is None:
    mcdc_python = sys.executable
else:
    mcdc_python = str(Path(mcdc_python).expanduser())

account = user_platform_config.get("account")
if account is None and not args.dry_run:
    raise ValueError(
        f"Platform '{args.platform}' requires an account. Create configs/user_config.py "
        "from configs/user_config.py.template."
    )
if account is None:
    account = "UNCONFIGURED"

# ======================================================================================
# Load tasks
# ======================================================================================

with task_file.open("r") as stream:
    task_config = yaml.safe_load(stream)
tasks = performance_tasks(task_config, args.N_node_max, args.platform)


# ======================================================================================
# Build Maestro study
# ======================================================================================

# Each case or matrix point becomes one independent Maestro step.
steps = []
skipped_tasks = []
case_walltimes = {}
cpu_cores = platform["cpu_cores_per_node"]

for task in tasks:
    case_dir = case_directory(suite_dir, task)
    input_file = case_dir / "input.py"
    if not input_file.is_file():
        raise FileNotFoundError(f"Performance input not found: {input_file}")
    if task_output_complete(suite_dir, task):
        skipped_tasks.append(task["name"])
        print(f"Skip complete task: {task['name']}")
        continue

    walltime = get_case_walltime(
        {"walltime_factor": task["workload_multiplier"]},
        platform,
        WALLTIME_BASE_HOURS,
    )
    case_walltimes[task["name"]] = walltime
    command = (
        f"{shlex.quote(mcdc_python)} {shlex.quote(str(run_case))} "
        f"--name {shlex.quote(task['case'])} "
        f"--platform {args.platform} "
        f"--nodes {task['N_node']} "
        f"--multiplier {task['workload_multiplier']} "
        f"--N_particle_base {task['N_particle_base']} "
        '--launcher "$(LAUNCHER)"'
    )
    steps.append(
        {
            "name": task["name"],
            "description": (
                f"{task['case']}: {task['N_node']} nodes, "
                f"workload multiplier {task['workload_multiplier']}"
            ),
            "run": {
                "cmd": command,
                "nodes": task["N_node"],
                "procs": task["N_node"] * resources["ranks_per_node"],
                "walltime": walltime,
                "exclusive": True,
            },
        }
    )
    if resources["target"] == "gpu":
        run = steps[-1]["run"]
        run["gpus"] = 1
        if platform["scheduler"] == "flux":
            # Exclusive allocation reserves whole nodes. A nonexclusive inner
            # launcher preserves Flux's explicit one-GPU-per-rank binding.
            run["exclusive"] = {"allocation": True, "launcher": False}
        elif platform["scheduler"] == "lsf":
            run.update(
                {
                    "rs per node": resources["ranks_per_node"],
                    "tasks per rs": 1,
                    "cpus per rs": 1,
                }
            )

study = {
    "description": {
        "name": f"maestro_run_{args.platform}",
        "description": "MC/DC parallel-performance scaling study",
    },
    "env": {"variables": {}},
    "batch": {
        "type": platform["scheduler"],
        "host": platform["host"],
        "bank": account,
    },
    "study": steps,
}
queue = user_platform_config.get("queue")
reservation = user_platform_config.get("reservation")
if queue is not None:
    study["batch"]["queue"] = queue
if reservation is not None:
    study["batch"]["reservation"] = reservation

# ======================================================================================
# Write Maestro study
# ======================================================================================

with study_file.open("w") as stream:
    yaml.dump(study, stream, sort_keys=False)

# ======================================================================================
# Summary
# ======================================================================================

print(f"Platform : {args.platform}")
print(f"Nodes    : 1 through {args.N_node_max} (powers of two)")
print(f"Target   : {resources['target']}")
print(f"Procs    : {resources['ranks_per_node']} per node")
print(f"GPUs     : {resources['gpus_per_node']} per node")
print(f"Tasks    : {len(steps)}")
print(f"Skipped  : {len(skipped_tasks)}")
print(f"Study    : {study_file}")
print(f"Python   : {mcdc_python}")
print(f"Scheduler: {platform['scheduler']}")
print(f"Account  : {account}")
print(f"Queue    : {queue}")
print(f"Reserv.  : {reservation}")
print("Exclusive: True")
print("Walltimes:")
for task_name, walltime in case_walltimes.items():
    print(f"  {task_name}: {walltime}")

if args.dry_run or not steps:
    raise SystemExit(0)

# ======================================================================================
# Launch Maestro
# ======================================================================================

maestro_python = user_platform_config.get("maestro_python")
env = os.environ.copy()
if maestro_python is None:
    maestro_command = ["maestro", "run", study_file.name]
else:
    maestro_python = Path(maestro_python).expanduser()
    env["PATH"] = f"{maestro_python.parent}:{env['PATH']}"
    maestro_command = [
        str(maestro_python),
        "-m",
        "maestrowf.maestro",
        "run",
        study_file.name,
    ]
subprocess.run(maestro_command, cwd=suite_dir, check=True, env=env)

# ======================================================================================
# Store launch metadata
# ======================================================================================

# Save the effective configuration alongside the generated Maestro run.
maestro_runs = sorted(
    suite_dir.glob(f"maestro_run_{args.platform}_*"),
    key=lambda path: path.stat().st_mtime,
)
if not maestro_runs:
    raise RuntimeError("Maestro did not create a maestro_run_* directory.")

launch_config = {
    "platform": args.platform,
    "scheduler": platform["scheduler"],
    "N_node_max": args.N_node_max,
    "cpu_cores_per_node": cpu_cores,
    **resources,
    "output_layout": 2,
    "walltime_base_hours": WALLTIME_BASE_HOURS,
    "task_walltimes": case_walltimes,
    "mcdc_python": mcdc_python,
}
latest_run = maestro_runs[-1]
with (latest_run / "launch_config.yaml").open("w") as stream:
    yaml.dump(launch_config, stream, sort_keys=False)
with (latest_run / "task.yaml").open("w") as stream:
    yaml.dump(task_config, stream, sort_keys=False)
