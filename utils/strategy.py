"""Backtest engine for Bollinger Bands strategy — parametrizable por par."""

import pandas as pd
import streamlit as st

INITIAL_CAPITAL = 5_000.0


def _candle_ok(
    open_p: float, high_p: float, low_p: float, close_p: float,
    pip_size: float,
) -> bool:
    """Return True if candle meets body/wick size requirements."""
    body_min = 7 * pip_size
    wick_max = 4 * pip_size
    body = abs(close_p - open_p)
    upper_wick = high_p - max(open_p, close_p)
    lower_wick = min(open_p, close_p) - low_p
    return body >= body_min and upper_wick <= wick_max and lower_wick <= wick_max


def _detect_signal(row: pd.Series) -> str | None:
    """Return 'BUY', 'SELL', or None based on candle vs Bollinger mid-band."""
    bbm = row["bb_bbm"]
    o, c = row["OPEN"], row["CLOSE"]
    if o > bbm and c > bbm and c > o:
        return "BUY"
    if o < bbm and c < bbm and c < o:
        return "SELL"
    return None


def _find_close(
    df: pd.DataFrame,
    start_idx: int,
    trade_type: str,
    sl: float,
    tp: float,
) -> dict | None:
    """Search forward from start_idx for first SL or TP hit."""
    for j in range(start_idx, len(df)):
        candle = df.iloc[j]
        hit_sl = hit_tp = False

        if trade_type == "BUY":
            hit_sl = candle["LOW"] <= sl
            hit_tp = candle["HIGH"] >= tp
        else:
            hit_sl = candle["HIGH"] >= sl
            hit_tp = candle["LOW"] <= tp

        if hit_sl:
            return {"idx": j, "time": candle.name, "price": sl, "hit": "SL"}
        if hit_tp:
            return {"idx": j, "time": candle.name, "price": tp, "hit": "TP"}

    return None


def _calc_pnl(
    trade_type: str,
    entry: float,
    exit_price: float,
    pip_size: float,
    pip_value: float,
    commission: float,
) -> float:
    """Calculate net P&L in USD (including commission).

    pip_value must be the effective value already adjusted for lot size.
    """
    pnl_pips = (
        (exit_price - entry) / pip_size
        if trade_type == "BUY"
        else (entry - exit_price) / pip_size
    )
    return pnl_pips * pip_value - commission


@st.cache_data
def run_backtest(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Execute full backtest of the Bollinger Bands strategy.

    Rules:
    - Signal on candle i → entry at OPEN of candle i+1
    - SL and TP in pips (from params)
    - Stop trading for the day after any losing trade

    Args:
        df:     OHLC DataFrame with 'bb_bbm' column and DatetimeIndex.
        params: Dict with keys: sl_pips, tp_pips, pip_size, pip_value,
                lote, comision.
                pip_value must be the effective USD value per pip
                already adjusted for lot size.

    Returns:
        DataFrame with one row per trade and cumulative Capital column.
    """
    sl_pips   = params["sl_pips"]
    tp_pips   = params["tp_pips"]
    pip_size  = params["pip_size"]
    pip_value = params["pip_value"]
    lote      = params["lote"]
    comision  = params["comision"]

    capital = INITIAL_CAPITAL
    results = []

    current_day = None
    puede_operar = True
    registro_primera_operacion = False

    for i in range(1, len(df) - 1):
        row = df.iloc[i]
        next_row = df.iloc[i + 1]

        entry_time = next_row.name
        if pd.isna(entry_time):
            continue

        entry_date = entry_time.date()

        # Reset diario
        if current_day != entry_date:
            current_day = entry_date
            puede_operar = True
            registro_primera_operacion = False

        if not puede_operar:
            continue

        # Filtro de vela
        if not _candle_ok(row["OPEN"], row["HIGH"], row["LOW"], row["CLOSE"], pip_size):
            continue

        signal = _detect_signal(row)
        if signal is None:
            continue

        entry_price = next_row["OPEN"]

        if signal == "BUY":
            sl = entry_price - sl_pips * pip_size
            tp = entry_price + tp_pips * pip_size
        else:
            sl = entry_price + sl_pips * pip_size
            tp = entry_price - tp_pips * pip_size

        close_info = _find_close(df, i + 1, signal, sl, tp)
        if close_info is None:
            continue

        pnl = _calc_pnl(signal, entry_price, close_info["price"], pip_size, pip_value, comision)
        capital += pnl

        results.append({
            "Fecha Apertura": entry_time,
            "Tipo":           signal,
            "Volumen":        lote,
            "Entrada":        entry_price,
            "S/L":            sl,
            "T/P":            tp,
            "Fecha Cierre":   close_info["time"],
            "Cierre":         close_info["price"],
            "Comisión":       -comision,
            "Beneficio":      pnl,
            "Capital":        capital,
        })

        # Control diario: para si hay pérdida
        if not registro_primera_operacion:
            registro_primera_operacion = True
            if pnl < 0:
                puede_operar = False
        elif pnl < 0:
            puede_operar = False

    return pd.DataFrame(results) if results else pd.DataFrame()
