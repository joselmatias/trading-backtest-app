"""Performance metrics calculation for backtest results."""

import pandas as pd
import streamlit as st

INITIAL_CAPITAL = 5_000.0


@st.cache_data
def calculate_metrics(df_trades: pd.DataFrame) -> dict:
    """Calculate key performance metrics from trade history.

    Args:
        df_trades: DataFrame returned by run_backtest().

    Returns:
        Dict with capital, trade counts, win rate, and drawdown stats.
    """
    if df_trades.empty:
        return {}

    capital_final = df_trades["Capital"].iloc[-1]
    total = len(df_trades)
    wins = int((df_trades["Beneficio"] > 0).sum())
    losses = int((df_trades["Beneficio"] < 0).sum())
    win_rate = wins / total * 100 if total > 0 else 0.0

    # Build equity series starting from initial capital
    equity = pd.concat([
        pd.Series([INITIAL_CAPITAL]),
        df_trades["Capital"].reset_index(drop=True),
    ])
    running_max = equity.cummax()
    dd_abs = running_max - equity
    dd_pct = (running_max - equity) / running_max * 100

    return {
        "capital_inicial": INITIAL_CAPITAL,
        "capital_final": capital_final,
        "total_trades": total,
        "win_trades": wins,
        "loss_trades": losses,
        "win_rate": win_rate,
        "max_drawdown_abs": float(dd_abs.max()),
        "max_drawdown_pct": float(dd_pct.max()),
    }
