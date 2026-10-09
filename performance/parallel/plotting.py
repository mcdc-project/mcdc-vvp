"""Plot measured performance envelopes and matched-workload scaling evidence."""

from collections import defaultdict

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
import numpy as np

COLORS = ("#0072B2", "#D55E00", "#009E73", "#8A52A1", "#CC79A7", "#555555")
LINESTYLES = ("-", "--", ":", "-.", (0, (5, 1, 1, 1)), (0, (1, 1)), (0, (5, 2)))


def grouped_curves(records):
    """Group measured points by platform, method, and allocation."""
    curves = defaultdict(list)
    for record in records:
        curves[(record["platform"], record["method"], record["N_node"])].append(record)
    for key, curve in curves.items():
        curve.sort(key=lambda r: r["N_history"])
        if len({r["N_history"] for r in curve}) != len(curve):
            raise ValueError(f"Duplicate workloads in comparison curve {key}.")
    return dict(sorted(curves.items()))


def style_axis(axis):
    """Keep performance axes readable without obscuring the observations."""
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", alpha=0.25)
    axis.set_axisbelow(True)


def finish_figure(figure, path):
    """Save a figure with its external annotations and release it."""
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def draw_curves(axis, curves, metric, ylabel, logarithmic=False):
    """Draw measurements with consistent group colors and node-count styles."""
    groups = sorted({key[:2] for key in curves})
    nodes = sorted({key[2] for key in curves})
    for (platform, method, count), curve in curves.items():
        color = COLORS[groups.index((platform, method)) % len(COLORS)]
        values = np.array([r[metric] for r in curve], dtype=float)
        values[~np.isfinite(values) | (values <= 0)] = np.nan
        axis.plot(
            [r["N_history"] for r in curve],
            values,
            color=color,
            linestyle=LINESTYLES[nodes.index(count) % len(LINESTYLES)],
            marker="o",
            markerfacecolor="none",
            markersize=4,
            label=f"{platform} · {method} · {count} node{'s' if count != 1 else ''}",
        )
    axis.set_xscale("log")
    valid = any(
        np.isfinite(r[metric]) and r[metric] > 0 for c in curves.values() for r in c
    )
    if logarithmic and valid:
        positive = [
            r[metric]
            for c in curves.values()
            for r in c
            if np.isfinite(r[metric]) and r[metric] > 0
        ]
        if max(positive) / min(positive) < 1.01:
            axis.set_ylim(min(positive) * 0.8, max(positive) * 1.2)
        axis.set_yscale("log")
    else:
        axis.set_ylim(bottom=0)
    if not valid:
        axis.text(
            0.5, 0.5, "No finite positive values", transform=axis.transAxes, ha="center"
        )
    axis.set(xlabel="Total histories, N", ylabel=ylabel)
    style_axis(axis)


def performance_figures(records, comparison, destination):
    """Show all five metrics and a two-panel per-node performance envelope."""
    curves = grouped_curves(records)
    for metric, filename, ylabel in (
        ("runtime_total", "runtime", "Total runtime [s]"),
        ("tracking_rate_per_node", "tracking_rate", "Tracking rate [histories/s/node]"),
        ("precision", "precision", r"Precision [$\%^{-2}$]"),
        ("precision_rate", "precision_rate", r"Precision rate [$\%^{-2}$/history]"),
        ("fom_per_node", "fom", r"FOM [$\%^{-2}$/s/node]"),
    ):
        figure, axis = plt.subplots(figsize=(8, 5))
        draw_curves(axis, curves, metric, ylabel, logarithmic=True)
        axis.set_title(f"{comparison}: {filename.replace('_', ' ')}")
        axis.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
        finish_figure(figure, destination / f"{filename}.png")
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    for axis, metric, ylabel in zip(
        axes,
        ("tracking_rate_per_node", "fom_per_node"),
        ("Tracking rate [histories/s/node]", r"FOM [$\%^{-2}$/s/node]"),
    ):
        draw_curves(axis, curves, metric, ylabel)
    figure.suptitle(f"{comparison}: Performance envelope", fontsize=16)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncols=min(3, len(labels)),
        fontsize=9,
    )
    figure.tight_layout()
    finish_figure(figure, destination / "performance_envelope.png")


def sample_curve(curve, histories):
    """Interpolate runtime and precision inside one measured bracket only."""
    counts = np.array([r["N_history"] for r in curve], dtype=float)
    if histories < counts[0] or histories > counts[-1]:
        raise ValueError("Requested summary point requires extrapolation.")
    index = int(np.searchsorted(counts, histories))
    if counts[index] == histories:
        lower = upper = curve[index]
        fraction = 0.0
    else:
        lower, upper = curve[index - 1], curve[index]
        fraction = (histories - lower["N_history"]) / (
            upper["N_history"] - lower["N_history"]
        )
    runtime = lower["runtime_total"] + fraction * (
        upper["runtime_total"] - lower["runtime_total"]
    )
    # Never bridge an invalid variance estimate by skipping to a farther point.
    precision = float("nan")
    if all(np.isfinite(r["precision"]) and r["precision"] > 0 for r in (lower, upper)):
        precision = lower["precision"] + fraction * (
            upper["precision"] - lower["precision"]
        )
    nodes = lower["N_node"]
    return {
        "N_node": nodes,
        "N_history": histories,
        "histories_per_node": histories / nodes,
        "runtime_total": runtime,
        "precision": precision,
        "precision_rate": precision / histories,
        "tracking_rate_per_node": histories / (nodes * runtime),
        "fom_per_node": precision / (nodes * runtime),
        "interpolated": lower is not upper,
        "interpolation": (
            "linear runtime and precision" if lower is not upper else "none"
        ),
        "lower_N_history": lower["N_history"],
        "upper_N_history": upper["N_history"],
        "lower_output": lower["output_file"],
        "upper_output": upper["output_file"],
        "reference_file": lower["reference_file"],
    }


