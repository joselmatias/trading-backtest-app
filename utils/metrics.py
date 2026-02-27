"""Performance metrics calculation for backtest results."""

import pandas as pd
import streamlit as st
from math import sqrt, erf

INITIAL_CAPITAL  = 5_000.0
PIP_VALUE        = 2.5      # $ per pip at 0.25 lots
RISK_PER_TRADE   = 50.0     # 20 pips × $2.50
BAR_MINUTES      = 15       # M15


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm_cdf(z: float) -> float:
    return 0.5 * (1 + erf(z / sqrt(2)))


def _streaks(win_flags: list) -> tuple:
    """(max_cw, max_cl, avg_cw, avg_cl) from a list of bool."""
    if not win_flags:
        return 0, 0, 0.0, 0.0
    w_streaks, l_streaks = [], []
    streak, kind = 1, win_flags[0]
    for i in range(1, len(win_flags)):
        if win_flags[i] == kind:
            streak += 1
        else:
            (w_streaks if kind else l_streaks).append(streak)
            streak, kind = 1, win_flags[i]
    (w_streaks if kind else l_streaks).append(streak)
    return (
        max(w_streaks, default=0), max(l_streaks, default=0),
        sum(w_streaks) / len(w_streaks) if w_streaks else 0.0,
        sum(l_streaks) / len(l_streaks) if l_streaks else 0.0,
    )


def _count_runs(win_flags: list) -> int:
    if not win_flags:
        return 0
    runs = 1
    for i in range(1, len(win_flags)):
        if win_flags[i] != win_flags[i - 1]:
            runs += 1
    return runs


def _max_stagnation_days(df_trades: pd.DataFrame) -> int:
    start = df_trades["Fecha Apertura"].min()
    eq = pd.Series(
        [INITIAL_CAPITAL] + df_trades["Capital"].tolist(),
        index=[start] + df_trades["Fecha Cierre"].tolist(),
    )
    eq_d = eq.resample("D").last().ffill()
    peak = eq_d.cummax()
    max_stag = cur = 0
    for under in (eq_d < peak):
        cur = cur + 1 if under else 0
        max_stag = max(max_stag, cur)
    return max_stag


# ── Public functions ──────────────────────────────────────────────────────────

@st.cache_data
def calculate_metrics(df_trades: pd.DataFrame) -> dict:
    """Basic metrics for the top dashboard cards."""
    if df_trades.empty:
        return {}
    capital_final = df_trades["Capital"].iloc[-1]
    total = len(df_trades)
    wins  = int((df_trades["Beneficio"] > 0).sum())
    losses = int((df_trades["Beneficio"] < 0).sum())
    equity = pd.concat([pd.Series([INITIAL_CAPITAL]),
                        df_trades["Capital"].reset_index(drop=True)])
    run_max = equity.cummax()
    dd_abs = run_max - equity
    dd_pct = (run_max - equity) / run_max * 100
    return {
        "capital_inicial":    INITIAL_CAPITAL,
        "capital_final":      capital_final,
        "total_trades":       total,
        "win_trades":         wins,
        "loss_trades":        losses,
        "win_rate":           wins / total * 100 if total else 0.0,
        "max_drawdown_abs":   float(dd_abs.max()),
        "max_drawdown_pct":   float(dd_pct.max()),
    }


