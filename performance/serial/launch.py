"""Build and launch the MC/DC serial-performance study with Maestro."""

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
from util import case_outputs_complete, task_modes

try:
    from configs.user_config import USER_CONFIG
except ImportError:
    USER_CONFIG = {}


# ======================================================================================
# Command-line arguments
# ======================================================================================

parser = argparse.ArgumentParser(
    description="Launch the MC/DC serial-performance suite."
)
parser.add_argument("--platform", default="local", choices=["local"] + list(PLATFORMS))
parser.add_argument(
    "--walltime",
    type=float,
    default=None,
    help="Set the base walltime in hours; each mode scales it by walltime_factor.",
)
args = parser.parse_args()


# ======================================================================================
# Paths and platform settings
# ======================================================================================

suite_dir = Path(__file__).resolve().parent
task_file = suite_dir / "task.yaml"
run_case = suite_dir / "run_case.py"
study_file = suite_dir / "study.yaml"
local = args.platform == "local"
user_platform_config = USER_CONFIG.get(args.platform, {})

mcdc_python = user_platform_config.get("mcdc_python")
if mcdc_python is None:
    mcdc_python = sys.executable
else:
    mcdc_python = str(Path(mcdc_python).expanduser())

if not local:
    platform = PLATFORMS[args.platform]
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

with task_file.open("r") as stream:
    tasks = yaml.safe_load(stream)


# ======================================================================================
# Build Maestro study
# ======================================================================================

# Each case and execution mode becomes one independent Maestro step.
steps = []
case_walltimes = {}
skipped_tasks = []
for case_name, task in tasks.items():
    case_dir = suite_dir / "cases" / case_name
    input_file = case_dir / "input.py"
    if not input_file.is_file():
        raise FileNotFoundError(f"Serial-performance input not found: {input_file}")

    for mode in task_modes(task):
        step_name = f"{case_name.replace('-', '_')}_{mode}"
        if case_outputs_complete(case_dir, task, mode):
            skipped_tasks.append(step_name)
            print(f"Skip complete case and mode: {case_name}, {mode}")
            continue

        command = f"{mcdc_python} {run_case} --name {case_name} --mode {mode}"
        if not local:
            command += ' --launcher "$(LAUNCHER)"'

        run = {"cmd": command}
        if not local:
            walltime = get_case_walltime(task[mode], platform, args.walltime)
            case_walltimes[step_name] = walltime
            run.update(nodes=1, procs=1, walltime=walltime, exclusive=True)

        steps.append(
            {
                "name": step_name,
                "description": f"Run serial-performance case: {case_name}, {mode}",
                "run": run,
            }
        )

if not steps:
    print("All configured cases are complete; nothing to launch.")
    raise SystemExit(0)

study = {
    "description": {
        "name": "maestro_run",
        "description": "MC/DC serial-performance suite",
    },
    "env": {"variables": {}},
    "study": steps,
}
if not local:
    batch = {
        "type": platform["scheduler"],
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

with study_file.open("w") as stream:
    yaml.dump(study, stream, sort_keys=False)

# ======================================================================================
# Launch Maestro
# ======================================================================================

maestro_python = None if local else user_platform_config.get("maestro_python")
env = os.environ.copy()
if maestro_python is None:
    maestro_command = ["maestro", "run", "study.yaml"]
else:
    maestro_python = Path(maestro_python).expanduser()
    env["PATH"] = f"{maestro_python.parent}:{env['PATH']}"
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

# Save the effective configuration alongside the generated Maestro run.
maestro_runs = sorted(
    suite_dir.glob("maestro_run_*"), key=lambda path: path.stat().st_mtime
)
if not maestro_runs:
    raise RuntimeError("Maestro did not create a maestro_run_* directory.")
latest_run = maestro_runs[-1]

launch_config = {
    "platform": args.platform,
    "scheduler": "local" if local else platform["scheduler"],
    "N_node": 1,
    "N_process": 1,
    "walltime": args.walltime,
    "case_walltimes": case_walltimes,
    "mcdc_python": mcdc_python,
}
with (latest_run / "launch_config.yaml").open("w") as stream:
    yaml.dump(launch_config, stream, sort_keys=False)
with task_file.open("r") as stream:
    task_config = yaml.safe_load(stream)
with (latest_run / "task.yaml").open("w") as stream:
    yaml.dump(task_config, stream, sort_keys=False)

# ======================================================================================
# Summary
# ======================================================================================

print(f"Platform : {args.platform}")
print("Nodes    : 1")
print("Procs    : 1")
print(f"Python   : {mcdc_python}")
print(f"Jobs     : {len(steps)} (one per case and mode)")
print(f"Skipped  : {len(skipped_tasks)}")
print(f"Study    : {study_file}")

if not local:
    print(f"Scheduler: {platform['scheduler']}")
    print(f"Account  : {account}")
    print(f"Queue    : {queue}")
    print(f"Reserv.  : {reservation}")
    print("Exclusive: True")
    print("Walltimes:")
    for case_name, walltime in case_walltimes.items():
        print(f"  {case_name}: {walltime}")
