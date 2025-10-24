#!/usr/bin/env python3
"""
plot_opscompleted.py
--------------------
Minimal script to graph PCP pmrep --csv exports (e.g., ds389.cn.opscompleted) on RHEL.
- Detects the time column automatically (Time/Timestamp/Date/Datetime), or use --time-col.
- Picks a metric column automatically if you don't pass --metric.
- Optional --resample and --rolling smoothing.
- Saves a PNG and (optionally) a single-page PDF.

Usage
-----
# Basic: detect time + first numeric metric
python3 plot_opscompleted.py --csv ds389_cn_opscompleted_all_pmrep_final.csv --out-dir ./plots

# Specify metric explicitly
python3 plot_opscompleted.py --csv ds389_cn_opscompleted_all_pmrep_final.csv \
  --metric ds389.cn.opscompleted --out-dir ./plots

# Add smoothing and resampling
python3 plot_opscompleted.py --csv ds389_cn_opscompleted_all_pmrep_final.csv \
  --metric ds389.cn.opscompleted --resample 1min --rolling 5 \
  --out-dir ./plots --pdf ./plots/opscompleted.pdf
"""
import argparse
import os
from pathlib import Path
from typing import Optional, List

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

CANDIDATE_TIME_COLS = ["time", "timestamp", "date", "datetime", "Time", "Timestamp", "Date", "Datetime"]

def detect_time_col(df: pd.DataFrame, forced: Optional[str] = None) -> str:
    if forced and forced in df.columns:
        return forced
    # try common names (case-insensitive mapping)
    lower_map = {c.lower(): c for c in df.columns}
    for cand in ["time", "timestamp", "date", "datetime"]:
        if cand in lower_map:
            return lower_map[cand]
    # fallback: first column
    return df.columns[0]

def pick_metric_col(df: pd.DataFrame, time_col: str, metric: Optional[str]) -> str:
    if metric and metric in df.columns:
        return metric
    numeric_cols = [c for c in df.columns if c != time_col and pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        raise SystemExit("No numeric metric columns found. Pass --metric explicitly.")
    # Prefer common ds389 column if present
    for preferred in ["ds389.cn.opscompleted", "ds389.cn.opsCompleted", "opscompleted"]:
        if preferred in numeric_cols:
            return preferred
    return numeric_cols[0]

def main():
    ap = argparse.ArgumentParser(description="Plot pmrep CSV (e.g., ds389.cn.opscompleted) into PNG/PDF.")
    ap.add_argument("--csv", required=True, help="Path to pmrep --csv file")
    ap.add_argument("--out-dir", required=True, help="Directory to save outputs")
    ap.add_argument("--pdf", default=None, help="Optional PDF path for the figure")
    ap.add_argument("--time-col", default=None, help="Time column name if auto-detect fails")
    ap.add_argument("--metric", default=None, help="Metric column to plot (defaults to first numeric)")
    ap.add_argument("--resample", default=None, help="Optional pandas offset alias (e.g., '1min', '30s')")
    ap.add_argument("--rolling", type=int, default=None, help="Optional rolling window (in samples after resample)")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load CSV
    df = pd.read_csv(args.csv)

    # Detect columns
    time_col = detect_time_col(df, args.time_col)
    try:
        df[time_col] = pd.to_datetime(df[time_col])
    except Exception:
        # leave as-is if parsing fails
        pass
    metric_col = pick_metric_col(df, time_col, args.metric)

    # Prepare series
    x = df[time_col]
    y = df[metric_col]

    # Optional resampling (requires datetime-like index)
    if pd.api.types.is_datetime64_any_dtype(x):
        s = pd.Series(y.values, index=x)
        if args.resample:
            # For counts like opscompleted, sum per bucket generally makes sense;
            # change to 'mean' if you prefer average over the interval.
            s = s.resample(args.resample).sum()
        else:
            s = s
        if args.rolling and args.rolling > 1:
            s = s.rolling(args.rolling, min_periods=1).mean()
        x = s.index
        y = s.values

    # Plot (one chart, no explicit colors)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x, y, linewidth=1.5)
    ax.set_title(metric_col)
    ax.set_xlabel(time_col)
    ax.set_ylabel(metric_col)
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    if pd.api.types.is_datetime64_any_dtype(x):
        fig.autofmt_xdate()
    plt.tight_layout()

    # Save files
    png_path = out_dir / f"{Path(args.csv).stem}.{metric_col.replace('/', '_')}.png"
    fig.savefig(png_path, dpi=140)

    if args.pdf:
        pdf_dir = Path(args.pdf).parent
        pdf_dir.mkdir(parents=True, exist_ok=True)
        with PdfPages(args.pdf) as pdf:
            pdf.savefig(fig, bbox_inches='tight')

    plt.close(fig)

    print(f"PNG saved: {png_path}")
    if args.pdf:
        print(f"PDF saved: {args.pdf}")

if __name__ == "__main__":
    main()
