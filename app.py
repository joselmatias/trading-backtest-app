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
    plot_wins_losses_by_day, plot_trade_duration, plot_monthly_heatmap,
    plot_streaks, plot_streak_frequency,
)
from utils.metrics import calculate_metrics, calculate_advanced_metrics, monthly_performance
from utils.strategy import run_backtest
from utils.analytics import (
    pnl_by_weekday, pnl_by_hour, long_vs_short,
    wins_losses_by_day, trade_duration_minutes,
    streak_analysis, pnl_frequency,
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

st.plotly_chart(
    plot_streaks(streak_analysis(df_trades)),
    use_container_width=True, config={"displayModeBar": True},
)

st.markdown("**Frecuencia de Rachas por Longitud**")
df_wins, df_losses = pnl_frequency(df_trades)
_fmt_freq = {"Frec. Relativa (%)": "{:.2f}%", "Frec. Acumulada (%)": "{:.2f}%"}

col_w, col_l = st.columns(2)
with col_w:
    st.markdown("Rachas **Ganadoras** (Win)")
    st.dataframe(df_wins.style.format(_fmt_freq), use_container_width=True, hide_index=True)
with col_l:
    st.markdown("Rachas **Perdedoras** (Loss)")
    st.dataframe(df_losses.style.format(_fmt_freq), use_container_width=True, hide_index=True)

st.plotly_chart(
    plot_streak_frequency(df_wins, df_losses),
    use_container_width=True, config={"displayModeBar": True},
)

st.divider()

# ── Performance Report ────────────────────────────────────────────────────────
st.subheader("📋 Performance Report")
adv = calculate_advanced_metrics(df_trades)
mp  = monthly_performance(df_trades)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Métricas", "📈 Stats", "🔢 Trades", "📅 Monthly P/L"])

with tab1:
    c = st.columns(5)
    c[0].metric("Total Profit",     f"${adv['total_profit']:,.2f}")
    c[1].metric("# of Trades",      adv['n_trades'])
    c[2].metric("Sharpe Ratio",     f"{adv['sharpe_ratio']:.2f}")
    c[3].metric("Profit Factor",    f"{adv['profit_factor']:.2f}")
    c[4].metric("Return/DD Ratio",  f"{adv['return_dd_ratio']:.2f}")
    c = st.columns(5)
    c[0].metric("Winning %",        f"{adv['winning_pct']:.1f}%")
    c[1].metric("Profit in Pips",   f"{adv['profit_in_pips']:,.0f}")
    c[2].metric("Drawdown $",       f"-${adv['max_dd_abs']:,.2f}")
    c[3].metric("Drawdown %",       f"-{adv['max_dd_pct']:.2f}%")
    c[4].metric("Daily Avg Profit", f"${adv['daily_avg_profit']:.2f}")
    c = st.columns(5)
    c[0].metric("Monthly Avg",      f"${adv['monthly_avg_profit']:,.2f}")
    c[1].metric("Avg Trade",        f"${adv['avg_trade']:.2f}")
    c[2].metric("Yearly Avg $",     f"${adv['yearly_avg_profit']:,.2f}")
    c[3].metric("Yearly Avg %",     f"{adv['yearly_avg_pct']:.1f}%")
    c[4].metric("Annual Max DD%",   f"-{adv['annual_max_dd_pct']:.2f}%")
    c = st.columns(5)
    c[0].metric("R Expectancy",     f"{adv['r_expectancy']:.3f}R")
    c[1].metric("R Exp. Score",     f"{adv['r_expectancy_score']:.2f}")
    c[2].metric("SQN",              f"{adv['sqn']:.2f} — {adv['sqn_label']}")
    c[3].metric("CAGR",             f"{adv['cagr']:.1f}%")
    c[4].metric("STR Quality",      adv['sqn_label'])

with tab2:
    rows = [
        ("Wins / Losses Ratio",    f"{adv['wins_losses_ratio']:.2f}"),
        ("Payout Ratio",           f"{adv['payout_ratio']:.2f}"),
        ("Avg # Bars in Trade",    f"{adv['avg_bars_trade']:.1f}"),
        ("AHPR",                   f"{adv['ahpr']:.4f}%"),
        ("Z-Score",                f"{adv['z_score']:.2f}"),
        ("Z-Probability",          f"{adv['z_probability']:.1f}%"),
        ("Expectancy",             f"${adv['expectancy']:.2f}"),
        ("Deviation",              f"${adv['deviation']:.2f}"),
        ("Exposure",               f"{adv['exposure_pct']:.1f}%"),
        ("Stagnation in Days",     f"{adv['stagnation_days']}"),
        ("Stagnation in %",        f"{adv['stagnation_pct']:.1f}%"),
    ]
    st.dataframe(pd.DataFrame(rows, columns=["Métrica", "Valor"]),
                 hide_index=True, use_container_width=True)

with tab3:
    rows = [
        ("# of Wins",           adv['n_wins']),
        ("# of Losses",         adv['n_losses']),
        ("# Cancelled/Expired", adv['n_cancelled']),
        ("Gross Profit",        f"${adv['gross_profit']:,.2f}"),
        ("Gross Loss",          f"${adv['gross_loss']:,.2f}"),
        ("Average Win",         f"${adv['avg_win']:,.2f}"),
        ("Average Loss",        f"${adv['avg_loss']:,.2f}"),
        ("Largest Win",         f"${adv['largest_win']:,.2f}"),
        ("Largest Loss",        f"${adv['largest_loss']:,.2f}"),
        ("Max Consec. Wins",    adv['max_consec_wins']),
        ("Max Consec. Losses",  adv['max_consec_losses']),
        ("Avg Consec. Wins",    f"{adv['avg_consec_wins']:.1f}"),
        ("Avg Consec. Losses",  f"{adv['avg_consec_losses']:.1f}"),
        ("Avg Bars in Wins",    f"{adv['avg_bars_wins']:.1f}"),
        ("Avg Bars in Losses",  f"{adv['avg_bars_losses']:.1f}"),
    ]
    st.dataframe(pd.DataFrame(rows, columns=["Métrica", "Valor"]),
                 hide_index=True, use_container_width=True)

with tab4:
    st.plotly_chart(plot_monthly_heatmap(mp),
                    use_container_width=True, config={"displayModeBar": True})

    def _color_monthly(val):
        if isinstance(val, (int, float)):
            return "color: #00cc66" if val > 0 else "color: #ff4444" if val < 0 else ""
        return ""
    st.dataframe(mp.style.map(_color_monthly).format("${:,.2f}"),
                 use_container_width=True)
