"""Run one point in a parallel-performance scaling matrix."""

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from util import (
    case_directory,
    output_directory,
    output_name,
    performance_task,
    platform_resources,
    task_output_complete,
)
from configs.platform_config import PLATFORMS

parser = argparse.ArgumentParser()
parser.add_argument("--name", required=True)
parser.add_argument("--nodes", type=int, required=True)
parser.add_argument("--multiplier", type=int, required=True)
parser.add_argument("--N_particle_base", type=int, required=True)
parser.add_argument("--launcher", default="")
parser.add_argument("--platform", choices=PLATFORMS, required=True)
args = parser.parse_args()

suite_dir = Path(__file__).resolve().parent
task = performance_task(
    args.name,
    args.N_particle_base,
    args.nodes,
    args.multiplier,
    args.platform,
)
case_dir = case_directory(suite_dir, task)
input_file = case_dir / "input.py"
output = output_name(task)
output_dir = output_directory(suite_dir, task)

if not input_file.is_file():
    raise FileNotFoundError(input_file)

if task_output_complete(suite_dir, task):
    print(f"Skip complete task: {task['name']}")
    raise SystemExit(0)

# Keep each launch's caches separate, including retries of the same matrix point.
# Use the shared suite filesystem so every MPI rank can load rank zero's artifacts.
output_dir.mkdir(parents=True, exist_ok=True)
workspaces_dir = suite_dir / "workspaces" / args.platform
workspaces_dir.mkdir(parents=True, exist_ok=True)
work_dir = Path(tempfile.mkdtemp(prefix=f"{task['name']}_", dir=workspaces_dir))
env = os.environ.copy()
env["NUMBA_CACHE_DIR"] = str(work_dir / "__numba_cache__")

command = [
    *shlex.split(args.launcher),
    sys.executable,
    str(input_file),
    "--mode=numba",
    f"--N_particle={task['N_particle']}",
    f"--output={output_dir / output}",
    "--no-progress_bar",
]
resources = platform_resources(args.platform)
command.append(f"--target={resources['target']}")
if resources["target"] == "gpu":
    command.append("--gpu_state_storage=united")

print("=" * 80)
print(f"Task                : {task['name']}")
print(f"Platform / target   : {args.platform} / {resources['target']}")
print(f"Nodes               : {task['N_node']}")
print(f"Workload multiplier : {task['workload_multiplier']}")
print(f"Particles per batch : {task['N_particle']}")
print(f"Working directory   : {work_dir}")
print(f"Command             : {shlex.join(command)}")
print("=" * 80)
subprocess.run(command, cwd=work_dir, env=env, check=True)
