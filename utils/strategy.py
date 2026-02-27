"""Backtest engine for Bollinger Bands strategy on EURUSD M15."""

import pandas as pd
import streamlit as st

# --- Strategy constants ---
INITIAL_CAPITAL = 5_000.0
VOLUME = 0.25
COMMISSION = 2.5          # USD per trade
PIP = 0.00010
PIP_VALUE = VOLUME * 10   # $2.50 per pip at 0.25 lots

BODY_MIN = 7 * PIP        # Minimum candle body
WICK_MAX = 4 * PIP        # Maximum wick (upper or lower)
SL_PIPS = 20
TP_PIPS = 100


def _candle_ok(open_p: float, high_p: float, low_p: float, close_p: float) -> bool:
    """Return True if candle meets body/wick size requirements."""
    body = abs(close_p - open_p)
    upper_wick = high_p - max(open_p, close_p)
    lower_wick = min(open_p, close_p) - low_p
    return body >= BODY_MIN and upper_wick <= WICK_MAX and lower_wick <= WICK_MAX


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
    """Search forward from start_idx for first SL or TP hit.

    For ambiguous candles (both hit), SL is prioritised (conservative).

    Returns dict with idx, time, price, hit ('SL'/'TP'), or None if not found.
    """
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


def _calc_pnl(trade_type: str, entry: float, exit_price: float) -> float:
    """Calculate net P&L in USD (including commission)."""
    pnl_pips = (exit_price - entry) / PIP if trade_type == "BUY" else (entry - exit_price) / PIP
    return pnl_pips * PIP_VALUE - COMMISSION


@st.cache_data
def run_backtest(df: pd.DataFrame) -> pd.DataFrame:
    """Execute full backtest of the Bollinger Bands strategy.

    Rules:
    - Signal on candle i → entry at OPEN of candle i+1
    - SL: 20 pips from entry | TP: 100 pips from entry
    - Only 1 active trade at a time
    - Stop trading for the day after any losing trade

    Args:
        df: OHLC DataFrame with 'bb_bbm' column and DatetimeIndex.

    Returns:
        DataFrame with one row per trade and cumulative Capital column.
    """
    capital = INITIAL_CAPITAL
    results: list[dict] = []

    current_day = None
    puede_operar = True
    i = 1

    while i < len(df) - 1:
        row = df.iloc[i]
        next_row = df.iloc[i + 1]

        entry_time = next_row.name
        entry_date = entry_time.date()

        # Daily reset
        if current_day != entry_date:
            current_day = entry_date
            puede_operar = True

        if not puede_operar:
            i += 1
            continue

        # Candle filter
        if not _candle_ok(row["OPEN"], row["HIGH"], row["LOW"], row["CLOSE"]):
            i += 1
            continue

        signal = _detect_signal(row)
        if signal is None:
            i += 1
            continue

        entry_price = next_row["OPEN"]

        if signal == "BUY":
            sl = entry_price - SL_PIPS * PIP
            tp = entry_price + TP_PIPS * PIP
        else:
            sl = entry_price + SL_PIPS * PIP
            tp = entry_price - TP_PIPS * PIP

        # Search for SL/TP hit starting from the entry candle itself
        close_info = _find_close(df, i + 1, signal, sl, tp)

        if close_info is None:
            # Trade never closed (end of data) — skip without recording
            i += 1
            continue

        pnl = _calc_pnl(signal, entry_price, close_info["price"])
        capital += pnl

        results.append({
            "Fecha Apertura": entry_time,
            "Tipo": signal,
            "Volumen": VOLUME,
            "Entrada": entry_price,
            "S/L": sl,
            "T/P": tp,
            "Fecha Cierre": close_info["time"],
            "Cierre": close_info["price"],
            "Comisión": -COMMISSION,
            "Beneficio": pnl,
            "Capital": capital,
        })

        # Stop trading for the day after a loss
        if pnl < 0:
            puede_operar = False

        # Jump past the closing candle (1 trade at a time)
        i = close_info["idx"] + 1

    return pd.DataFrame(results) if results else pd.DataFrame()
