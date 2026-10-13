"""
hermes_data_io.py
==================
Loads and validates OHLCV CSVs for the crypto grid backtester.

Expected file naming (place under --data-dir, default ./data):
    {SYMBOL}_{TIMEFRAME}.csv          e.g. BTCUSDT_1h.csv, ETHUSDT_15m.csv

Expected columns (header row, case-insensitive):
    timestamp, open, high, low, close, volume
timestamp must be parseable (ISO8601 or epoch seconds/ms), UTC assumed unless
a timezone offset is present in the strings.
"""

from __future__ import annotations
import os
import pandas as pd


REQUIRED_COLS = ["timestamp", "open", "high", "low", "close", "volume"]


class DataUnavailable(Exception):
    pass


def load_ohlcv(data_dir: str, symbol: str, timeframe: str) -> pd.DataFrame:
    path = os.path.join(data_dir, f"{symbol}_{timeframe}.csv")
    if not os.path.exists(path):
        raise DataUnavailable(f"missing file: {path}")

    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise DataUnavailable(f"{path}: missing columns {missing}")

    # timestamp parsing: try ISO first, then epoch ms, then epoch s
    ts = df["timestamp"]
    parsed = pd.to_datetime(ts, utc=True, errors="coerce")
    if parsed.isna().mean() > 0.5:
        for unit in ("ms", "s"):
            try:
                cand = pd.to_datetime(ts.astype("int64"), unit=unit, utc=True)
                if cand.notna().all():
                    parsed = cand
                    break
            except (ValueError, TypeError):
                continue
    if parsed.isna().any():
        raise DataUnavailable(f"{path}: unparseable timestamps in {int(parsed.isna().sum())} rows")
    df["timestamp"] = parsed

    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    bad = df[["open", "high", "low", "close", "volume"]].isna().any(axis=1)
    if bad.any():
        df = df[~bad]  # drop invalid rows, logged reason: non-numeric OHLCV

    df = df.sort_values("timestamp")
    dupes = df["timestamp"].duplicated().sum()
    if dupes:
        df = df.drop_duplicates(subset="timestamp", keep="last")

    df = df.reset_index(drop=True)
    if len(df) < 50:
        raise DataUnavailable(f"{path}: only {len(df)} usable rows after cleaning (need >=50)")

    # Exclude an incomplete final candle by default -- we can't know if the
    # last row is a closed candle from a CSV alone, so this is a documented
    # assumption: always drop the very last row before backtesting.
    df = df.iloc[:-1].reset_index(drop=True)
    return df


def slice_last_n_days(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Most recent N calendar days, or the max contiguous history available
    when less than N days exists (per skill Default Assumptions)."""
    if df.empty:
        return df
    cutoff = df["timestamp"].iloc[-1] - pd.Timedelta(days=days)
    return df[df["timestamp"] >= cutoff].reset_index(drop=True)
