#!/usr/bin/env python3
import argparse
import sys
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

def fail(msg: str):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)

def main():
    ap = argparse.ArgumentParser(description="Linear trend + simple forecast for a PCP metric CSV.")
    ap.add_argument("--csv", required=True, help="Input CSV path from pmrep (must contain columns: Time,<metric>)")
    ap.add_argument("--metric", required=True, help="Exact metric column name in the CSV (e.g. ds389.cn.opscompleted)")
    ap.add_argument("--interval", default="5min", help="Resample frequency (e.g. 1min, 5min, 30s)")
    ap.add_argument("--horizon_hours", type=int, default=24, help="Forecast horizon in hours (default: 24)")
    ap.add_argument("--threshold", type=float, default=None, help="Optional target value to compute ETA")
    ap.add_argument("--out_forecast", default="/tmp/forecast.csv", help="Output CSV for observed+predicted series")
    args = ap.parse_args()

    # --- Load
    try:
        df = pd.read_csv(args.csv)
    except Exception as e:
        fail(f"Cannot read CSV {args.csv}: {e}")

    if "Time" not in df.columns:
        fail("CSV must have a 'Time' column.")
    if args.metric not in df.columns:
        fail(f"CSV does not contain metric column '{args.metric}'.")

    # --- Parse & clean
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce", utc=False)
    df = df.dropna(subset=["Time"])
    df = df.sort_values("Time").drop_duplicates("Time").set_index("Time")

    # Ensure metric numeric
    s = pd.to_numeric(df[args.metric], errors="coerce").dropna()
    if s.empty:
        fail("No numeric data points found after cleaning.")

    # Align to fixed grid and forward-fill to stabilize ML input
    try:
        s = s.resample(args.interval).last().ffill()
    except Exception as e:
        fail(f"Invalid interval '{args.interval}': {e}")

    if len(s) < 3:
        fail("Not enough points after resampling (need >= 3).")

    # --- Prepare regression variables
    t0 = s.index[0]
    # seconds since t0 -> hours
    X = ((s.index - t0).total_seconds().to_numpy().reshape(-1, 1)) / 3600.0
    y = s.to_numpy(dtype=float)

    # --- Train linear regression
    model = LinearRegression()
    model.fit(X, y)
    slope = float(model.coef_[0])       # units of metric per hour
    intercept = float(model.intercept_)

    # --- Forecast
    freq_off = pd.tseries.frequencies.to_offset(args.interval)
    step_seconds = pd.Timedelta(freq_off).total_seconds()
    n_steps = max(int((args.horizon_hours * 3600) / step_seconds), 1)

    future_idx = pd.date_range(s.index[-1] + freq_off, periods=n_steps, freq=freq_off)
    Xf = ((future_idx - t0).total_seconds().to_numpy().reshape(-1, 1)) / 3600.0
    y_pred = model.predict(Xf)

    # --- Build output (observed + predicted)
    out_hist = pd.DataFrame({"Time": s.index, "value": s.values, "type": "observed"})
    out_pred = pd.DataFrame({"Time": future_idx, "value": y_pred, "type": "predicted"})
    out = pd.concat([out_hist, out_pred], ignore_index=True)
    out.to_csv(args.out_forecast, index=False)

    print(f"Trend slope (per hour): {slope:.6f}")
    print(f"Intercept: {intercept:.6f}")
    print(f"Saved forecast CSV → {args.out_forecast}")

    # --- Optional ETA to threshold
    if args.threshold is not None:
        if slope == 0:
            print(f"ETA: slope=0, cannot reach threshold {args.threshold} from a linear trend.")
        else:
            x_eta_hours = (args.threshold - intercept) / slope
            eta_ts = pd.to_datetime(t0) + pd.to_timedelta(x_eta_hours, unit="h")
            # If forecasted time is before last observed, threshold already crossed under the linear model
            if eta_ts <= s.index[-1]:
                print(f"ETA: threshold {args.threshold} would have been reached by {eta_ts} (<= last observed).")
            else:
                print(f"ETA to {args.threshold}: {eta_ts}")

if __name__ == "__main__":
    main()


