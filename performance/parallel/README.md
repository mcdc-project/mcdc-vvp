# Parallel Performance

This suite compares total runtime, tracking rate, precision, precision rate, and figure of merit across platforms and transport methods in Numba mode.
The detailed Performance envelope provides context for the Performance level + scaling evidence summary.

## Directory layout

```text
cases/<case>/
  input.py                         Model definition
  outputs/<platform>/
    output_<platform>_n004_m16.h5   Full tally output for one matrix point
workspaces/<platform>/<task>_*/    Isolated per-launch working directories and caches
maestro_run_<platform>_*/          Maestro records and saved launch/task configuration
results/
  studies/                         Copies of the processed study configurations
  <comparison>/                    Measured records, summary records, and figures

task.yaml                          Case definitions and baseline particle counts
study_<platform>.yaml              Generated, untracked Maestro study
launch.py                          Build and launch a platform's study
run_case.py                        Execute one matrix point
process.py                         Combine completed platform studies
plotting.py                        Draw curves and interpolate summary workloads
util.py                            Shared task and resource definitions
cleanup.py                         Remove generated outputs and results
```

## Configuration

Each entry in `task.yaml` identifies `cases/<case>/input.py` and its baseline particles per batch.
Keep the batch count and physical problem fixed while calibrating the baseline for approximately one hour on one full node, including full tally output.

```yaml
kobayashi-detector:
  method: Analog
  N_particle_base: 30_000_000
```

A scalar baseline applies to every platform.
Alternatively, provide a mapping under `N_particle_base` with a separately calibrated positive integer for each selected platform, such as `dane` and `tuolumne`.
Missing platform baselines raise an error rather than silently using another platform's calibration.
The checked-in baseline is not a separate GPU calibration.
The case input determines `N_batch` and defines its multigroup materials directly, so the current case needs no external data directory.
For future cases with external data, resolve paths relative to `__file__` or use absolute paths because simulations run from isolated working directories.

The matrix uses node counts `1, 2, 4, 8, 16, 32, 64` through `N_node_max`, and workload multipliers `1, 2, 4, 8, 16`.
Particles per batch are `N_particle_base * N_node * multiplier`.
Each point is an independent job with exclusive node allocation and requested walltime of `1.5 * multiplier` hours, capped by the platform limit.
Thus the nominal walltimes are `1.5, 3, 6, 12, 24` hours, including a 50% calibration buffer.
Dane uses one MPI rank per CPU core; Tuolumne and other configured GPU platforms use one rank per GPU, `--target=gpu`, and `--gpu_state_storage=united`.
GPU runs do not attempt to occupy all CPU cores.
Compilation remains part of total runtime and caching is not enabled by this suite.

The top-level launch configuration accepts either one platform or a list for this suite:

```python
"performance/parallel": {
    "enabled": True,
    "platform": ["dane", "tuolumne"],
    "N_node_max": 64,
},
```

On each target machine, run the top-level launcher with that machine's `--platform` value.
The list selects compatible hosts; it does not submit to another machine remotely.
Platform lists are not enabled for the serial or verification suites, whose outputs do not yet have this isolation.
Use `configs/platform_config.py` for hardware/scheduler settings and `configs/user_config.py` for accounts, queues, reservations, and interpreter paths.
On Tuolumne, load the required ROCm environment and invoke the launcher through `flux env` when needed by the configured Python/Flux installation.

### Comparing methods

Separate case inputs can join one comparison by declaring the same `comparison` label and different `method` labels in `task.yaml`.
For example, analog and weight-window case entries can both use `comparison: kobayashi-detector` with `method: Analog` and `method: Weight windows`, respectively.
Without these fields, the comparison defaults to the case name and the method label to `Numba`.
Only group equivalent physical observables, tally grids, normalization conventions, and batch counts.
Adding a case requires only its input and task entry, not a case-specific launcher or processor.

## Launching

From this suite, preview the study without submitting jobs:

```console
python launch.py --platform dane --N_node_max 64 --dry_run
python launch.py --platform tuolumne --N_node_max 64 --dry_run
```

Omit `--dry_run` to submit on the selected machine.
Matching completed outputs are skipped; a different baseline or rank count in an existing output raises an error and requires moving that output aside.
Platform names appear in output directories, filenames, task names, study files, Maestro directories, and workspace paths, preventing Dane and Tuolumne from overwriting each other's runs.
For example, `cases/kobayashi-detector/outputs/tuolumne/output_tuolumne_n004_m16.h5` contains a four-node run with `N_particle = N_particle_base * 4 * 16` per batch.
Each invocation, including retries, gets a unique workspace and `NUMBA_CACHE_DIR` on the shared filesystem.
Every MPI rank of that job shares the workspace; all allocated nodes must be able to access it.
The input stays in its case directory and HDF5 output is written directly to its absolute platform-specific path, with no move-back step.
Workspaces are retained for inspection until cleanup.

## Processing

Bring the platform output directories and saved Maestro configuration directories together under one suite directory before processing results collected on different filesystems.
Without arguments, the processor combines the latest saved study for each available platform:

```console
python process.py
```

