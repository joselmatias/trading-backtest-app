"""Backtest engine for Bollinger Bands strategy — parametrizable por par."""

import pandas as pd
import streamlit as st

INITIAL_CAPITAL = 5_000.0


def _candle_ok(
    open_p: float, high_p: float, low_p: float, close_p: float,
    pip_size: float,
    body_min_pips: int = 9,
    wick_max_pips: int = 4,
) -> bool:
    """Return True if candle meets body/wick size requirements."""
    body_min = body_min_pips * pip_size
    wick_max = wick_max_pips * pip_size
    body = abs(close_p - open_p)
    upper_wick = high_p - max(open_p, close_p)
    lower_wick = min(open_p, close_p) - low_p
    return body >= body_min and upper_wick <= wick_max and lower_wick <= wick_max


def _detect_signal(row: pd.Series) -> str | None:
    """Return 'BUY', 'SELL', or None based on candle vs Bollinger mid-band."""
    bbm  = row["bb_bbm"]
    rsi2 = row["rsi_2"]
    o, c = row["OPEN"], row["CLOSE"]
    if o > bbm and c > bbm and c > o and rsi2 <= 5:
        return "BUY"
    if o < bbm and c < bbm and c < o and rsi2 >= 95:
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
    - Stop new entries for the rest of the day when a trade closes with SL
      (block starts at the exact SL close timestamp)
    - Maximum 2 simultaneous open positions at any time

    Args:
        df:     OHLC DataFrame with 'bb_bbm' column and DatetimeIndex.
        params: Dict with keys: sl_pips, tp_pips, pip_size, pip_value,
                lote, comision.
                pip_value must be the effective USD value per pip
                already adjusted for lot size.

    Returns:
        DataFrame with one row per trade and cumulative Capital column.
    """
    sl_pips        = params["sl_pips"]
    tp_pips        = params["tp_pips"]
    pip_size       = params["pip_size"]
    pip_value      = params["pip_value"]
    lote           = params["lote"]
    comision       = params["comision"]
    body_min_pips  = params.get("body_min_pips", 9)
    wick_max_pips  = params.get("wick_max_pips", 4)

    capital = INITIAL_CAPITAL
    results = []

    # key: date, value: datetime from which that day is blocked
    blocked_from: dict = {}

    for i in range(1, len(df) - 1):
        row = df.iloc[i]
        next_row = df.iloc[i + 1]

        entry_time = next_row.name
        if pd.isna(entry_time):
            continue

        entry_date = entry_time.date()

        # Skip if this entry falls within a blocked window
        if entry_date in blocked_from and entry_time >= blocked_from[entry_date]:
            continue

        # Límite de posiciones simultáneas: máximo 2
        open_positions = sum(
            1 for t in results
            if t["Fecha Apertura"] <= entry_time < t["Fecha Cierre"]
        )
        if open_positions >= 2:
            continue

        # Filtro de vela
        if not _candle_ok(row["OPEN"], row["HIGH"], row["LOW"], row["CLOSE"], pip_size, body_min_pips, wick_max_pips):
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

        body_pips = round(abs(row["CLOSE"] - row["OPEN"]) / pip_size, 1)

        results.append({
            "Fecha Apertura": entry_time,
            "Tipo":           signal,
            "Volumen":        lote,
            "Cuerpo (pips)":  body_pips,
            "Entrada":        entry_price,
            "S/L":            sl,
            "T/P":            tp,
            "Fecha Cierre":   close_info["time"],
            "Cierre":         close_info["price"],
            "Comisión":       -comision,
            "Beneficio":      pnl,
            "Capital":        capital,
        })

        # Block rest of close day if trade hit SL (pnl < 0)
        if pnl < 0:
            close_dt   = close_info["time"]
            close_date = close_dt.date()
            if close_date not in blocked_from or close_dt < blocked_from[close_date]:
                blocked_from[close_date] = close_dt

    return pd.DataFrame(results) if results else pd.DataFrame()
