# MC/DC-VVP

![MC/DC logo](https://raw.githubusercontent.com/mcdc-project/mcdc/main/assets/mcdc-logo.svg)

[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

A collection of verification, validation, and performance (VVP) test suites for [MC/DC](https://github.com/mcdc-project/mcdc).

The repository provides a unified framework for launching, processing, and organizing MC/DC-VVP campaigns on local workstations and HPC platforms.
Each suite is self-contained and can be executed independently, while the top-level workflow enables reproducible campaign-wide execution.
Workflow orchestration is performed using [Maestro](https://github.com/llnl/maestrowf).

## Directory layout

```text
configs/               Shared platform, user, and launch configurations
verification/          Verification suites and their cases
validation/            Validation suites and their cases
performance/           Performance test suites and their cases
results/               Processed results organized by suite
release/               Flattened figures prepared as release assets

launch.py              Launch all enabled suites
process.py             Process suites and collect their results
cleanup.py             Remove generated outputs and processed results
prepare_release.py     Prepare figures for a GitHub release
```

MC/DC-VVP uses **suite**, **case**, and **task** as standard terms for its organizational hierarchy:

```text
suite
└── case
    └── task
```

- A **suite** is a self-contained collection of related VVP cases with a shared launch and processing workflow.
- A **case** is one individual problem definition and its inputs, reference solution or data, and processing logic.
- A **task** is one execution of a case at one sampling level, such as one `N_particle` or `N_active` value.

A suite contains cases, and each case generates one or more tasks from the suite's `task.yaml` configuration.
Maestro currently represents each case as one workflow step, and `run_case.py` executes that case's tasks sequentially.
The hierarchy also defines restart behavior: an existing output skips its task, a case with all task outputs is omitted, and a suite with all cases complete does not launch.
Every integrated suite provides a README that describes its layout, configuration, workflow, and cases.

## Adding content

To add a case, create its directory under the appropriate suite's `cases/`, implement the common files described in the suite README, and register its task sequence in the suite's `task.yaml`.
Place data shared by multiple cases in the suite's `data/` directory when appropriate.
A new suite should provide its own README, `launch.py`, `process.py`, and `cleanup.py`, then be registered in `configs/launch_config.py.template`.

## Configurations

### Launch configuration

Create the local launch configuration:

```bash
cp configs/launch_config.py.template configs/launch_config.py
```

Edit `configs/launch_config.py` to enable the desired suites and set their platform and launch options.
Use `platform=None` for local execution or a name from `configs/platform_config.py` for HPC execution.
For HPC execution, `N_node` sets the number of nodes and each node uses all available CPU cores.
The parallel-performance suite instead uses `N_node_max` to generate every power-of-two node count through that value.
It accepts a platform list such as `"platform": ["dane", "tuolumne"]`, isolates each platform's outputs, and uses all GPUs on GPU-equipped platforms or all CPU cores on CPU-only platforms.
For HPC execution, a suite's base `walltime` in hours is scaled by each case's `walltime_factor` in that suite's `task.yaml`.
The scaled value is rounded up to the scheduler's supported resolution, the platform maximum remains the final limit, and local execution ignores walltime settings.
Run the top-level `python cleanup.py` before launching when the entire configured campaign should start fresh.

### User configuration

For HPC execution, also create `configs/user_config.py` from its template and provide the account and optional queue, reservation, and Python paths for the target platform.

## Launching and processing

### Launching suites

Launch locally enabled suites configured with `platform=None`:

```bash
python launch.py
```

Launch enabled suites configured for a specific HPC platform:

```bash
python launch.py --platform tuolumne
```

The `--platform` option selects suites with a matching configured platform.
For parallel performance, it selects membership in the configured platform list; run the command separately on each target machine rather than submitting remotely.

### Processing results

Process registered suites and collect their results:

```bash
python process.py
```

For each suite registered in `configs/launch_config.py`, the top-level processor invokes the suite processor when a Maestro run is available and then moves the generated `results/` directory under the same suite path in the top-level `results/` directory.
An existing suite `results/` directory can still be collected when no Maestro run is present, and suites with neither are skipped.
The SINBAD suite additionally requires `sinbad_root` in `configs/launch_config.py` so its processor can read the locally available licensed experimental tables.
Within each suite, `convergence/` contains study-wide convergence figures and `comparison/` contains plots or animations from the largest-statistics result.
These directories apply to verification; parallel performance instead combines the latest saved study per platform under `results/<comparison>/`, as described in its suite README.
Collecting a suite results replaces that suite's existing top-level ones.

### Preparing release assets

Prepare the collected PNG and GIF figures for upload as GitHub release assets:

```bash
python prepare_release.py
```

The script recreates `release/`, copies every figure from `results/`, and replaces each directory boundary in its relative path with `--` to form a unique flat asset name.
The structured files in `results/` are not modified.

Remove generated case outputs and processed results from every registered suite:

```bash
python cleanup.py
```

Cleanup removes Maestro run directories and retains reference data.

## Suites

### Verification

#### Analytical verification

Analytical verification demonstrates the expected statistical convergence of MC/DC by comparing numerical solutions against analytical and semi-analytical reference solutions as the sampling effort is increased.

| Physics | Suite | Description |
| :------ | :---- | :---------- |
| Neutron transport | [Fixed-source](verification/analytical/neutron/fixed_source/README.md) | Multigroup steady-state and transient cases, including a two-group manufactured solution, Reed's problem, AZURV1 variants, and infinite SHEM-361 benchmarks. |
| Neutron transport | [k-eigenvalue](verification/analytical/neutron/k_eigenvalue/README.md) | Homogeneous and Kornreich-Parsons one-group slab benchmarks, plus infinite homogeneous SHEM-361 cases. |

#### Code-to-code verification

Code-to-code verification assesses whether relative differences among independently implemented transport codes decrease at the expected statistical rate as their sampling effort increases.
Convergence proportional to $N^{-1/2}$ supports that the participating codes are approaching the same solution at the expected Monte Carlo rate, although agreement alone cannot exclude shared bias.
The arithmetic mean of all participating code estimates at the largest sampling level defines a fixed comparison reference for every level, allowing a case to include two or more codes without designating one as exact.

| Physics | Suite | Description |
| :------ | :---- | :---------- |
| Neutron transport | [Code-to-code](verification/code_to_code/neutron/README.md) | Time-dependent C5G7 and Kobayashi comparisons among participating codes. |

### Validation

Validation suites compare MC/DC predictions against experimental measurements.

| Physics | Suite | Description |
| :------ | :---- | :---------- |
| Neutron shielding | [SINBAD](validation/sinbad/README.md) | Experimental neutron leakage and flux spectra for the OKTAVIAN Si-60 and FNG/TUD SiC assemblies. |

### Performance

The performance suites evaluate computational performance, scalability, and efficiency across supported execution platforms.
Total histories $N$, total runtime $T$ [s], and maximum relative variance $V$ [$\%^2$], expressed in percent squared and calculated using the largest-history result as the reference, are used to derive the performance metrics:

- Tracking rate $N/T$: histories processed per second [histories/s].
- Precision $1/V$: inverse maximum relative variance [$\%^{-2}$].
- Precision rate $1/(VN)$: precision gained per history [$\%^{-2}$/history].
- Figure of merit (FOM) $1/(TV)$: precision gained per second, equal to the product of tracking rate and precision rate [$\%^{-2}$/s].

For parallel runs on $P$ nodes, tracking rate and FOM are reported per node as $N/(PT)$ and $1/(PTV)$, respectively.

| Suite | Description |
| :---- | :---------- |
| [Serial](performance/serial/README.md) | Single-process Python and Numba studies. |
| [Parallel](performance/parallel/README.md) | Full-node Numba strong- and weak-scaling studies. |

Parallel results pair a detailed **Performance envelope** with a **Performance level + scaling evidence** summary at common histories-per-node workloads.
The summary compares weak scaling to the left of its main bar and workload sensitivity, as indirect strong-scaling evidence, to its right.
Interpolation is marked and restricted to measured ranges; the envelope indicates whether the selected level is near saturation.

## Documentation

This README and the suite READMEs describe how to configure, run, and process VVP campaigns.
The [VVP section of the MC/DC documentation](https://mcdc.readthedocs.io/en/dev/project/vvp/index.html) presents problem definitions, reference solutions, and published campaign results.
