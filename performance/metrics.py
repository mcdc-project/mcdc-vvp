"""Shared tally validation and reference-based performance statistics."""

import h5py
import numpy as np


def tally_score_paths(output):
    """Return tally-score groups with matching mean and standard-deviation datasets."""
    paths = []
    if "tallies" in output:
        for tally_name, tally in output["tallies"].items():
            for score_name, score in tally.items():
                if not isinstance(score, h5py.Group):
                    continue
                if "mean" not in score and "sdev" not in score:
                    continue
                if (
                    "mean" not in score
                    or "sdev" not in score
                    or score["mean"].shape != score["sdev"].shape
                ):
                    raise ValueError(
                        f"Incomplete tally score: {score.name} in {output.filename}"
                    )
                paths.append(f"tallies/{tally_name}/{score_name}")
    if not paths:
        raise ValueError(
            f"Missing full tally results in {output.filename}; move the old output "
            "aside and rerun without --no-tally_output."
        )
    return sorted(paths)


def output_complete(output_file):
    """Check for an existing output and reject files lacking required tally results."""
    if not output_file.is_file():
        return False
    with h5py.File(output_file, "r") as output:
        tally_score_paths(output)
    return True


def maximum_relative_variance(output_file, reference_file):
    """Return the maximum squared standard error relative to fixed reference means."""
    maximum = 0.0
    nonzero_bins = 0
    with h5py.File(output_file, "r") as output, h5py.File(
        reference_file, "r"
    ) as reference:
        paths = tally_score_paths(reference)
        if tally_score_paths(output) != paths:
            raise ValueError(f"Tally scores do not match the reference: {output_file}")
        for tally_name in reference["tallies"]:
            reference_grid = reference[f"tallies/{tally_name}"].get("grid")
            output_grid = output[f"tallies/{tally_name}"].get("grid")
            if (reference_grid is None) != (output_grid is None):
                raise ValueError(
                    f"Tally grids do not match the reference: {output_file}"
                )
            if reference_grid is not None:
                if set(reference_grid) != set(output_grid) or any(
                    not np.array_equal(reference_grid[key][()], output_grid[key][()])
                    for key in reference_grid
                ):
                    raise ValueError(
                        f"Tally grids do not match the reference: {output_file}"
                    )
        for path in paths:
            mean = reference[f"{path}/mean"]
            sdev = output[f"{path}/sdev"]
            if sdev.shape != mean.shape:
                raise ValueError(
                    f"Tally shape does not match the reference: {path} in {output_file}"
                )
            # Read slabs to avoid loading large space-time tallies in full.
            if mean.shape:
                row_size = max(1, int(np.prod(mean.shape[1:])))
                stride = max(1, 1_000_000 // row_size)
                selections = (
                    slice(start, start + stride)
                    for start in range(0, mean.shape[0], stride)
                )
            else:
                selections = [()]
            for selection in selections:
                reference_mean = np.asarray(mean[selection])
                standard_error = np.asarray(sdev[selection])
                if not np.all(np.isfinite(reference_mean)):
                    raise ValueError(
                        f"Nonfinite reference mean: {path} in {reference_file}"
                    )
                mask = reference_mean != 0.0
                count = int(np.count_nonzero(mask))
                if not count:
                    continue
                values = standard_error[mask]
                if not np.all(np.isfinite(values)) or np.any(values < 0.0):
                    raise ValueError(
                        f"Invalid tally standard deviation: {path} in {output_file}"
                    )
                relative_variance = (values / reference_mean[mask]) ** 2
                maximum = max(maximum, float(np.max(relative_variance)))
                nonzero_bins += count
    return (maximum if nonzero_bins else float("nan")), nonzero_bins
