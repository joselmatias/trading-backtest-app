"""Data loading and indicator calculation for EURUSD M15 backtest."""

import pandas as pd
import streamlit as st
from ta.volatility import BollingerBands
from pathlib import Path

DATA_PATH = Path("data/EURUSD_M15.csv")
BB_WINDOW = 20
BB_DEV = 2


@st.cache_data
def load_csv() -> pd.DataFrame | None:
    """Load and preprocess OHLC CSV exported from MetaTrader.

    Expects tab-separated columns: <DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> ...
    Returns DataFrame with DatetimeIndex and uppercase OHLC columns, or None on error.
    """
    if not DATA_PATH.exists():
        return None
    try:
        df = pd.read_csv(
            DATA_PATH,
            sep="\t",
            encoding="utf-8-sig",
            skipinitialspace=True,
        )
        # Strip angle brackets from column names: <DATE> -> DATE
        df.columns = [col.strip("<>").strip() for col in df.columns]

        required_raw = {"DATE", "TIME", "OPEN", "HIGH", "LOW", "CLOSE"}
        if not required_raw.issubset(df.columns):
            return None

        df["datetime"] = pd.to_datetime(
            df["DATE"] + " " + df["TIME"],
            format="%Y.%m.%d %H:%M:%S",
        )
        df = df.set_index("datetime").sort_index()
        df = df[["OPEN", "HIGH", "LOW", "CLOSE"]].astype(float)
        return df

    except Exception:
        return None


@st.cache_data
def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add Bollinger Bands middle band (bb_bbm) to the OHLC DataFrame.

    Drops rows where bb_bbm is NaN (first BB_WINDOW - 1 rows).
    """
    df = df.copy()
    bb = BollingerBands(close=df["CLOSE"], window=BB_WINDOW, window_dev=BB_DEV)
    df["bb_bbm"] = bb.bollinger_mavg()
    return df.dropna(subset=["bb_bbm"])