@st.cache_data
def calculate_advanced_metrics(df_trades: pd.DataFrame) -> dict:
    """Full performance report metrics."""
    if df_trades.empty:
        return {}

    pnl     = df_trades["Beneficio"]
    capital = df_trades["Capital"]
    n       = len(df_trades)
    wins    = pnl[pnl > 0]
    losses  = pnl[pnl < 0]
    nw, nl  = len(wins), len(losses)

    gross_profit = float(wins.sum())
    gross_loss   = float(losses.sum())
    total_profit = float(pnl.sum())
    avg_win  = float(wins.mean())  if nw else 0.0
    avg_loss = float(losses.mean()) if nl else 0.0
    win_rate = nw / n if n else 0.0

    # Time range
    start  = df_trades["Fecha Apertura"].min()
    end    = df_trades["Fecha Cierre"].max()
    days   = max((end - start).days, 1)
    years  = days / 365.25
    months = days / 30.44

    # Capital series
    equity = pd.concat([pd.Series([INITIAL_CAPITAL]),
                        capital.reset_index(drop=True)])
    run_max = equity.cummax()
    dd_abs  = float((run_max - equity).max())
    dd_pct  = float(((run_max - equity) / run_max * 100).max())

    cap_final    = INITIAL_CAPITAL + total_profit
    cagr         = (cap_final / INITIAL_CAPITAL) ** (1 / years) - 1 if years > 0 else 0.0
    return_pct   = (cap_final - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    ret_dd_ratio = return_pct / dd_pct if dd_pct else 0.0

    # Sharpe (daily equity)
    daily_eq  = df_trades.set_index("Fecha Cierre")["Capital"].resample("D").last().ffill()
    daily_ret = daily_eq.pct_change().dropna()
    sharpe    = float(daily_ret.mean() / daily_ret.std() * sqrt(252)) if daily_ret.std() else 0.0

    # R multiples & SQN
    r_mult   = pnl / RISK_PER_TRADE
    r_exp    = float(r_mult.mean())
    r_std    = float(r_mult.std())
    sqn      = float(sqrt(n) * r_exp / r_std) if r_std else 0.0
    sqn_lbl  = ("Holy Grail" if sqn >= 7 else "Excellent" if sqn >= 5
                else "Good" if sqn >= 3 else "Average" if sqn >= 2 else "Poor")

    # Z-Score
    win_flags = (pnl > 0).tolist()
    R_runs = _count_runs(win_flags)
    z_score = z_prob = 0.0
    if nw > 0 and nl > 0 and n > 2:
        E_R   = 1 + 2 * nw * nl / n
        Var_R = 2 * nw * nl * (2 * nw * nl - n) / (n ** 2 * (n - 1))
        if Var_R > 0:
            z_score = (R_runs - E_R) / sqrt(Var_R)
            z_prob  = _norm_cdf(abs(z_score)) * 100

    # Streaks
    max_cw, max_cl, avg_cw, avg_cl = _streaks(win_flags)

    # Trade durations
    dur_min  = (df_trades["Fecha Cierre"] - df_trades["Fecha Apertura"]).dt.total_seconds() / 60
    dur_bars = dur_min / BAR_MINUTES
    wi, li   = pnl > 0, pnl < 0
    avg_bars   = float(dur_bars.mean())
    avg_bars_w = float(dur_bars[wi].mean()) if nw else 0.0
    avg_bars_l = float(dur_bars[li].mean()) if nl else 0.0

    # Exposure
    exposure = float(dur_min.sum() / (days * 24 * 60) * 100)

    # AHPR
    cap_before = pd.concat([pd.Series([INITIAL_CAPITAL]),
                             capital.iloc[:-1].reset_index(drop=True)])
    ahpr = float(((capital.reset_index(drop=True) - cap_before) / cap_before).mean() * 100)

    # Stagnation
    stag_days = _max_stagnation_days(df_trades)

    # Profit in pips
    profit_in_pips = float(((pnl + 2.5) / PIP_VALUE).sum())

    return {
        # ── Main metrics ──
        "total_profit":      total_profit,
        "n_trades":          n,
        "sharpe_ratio":      sharpe,
        "profit_factor":     gross_profit / abs(gross_loss) if gross_loss else float("inf"),
        "return_dd_ratio":   ret_dd_ratio,
        "winning_pct":       win_rate * 100,
        "profit_in_pips":    profit_in_pips,
        "max_dd_abs":        dd_abs,
        "max_dd_pct":        dd_pct,
        "daily_avg_profit":  total_profit / days,
        "monthly_avg_profit":total_profit / months,
        "avg_trade":         total_profit / n if n else 0.0,
        "yearly_avg_profit": total_profit / years if years else 0.0,
        "yearly_avg_pct":    cagr * 100,
        "annual_max_dd_pct": dd_pct / years if years else dd_pct,
        "r_expectancy":      r_exp,
        "r_expectancy_score":sqn,
        "sqn":               sqn,
        "sqn_label":         sqn_lbl,
        "cagr":              cagr * 100,
        # ── Stats ──
        "wins_losses_ratio": nw / nl if nl else float("inf"),
        "payout_ratio":      abs(avg_win / avg_loss) if avg_loss else 0.0,
        "avg_bars_trade":    avg_bars,
        "ahpr":              ahpr,
        "z_score":           z_score,
        "z_probability":     z_prob,
        "expectancy":        win_rate * avg_win + (1 - win_rate) * avg_loss,
        "deviation":         float(pnl.std()),
        "exposure_pct":      exposure,
        "stagnation_days":   stag_days,
        "stagnation_pct":    stag_days / max(days, 1) * 100,
        # ── Trades ──
        "n_wins":            nw,
        "n_losses":          nl,
        "n_cancelled":       0,
        "gross_profit":      gross_profit,
        "gross_loss":        gross_loss,
        "avg_win":           avg_win,
        "avg_loss":          avg_loss,
        "largest_win":       float(wins.max()) if nw else 0.0,
        "largest_loss":      float(losses.min()) if nl else 0.0,
        "max_consec_wins":   max_cw,
        "max_consec_losses": max_cl,
        "avg_consec_wins":   avg_cw,
        "avg_consec_losses": avg_cl,
        "avg_bars_wins":     avg_bars_w,
        "avg_bars_losses":   avg_bars_l,
    }


@st.cache_data
def monthly_performance(df_trades: pd.DataFrame) -> pd.DataFrame:
    """Monthly P/L pivot: rows = year, columns = month name."""
    month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    df = df_trades.copy()
    df["year"]  = df["Fecha Cierre"].dt.year
    df["month"] = df["Fecha Cierre"].dt.month
    pivot = (
        df.groupby(["year", "month"])["Beneficio"]
        .sum()
        .unstack(fill_value=0)
    )
    pivot.columns = [month_names[c] for c in pivot.columns]
    pivot["Total"] = pivot.sum(axis=1)
    return pivot
