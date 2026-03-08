"""Analytical breakdowns of backtest trade data."""

import pandas as pd
import streamlit as st

WEEKDAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAY_MAP   = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


@st.cache_data
def pnl_by_weekday(df_trades: pd.DataFrame) -> pd.DataFrame:
    """Total and average P/L grouped by weekday of trade entry."""
    df = df_trades.copy()
    df["weekday_num"] = df["Fecha Apertura"].dt.dayofweek
    df["weekday"] = df["weekday_num"].map(WEEKDAY_MAP)
    return (
        df.groupby(["weekday_num", "weekday"])["Beneficio"]
        .agg(total_pnl="sum", trades="count", avg_pnl="mean")
        .reset_index()
        .sort_values("weekday_num")
    )


@st.cache_data
def pnl_by_hour(df_trades: pd.DataFrame) -> pd.DataFrame:
    """Total and average P/L grouped by hour of trade entry (0–23)."""
    df = df_trades.copy()
    df["hour"] = df["Fecha Apertura"].dt.hour
    return (
        df.groupby("hour")["Beneficio"]
        .agg(total_pnl="sum", trades="count", avg_pnl="mean")
        .reset_index()
    )


@st.cache_data
def long_vs_short(df_trades: pd.DataFrame) -> pd.DataFrame:
    """Per-side (BUY/SELL) performance stats."""
    def _stats(g: pd.DataFrame) -> pd.Series:
        wins   = (g["Beneficio"] > 0).sum()
        losses = (g["Beneficio"] < 0).sum()
        total  = len(g)
        return pd.Series({
            "Trades":    total,
            "Wins":      int(wins),
            "Losses":    int(losses),
            "Win Rate":  round(wins / total * 100, 1) if total else 0,
            "Total P/L": round(g["Beneficio"].sum(), 2),
            "Avg P/L":   round(g["Beneficio"].mean(), 2),
            "Avg Win":   round(g.loc[g["Beneficio"] > 0, "Beneficio"].mean(), 2) if wins else 0,
            "Avg Loss":  round(g.loc[g["Beneficio"] < 0, "Beneficio"].mean(), 2) if losses else 0,
        })
    return df_trades.groupby("Tipo", sort=False).apply(_stats).reset_index()


@st.cache_data
def wins_losses_by_day(df_trades: pd.DataFrame) -> pd.DataFrame:
    """Daily count of winning and losing trades."""
    df = df_trades.copy()
    df["date"]   = pd.to_datetime(df["Fecha Apertura"].dt.date)
    df["result"] = df["Beneficio"].apply(lambda x: "Win" if x > 0 else "Loss")
    pivot = (
        df.groupby(["date", "result"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for col in ["Win", "Loss"]:
        if col not in pivot.columns:
            pivot[col] = 0
    return pivot


@st.cache_data
def trade_duration_minutes(df_trades: pd.DataFrame) -> pd.Series:
    """Trade duration in minutes (entry → close)."""
    return (
        (df_trades["Fecha Cierre"] - df_trades["Fecha Apertura"])
        .dt.total_seconds()
        .div(60)
        .rename("duration_min")
    )


@st.cache_data
def streak_analysis(df_trades: pd.DataFrame) -> pd.DataFrame:
    """Consecutive win/loss streaks with length and cumulative P&L per streak."""
    streaks = []
    current_win = None
    count = 0
    pnl = 0.0
    streak_num = 0

    for _, row in df_trades.iterrows():
        is_win = row["Beneficio"] > 0
        if current_win is None or is_win == current_win:
            count += 1
            pnl += row["Beneficio"]
            current_win = is_win
        else:
            streak_num += 1
            streaks.append({
                "racha": streak_num,
                "tipo": "Win" if current_win else "Loss",
                "longitud": count,
                "pnl": round(pnl, 2),
                "longitud_signed": count if current_win else -count,
            })
            current_win = is_win
            count = 1
            pnl = row["Beneficio"]

    if current_win is not None:
        streak_num += 1
        streaks.append({
            "racha": streak_num,
            "tipo": "Win" if current_win else "Loss",
            "longitud": count,
            "pnl": round(pnl, 2),
            "longitud_signed": count if current_win else -count,
        })

    return pd.DataFrame(streaks)


@st.cache_data
def pnl_frequency(df_trades: pd.DataFrame) -> pd.Series:
    """Raw P&L series for frequency distribution and CDF analysis."""
    return df_trades["Beneficio"].copy()
