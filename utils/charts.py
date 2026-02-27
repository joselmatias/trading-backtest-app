"""Plotly chart builders for backtest visualization."""

import pandas as pd
import plotly.graph_objects as go

INITIAL_CAPITAL = 5_000.0
COLOR_BLUE = "#1f77b4"
COLOR_RED = "#ff4444"
COLOR_GREEN = "#00cc66"


def plot_equity_curve(df_trades: pd.DataFrame) -> go.Figure:
    """Line chart of cumulative capital over time.

    Starts at INITIAL_CAPITAL (first trade open), ends at last trade close.
    """
    dates = [df_trades["Fecha Apertura"].iloc[0]] + df_trades["Fecha Cierre"].tolist()
    equity = [INITIAL_CAPITAL] + df_trades["Capital"].tolist()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=equity,
        mode="lines+markers",
        line=dict(color=COLOR_BLUE, width=2),
        marker=dict(size=5),
        name="Capital",
        hovertemplate="<b>%{x}</b><br>Capital: $%{y:,.2f}<extra></extra>",
    ))
    fig.add_hline(
        y=INITIAL_CAPITAL,
        line_dash="dot",
        line_color="gray",
        annotation_text=f"Capital Inicial ${INITIAL_CAPITAL:,.0f}",
        annotation_position="bottom right",
    )
    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Fecha",
        yaxis_title="Capital (USD)",
        hovermode="x unified",
        template="plotly_dark",
        margin=dict(t=50, b=40),
    )
    return fig


def _build_equity_series(df_trades: pd.DataFrame) -> pd.Series:
    """Build equity series indexed by Fecha Cierre, prepended with initial capital."""
    first_date = df_trades["Fecha Cierre"].iloc[0]
    init = pd.Series([INITIAL_CAPITAL], index=[first_date])
    rest = df_trades.set_index("Fecha Cierre")["Capital"]
    return pd.concat([init, rest])


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