def summary_points(curves, factor, steps):
    """Choose shared workloads for both wings, stopping before extrapolation."""
    groups = sorted({key[:2] for key in curves})
    maximum_nodes = {
        group: max(key[2] for key in curves if key[:2] == group) for group in groups
    }
    h_max = min(curve[-1]["histories_per_node"] for curve in curves.values())
    h_min = max(curve[0]["histories_per_node"] for curve in curves.values())
    if h_min > h_max:
        return (
            [],
            "No common histories-per-node range; collect overlap data or select compatible studies.",
        )
    right_min = max(
        curves[(*group, nodes)][0]["histories_per_node"]
        for group, nodes in maximum_nodes.items()
    )
    workloads = []
    for step in range(1, steps + 1):
        target = h_max / factor**step
        if target < right_min:
            break
        workloads.append(target)
    rows = []
    for platform, method in groups:
        max_nodes = maximum_nodes[(platform, method)]
        selections = [
            (key[2], h_max, "weak", str(key[2]))
            for key in curves
            if key[:2] == (platform, method) and key[2] < max_nodes
        ]
        selections.append((max_nodes, h_max, "main", "M"))
        selections.extend(
            (max_nodes, h, "workload", f"r{i}") for i, h in enumerate(workloads, 1)
        )
        for nodes, h, role, label in selections:
            rows.append(
                {
                    "platform": platform,
                    "method": method,
                    "role": role,
                    "label": label,
                    "h_max": h_max,
                    "workload_fraction": h / h_max,
                    **sample_curve(curves[(platform, method, nodes)], h * nodes),
                }
            )
    note = f"Common maximum: {h_max:,.6g} histories/node; rightward workload reduction: ×{factor:g}."
    if len(workloads) < steps:
        note += f" Right wing limited to {len(workloads)} supported steps (no extrapolation)."
    return rows, note


def scaling_summary(records, comparison, destination, factor, steps):
    """Plot main bars between direct weak-scaling and indirect strong-scaling evidence."""
    curves = grouped_curves(records)
    rows, note = summary_points(curves, factor, steps)
    print(f"{comparison}: {note}")
    figure, axes = plt.subplots(1, 2, figsize=(14, 6))
    figure.suptitle(f"{comparison}: Performance level + scaling evidence", fontsize=16)
    groups = sorted({(r["platform"], r["method"]) for r in rows})
    if not rows:
        for axis in axes:
            axis.text(
                0.5,
                0.5,
                "No shared workload range",
                transform=axis.transAxes,
                ha="center",
            )
            axis.set_axis_off()
    for axis, metric, ylabel in zip(
        axes,
        ("tracking_rate_per_node", "fom_per_node"),
        ("Tracking rate [histories/s/node]", r"FOM [$\%^{-2}$/s/node]"),
    ):
        labels = []
        max_bars = max(
            (sum((r["platform"], r["method"]) == g for r in rows) for g in groups),
            default=1,
        )
        width = 0.82 / max_bars
        for group_index, group in enumerate(groups):
            points = [r for r in rows if (r["platform"], r["method"]) == group]
            main_index = next(i for i, r in enumerate(points) if r["role"] == "main")
            labels.append(
                f"{group[0]}\n{group[1]}\nM: {points[main_index]['N_node']} nodes"
            )
            for i, row in enumerate(points):
                x = group_index - len(points) * width / 2 + (i + 0.5) * width
                color = np.array(to_rgb(COLORS[group_index % len(COLORS)]))
                color += (1 - color) * min(0.65, 0.12 * abs(i - main_index))
                height = row[metric]
                if np.isfinite(height) and height > 0:
                    axis.bar(
                        x,
                        height,
                        width=width,
                        color=color,
                        edgecolor="#344254",
                        linewidth=1.8 if row["role"] == "main" else 0.4,
                        hatch="///" if row["interpolated"] else None,
                    )
                    axis.annotate(
                        row["label"],
                        (x, height),
                        xytext=(0, 4),
                        textcoords="offset points",
                        ha="center",
                        fontsize=8,
                    )
                else:
                    axis.text(
                        x, 0, "N/A", ha="center", va="bottom", rotation=90, fontsize=8
                    )
        axis.set_xticks(range(len(groups)), labels, fontsize=9)
        axis.set_ylabel(ylabel)
        axis.set_ylim(0, axis.get_ylim()[1] * 1.15)
        style_axis(axis)
    figure.text(
        0.5,
        0.91,
        "← Fewer nodes, same histories/node   |   M   |   Same nodes, fewer histories/node →",
        ha="center",
        fontsize=11,
    )
    figure.legend(
        handles=[
            Patch(facecolor="#d2d9e0", edgecolor="#344254", label="Measured"),
            Patch(
                facecolor="#d2d9e0",
                edgecolor="#344254",
                hatch="///",
                label="Interpolated",
            ),
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, 0.08),
        ncols=2,
        frameon=False,
    )
    figure.text(
        0.05,
        0.03,
        note
        + "\nLeft + M: direct weak scaling. M + right: indirect strong-scaling evidence. FOM also depends on precision.",
        fontsize=9,
    )
    figure.subplots_adjust(top=0.83, bottom=0.29, wspace=0.27)
    finish_figure(figure, destination / "scaling_summary.png")
    return rows
