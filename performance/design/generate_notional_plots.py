"""Generate synthetic performance illustrations without running transport cases."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np

NODES = (1, 4, 16)
METHODS = ("Analog", "Weight windows")
PLATFORMS = ("CPU", "GPU")
COLORS = {
    ("CPU", "Analog"): "#0072B2",
    ("CPU", "Weight windows"): "#009E73",
    ("GPU", "Analog"): "#D55E00",
    ("GPU", "Weight windows"): "#8A52A1",
}
LINESTYLES = {1: "-", 4: "--", 16: ":"}
WORKLOAD_DIVISORS = (4, 16, 64, 256)


def synthetic_series(platform, method, nodes):
    """Construct notional timing and precision on platform-specific history grids."""
    base = 1_000_000 if platform == "CPU" else 5_000_000
    throughput = {
        ("CPU", "Analog"): 150_000,
        ("CPU", "Weight windows"): 90_000,
        ("GPU", "Analog"): 1_600_000,
        ("GPU", "Weight windows"): 800_000,
    }[platform, method]
    startup = 75.0 if platform == "CPU" else 110.0
    # Fixed method overhead matters when strong scaling reduces work per node.
    # It stays constant under weak scaling, apart from a small common node cost.
    method_overhead = 0.0
    if method == "Weight windows":
        method_overhead = 1200.0 if platform == "CPU" else 500.0
    overhead = startup + method_overhead + 2.0 * np.log2(nodes)
    # Continue sampling well into the plateau for each configuration.
    count = max(
        13 if platform == "CPU" else 14,
        int(
            np.ceil(
                np.log2(
                    1000.0
                    * (startup + method_overhead + 2.0 * np.log2(max(NODES)))
                    * throughput
                    / base
                )
            )
        )
        + 1,
    )
    histories = base * nodes * 2.0 ** np.arange(count)
    runtime = overhead + histories / (nodes * throughput)
    precision_rate = 2.0e-6 if method == "Analog" else 8.0e-6
    precision = precision_rate * histories
    return {
        "histories": histories,
        "runtime": runtime,
        "precision": precision,
        "tracking_rate": histories / (nodes * runtime),
        "fom": precision / (nodes * runtime),
    }


def sample_at(series, histories, nodes):
    """Interpolate timing and precision only within the sampled history range."""
    samples = series["histories"]
    if not samples[0] <= histories <= samples[-1]:
        raise ValueError("The selected workload would require extrapolation.")
    runtime = np.interp(histories, samples, series["runtime"])
    precision = np.interp(histories, samples, series["precision"])
    tracking_rate = histories / (nodes * runtime)
    precision_rate = precision / histories
    fom = precision / (nodes * runtime)
    assert np.isclose(fom, tracking_rate * precision_rate)
    return {
        "tracking_rate": tracking_rate,
        "fom": fom,
        "interpolated": not np.any(samples == histories),
    }


def style_axis(axis):
    """Apply consistent, unobtrusive axes and grid styling."""
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", color="#dce2e8", linewidth=0.8)
    axis.set_axisbelow(True)
    axis.tick_params(axis="both", length=3, color="#687584")


def save_curves(destination):
    """Show the full notional tracking-rate and FOM curves by platform."""
    series_by_configuration = {
        (platform, method, nodes): synthetic_series(platform, method, nodes)
        for platform in PLATFORMS
        for method in METHODS
        for nodes in NODES
    }
    history_limits = (
        min(series["histories"][0] for series in series_by_configuration.values())
        * 0.7,
        max(series["histories"][-1] for series in series_by_configuration.values())
        * 1.25,
    )
    figure, axes = plt.subplots(2, 2, figsize=(13, 8.5), sharex=True)
    figure.subplots_adjust(
        left=0.085, right=0.98, bottom=0.13, top=0.80, hspace=0.40, wspace=0.24
    )
    figure.suptitle(
        "Performance envelopes",
        x=0.085,
        y=0.975,
        ha="left",
        fontsize=22,
        fontweight="bold",
    )
    figure.text(
        0.085,
        0.927,
        "NOTIONAL DATA  •  Synthetic CPU/GPU configurations; not MC/DC measurements",
        fontsize=11,
        color="#687584",
    )
    for row, platform in enumerate(PLATFORMS):
        for column, metric in enumerate(("tracking_rate", "fom")):
            axis = axes[row, column]
            for method in METHODS:
                for nodes in NODES:
                    series = series_by_configuration[platform, method, nodes]
                    scale = 1e6 if metric == "tracking_rate" else 1.0
                    axis.plot(
                        series["histories"],
                        series[metric] / scale,
                        color=COLORS[platform, method],
                        linestyle=LINESTYLES[nodes],
                        linewidth=2.0,
                        marker="o",
                        markersize=3.5,
                        markerfacecolor="white",
                    )
            axis.set_xscale("log")
            axis.set_xlim(*history_limits)
            axis.set_ylim(bottom=0)
            axis.set_title(
                f"{platform} · {'Tracking rate' if column == 0 else 'FOM'} per node",
                loc="left",
                fontweight="bold",
                pad=10,
            )
            axis.set_ylabel(
                "Million histories/s/node"
                if column == 0
                else r"Precision/s/node [$\%^{-2}$/s/node]"
            )
            if row == 1:
                axis.set_xlabel(r"Total histories, $N$")
            style_axis(axis)
    method_handles = [
        Line2D([], [], color=COLORS[p, m], linewidth=3, label=f"{p} · {m}")
        for p in PLATFORMS
        for m in METHODS
    ]
    node_handles = [
        Line2D(
            [],
            [],
            color="#344254",
            linestyle=LINESTYLES[p],
            linewidth=2,
            label=f"{p} node{'s' if p > 1 else ''}",
        )
        for p in NODES
    ]
    figure.legend(
        handles=method_handles + node_handles,
        loc="upper left",
        bbox_to_anchor=(0.075, 0.902),
        ncols=4,
        frameon=False,
        columnspacing=1.5,
        fontsize=10,
    )
    figure.text(
        0.085,
        0.035,
        "Open circles: synthetic samples.  Line style: node count.\n"
        "Panels use different vertical ranges; compare numerical values, not apparent curve heights.",
        fontsize=10,
        color="#687584",
        linespacing=1.6,
    )
    figure.savefig(destination / "performance_curves.png", dpi=180)
    plt.close(figure)


def common_maximum_per_node():
    """Find the largest histories per node covered by every compared curve."""
    return min(
        synthetic_series(platform, method, nodes)["histories"][-1] / nodes
        for platform in PLATFORMS
        for method in METHODS
        for nodes in NODES
    )


def summary_points(platform, method):
    """Select matched-workload anchors and wings without extrapolation."""
    nodes = max(NODES)
    maximum_per_node = common_maximum_per_node()
    maximum_histories = maximum_per_node * nodes
    # Left to right: fewer nodes, main bar, then fewer histories per node.
    selections = [(p, maximum_per_node * p, "weak") for p in sorted(NODES) if p < nodes]
    selections.append((nodes, maximum_histories, "main"))
    selections.extend(
        (nodes, maximum_histories / divisor, "workload")
        for divisor in WORKLOAD_DIVISORS
    )
    return [
        {
            "nodes": nodes,
            "histories": histories,
            "histories_per_node": histories / nodes,
            "role": role,
            **sample_at(synthetic_series(platform, method, nodes), histories, nodes),
        }
        for nodes, histories, role in selections
    ]


def save_summary(destination):
    """Show achieved performance between weak-scaling and workload-sensitivity wings."""
    title = "Performance level + scaling evidence"
    maximum_per_node = common_maximum_per_node()
    workload_label = f"Main bar M: {max(NODES)} nodes × {maximum_per_node / 1e9:.3f} billion histories/node, shared by all groups"
    selection_label = "← Fewer nodes, fixed histories/node     |     M     |     Fixed nodes, fewer histories/node →"
    histories_label = "Bar order: 1 node / 4 nodes / M (16 nodes) / a / b / c / d;   a–d: h_max ÷ 4 / 16 / 64 / 256"
    figure, axes = plt.subplots(1, 2, figsize=(13, 6.5))
    figure.subplots_adjust(left=0.085, right=0.98, bottom=0.28, top=0.70, wspace=0.25)
    figure.suptitle(
        title,
        x=0.085,
        y=0.975,
        ha="left",
        fontsize=20,
        fontweight="bold",
    )
    figure.text(
        0.085,
        0.91,
        f"NOTIONAL DATA  •  {workload_label}",
        fontsize=11,
        color="#687584",
        va="top",
    )
    figure.text(
        0.085,
        0.85,
        f"{selection_label}\n{histories_label}",
        fontsize=11,
        color="#344254",
        linespacing=1.6,
        va="top",
    )
    combinations = [(p, m) for p in PLATFORMS for m in METHODS]
    for axis, metric in zip(axes, ("tracking_rate", "fom")):
        group_labels = []
        for group, (platform, method) in enumerate(combinations):
            points = summary_points(platform, method)
            main_index = next(
                i for i, point in enumerate(points) if point["role"] == "main"
            )
            width = 0.81 / len(points)
            label = f"{platform}\n{method}"
            group_labels.append(label)
            for index, values in enumerate(points):
                height = values[metric] / (1e6 if metric == "tracking_rate" else 1)
                color = np.array(to_rgb(COLORS[platform, method]))
                color = color + (1.0 - color) * 0.13 * abs(index - main_index)
                axis.bar(
                    group - 0.405 + index * width,
                    height,
                    width=width,
                    align="edge",
                    color=color,
                    edgecolor="#344254",
                    linewidth=1.8 if values["role"] == "main" else 0.4,
                    hatch="///" if values["interpolated"] else None,
                )
                bar_label = (
                    "M"
                    if values["role"] == "main"
                    else (
                        str(values["nodes"])
                        if values["role"] == "weak"
                        else "abcd"[index - main_index - 1]
                    )
                )
                axis.annotate(
                    bar_label,
                    (group - 0.405 + (index + 0.5) * width, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    fontsize=9,
                    fontweight="bold" if values["role"] == "main" else "normal",
                    color="#344254",
                )
        axis.set_xticks(range(len(combinations)), group_labels)
        axis.tick_params(axis="x", labelsize=9.5)
        axis.set_ylim(0, axis.get_ylim()[1] * 1.16)
        axis.set_ylabel(
            "Million histories/s/node"
            if metric == "tracking_rate"
            else r"Precision/s/node [$\%^{-2}$/s/node]"
        )
        axis.set_title(
            "Tracking rate per node" if metric == "tracking_rate" else "FOM per node",
            loc="left",
            fontweight="bold",
            pad=14,
        )
        style_axis(axis)
    figure.legend(
        handles=[
            Patch(
                facecolor="#d2d9e0",
                edgecolor="#344254",
                label="Exact synthetic sampling point",
            ),
        ]
        + [
            Patch(
                facecolor="#d2d9e0",
                edgecolor="#344254",
                hatch="///",
                label="Interpolated synthetic point",
            )
        ],
        loc="lower left",
        bbox_to_anchor=(0.075, 0.13),
        ncols=2,
        frameon=False,
        fontsize=10,
    )
    figure.text(
        0.085,
        0.035,
        "Left + M: direct weak-scaling comparison.  M + right: indirect strong-scaling evidence from workload sensitivity.\n"
        "All groups share the same workload targets.  Hatched bars interpolate runtime and precision; no extrapolation.",
        fontsize=10,
        color="#687584",
        linespacing=1.6,
    )
    figure.savefig(destination / "scaling_summary.png", dpi=180)
    plt.close(figure)


def main():
    """Write reproducible documentation figures next to the design note."""
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "text.color": "#263548",
            "axes.labelcolor": "#344254",
            "xtick.color": "#344254",
            "ytick.color": "#344254",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    destination = Path(__file__).resolve().parent / "figures"
    destination.mkdir(exist_ok=True)
    save_curves(destination)
    save_summary(destination)
    print(f"Wrote two synthetic illustrations to {destination}")


if __name__ == "__main__":
    main()
