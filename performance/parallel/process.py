"""Compare parallel performance across saved platform and method studies."""

import argparse
import csv
import math
import shutil
from collections import defaultdict
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import numpy as np
import yaml

from util import output_directory, output_name, performance_tasks, tally_score_paths
from performance.metrics import maximum_relative_variance
from plotting import grouped_curves, performance_figures, scaling_summary


def saved_studies(suite_dir, requested):
    """Read explicit studies or select the latest saved study for each platform."""
    paths = [Path(path).expanduser() for path in requested]
    if not paths:
        paths = sorted(suite_dir.glob("maestro_run_*"), key=lambda p: p.stat().st_mtime)
    selected = {}
    for path in paths:
        if not path.is_absolute():
            path = suite_dir / path
        launch_file = path / "launch_config.yaml"
        task_file = path / "task.yaml"
        if not launch_file.is_file() or not task_file.is_file():
            if requested:
                raise FileNotFoundError(
                    f"Missing launch_config.yaml or task.yaml in {path}"
                )
            print(f"Skip study without saved metadata: {path.name}")
            continue
        with launch_file.open() as stream:
            launch = yaml.safe_load(stream)
        with task_file.open() as stream:
            tasks = yaml.safe_load(stream)
        key = str(path) if requested else launch["platform"]
        selected[key] = (path, launch, tasks)
    if not selected:
        raise FileNotFoundError("No saved parallel-performance studies found.")
    return list(selected.values())


def collect_records(suite_dir, studies):
    """Read completed outputs with their saved platform-specific launch settings."""
    records = []
    seen = set()
    for study, launch, settings in studies:
        platform = launch["platform"]
        for task in performance_tasks(settings, launch["N_node_max"], platform):
            if launch.get("output_layout", 1) == 1:
                # Legacy outputs are read only when a saved study identifies them.
                output_file = (
                    suite_dir
                    / "cases"
                    / task["case"]
                    / (
                        f"output_n{task['N_node']:03d}_m{task['workload_multiplier']:02d}.h5"
                    )
                )
            elif launch["output_layout"] == 2:
                output_file = (
                    output_directory(suite_dir, task) / f"{output_name(task)}.h5"
                )
            else:
                raise ValueError(f"Unknown output layout in {study}.")
            if not output_file.is_file():
                print(f"Skip incomplete task: {task['name']}")
                continue
            if output_file in seen:
                raise ValueError(
                    f"Selected studies overlap at {output_file}; select only one."
                )
            seen.add(output_file)
            with h5py.File(output_file, "r") as output:
                tally_score_paths(output)
                performance = output["performance"]
                if int(output["settings/N_particle"][()].item()) != task["N_particle"]:
                    raise ValueError(f"Particle count mismatch in {output_file}.")
                record = {key: value for key, value in task.items() if key != "name"}
                record.update(
                    target=launch.get("target", "cpu"),
                    source_study=study.name,
                    output_file=str(output_file.relative_to(suite_dir)),
                    N_batch=int(output["settings/N_batch"][()].item()),
                    N_history=int(performance["N_history"][()].item()),
                    N_rank=int(performance["N_rank"][()].item()),
                    effective_variance=float(
                        performance["effective_variance"][()].item()
                    ),
                    runtime_total=float(performance["runtime"][()].item()),
                )
                for name in ("preparation", "simulation", "output", "bank_management"):
                    path = f"runtime/{name}"
                    record[f"runtime_{name}"] = (
                        float(output[path][()].item())
                        if path in output
                        else float("nan")
                    )
            if (
                not math.isfinite(record["runtime_total"])
                or record["runtime_total"] <= 0
            ):
                raise ValueError(f"Invalid total runtime in {output_file}.")
            if record["N_history"] <= 0 or record["N_batch"] <= 0:
                raise ValueError(f"Invalid history or batch count in {output_file}.")
            ranks_per_node = launch.get(
                "ranks_per_node", launch.get("cpu_cores_per_node")
            )
            if record["N_rank"] != task["N_node"] * ranks_per_node:
                raise ValueError(
                    f"Rank count does not match the saved launch in {output_file}."
                )
            record["histories_per_node"] = record["N_history"] / record["N_node"]
            record["tracking_rate"] = record["N_history"] / record["runtime_total"]
            record["tracking_rate_per_node"] = (
                record["tracking_rate"] / record["N_node"]
            )
            records.append(record)
    if not records:
        raise RuntimeError("No completed performance tasks were found.")
    return records


