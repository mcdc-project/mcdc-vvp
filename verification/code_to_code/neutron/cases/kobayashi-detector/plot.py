"""Plot one detector result pair against the fixed largest-sample reference."""

import argparse

from process import (
    check_time_grid,
    load_mcdc_results,
    load_openmc_results,
    plot_history,
)
from util import comparison_reference, relative_difference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mcdc_output")
    parser.add_argument("openmc_output")
    parser.add_argument("mcdc_reference_output")
    parser.add_argument("openmc_reference_output")
    args = parser.parse_args()

    first, time, _ = load_mcdc_results(args.mcdc_output)
    second, second_time = load_openmc_results(args.openmc_output)
    first_reference, reference_time, _ = load_mcdc_results(args.mcdc_reference_output)
    second_reference, second_reference_time = load_openmc_results(
        args.openmc_reference_output
    )
    for grid in (second_time, reference_time, second_reference_time):
        check_time_grid(time, grid)
    reference = comparison_reference(first_reference, second_reference)
    plot_history(
        time,
        [first, second],
        ["MC/DC", "OpenMC"],
        "Detector capture per source particle per time bin",
        "comparison.png",
    )
    plot_history(
        time,
        [100.0 * relative_difference(reference, first, second)],
        ["MC/DC − OpenMC"],
        "Relative difference (%)",
        "difference.png",
    )


if __name__ == "__main__":
    main()
