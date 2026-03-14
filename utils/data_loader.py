"""Data loading and indicator calculation for EURUSD M15 backtest."""

import pandas as pd
import streamlit as st
from ta.volatility import BollingerBands
from pathlib import Path

BB_WINDOW = 20
BB_DEV = 2


@st.cache_data
def load_csv(path: str) -> pd.DataFrame | None:
    """Load and preprocess OHLC CSV exported from MetaTrader.

    Args:
        path: Ruta relativa o absoluta al archivo CSV.

    Expects tab-separated columns: <DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> ...
    Returns DataFrame with DatetimeIndex and uppercase OHLC columns, or None on error.
    """
    data_path = Path(path)
    if not data_path.exists():
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
    from ta.momentum import RSIIndicator
    df = df.copy()
    bb = BollingerBands(close=df["CLOSE"], window=BB_WINDOW, window_dev=BB_DEV)
    df["bb_bbm"] = bb.bollinger_mavg()
    rsi2 = RSIIndicator(close=df["CLOSE"], window=2)
    df["rsi_2"] = rsi2.rsi()
    return df.dropna(subset=["bb_bbm", "rsi_2"])


def calcular_pip_value_usdchf(df_ohlcv: pd.DataFrame, lote: float = 0.25) -> float:
    """Calcula el pip value efectivo en USD para USDCHF al tamaño de lote dado.

    El pip de USDCHF está denominado en CHF, por lo que se convierte a USD
    dividiendo por el precio USDCHF promedio:
        pip_value_usd = (0.0001 / precio_usdchf) × 100_000 × lote

    Args:
        df_ohlcv: DataFrame con columna CLOSE del par USDCHF.
        lote:     Tamaño de lote (default 0.25).

    Returns:
        Pip value efectivo en USD (ya incluye el lote).
    """
    precio_promedio = df_ohlcv["CLOSE"].mean()
    return round((0.0001 / precio_promedio) * 100_000 * lote, 4)