def add_precision(suite_dir, records):
    """Use one reference and fixed nonzero-bin mask across all compared groups."""
    if len({record["N_batch"] for record in records}) != 1:
        raise ValueError(
            "Batch counts must match across compared platforms and methods."
        )
    reference = max(
        records,
        key=lambda r: (
            r["N_history"],
            -r["N_node"],
            r["platform"],
            r["method"],
            r["case"],
        ),
    )
    reference_file = suite_dir / reference["output_file"]
    print(f"Reference for {reference['comparison']}: {reference_file}")
    for record in records:
        variance, count = maximum_relative_variance(
            suite_dir / record["output_file"], reference_file
        )
        precision = (
            1.0e-4 / variance
            if np.isfinite(variance) and variance > 0
            else float("nan")
        )
        record.update(
            reference_file=reference["output_file"],
            reference_platform=reference["platform"],
            reference_method=reference["method"],
            reference_case=reference["case"],
            reference_N_node=reference["N_node"],
            reference_workload_multiplier=reference["workload_multiplier"],
            reference_N_particle=reference["N_particle"],
            reference_N_history=reference["N_history"],
            N_reference_nonzero_bin=count,
            max_relative_variance=variance,
            precision=precision,
            precision_rate=precision / record["N_history"],
            fom=precision / record["runtime_total"],
            fom_per_node=precision / (record["runtime_total"] * record["N_node"]),
        )
        if not np.isfinite(precision):
            print(f"Omit invalid precision metrics: {record['output_file']}")


def write_records(path, records):
    """Export measured or interpolated records with their provenance."""
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main():
    """Process selected studies into detailed curves and a common-workload summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "maestro_runs", nargs="*", help="Saved studies; default: latest per platform."
    )
    parser.add_argument(
        "--workload_factor",
        type=float,
        default=4.0,
        help="Right-wing reduction factor (default: 4).",
    )
    parser.add_argument(
        "--workload_steps",
        type=int,
        default=4,
        help="Maximum number of right-wing bars (default: 4).",
    )
    args = parser.parse_args()
    if not math.isfinite(args.workload_factor) or args.workload_factor <= 1:
        parser.error("--workload_factor must be finite and greater than one.")
    if args.workload_steps < 0:
        parser.error("--workload_steps must be nonnegative.")
    suite_dir = Path(__file__).resolve().parent
    studies = saved_studies(suite_dir, args.maestro_runs)
    records = collect_records(suite_dir, studies)
    groups = defaultdict(list)
    for record in records:
        comparison = record["comparison"]
        if (
            not isinstance(comparison, str)
            or Path(comparison).name != comparison
            or comparison in (".", "..")
        ):
            raise ValueError(
                f"Comparison must be a simple directory name: {comparison!r}."
            )
        groups[comparison].append(record)
    # Validate all tallies before replacing any processed results.
    for group in groups.values():
        add_precision(suite_dir, group)
        grouped_curves(group)
    results_dir = suite_dir / "results"
    if results_dir.is_dir():
        shutil.rmtree(results_dir)
    results_dir.mkdir()
    for index, (study, launch, tasks) in enumerate(studies):
        destination = results_dir / "studies" / f"{index:03d}_{study.name}"
        destination.mkdir(parents=True)
        for filename in ("launch_config.yaml", "task.yaml"):
            shutil.copy2(study / filename, destination / filename)
    for comparison, group in sorted(groups.items()):
        group.sort(
            key=lambda r: (r["platform"], r["method"], r["N_node"], r["N_history"])
        )
        destination = results_dir / comparison
        destination.mkdir()
        write_records(destination / "records.csv", group)
        performance_figures(group, comparison, destination)
        summary = scaling_summary(
            group, comparison, destination, args.workload_factor, args.workload_steps
        )
        if summary:
            write_records(destination / "scaling_summary.csv", summary)
    print(
        f"Processed {len(records)} tasks from {len(studies)} studies into {results_dir}"
    )


if __name__ == "__main__":
    main()
