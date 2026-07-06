import argparse
from pathlib import Path

import yaml

from platform_config import PLATFORMS


parser = argparse.ArgumentParser(
    description="Generate a MaestroWF study.yaml for MC/DC VVP."
)
parser.add_argument("--task-file", default="task.yaml")
parser.add_argument("--output", default="study.yaml")
parser.add_argument(
    "--platform",
    default="local",
    choices=["local"] + list(PLATFORMS.keys()),
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

if args.mpi and args.platform == "local":
    parser.error(
        "--mpi requires a cluster platform. "
        "Specify --platform <platform>."
    )

suite_dir = Path(__file__).resolve().parent
task_file = suite_dir / args.task_file
output_file = suite_dir / args.output

local = args.platform == "local"

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

with task_file.open("r") as f:
    tasks = yaml.safe_load(f)


steps = []

for case_name in tasks:
    safe_case_name = case_name.replace("-", "_")

    command = f"python ../../run_case.py --name {case_name}"

    if args.mpi:
        command += ' --mpi "$(LAUNCHER)"'

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
        "description": "MC/DC verification - analytical neutron - fixed source",
    },
    "env": {
        "variables": {},
    },
    "study": steps,
}

if not local:
    study["batch"] = {
        "type": scheduler,
    }


with output_file.open("w") as f:
    yaml.dump(study, f, sort_keys=False)


print(f"Wrote {output_file}")
print(f"Platform : {args.platform}")
print(f"MPI      : {args.mpi}")

if not local:
    print(f"Scheduler: {scheduler}")
    print(f"Walltime : {walltime}")
    print(f"Nodes    : 1")
    print(f"Procs    : {cpu_cores if args.mpi else 1}")

print(f"Cases    : {len(steps)}")
