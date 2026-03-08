"""Data loading and indicator calculation for EURUSD M15 backtest."""

import pandas as pd
import streamlit as st
from ta.volatility import BollingerBands
from pathlib import Path

# Registro de datasets disponibles: nombre_display → ruta CSV
DATASETS: dict[str, Path] = {
    "Seacrest Market": Path("data/seacrest_market/EURUSD_M15.csv"),
    "Alpha":           Path("data/alpha/EURUSD_M15.csv"),
    "Wemastertrade":   Path("data/wemastertrade/EURUSD__M15_202501020100_202603062345.csv"),
}

BB_WINDOW = 20
BB_DEV = 2


@st.cache_data
def load_csv(dataset: str) -> pd.DataFrame | None:
    """Load and preprocess OHLC CSV exported from MetaTrader.

    Args:
        dataset: Nombre del dataset (debe existir en DATASETS).

    Expects tab-separated columns: <DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> ...
    Returns DataFrame with DatetimeIndex and uppercase OHLC columns, or None on error.
    """
    data_path = DATASETS.get(dataset)
    if data_path is None or not data_path.exists():
        return None
    try:
        df = pd.read_csv(
            data_path,
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
