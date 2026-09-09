"""
run_pipeline.py
================
Runs the entire project pipeline end-to-end, in order, stopping and
reporting immediately if any stage fails. This is the script used to
validate (Step 31 of the project spec) that the whole project is
reproducible from a clean state.

Run:
    python src/run_pipeline.py
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

STAGES = [
    "generate_data.py",
    "clean_data.py",
    "build_sqlite_db.py",
    "test_sql.py",
    "eda.py",
    "cohort_analysis.py",
    "segmentation.py",
    "statistical_analysis.py",
    "feature_engineering.py",
    "churn_model.py",
    "build_notebooks.py",
]

def main():
    overall_start = time.time()
    for stage in STAGES:
        print(f"\n{'#'*80}\n# RUNNING: {stage}\n{'#'*80}")
        start = time.time()
        result = subprocess.run([sys.executable, stage], cwd=SRC)
        elapsed = time.time() - start
        if result.returncode != 0:
            print(f"\n!!! STAGE FAILED: {stage} (exit code {result.returncode}) after {elapsed:.1f}s")
            sys.exit(1)
        print(f"--- {stage} completed OK in {elapsed:.1f}s ---")
    total = time.time() - overall_start
    print(f"\n{'='*80}\nPIPELINE COMPLETE — all {len(STAGES)} stages passed in {total:.1f}s\n{'='*80}")

if __name__ == "__main__":
    main()
