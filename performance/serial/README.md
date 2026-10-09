# Serial Performance

This suite measures MC/DC runtime, tracking rate, precision, precision rate, and figure of merit in the configured Numba and/or Python modes, using one process per job.
It can run locally or on one exclusive cluster node through the top-level MC/DC-VVP workflow.

## Directory layout

```text
cases/              Serial performance case definitions
  <case>/
    input.py         Define and run one MC/DC model
    output_*.h5      Generated outputs including full tally results
data/               Shared multigroup cross-section data
maestro_run_*/      Generated Maestro workflow directories
results/            Processed tables and performance figures

task.yaml           Configure the particle-count study for each case
study.yaml          Generated Maestro study definition

launch.py           Build and launch the Maestro study
run_case.py         Run one case in one execution mode
process.py          Generate runtime, precision, and figure-of-merit results

cleanup.py          Remove generated outputs and results
util.py             Provide shared task-generation utilities
```

## Configuration

Each case in `task.yaml` contains a `numba` block, a `python` block, or both.
Each mode block defines its own logarithmic particle-count bounds, number of sampling points, and walltime factor.
Each case-mode pair is an independent Maestro step that runs only that mode's sampling points sequentially.
Numba and Python jobs have no dependency on each other and can be scheduled independently.
The launch-level `--walltime` is specified in hours and multiplied by each mode's `walltime_factor`.
The result is rounded up to the scheduler resolution and capped at the platform maximum.
When `--walltime` is omitted, the platform maximum is used as the base; local runs ignore walltime.
For example, `--walltime 1.0` and a mode's `walltime_factor: 0.5` request 30 minutes for that job.
The input file defines settings such as `N_batch`; processing reads the actual settings and total history count from each output.

Only modes with a task block are enabled; omit `python` for Numba-only runs.
For example, this case launches separate jobs with 11 Numba points and seven Python points:

```yaml
kobayashi-detector:
  numba:
    logN_min: 1
    logN_max: 6
    N_task: 11
    walltime_factor: 1.0
  python:
    logN_min: 1
    logN_max: 4
    N_task: 7
    walltime_factor: 1.0
```

Every run saves full tally results, standard metadata, runtime details, and the `performance/` group.
Output names encode the mode and particle count, for example `output_numba_10000.h5`.
Numba caching remains disabled so every Numba measurement includes compilation.
Each cluster job requests one process on one exclusive node.
HPC runs use the shared platform settings in `configs/platform_config.py` and user-specific account, queue, reservation, and Python paths in `configs/user_config.py`.
The C5G7 input uses the shared cross sections in `data/MGXS-C5G7.h5`.

## Launching and processing

From this suite directory, launch locally:

```console
python launch.py
```

Launch on a supported cluster:

```console
python launch.py --platform dane --walltime 1.0
```

Completed mode and particle-count outputs are skipped on relaunch, and each case-mode job is skipped independently when all of its outputs exist.
Run `python process.py` after the jobs finish.
Pass a `maestro_run_<timestamp>` directory to process a specific launch.
Processing uses that run's saved `task.yaml`, not the current suite-level file.
Older saved task files using shared bounds or `python_mode` must be converted to the nested mode-block format before processing.

For each case, processing creates `records.csv` and five log-log plots against total histories, $N$.
The plots are `runtime.png`, `tracking_rate.png`, `precision.png`, `precision_rate.png`, and `fom.png`.
The runtime is the total MC/DC runtime, including Numba compilation.
The tracking rate is the number of histories divided by total runtime.
For each case, the available configured output with the largest total history count supplies the reference tally means for both modes; Numba is preferred on a tie.
For each run, the maximum relative variance is $V_{\max} = \max_{i:\mu_{i,\mathrm{ref}}\ne 0} (s_i/\mu_{i,\mathrm{ref}})^2$, where $s_i$ is that run's tally standard error (`sdev`).
The maximum includes all tally scores and bins whose reference mean is nonzero, even if the current run's mean is zero.
This uses the variance normalized by a fixed reference mean, not the squared difference between the current and reference means.
Tally scores, shapes, and grids must match the reference.
The tally validation and reference-based variance calculation in `../metrics.py` are shared with the parallel suite.
The plots and derived CSV metrics use $V_{\%,\max} = 10^4 V_{\max}$ in percent squared.
With total runtime $T$, precision is $1/V_{\%,\max}$ in $\%^{-2}$, precision rate is $1/(V_{\%,\max}N)$ in $\%^{-2}$ per history, and figure of merit (FOM) is $1/(TV_{\%,\max})$ in $\%^{-2}$ per second.
FOM is the product of tracking rate and precision rate: $(N/T)\,[1/(V_{\%,\max}N)] = 1/(TV_{\%,\max})$.
Runtime and history count come from `performance/runtime` and `performance/N_history`.
The CSV records all derived metrics, `performance/N_rank`, the fractional `max_relative_variance_<mode>`, the reference mode and particle/history counts, and `N_reference_nonzero_bin`.
The unchanged fractional `performance/effective_variance` is retained in the CSV for comparison but is not used for plotting.
If no reference bins have nonzero means, or the maximum relative variance is nonfinite or nonpositive, derived precision, precision-rate, and FOM values are recorded as `nan` and omitted from the plots.
If a metric has no finite positive values, its plot displays an explanatory message instead of a curve.
Each mode is processed independently using its own particle-count grid, so a missing output in one mode does not discard the other mode's point.
Overlapping particle-count points must have matching history and batch counts, and every output must have exactly one MPI rank.
Each curve uses its own history counts; CSV rows cover the union of available particle counts, with blank mode-specific fields where no measurement exists.
Modes with no available outputs are omitted from the curves and CSV columns.
All runtime-dependent metrics use the measured total runtime without subtracting compilation time or other overhead.
Runtime now includes full tally output, so older measurements that omitted tally output represent a different workload.
Processing requires at least one available sampling point in any configured mode.
Numba uses a solid blue line with hollow circles, and Python uses a dashed vermilion line with crosses.

Run `python cleanup.py` to remove generated outputs, Maestro records, processed results, and `study.yaml`.
The study file is untracked and regenerated by `launch.py` for the selected platform.
Outputs without full tally results are rejected rather than silently reused or overwritten; move them aside before relaunching to regenerate them.

## Cases

| Case | Description |
| :--- | :---------- |
| [`c5g7-4phase`](cases/c5g7-4phase/) | Four-phase C5G7 transient problem. |
| [`kobayashi`](cases/kobayashi/) | Time-dependent Kobayashi dog-leg problem. |
