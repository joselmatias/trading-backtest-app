"""Trading Backtest Analyzer - EURUSD M15

Streamlit UI layer — layout and display only.
All business logic lives in utils/.
"""

import pandas as pd
import streamlit as st

from utils.data_loader import DATASETS, calculate_indicators, load_csv
from utils.charts import (
    plot_drawdown_abs, plot_drawdown_pct, plot_equity_curve,
    plot_pnl_by_weekday, plot_pnl_by_hour, plot_long_vs_short,
    plot_wins_losses_by_day, plot_trade_duration,
)
from utils.metrics import calculate_metrics
from utils.strategy import run_backtest
from utils.analytics import (
    pnl_by_weekday, pnl_by_hour, long_vs_short,
    wins_losses_by_day, trade_duration_minutes,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Backtest EURUSD M15",
    page_icon="📊",
    layout="wide",
)

st.title("📊 TRADING BACKTEST ANALYZER — EURUSD M15")
st.divider()

# ── Dataset selector (sidebar) ────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")
    dataset = st.radio(
        "Selecciona dataset:",
        options=list(DATASETS.keys()),
        index=0,
    )
    st.caption(f"📁 `{DATASETS[dataset]}`")

# ── Load & validate data ──────────────────────────────────────────────────────
df_raw = load_csv(dataset)

if df_raw is None:
    st.error(
        f"Archivo no encontrado: `{DATASETS[dataset]}`  \n"
        "Asegúrate de que el CSV existe y tiene columnas: "
        "`<DATE>  <TIME>  <OPEN>  <HIGH>  <LOW>  <CLOSE>`"
    )
    st.stop()

df = calculate_indicators(df_raw)

if df.empty:
    st.warning("El DataFrame quedó vacío tras calcular los indicadores.")
    st.stop()

# ── Run backtest ──────────────────────────────────────────────────────────────
with st.spinner("Ejecutando backtest…"):
    df_trades = run_backtest(df)

if df_trades.empty:
    st.warning(
        "El backtest no generó operaciones con los datos actuales.  \n"
        "Verifica el rango de fechas o los filtros de la estrategia."
    )
    st.stop()

# ── Metrics ───────────────────────────────────────────────────────────────────
m = calculate_metrics(df_trades)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Capital Inicial", f"${m['capital_inicial']:,.2f}")
with col2:
    delta_usd = m["capital_final"] - m["capital_inicial"]
    st.metric(
        "Capital Final",
        f"${m['capital_final']:,.2f}",
        delta=f"${delta_usd:+,.2f}",
    )
with col3:
    st.metric("Total Trades", m["total_trades"])

col4, col5, col6 = st.columns(3)
with col4:
    st.metric(
        "Win Rate",
        f"{m['win_rate']:.1f}%",
        delta=f"{m['win_trades']}W  /  {m['loss_trades']}L",
    )
with col5:
    st.metric("Max Drawdown $", f"-${m['max_drawdown_abs']:,.2f}")
with col6:
    st.metric("Max Drawdown %", f"-{m['max_drawdown_pct']:.2f}%")

st.divider()

# ── Equity Curve ──────────────────────────────────────────────────────────────
st.subheader("📈 Equity Curve")
st.plotly_chart(
    plot_equity_curve(df_trades),
    use_container_width=True,
    config={"displayModeBar": True},
)

st.divider()

# ── Drawdown ──────────────────────────────────────────────────────────────────
st.subheader("📉 Drawdown Analysis")
col_dd1, col_dd2 = st.columns(2)
with col_dd1:
    st.plotly_chart(
        plot_drawdown_abs(df_trades),
        use_container_width=True,
        config={"displayModeBar": True},
    )
with col_dd2:
    st.plotly_chart(
        plot_drawdown_pct(df_trades),
        use_container_width=True,
        config={"displayModeBar": True},
    )

st.divider()

# ── Trade History ─────────────────────────────────────────────────────────────
st.subheader("📋 Trade History")

price_cols = ["Entrada", "S/L", "T/P", "Cierre"]
money_cols = ["Beneficio", "Capital", "Comisión"]

fmt: dict[str, str] = {col: "{:.5f}" for col in price_cols}
fmt.update({col: "${:,.2f}" for col in money_cols})
fmt["Volumen"] = "{:.2f}"


def _color_pnl(val: float) -> str:
    return "color: #00cc66" if val > 0 else "color: #ff4444"


st.dataframe(
    df_trades.style
        .map(_color_pnl, subset=["Beneficio"])
        .format(fmt),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ── Analytics ─────────────────────────────────────────────────────────────────
st.subheader("📊 Analytics")

col_a1, col_a2 = st.columns(2)
with col_a1:
    st.plotly_chart(
        plot_pnl_by_weekday(pnl_by_weekday(df_trades)),
        use_container_width=True, config={"displayModeBar": True},
    )
with col_a2:
    st.plotly_chart(
        plot_pnl_by_hour(pnl_by_hour(df_trades)),
        use_container_width=True, config={"displayModeBar": True},
    )

st.plotly_chart(
    plot_long_vs_short(long_vs_short(df_trades)),
    use_container_width=True, config={"displayModeBar": True},
)

st.plotly_chart(
    plot_wins_losses_by_day(wins_losses_by_day(df_trades)),
    use_container_width=True, config={"displayModeBar": True},
)

st.plotly_chart(
    plot_trade_duration(trade_duration_minutes(df_trades)),
    use_container_width=True, config={"displayModeBar": True},
)
