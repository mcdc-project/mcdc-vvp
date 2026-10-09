# SINBAD validation

This suite compares MC/DC neutron-transport calculations with experimental benchmark quantities from the OECD/NEA Shielding Integral Benchmark Archive and Database (SINBAD). It currently includes only cases for which MC/DC can calculate the benchmark observable directly: the OKTAVIAN Si-60 neutron-leakage spectrum and the four FNG/TUD SiC neutron spectra. Models that still require response-function or coupled neutron-photon capabilities are not part of the executable suite.

The repository contains the MC/DC models and processing scripts but does not redistribute the licensed SINBAD packages. The official packages are required only when processing comparisons that read their experimental tables.

The suite uses the same Maestro-based workflow as the code-to-code verification suite. Each configured benchmark case is an independent task, and its particle count is the number of source particles per batch. The batch count remains defined by the case input.

## Directory layout

```text
oktavian-si-60/        OKTAVIAN silicon-pile leakage experiments
fng-tud-sic/           FNG/TUD SiC spectral measurements at P1-P4

task.yaml              Configured benchmark cases and particle counts
study.yaml             Generated Maestro study definition
maestro_run_*/         Generated Maestro workflow directories
results/               Processed figures and launch metadata

launch.py              Build and launch the suite
run_case.py            Execute one configured case
process.py             Plot and collect completed results
cleanup.py             Remove generated outputs and workflow products
util.py                Shared task and SINBAD-package helpers
```

Each runnable case directory contains an `input.py` and `plot.py`. Benchmark-level READMEs describe the experiment, model, quantity of interest, limitations, and references.

## Task configuration

`task.yaml` is a nested mapping from benchmark directory to case directory. Each case specifies its number of source particles per batch and its multiplier on the launch-level base walltime:

```yaml
oktavian-si-60:
  neutron_leakage:
    N_particle: 1_000_000_000
    walltime_factor: 0.34

fng-tud-sic:
  p1:
    N_particle: 1_000_000_000
    walltime_factor: 0.01
  p2:
    N_particle: 1_000_000_000
    walltime_factor: 0.00875
  p3:
    N_particle: 1_000_000_000
    walltime_factor: 0.00875
  p4:
    N_particle: 1_000_000_000
    walltime_factor: 0.00875
```

Only cases with a directly calculable benchmark observable should be enabled. The current task file contains the five neutron-spectrum cases supported by this suite.

Outputs are named `output_<N_particle>.h5`. A case is skipped when its expected output already exists, allowing interrupted studies to resume without repeating completed calculations.

## Launching

From this directory, launch locally with the active Python environment:

```bash
python launch.py
```

Launch on a configured HPC platform with:

```bash
python launch.py --platform dane --N_node 10 --walltime 24
```

`N_node` is the number of nodes assigned to every case in that launch, with all configured CPU cores used on each node. `walltime` is the base duration in hours; each case receives `walltime * walltime_factor`, rounded up to the scheduler resolution and limited by the platform maximum. Local execution requires one node and ignores walltime.

With the configured 24-hour base walltime, the factors above request 8 hours 9 minutes 36 seconds for OKTAVIAN, 14 minutes 24 seconds for FNG/TUD P1, and 12 minutes 37 seconds for FNG/TUD P2-P4. These values are calibrated for the 10-node Dane configuration and include at least a 50% buffer above the observed run time for every case.

The platform and user settings come from `configs/platform_config.py` and `configs/user_config.py`. The effective node count, base walltime, scaled case walltimes, process count, platform, and Python executable are recorded in each Maestro run's `launch_config.yaml`. The selected MC/DC environment must be able to locate the required native nuclear-data library.

To enable this suite through the repository-level launcher and processor, add its entry from `configs/launch_config.py.template` to the local `configs/launch_config.py` and set `sinbad_root` to the local SINBAD repository directory.

## Processing

After the Maestro study completes, provide the directory containing the locally available SINBAD repositories:

```bash
python process.py /path/to/sinbad
```

To process a particular study instead of the latest one:

```bash
python process.py /path/to/sinbad maestro_run_<timestamp>
```

The processor resolves each official package below the supplied root, runs the corresponding case plot script, and stores figures under `results/<benchmark>/<case>/`. It also preserves the effective launch and task configurations in `results/`.

Use `python cleanup.py` to remove simulation outputs and generated figures from the configured cases, along with processed results, Maestro run directories, and `study.yaml`. Incomplete benchmark models outside `task.yaml` are left untouched.

## Benchmarks

| Benchmark | Cases | Quantity of interest |
| :--- | :--- | :--- |
| [OKTAVIAN Si-60](oktavian-si-60/) | `neutron_leakage` | Neutron leakage spectrum from 3.0288 to 13.574 MeV |
| [FNG/TUD SiC](fng-tud-sic/) | `p1`, `p2`, `p3`, `p4` | Neutron flux spectrum from 0.999 to 15.22 MeV at four measurement depths |
