"""Plotly chart builders for backtest visualization."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

INITIAL_CAPITAL = 5_000.0
COMMISSION = 2.5
COLOR_BLUE = "#1f77b4"
COLOR_RED = "#ff4444"
COLOR_GREEN = "#00cc66"


def plot_equity_curve(df_trades: pd.DataFrame) -> go.Figure:
    """Equity curve (top) + drawdown % mini chart (bottom), shared X axis."""
    events = []  # (datetime, capital_delta)
    for _, row in df_trades.iterrows():
        is_multiday = row["Fecha Cierre"].date() > row["Fecha Apertura"].date()
        if is_multiday:
            events.append((row["Fecha Apertura"], -COMMISSION))
            events.append((row["Fecha Cierre"], row["Beneficio"] + COMMISSION))
        else:
            events.append((row["Fecha Cierre"], row["Beneficio"]))

    events.sort(key=lambda x: x[0])

    dates = [df_trades["Fecha Apertura"].min()]
    equity = [INITIAL_CAPITAL]
    capital = INITIAL_CAPITAL
    for dt, delta in events:
        capital = round(capital + delta, 2)
        dates.append(dt)
        equity.append(capital)

    # Drawdown %
    eq_series = pd.Series(equity, index=dates)
    running_max = eq_series.cummax()
    dd_pct = -((running_max - eq_series) / running_max * 100)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.72, 0.28],
        vertical_spacing=0.03,
    )

    # ── Row 1: Equity Curve ────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=dates, y=equity,
        mode="lines+markers",
        line=dict(color=COLOR_BLUE, width=2),
        marker=dict(size=4),
        name="Capital",
        hovertemplate="<b>%{x}</b><br>Capital: $%{y:,.2f}<extra></extra>",
    ), row=1, col=1)

    # Línea capital inicial como trace (add_hline no soporta row= en todas las versiones)
    fig.add_trace(go.Scatter(
        x=[dates[0], dates[-1]],
        y=[INITIAL_CAPITAL, INITIAL_CAPITAL],
        mode="lines",
        line=dict(color="gray", width=1, dash="dot"),
        name=f"Capital Inicial ${INITIAL_CAPITAL:,.0f}",
        hoverinfo="skip",
        showlegend=False,
    ), row=1, col=1)

    # ── Row 2: Drawdown % mini ─────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=dates, y=dd_pct.values,
        mode="lines",
        line=dict(color=COLOR_RED, width=1),
        fill="tozeroy",
        fillcolor="rgba(255, 68, 68, 0.25)",
        name="Drawdown %",
        hovertemplate="<b>%{x}</b><br>DD: %{y:.2f}%<extra></extra>",
    ), row=2, col=1)

    fig.update_layout(
        title="Equity Curve",
        hovermode="x unified",
        template="plotly_dark",
        showlegend=False,
        margin=dict(t=50, b=40),
        height=520,
    )
    fig.update_yaxes(title_text="Capital (USD)", row=1, col=1)
    fig.update_yaxes(title_text="DD (%)", row=2, col=1)
    fig.update_xaxes(title_text="Fecha", row=2, col=1)
    return fig


def _build_equity_series(df_trades: pd.DataFrame) -> pd.Series:
    """Build equity series sorted chronologically using the same event logic as plot_equity_curve.

    Multi-day trades: commission at Fecha Apertura, gross P&L at Fecha Cierre.
    Same-day trades: single net event at Fecha Cierre.
    """
    events = []
    for _, row in df_trades.iterrows():
        is_multiday = row["Fecha Cierre"].date() > row["Fecha Apertura"].date()
        if is_multiday:
            events.append((row["Fecha Apertura"], -COMMISSION))
            events.append((row["Fecha Cierre"], row["Beneficio"] + COMMISSION))
        else:
            events.append((row["Fecha Cierre"], row["Beneficio"]))

    events.sort(key=lambda x: x[0])

    dates = [df_trades["Fecha Apertura"].min()]
    values = [INITIAL_CAPITAL]
    capital = INITIAL_CAPITAL
    for dt, delta in events:
        capital = round(capital + delta, 2)
        dates.append(dt)
        values.append(capital)

    return pd.Series(values, index=dates)


def plot_drawdown_abs(df_trades: pd.DataFrame) -> go.Figure:
    """Area chart of absolute drawdown in USD (shown as negative values)."""
    equity = _build_equity_series(df_trades)
    running_max = equity.cummax()
    dd = -(running_max - equity)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd.index,
        y=dd.values,
        fill="tozeroy",
        line=dict(color=COLOR_RED, width=1),
        fillcolor="rgba(255, 68, 68, 0.3)",
        name="Drawdown $",
        hovertemplate="<b>%{x}</b><br>Drawdown: $%{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        title="Drawdown Absoluto (USD)",
        xaxis_title="Fecha",
        yaxis_title="Drawdown (USD)",
        template="plotly_dark",
        margin=dict(t=50, b=40),
    )
    return fig


def plot_drawdown_pct(df_trades: pd.DataFrame) -> go.Figure:
    """Line chart of relative drawdown as percentage (shown as negative values)."""
    equity = _build_equity_series(df_trades)
    running_max = equity.cummax()
    dd_pct = -((running_max - equity) / running_max * 100)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd_pct.index,
        y=dd_pct.values,
        mode="lines",
        line=dict(color=COLOR_RED, width=2),
        fill="tozeroy",
        fillcolor="rgba(255, 68, 68, 0.15)",
        name="Drawdown %",
        hovertemplate="<b>%{x}</b><br>Drawdown: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        title="Drawdown Relativo (%)",
        xaxis_title="Fecha",
        yaxis_title="Drawdown (%)",
        template="plotly_dark",
        margin=dict(t=50, b=40),
    )
    return fig


# ── Analytics charts ──────────────────────────────────────────────────────────

def _bar_colors(values: list) -> list[str]:
    """Green for positive values, red for negative."""
    return [COLOR_GREEN if v >= 0 else COLOR_RED for v in values]


def plot_pnl_by_weekday(df_analysis: pd.DataFrame) -> go.Figure:
    """Bar chart of total P/L per weekday."""
    labels = df_analysis["weekday"].tolist()
    values = df_analysis["total_pnl"].tolist()
    trades = df_analysis["trades"].tolist()

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=_bar_colors(values),
        hovertemplate="<b>%{x}</b><br>P/L: $%{y:,.2f}<br>Trades: %{customdata}<extra></extra>",
        customdata=trades,
    ))
    fig.add_hline(y=0, line_color="gray", line_width=1)
    fig.update_layout(
        title="P/L por Día de la Semana",
        xaxis_title="Día", yaxis_title="P/L (USD)",
        template="plotly_dark", margin=dict(t=50, b=40),
    )
    return fig


def plot_pnl_by_hour(df_analysis: pd.DataFrame) -> go.Figure:
    """Bar chart of total P/L per entry hour."""
    hours  = df_analysis["hour"].tolist()
    values = df_analysis["total_pnl"].tolist()
    trades = df_analysis["trades"].tolist()

    fig = go.Figure(go.Bar(
        x=hours, y=values,
        marker_color=_bar_colors(values),
        hovertemplate="<b>%{x}:00h</b><br>P/L: $%{y:,.2f}<br>Trades: %{customdata}<extra></extra>",
        customdata=trades,
    ))
    fig.add_hline(y=0, line_color="gray", line_width=1)
    fig.update_layout(
        title="P/L por Hora de Entrada",
        xaxis=dict(title="Hora", dtick=1),
        yaxis_title="P/L (USD)",
        template="plotly_dark", margin=dict(t=50, b=40),
    )
    return fig


def plot_long_vs_short(df_analysis: pd.DataFrame) -> go.Figure:
    """Grouped bar chart comparing BUY vs SELL on key metrics."""
    tipos  = df_analysis["Tipo"].tolist()
    colors = [COLOR_GREEN if t == "BUY" else COLOR_RED for t in tipos]

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("Total P/L ($)", "Win Rate (%)", "Avg P/L por Trade ($)"),
    )
    for col, metric in enumerate(["Total P/L", "Win Rate", "Avg P/L"], start=1):
        fig.add_trace(go.Bar(
            x=tipos, y=df_analysis[metric].tolist(),
            marker_color=colors, showlegend=False,
            hovertemplate=f"<b>%{{x}}</b><br>{metric}: %{{y:.2f}}<extra></extra>",
        ), row=1, col=col)

    fig.update_layout(
        title="Long vs Short — Comparativa",
        template="plotly_dark", margin=dict(t=60, b=40),
    )
    return fig


def plot_wins_losses_by_day(df_analysis: pd.DataFrame) -> go.Figure:
    """Stacked bar chart of daily wins and losses."""
    dates = df_analysis["date"].tolist()
    wins  = df_analysis.get("Win",  pd.Series(dtype=int)).tolist()
    losses = df_analysis.get("Loss", pd.Series(dtype=int)).tolist()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates, y=wins, name="Win", marker_color=COLOR_GREEN,
        hovertemplate="<b>%{x}</b><br>Wins: %{y}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=dates, y=losses, name="Loss", marker_color=COLOR_RED,
        hovertemplate="<b>%{x}</b><br>Losses: %{y}<extra></extra>",
    ))
    fig.update_layout(
        title="Wins / Losses por Día",
        barmode="stack",
        xaxis_title="Fecha", yaxis_title="Trades",
        template="plotly_dark", margin=dict(t=50, b=40),
    )
    return fig


def plot_monthly_heatmap(df_monthly: pd.DataFrame) -> go.Figure:
    """Heatmap of monthly P/L (rows=year, cols=month)."""
    data = df_monthly.drop(columns=["Total"], errors="ignore")
    z    = data.values.tolist()
    text = [[f"${v:,.0f}" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        x=data.columns.tolist(),
        y=[str(y) for y in data.index.tolist()],
        z=z,
        text=text,
        texttemplate="%{text}",
        zmid=0,
        colorscale=[[0, COLOR_RED], [0.5, "#1a1a2e"], [1, COLOR_GREEN]],
        hovertemplate="<b>%{y} — %{x}</b><br>P/L: $%{z:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        title="Monthly Performance ($)",
        template="plotly_dark",
        margin=dict(t=50, b=40),
    )
    return fig


def plot_streaks(df_streaks: pd.DataFrame) -> go.Figure:
    """Bar chart of consecutive win/loss streaks (positive = wins, negative = losses)."""
    colors = [COLOR_GREEN if t == "Win" else COLOR_RED for t in df_streaks["tipo"]]

    fig = go.Figure(go.Bar(
        x=df_streaks["racha"],
        y=df_streaks["longitud_signed"],
        marker_color=colors,
        customdata=list(zip(df_streaks["tipo"], df_streaks["longitud"], df_streaks["pnl"])),
        hovertemplate=(
            "<b>Racha #%{x}</b><br>"
            "Tipo: %{customdata[0]}<br>"
            "Longitud: %{customdata[1]} trades<br>"
            "P&L acumulado: $%{customdata[2]:,.2f}<extra></extra>"
        ),
    ))
    fig.add_hline(y=0, line_color="gray", line_width=1)
    fig.update_layout(
        title="Rachas Consecutivas (Wins / Losses)",
        xaxis_title="Racha #",
        yaxis_title="Trades consecutivos",
        template="plotly_dark",
        margin=dict(t=50, b=40),
    )
    return fig


def plot_streak_frequency(df_wins: pd.DataFrame, df_losses: pd.DataFrame) -> go.Figure:
    """Side-by-side bar charts of streak length frequency for wins and losses."""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Rachas Ganadoras (Win)", "Rachas Perdedoras (Loss)"),
    )

    fig.add_trace(go.Bar(
        x=df_wins["Longitud Racha"],
        y=df_wins["Frec. Relativa (%)"],
        marker_color=COLOR_GREEN,
        name="Win",
        customdata=list(zip(df_wins["N° Rachas"], df_wins["Frec. Acumulada (%)"])),
        hovertemplate=(
            "<b>Longitud %{x}</b><br>"
            "N° Rachas: %{customdata[0]}<br>"
            "Frec. Relativa: %{y:.2f}%<br>"
            "Frec. Acumulada: %{customdata[1]:.2f}%<extra></extra>"
        ),
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=df_losses["Longitud Racha"],
        y=df_losses["Frec. Relativa (%)"],
        marker_color=COLOR_RED,
        name="Loss",
        customdata=list(zip(df_losses["N° Rachas"], df_losses["Frec. Acumulada (%)"])),
        hovertemplate=(
            "<b>Longitud %{x}</b><br>"
            "N° Rachas: %{customdata[0]}<br>"
            "Frec. Relativa: %{y:.2f}%<br>"
            "Frec. Acumulada: %{customdata[1]:.2f}%<extra></extra>"
        ),
    ), row=1, col=2)

    fig.update_xaxes(title_text="Trades consecutivos", dtick=1)
    fig.update_yaxes(title_text="Frecuencia relativa (%)", row=1, col=1)
    fig.update_yaxes(title_text="Frecuencia relativa (%)", row=1, col=2)
    fig.update_layout(
        title="Frecuencia de Rachas por Longitud",
        template="plotly_dark",
        showlegend=False,
        margin=dict(t=60, b=50),
    )
    return fig


def plot_pnl_frequency(pnl: pd.Series) -> go.Figure:
    """Two-panel chart: P&L histogram (relative %) + cumulative distribution (CDF)."""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Distribución de P&L (Frecuencia Relativa)", "Frecuencia Acumulada (CDF)"),
        column_widths=[0.55, 0.45],
    )

    # ── Left: histogram with auto bins ────────────────────────────────────────
    counts, edges = np.histogram(pnl, bins=20)
    mids = (edges[:-1] + edges[1:]) / 2
    total = counts.sum()
    rel = counts / total * 100
    bar_w = (edges[1] - edges[0]) * 0.85
    colors = [COLOR_GREEN if m >= 0 else COLOR_RED for m in mids]

    fig.add_trace(go.Bar(
        x=mids, y=rel,
        width=bar_w,
        marker_color=colors,
        name="Frecuencia relativa",
        hovertemplate="P&L: $%{x:,.0f}<br>Frecuencia: %{y:.1f}%<br>Trades: %{customdata}<extra></extra>",
        customdata=counts,
    ), row=1, col=1)
    fig.add_vline(x=0, line_dash="dot", line_color="gray", row=1, col=1)

    # ── Right: CDF ────────────────────────────────────────────────────────────
    sorted_pnl = np.sort(pnl.values)
    cdf = np.arange(1, len(sorted_pnl) + 1) / len(sorted_pnl) * 100

    fig.add_trace(go.Scatter(
        x=sorted_pnl, y=cdf,
        mode="lines",
        line=dict(color="orange", width=2),
        name="CDF acumulada",
        hovertemplate="P&L: $%{x:,.2f}<br>Acumulada: %{y:.1f}%<extra></extra>",
        fill="tozeroy",
        fillcolor="rgba(255,165,0,0.10)",
    ), row=1, col=2)
    fig.add_vline(x=0, line_dash="dot", line_color="gray", row=1, col=2)
    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                  annotation_text="50%", annotation_position="right",
                  row=1, col=2)

    fig.update_layout(
        title="Distribución de P&L — Frecuencia Relativa y Acumulada",
        template="plotly_dark",
        margin=dict(t=60, b=50),
        showlegend=False,
    )
    fig.update_xaxes(title_text="P&L ($)", row=1, col=1)
    fig.update_xaxes(title_text="P&L ($)", row=1, col=2)
    fig.update_yaxes(title_text="% de trades", row=1, col=1)
    fig.update_yaxes(title_text="% acumulado", range=[0, 105], row=1, col=2)
    return fig


def plot_trade_duration(durations: pd.Series) -> go.Figure:
    """Histogram of trade durations in minutes with average line."""
    avg = durations.mean()

    fig = go.Figure(go.Histogram(
        x=durations, nbinsx=40,
        marker_color=COLOR_BLUE, opacity=0.85,
        hovertemplate="Duración: %{x:.0f} min<br>Trades: %{y}<extra></extra>",
    ))
    fig.add_vline(
        x=avg, line_dash="dash", line_color="orange",
        annotation_text=f"Promedio: {avg:.0f} min",
        annotation_position="top right",
    )
    fig.update_layout(
        title="Distribución de Duración de Trades",
        xaxis_title="Duración (minutos)", yaxis_title="Número de Trades",
        template="plotly_dark", margin=dict(t=50, b=40),
    )
    return fig
