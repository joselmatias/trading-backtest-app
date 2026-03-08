"""Correlation analysis module for multi-asset MT5 CSV data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import streamlit as st

DATA_DIR = Path("data/correlaciones")

BG_COLOR   = "#0a0d14"
ACCENT     = "#00c8ff"
GRID_COLOR = "#1e2535"
TEXT_COLOR = "#e0e4ef"

_PLOTLY_LAYOUT = dict(
    paper_bgcolor=BG_COLOR,
    plot_bgcolor=BG_COLOR,
    font=dict(color=TEXT_COLOR, family="Inter, sans-serif"),
)


# ── Data loading ──────────────────────────────────────────────────────────────

def _parse_mt5_csv(path: Path) -> pd.Series | None:
    """Parse a MT5 tab-separated CSV and return a CLOSE price Series indexed by datetime."""
    try:
        df = pd.read_csv(path, sep="\t", encoding="utf-8-sig", skipinitialspace=True)
        df.columns = [c.strip("<>").strip() for c in df.columns]
        if not {"DATE", "TIME", "CLOSE"}.issubset(df.columns):
            return None
        df["datetime"] = pd.to_datetime(
            df["DATE"] + " " + df["TIME"], format="%Y.%m.%d %H:%M:%S"
        )
        df = df.set_index("datetime").sort_index()
        return df["CLOSE"].astype(float).rename(path.stem)
    except Exception:
        return None


@st.cache_data
def cargar_datos() -> tuple[dict[str, pd.Series], str | None]:
    """Load all MT5 CSVs from data/correlaciones/.

    Returns (series_dict, error_message).
    series_dict keys = file stems; values = Close price Series.
    error_message is None on success, a string on failure.
    """
    if not DATA_DIR.exists():
        return {}, f"Carpeta `{DATA_DIR}` no encontrada. Créala y agrega al menos 2 CSVs de MT5."

    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if len(csv_files) < 2:
        return {}, (
            f"Se encontraron {len(csv_files)} archivo(s) CSV en `{DATA_DIR}`. "
            "Se necesitan al menos 2 para calcular correlaciones."
        )

    series: dict[str, pd.Series] = {}
    for f in csv_files:
        s = _parse_mt5_csv(f)
        if s is not None and not s.empty:
            series[f.stem] = s

    if len(series) < 2:
        return {}, "No se pudieron parsear al menos 2 CSVs válidos. Verifica el formato de columnas."

    return series, None


# ── Resampling ────────────────────────────────────────────────────────────────

TIMEFRAMES = {"M15": None, "1H": "1h", "4H": "4h", "1D": "1D"}


@st.cache_data
def resamplear_series(
    series: dict[str, pd.Series], timeframe: str
) -> dict[str, pd.Series]:
    """Resample all Close price series to a higher timeframe.

    timeframe must be a key of TIMEFRAMES. 'M15' returns the original series.
    Uses last() to get the closing price of each period.
    """
    rule = TIMEFRAMES.get(timeframe)
    if rule is None:
        return series  # M15 — no resampling needed
    return {name: s.resample(rule).last().dropna() for name, s in series.items()}


# ── Return alignment ──────────────────────────────────────────────────────────

@st.cache_data
def alinear_retornos(series: dict[str, pd.Series]) -> pd.DataFrame:
    """Align price series by inner join, forward-fill gaps, then compute log returns.

    Returns a DataFrame where each column is the log-return series for one asset.
    """
    df_prices = pd.concat(series.values(), axis=1, join="inner")
    df_prices.ffill(inplace=True)
    df_returns = np.log(df_prices / df_prices.shift(1)).dropna()
    return df_returns


# ── Charts ────────────────────────────────────────────────────────────────────

def plot_heatmap(df_returns: pd.DataFrame) -> go.Figure:
    """Pearson correlation heatmap with diverging color scale (blue–white–red)."""
    corr = df_returns.corr()
    labels = corr.columns.tolist()
    z = corr.values

    text = [[f"{v:.2f}" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=labels,
        y=labels,
        text=text,
        texttemplate="%{text}",
        colorscale=[
            [0.0,  "#d73027"],
            [0.25, "#f46d43"],
            [0.5,  "#ffffbf"],
            [0.75, "#74add1"],
            [1.0,  "#4575b4"],
        ],
        zmid=0,
        zmin=-1,
        zmax=1,
        colorbar=dict(
            title=dict(text="Correlación", font=dict(color=TEXT_COLOR)),
            tickfont=dict(color=TEXT_COLOR),
        ),
    ))

    fig.update_layout(
        title=dict(text="Mapa de Correlación (Pearson)", font=dict(color=TEXT_COLOR, size=16)),
        **_PLOTLY_LAYOUT,
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_COLOR)),
        yaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_COLOR), autorange="reversed"),
        height=max(400, len(labels) * 70 + 120),
    )
    return fig


def plot_rolling_corr(
    df_returns: pd.DataFrame,
    asset_a: str,
    asset_b: str,
    window: int = 60,
) -> go.Figure:
    """Rolling Pearson correlation between two assets."""
    roll = df_returns[asset_a].rolling(window).corr(df_returns[asset_b]).dropna()

    fig = go.Figure()

    # Fill between 0 and rolling corr (green positive, red negative)
    fig.add_trace(go.Scatter(
        x=roll.index, y=roll.values,
        fill="tozeroy",
        fillcolor="rgba(0,200,100,0.15)",
        line=dict(color=ACCENT, width=1.5),
        name="Correlación rodante",
    ))

    # Reference lines at 0, +0.7, -0.7
    for level, label, color in [
        (0.7,  "+0.7 (alta pos.)", "#00cc66"),
        (-0.7, "−0.7 (alta neg.)", "#ff4444"),
        (0.0,  "0",               "#888888"),
    ]:
        fig.add_trace(go.Scatter(
            x=[roll.index.min(), roll.index.max()],
            y=[level, level],
            mode="lines",
            line=dict(color=color, width=1, dash="dash"),
            name=label,
        ))

    fig.update_layout(
        title=dict(
            text=f"Correlación Rodante ({window} períodos) — {asset_a} vs {asset_b}",
            font=dict(color=TEXT_COLOR, size=15),
        ),
        **_PLOTLY_LAYOUT,
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_COLOR)),
        yaxis=dict(
            gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_COLOR),
            range=[-1.1, 1.1], zeroline=False,
        ),
        legend=dict(font=dict(color=TEXT_COLOR), bgcolor="rgba(0,0,0,0)"),
        height=380,
    )
    return fig


def plot_scatter_retornos(
    df_returns: pd.DataFrame,
    asset_a: str,
    asset_b: str,
) -> go.Figure:
    """Scatter of log-returns for two assets with OLS regression line, R², and beta."""
    x = df_returns[asset_a].values
    y = df_returns[asset_b].values

    # OLS
    mask = np.isfinite(x) & np.isfinite(y)
    x_, y_ = x[mask], y[mask]
    beta, alpha = np.polyfit(x_, y_, 1)
    y_hat = beta * x_ + alpha

    r2 = np.corrcoef(x_, y_)[0, 1] ** 2
    pearson_r = np.corrcoef(x_, y_)[0, 1]

    x_line = np.linspace(x_.min(), x_.max(), 200)
    y_line = beta * x_line + alpha

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_, y=y_,
        mode="markers",
        marker=dict(color=ACCENT, size=4, opacity=0.5),
        name="Retornos",
    ))

    fig.add_trace(go.Scatter(
        x=x_line, y=y_line,
        mode="lines",
        line=dict(color="#ff7f0e", width=2),
        name=f"Regresión  β={beta:.3f}  R²={r2:.3f}",
    ))

    fig.update_layout(
        title=dict(
            text=(
                f"Dispersión de Retornos — {asset_a} vs {asset_b}"
                f"  |  r = {pearson_r:.3f}   β = {beta:.3f}   R² = {r2:.3f}"
            ),
            font=dict(color=TEXT_COLOR, size=14),
        ),
        **_PLOTLY_LAYOUT,
        xaxis=dict(
            title=dict(text=asset_a, font=dict(color=TEXT_COLOR)),
            gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_COLOR),
        ),
        yaxis=dict(
            title=dict(text=asset_b, font=dict(color=TEXT_COLOR)),
            gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_COLOR),
        ),
        legend=dict(font=dict(color=TEXT_COLOR), bgcolor="rgba(0,0,0,0)"),
        height=420,
    )
    return fig


# ── Descorrelation table ──────────────────────────────────────────────────────

@st.cache_data
def tabla_descorrelacion(df_returns: pd.DataFrame) -> pd.DataFrame:
    """Ranking table of asset pairs sorted by absolute correlation (ascending = most decorrelated).

    Columns: Par, Correlación, |Correlación|, Clasificación
    """
    corr = df_returns.corr()
    assets = corr.columns.tolist()
    rows = []
    for i, a in enumerate(assets):
        for b in assets[i + 1:]:
            r = corr.loc[a, b]
            abs_r = abs(r)
            if abs_r < 0.3:
                label = "🟢 Baja"
            elif abs_r < 0.7:
                label = "🟡 Moderada"
            else:
                label = "🔴 Alta"
            rows.append({
                "Par": f"{a} / {b}",
                "Correlación": round(r, 4),
                "|Correlación|": round(abs_r, 4),
                "Clasificación": label,
            })

    df_out = pd.DataFrame(rows).sort_values("|Correlación|").reset_index(drop=True)
    return df_out
