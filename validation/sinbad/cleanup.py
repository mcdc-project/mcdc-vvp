"""Remove generated outputs for configured SINBAD validation cases."""

import shutil
from pathlib import Path

from util import case_directory, load_tasks

suite_dir = Path(__file__).resolve().parent
_, tasks = load_tasks(suite_dir / "task.yaml")

# Leave incomplete benchmark models untouched; clean only configured runnable cases.
for benchmark, case, _task in tasks:
    case_dir = case_directory(suite_dir, benchmark, case)
    for pattern in ("output*.h5", "*.png", "*.gif"):
        for generated_file in case_dir.glob(pattern):
            generated_file.unlink()

results_dir = suite_dir / "results"
if results_dir.is_dir():
    shutil.rmtree(results_dir)

for maestro_run in suite_dir.glob("maestro_run_*"):
    if maestro_run.is_dir():
        shutil.rmtree(maestro_run)

study_file = suite_dir / "study.yaml"
if study_file.is_file():
    study_file.unlink()
