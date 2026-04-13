import argparse
import datetime
import importlib.metadata
import os
import shutil
import subprocess
import yaml

# =====================================================================================
# Generate metadata
# =====================================================================================

# Get the metadata
mcdc_version = importlib.metadata.version("mcdc")
vv_hash = (
    subprocess.check_output(
        ["git", "-C", ".", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
    )
    .decode("utf-8")
    .strip()
)
date = datetime.datetime.now().isoformat()

# Set the yaml file
with open("results/version.yaml", "w") as f:
    metadata = {
        "mcdc-source-version": mcdc_version,
        "mcdc-vv-hash": vv_hash,
        "date": date,
    }
    yaml.dump(metadata, f, sort_keys=False)

# =====================================================================================
# Setup
# =====================================================================================

# Option parser
parser = argparse.ArgumentParser(description="MC/DC Verification - Analytical")
parser.add_argument("--srun", type=int, default=0)
parser.add_argument("--mpiexec", type=int, default=0)
parser.add_argument("--mpirun", type=int, default=0)
args, unargs = parser.parse_known_args()

# Get the MPI option
mpi_option = ""
if args.srun > 0 or args.mpiexec > 0 or args.mpirun > 0:
    if args.srun > 1:
        mpi_option = f"--srun {args.srun}"
    elif args.mpiexec > 1:
        mpi_option = f"--mpiexec {args.mpiexec}"
    elif args.mpirun > 1:
        mpi_option = f"--mpirun {args.mpirun}"

# Set up results folder
if os.path.exists("results"):
    shutil.rmtree("results")
os.makedirs("results")
os.makedirs("results/verification/analytical/neutron/")

# Into the analytical verification subfolder
os.chdir("verification/analytical")

# =====================================================================================
# Neutron
# =====================================================================================

os.chdir("neutron")

# =======
# Suite A
# =======

os.chdir("suite_A")

# Run
os.system(f"python run.py {mpi_option}")

# Move results to top folder
os.system("mv results ../../../../results/verification/analytical/neutron/suite_A")

os.chdir("..")
os.chdir("..")
os.chdir("../..")
