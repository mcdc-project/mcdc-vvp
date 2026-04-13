import argparse
import datetime
import importlib.metadata
import os
import shutil
import subprocess
import yaml

from pathlib import Path
from platform import (
    CPU_CORES_PER_NODE,
    MAX_TIME,
    PLATFORMS,
    JOB_SUBMISSION,
    JOB_SCHEDULER,
    JOB_TIME,
)

# ======================================================================================
# Run options
# ======================================================================================

parser = argparse.ArgumentParser(description="MC/DC Verification, Validation, and Performance Test Suite")
parser_mode = parser.add_mutually_exclusive_group(required=True)
parser_mode.add_argument("--verification", default=False, action="store_true")
parser_mode.add_argument("--validation", default=False, action="store_true")
parser_mode.add_argument("--performance", default=False, action="store_true")
parser.add_argument("--platform", type=str, required=True, choices=PLATFORMS)
parser.add_argument("--rewrite_results", default=False, action="store_true")
parser.add_argument("--save_recent_output", default=False, action="store_true")
args, unargs = parser.parse_known_args()

# Set active modes
verification = args.verification
validation = args.validation
performance = args.performance

# Set options
rewrite = args.rewrite_results

# Set platform parameters
platform = args.platform
job_submission = JOB_SUBMISSION[platform]
job_scheduler = JOB_SCHEDULER[platform]
job_time = JOB_TIME[platform]
max_time = MAX_TIME[platform]
cpus_per_node = CPU_CORES_PER_NODE[platform]

# Get the PBS template
with open("pbs_templates/%s.pbs"%job_scheduler, 'r') as f:
    pbs_template = f.read()


# =====================================================================================
# Preparation
# =====================================================================================

base_path = str(Path(".").resolve())

# Set up results folder
def make_folder(path, rewrite=False):
    if rewrite and Path(path).exists():
        shutil.rmtree(path)
    Path(path).mkdir(parents=True, exist_ok=True)
make_folder(base_path + '/results')

# Get the metadata
mcdc_version = importlib.metadata.version("mcdc")
vv_hash = (
    subprocess.check_output(
        ["git", "-C", ".", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
    )
    .decode("utf-8")
    .strip()
)

# Set the metadata yaml file
with open("results/version.yaml", "w") as f:
    metadata = {
        "mcdc-source-version": mcdc_version,
        "mcdc-vv-hash": vv_hash,
    }
    yaml.dump(metadata, f, sort_keys=False)

# =====================================================================================
# Verification
# =====================================================================================

if verification:

    # =================================================================================
    # Verification - Analytical - Neutron - Suite A
    # =================================================================================
    """
    Running the subfolder run.py script,
    on a full node, with all CPUs, allocating the maximum time
    """

    # Folder paths
    relative_path = "verification/analytical/neutron/suite_A"
    test_path = f"{base_path}/{relative_path}"
    result_path = f"{base_path}/results/{relative_path}"

    # Set up result folder
    make_folder(result_path, rewrite)

    # Into test folder
    os.chdir(test_path)

    # The commands
    commands = f"python run.py --srun {cpus_per_node}\n"
    # Move results to the result folder
    commands += f"mv results {result_path}\n"
    
    # Build the PBS file
    pbs_text = pbs_template[:]
    pbs_text = pbs_text.replace('<N_NODE>', '1')
    pbs_text = pbs_text.replace('<JOB_NAME>', 'mcdc-ver-n-A')
    pbs_text = pbs_text.replace('<TIME>', job_time.replace('XX', str(max_time)))
    pbs_text = pbs_text.replace('<CASE>', "")
    pbs_text = pbs_text.replace('<COMMANDS>', commands)
    with open(f"submit.pbs", 'w') as f:
        f.write(pbs_text)

    # Submit job
    os.system("%s submit.pbs" % job_submission)

    # Return to base
    os.chdir(base_path)
    
    # =================================================================================
    # Verification - Benchmark - Neutron - Multigroup 
    # =================================================================================
    """
    Running the each subfolder run.py script,
    on maximum number of nodes, with all CPUs, allocating the maximum time
    """

exit()
# =====================================================================================
# Validation
# =====================================================================================

if validation:
    # Set up results folder
    make_folder("results/validation/neutron", rewrite)

# =====================================================================================
# Performance
# =====================================================================================

if performance:
    # Set up results folder
    make_folder("results/performance/neutron", rewrite)
