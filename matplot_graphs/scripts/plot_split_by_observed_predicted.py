#!/usr/bin/env python3
"""
plot_split_by_label.py
----------------------
Plot a single CSV that contains BOTH observed and forecasted rows,
distinguished by a label column (e.g., 'type' with values 'observed'/'predicted').

Features
- Distinct colors for observed vs. predicted.
- Vertical line at first predicted timestamp.
- Optional resample and rolling smoothing.
- Optional confidence band if columns like lower/upper or yhat_lower/yhat_upper exist.

Usage
python3 plot_split_by_label.py \
  --csv forecast_opscompleted.csv \
  --time-col Time --value-col value \
  --label-col type --predicted-label predicted \
  --out ./plots/ops_obs_pred.png --pdf ./plots/ops_obs_pred.pdf \
  --resample 1min --rolling 5
"""
import argparse
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

def detect_time_col(df: pd.DataFrame, forced: Optional[str]) -> str:
    if forced and forced in df.columns:
        return forced
    lower = {c.lower(): c for c in df.columns}
    for cand in ["time", "timestamp", "date", "datetime"]:
        if cand in lower:
            return lower[cand]
    return df.columns[0]

def detect_value_col(df: pd.DataFrame, time_col: str, forced: Optional[str]) -> str:
    if forced and forced in df.columns:
        return forced
    # pick first numeric col that's not time
    for c in df.columns:
        if c == time_col: 
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            return c
    raise SystemExit("No numeric value column found; pass --value-col.")

def find_ci_columns(df: pd.DataFrame, base: str):
    candidates = [
        (f"{base}_lower", f"{base}_upper"),
        (f"{base}.lower", f"{base}.upper"),
        ("yhat_lower", "yhat_upper"),
        ("lower", "upper"),
        ("lo", "hi"),
    ]
    for lo, hi in candidates:
        if lo in df.columns and hi in df.columns:
            return lo, hi
    return None, None

def main():
    ap = argparse.ArgumentParser(description="Plot observed vs predicted rows from a single CSV by label.")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--time-col", default=None)
    ap.add_argument("--value-col", default=None)
    ap.add_argument("--label-col", required=True, help="Column that marks observed/predicted rows")
    ap.add_argument("--predicted-label", required=True, help="Value in --label-col that denotes forecast rows")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pdf", default=None)
    ap.add_argument("--resample", default=None, help="Pandas offset alias (e.g., '1min', '30s')")
    ap.add_argument("--resample-agg", default="sum", choices=["sum", "mean", "max", "min"])
    ap.add_argument("--rolling", type=int, default=None, help="Rolling mean window after resample")
    ap.add_argument("--observed-color", default="#1f77b4")
    ap.add_argument("--predicted-color", default="#d62728")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    tcol = detect_time_col(df, args.time_col)
    try:
        df[tcol] = pd.to_datetime(df[tcol])
    except Exception:
        pass
    vcol = detect_value_col(df, tcol, args.value_col)

    if args.label_col not in df.columns:
        raise SystemExit(f"--label-col '{args.label_col}' not found in CSV columns: {list(df.columns)}")

    # Split observed vs predicted
    is_pred = df[args.label_col].astype(str).str.lower() == str(args.predicted_label).lower()
    df_obs = df.loc[~is_pred, [tcol, vcol]].copy()
    df_pred = df.loc[is_pred, [tcol, vcol]].copy()

    # Optional resample & rolling
    def process(ts_df: pd.DataFrame):
        x = ts_df[tcol]
        y = ts_df[vcol]
        if pd.api.types.is_datetime64_any_dtype(x):
            s = pd.Series(y.values, index=x)
            if args.resample:
                if args.resample_agg == "sum":
                    s = s.resample(args.resample).sum()
                elif args.resample_agg == "mean":
                    s = s.resample(args.resample).mean()
                elif args.resample_agg == "max":
                    s = s.resample(args.resample).max()
                elif args.resample_agg == "min":
                    s = s.resample(args.resample).min()
            if args.rolling and args.rolling > 1:
                s = s.rolling(args.rolling, min_periods=1).mean()
            return s
        return pd.Series(y.values, index=x)

    s_obs = process(df_obs)
    s_pred = process(df_pred)

    # Build aligned df (to find forecast start and align x-axis)
    aligned = pd.concat({"Observed": s_obs, "Predicted": s_pred}, axis=1)

    # CI band (optional, if present in CSV)
    lo_col, hi_col = find_ci_columns(df, vcol)
    ci = None
    if lo_col and hi_col and pd.api.types.is_datetime64_any_dtype(aligned.index):
        s_lo = pd.Series(df.loc[is_pred, lo_col].values, index=df.loc[is_pred, tcol])
        s_hi = pd.Series(df.loc[is_pred, hi_col].values, index=df.loc[is_pred, tcol])
        if args.resample:
            agg = args.resample_agg
            if agg == "sum":
                s_lo = s_lo.resample(args.resample).sum()
                s_hi = s_hi.resample(args.resample).sum()
            elif agg == "mean":
                s_lo = s_lo.resample(args.resample).mean()
                s_hi = s_hi.resample(args.resample).mean()
            elif agg == "max":
                s_lo = s_lo.resample(args.resample).max()
                s_hi = s_hi.resample(args.resample).max()
            elif agg == "min":
                s_lo = s_lo.resample(args.resample).min()
                s_hi = s_hi.resample(args.resample).min()
        if args.rolling and args.rolling > 1:
            s_lo = s_lo.rolling(args.rolling, min_periods=1).mean()
            s_hi = s_hi.rolling(args.rolling, min_periods=1).mean()
        ci = pd.concat({"lo": s_lo, "hi": s_hi}, axis=1)

    # Forecast start (first valid predicted index)
    f_start = aligned["Predicted"].first_valid_index()

    # Plot
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(aligned.index, aligned["Observed"], linewidth=1.5, label="Observed", color=args.observed_color)
    ax.plot(aligned.index, aligned["Predicted"], linewidth=1.5, label="Predicted", color=args.predicted_color)

    if ci is not None:
        ci = ci.reindex(aligned.index)
        ax.fill_between(ci.index, ci["lo"], ci["hi"], alpha=0.2, color=args.predicted_color, label="Prediction CI")

    if f_start is not None:
        ax.axvline(f_start, linestyle='--')

    ax.set_title(vcol)
    ax.set_xlabel(tcol)
    ax.set_ylabel(vcol)
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    if pd.api.types.is_datetime64_any_dtype(aligned.index):
        fig.autofmt_xdate()
    ax.legend(loc="best")
    plt.tight_layout()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    if args.pdf:
        with PdfPages(args.pdf) as pdf:
            pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

    print(f"PNG saved: {out_path}")
    if args.pdf:
        print(f"PDF saved: {args.pdf}")

if __name__ == "__main__":
    main()
