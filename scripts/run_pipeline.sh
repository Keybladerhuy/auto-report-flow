#!/usr/bin/env bash
set -euo pipefail

VENV_PYTHON="$(dirname "$0")/../.venv/bin/python"
PYTHON="$([ -f "$VENV_PYTHON" ] && echo "$VENV_PYTHON" || echo "python")"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TIMING_LOG="/tmp/pipeline_timing.txt"
T0=$(date +%s)

run_nb() {
    local nb="$1"
    local t=$(date +%s)
    "$PYTHON" -m nbconvert --to notebook --execute \
        "notebooks/${nb}.ipynb" \
        --output "/tmp/${nb}_executed.ipynb" \
        --ExecutePreprocessor.timeout=900 2>/dev/null
    echo "  ${nb}: $(( $(date +%s) - t ))s"
}

# ── Step 1: data cleaning ─────────────────────────────────────────────────────
# Skip if clean_retail.csv already exists and is newer than the source Excel.
# Re-run by deleting data/clean_retail.csv or touching the xlsx file.
CSV="$ROOT/data/clean_retail.csv"
XLSX="$ROOT/data/online_retail_II.xlsx"

if [ -f "$CSV" ] && [ "$CSV" -nt "$XLSX" ]; then
    echo "==> 01_data_cleaning  skipped (clean_retail.csv is up to date)"
else
    echo "==> 01_data_cleaning"
    run_nb "01_data_cleaning"
fi

# ── Steps 2–4: analysis ───────────────────────────────────────────────────────
# All three read from clean_retail.csv and write independent chart files —
# safe to run in parallel.
echo "==> 02 / 03 / 04 running in parallel ..."

pids=()
run_nb "02_sales_trend_analysis" & pids+=($!)
run_nb "03_product_performance"  & pids+=($!)
run_nb "04_customer_rfm"         & pids+=($!)

for pid in "${pids[@]}"; do
    wait "$pid" || { echo "ERROR: a notebook failed (PID $pid)"; exit 1; }
done

# ── Timing summary ────────────────────────────────────────────────────────────
TOTAL=$(( $(date +%s) - T0 ))
echo "==> Pipeline complete — ${TOTAL}s total"
echo "$(date '+%Y-%m-%d %H:%M:%S')  ${TOTAL}s" >> "$TIMING_LOG"
echo "    (timing log: $TIMING_LOG)"