To compare explicitly selected campaigns, pass their saved directories:

```console
python process.py maestro_run_dane_<timestamp> maestro_run_tuolumne_<timestamp>
```

Selection uses saved configurations, not the currently edited `task.yaml`.
Missing matrix points are reported and skipped; duplicate selected outputs are rejected.
Existing flat outputs such as `output_n004_m16.h5` remain readable through an explicitly identifying legacy saved study, but new launches never reuse or overwrite them.
Outputs without full tally results are rejected.
Changing a baseline requires keeping its old outputs and saved metadata together in a separate campaign copy; filenames distinguish platform, nodes, and multiplier, not arbitrary campaign revisions.

Each comparison produces:

| File | Content |
| :--- | :--- |
| `records.csv` | Measured metrics, platform/method, source paths, and reference provenance |
| `runtime.png` | Total runtime versus total histories |
| `tracking_rate.png` | Tracking rate per node versus total histories |
| `precision.png` | Precision versus total histories |
| `precision_rate.png` | Precision per history versus total histories |
| `fom.png` | FOM per node versus total histories |
| `performance_envelope.png` | Tracking rate and FOM per node, logarithmic histories and linear vertical axes |
| `scaling_summary.png` | Performance level + scaling evidence, with touching bars around M |
| `scaling_summary.csv` | Summary targets, measured/interpolated values, brackets, source paths, and reference |

The summary replaces separate strong- and weak-scaling efficiency plots.
Colors identify platform/method combinations and line styles identify node counts in the detailed curves.
All measured points remain in the envelope, including workloads beyond the summary's shared range.
If there is no common range, the summary figure explains the missing overlap and no summary CSV is generated.

### Metrics and reference

Use measured total runtime $T$ in seconds from `performance/runtime`, total histories $N$ from `performance/N_history`, and allocated nodes $P$.
No compilation-time adjustment is applied.
Within each comparison, choose one reference from the largest available total-history result across all platforms and methods, preferring fewer nodes on ties and then using deterministic platform/method/case ordering.
Every run uses that reference's fixed nonzero-mean bin mask.
The maximum fractional relative variance is $V=\max_{i:\mu_{i,\mathrm{ref}}\ne0}(s_i/\mu_{i,\mathrm{ref}})^2$, with the current run's standard error $s_i$.
The shared implementation in `../metrics.py` validates tally scores, grids, and shapes.
Batch counts must match within a comparison, and rank counts must match each study's saved CPU or GPU resource layout.

| Metric | Definition | Unit |
| :--- | :--- | :--- |
| Tracking rate per node | $R=N/(PT)$ | histories/s/node |
| Precision | $Q=10^{-4}/V$ | $\%^{-2}$ |
| Precision rate | $q=Q/N$ | $\%^{-2}$/history |
| FOM per node | $F=Q/(PT)=Rq$ | $\%^{-2}$/s/node |

Precision and precision rate are not divided by node count.
The measured CSV also retains whole-job tracking rate and FOM, raw `effective_variance`, fractional maximum relative variance, the reference path and history count, contributing-bin count, and runtime components.
Invalid or zero variance produces unavailable precision metrics, not infinite bars; timing metrics remain usable.
FOM comparisons reflect both timing and statistical efficiency, and are not pure scaling efficiencies.

### Main bar and wings

Each platform/method group uses its largest available node count for M and its right wing.
Choose the largest common histories-per-node value covered by every included curve, including the smaller-node curves on the left.
M uses that common value, which can be below a group's largest measured workload and need not give the tallest bar.
Moving left away from M reduces nodes at fixed histories per node: a direct weak-scaling comparison.
Moving right reduces histories per node at fixed nodes: workload sensitivity, providing indirect strong-scaling evidence without measuring additional node-dependent communication costs.
All groups use the same rightward reduction factor and workload targets.
By default, attempt four right-wing steps with a factor of four, stopping earlier for every group if any would require extrapolation.
Adjust this with `--workload_factor 2 --workload_steps 4` to match a five-point factor-two matrix when common coverage permits.
If main/left workloads have no common range, collect overlap data or explicitly select compatible studies rather than extrapolating.

Exact measurements are preferred; otherwise interpolate total runtime and precision separately, linearly between adjacent measured histories, then derive rates and FOM.
Hatching identifies interpolated bars, and the summary CSV records the bracket endpoints and files.
Invalid precision endpoints are not bridged; the corresponding FOM bar is marked unavailable.
Sparse interpolation is an approximation, so inspect the recorded brackets and collect more points when a conclusion depends on a wide interval.
The envelope indicates whether M reaches a plateau; the summary does not automatically claim asymptotic or ultimate performance.

## Cleanup

After all jobs have stopped, run `python cleanup.py` to remove generated outputs for every platform, workspaces and caches, Maestro records, processed results, and generated study files.
Inputs and `task.yaml` are preserved.
Study files are untracked and regenerated by the launcher.

## Cases

| Case | Description |
| :--- | :--- |
| [`kobayashi-detector`](cases/kobayashi-detector/) | Transient Kobayashi dog-leg problem with a fuel cube and detector capture tally. |
