"""Trading Backtest Analyzer - EURUSD / USDCHF M15

Streamlit UI layer — layout and display only.
All business logic lives in utils/.
"""

import os
import pandas as pd
import streamlit as st

from utils.data_loader import calculate_indicators, load_csv
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
    streak_analysis, pnl_frequency, equity_curve_data,
)
from utils.correlaciones import (
    cargar_datos, alinear_retornos, resamplear_series, TIMEFRAMES,
    plot_heatmap, plot_rolling_corr, plot_scatter_retornos, tabla_descorrelacion,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Backtest EURUSD M15",
    page_icon="📊",
    layout="wide",
)

st.title("📊 TRADING BACKTEST ANALYZER — EURUSD M15")
st.divider()

# ── Datasets & params ─────────────────────────────────────────────────────────
FUENTES_DATOS = {
    "EURUSD": {
        "Alpha":           "data/alpha/EURUSD_M15.csv",
        "Seacrest Market": "data/seacrest_market/EURUSD_M15.csv",
        "BT":              "data/bt_eurusd/EURUSD_M15.csv",
    },
    "USDCHF": {
        "WeMasterTrade":   "data/wemastertrade/USDCHF__M15_202501020100_202603062345.csv",
    },
}

PARAMS_PAR = {
    "EURUSD": {
        "pip_size":  0.0001,
        "pip_value": 10.0,    # USD por pip por lote estándar
        "comision":  2.50,
        "sl_pips":   20,
        "tp_pips":   100,
        "lote":      0.25,
        "decimales": 5,
    },
    "USDCHF": {
        "pip_size":  0.0001,
        "pip_value": 10.0,    # USD por pip por lote estándar (igual que EURUSD)
        "comision":  2.50,
        "sl_pips":   20,
        "tp_pips":   100,
        "lote":      0.25,
        "decimales": 5,
    },
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")
    modulo = st.radio(
        "Módulo:",
        options=["📊 Backtest", "📁 Portafolio WeMasterTrade", "🔗 Correlaciones"],
        index=0,
    )
    st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# MODULE: BACKTEST
# ═════════════════════════════════════════════════════════════════════════════
if modulo == "📊 Backtest":

    with st.sidebar:
        st.markdown("**📌 Par**")
        par = st.radio(
            "",
            options=list(FUENTES_DATOS.keys()),
            key="par_selector",
            label_visibility="collapsed",
        )

        st.markdown("**🏦 Broker**")
        broker = st.radio(
            "",
            options=list(FUENTES_DATOS[par].keys()),
            key="broker_selector",
            label_visibility="collapsed",
        )

        archivo = FUENTES_DATOS[par][broker]
        st.markdown(f"`{archivo}`")

    # ── File validation ───────────────────────────────────────────────────────
    if not os.path.exists(archivo):
        st.sidebar.error("⚠️ Archivo no encontrado")
        st.warning(
            f"No se encontró el archivo:\n\n"
            f"`{archivo}`\n\n"
            f"Coloca el CSV en esa ruta y recarga la app."
        )
        st.stop()

    # ── Load & validate data ──────────────────────────────────────────────────
    df_raw = load_csv(archivo)

    if df_raw is None:
        st.error(
            f"Error al leer: `{archivo}`  \n"
            "Asegúrate de que el CSV tiene columnas: "
            "`<DATE>  <TIME>  <OPEN>  <HIGH>  <LOW>  <CLOSE>`"
        )
        st.stop()

    df = calculate_indicators(df_raw)

    if df.empty:
        st.warning("El DataFrame quedó vacío tras calcular los indicadores.")
        st.stop()

    # ── Params (pip value dinámico para USDCHF) ───────────────────────────────
    params = PARAMS_PAR[par].copy()
    # Convertir pip_value por lote estándar a valor efectivo por posición
    # EURUSD y USDCHF usan la misma fórmula: pip_value_lote × lote = 10.0 × 0.25 = $2.50/pip
    params["pip_value"] = round(params["pip_value"] * params["lote"], 4)

    with st.sidebar:
        st.caption(
            f"Pip value: ${params['pip_value']:.4f} | "
            f"SL: {params['sl_pips']}p | TP: {params['tp_pips']}p | "
            f"Lote: {params['lote']}"
        )

    # ── Run backtest ──────────────────────────────────────────────────────────
    titulo = f"{par} M15 — Bollinger Bands | {broker}"

    with st.spinner("Ejecutando backtest…"):
        df_trades = run_backtest(df, params)

    if df_trades.empty:
        st.warning(
            "El backtest no generó operaciones con los datos actuales.  \n"
            "Verifica el rango de fechas o los filtros de la estrategia."
        )
        st.stop()

    # ── Metrics ───────────────────────────────────────────────────────────────
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

    # ── Equity Curve ──────────────────────────────────────────────────────────
    st.subheader("📈 Equity Curve")
    st.plotly_chart(
        plot_equity_curve(df_trades, title=titulo),
        use_container_width=True,
        config={"displayModeBar": True},
    )

    df_eq = equity_curve_data(df_trades)


    def _color_equity_row(row):
        if row["Evento"] == "Capital Inicial":
            color = "color: #aaaaaa"
        elif row["Evento"] == "Comisión (apertura)":
            color = "color: #ffaa00"
        elif "Ganancia" in row["Evento"]:
            color = "color: #00cc66"
        else:
            color = "color: #ff4444"
        return [color] * len(row)


    st.dataframe(
        df_eq.style
            .apply(_color_equity_row, axis=1)
            .format({"Delta ($)": "${:+,.2f}", "Capital ($)": "${:,.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Drawdown ──────────────────────────────────────────────────────────────
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

    # ── Trade History ─────────────────────────────────────────────────────────
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

    # ── Analytics ─────────────────────────────────────────────────────────────
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

    # ── Performance Report ────────────────────────────────────────────────────
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


# ═════════════════════════════════════════════════════════════════════════════
# MODULE: PORTAFOLIO WEMASTERTRADE
# ═════════════════════════════════════════════════════════════════════════════
elif modulo == "📁 Portafolio WeMasterTrade":

    # Fuentes fijas WeMasterTrade para ambos pares
    _PORT_FUENTES = {
        "EURUSD": "data/wemastertrade/EURUSD__M15_202501020100_202603062345.csv",
        "USDCHF": "data/wemastertrade/USDCHF__M15_202501020100_202603062345.csv",
    }

    # 0.5% de riesgo: lote 0.125 → pip_value efectivo = 10.0 × 0.125 = $1.25/pip
    # SL 20 pips × $1.25 = $25 = 0.5% de $5,000
    _PORT_PARAMS = {
        "pip_size":  0.0001,
        "pip_value": 1.25,
        "comision":  2.50,
        "sl_pips":   20,
        "tp_pips":   100,
        "lote":      0.125,
        "decimales": 5,
    }

    with st.sidebar:
        st.markdown("**📌 Pares**")
        st.caption("• EURUSD — WeMasterTrade")
        st.caption("• USDCHF — WeMasterTrade")
        st.divider()
        st.caption(
            f"Riesgo: 0.5% / operación  \n"
            f"Pip value: ${_PORT_PARAMS['pip_value']:.2f} | "
            f"Lote: {_PORT_PARAMS['lote']}  \n"
            f"SL: {_PORT_PARAMS['sl_pips']}p | TP: {_PORT_PARAMS['tp_pips']}p"
        )

    st.subheader("📁 Portafolio WeMasterTrade — EURUSD + USDCHF")

    # ── Validar archivos ──────────────────────────────────────────────────────
    archivos_faltantes = [p for p in _PORT_FUENTES.values() if not os.path.exists(p)]
    if archivos_faltantes:
        for f in archivos_faltantes:
            st.error(f"Archivo no encontrado: `{f}`")
        st.stop()

    # ── Cargar y preparar datos ───────────────────────────────────────────────
    with st.spinner("Ejecutando portafolio…"):
        raw_eur = load_csv(_PORT_FUENTES["EURUSD"])
        raw_chf = load_csv(_PORT_FUENTES["USDCHF"])

        if raw_eur is None or raw_chf is None:
            st.error("Error al leer uno de los CSVs. Verifica el formato de columnas.")
            st.stop()

        df_eur_ind = calculate_indicators(raw_eur)
        df_chf_ind = calculate_indicators(raw_chf)

        trades_eur = run_backtest(df_eur_ind, _PORT_PARAMS)
        trades_chf = run_backtest(df_chf_ind, _PORT_PARAMS)

    if trades_eur.empty and trades_chf.empty:
        st.warning("El portafolio no generó operaciones.")
        st.stop()

    # ── Combinar trades cronológicamente ─────────────────────────────────────
    from utils.strategy import INITIAL_CAPITAL as _CAP_INICIAL

    def _combinar(df_a: pd.DataFrame, par_a: str,
                  df_b: pd.DataFrame, par_b: str) -> pd.DataFrame:
        dfa = df_a.copy(); dfa["Par"] = par_a
        dfb = df_b.copy(); dfb["Par"] = par_b
        combined = pd.concat([dfa, dfb]).sort_values("Fecha Cierre").reset_index(drop=True)
        capital = _CAP_INICIAL
        caps = []
        for _, row in combined.iterrows():
            capital = round(capital + row["Beneficio"], 2)
            caps.append(capital)
        combined["Capital"] = caps
        return combined

    df_port = _combinar(trades_eur, "EURUSD", trades_chf, "USDCHF")

    # ── Métricas combinadas ───────────────────────────────────────────────────
    m = calculate_metrics(df_port)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Capital Inicial", f"${m['capital_inicial']:,.2f}")
    with col2:
        delta_usd = m["capital_final"] - m["capital_inicial"]
        st.metric("Capital Final", f"${m['capital_final']:,.2f}", delta=f"${delta_usd:+,.2f}")
    with col3:
        st.metric("Total Trades", m["total_trades"])

    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("Win Rate", f"{m['win_rate']:.1f}%",
                  delta=f"{m['win_trades']}W  /  {m['loss_trades']}L")
    with col5:
        st.metric("Max Drawdown $", f"-${m['max_drawdown_abs']:,.2f}")
    with col6:
        st.metric("Max Drawdown %", f"-{m['max_drawdown_pct']:.2f}%")

    st.divider()

    # ── Desglose por par ──────────────────────────────────────────────────────
    st.subheader("📊 Desglose por Par")

    def _resumen_par(df: pd.DataFrame, par: str) -> dict:
        if df.empty:
            return {"Par": par, "Trades": 0, "Wins": 0, "Losses": 0, "Win Rate": 0.0, "Total P&L": 0.0}
        wins = int((df["Beneficio"] > 0).sum())
        losses = int((df["Beneficio"] < 0).sum())
        return {
            "Par":       par,
            "Trades":    len(df),
            "Wins":      wins,
            "Losses":    losses,
            "Win Rate":  f"{wins / len(df) * 100:.1f}%",
            "Total P&L": round(df["Beneficio"].sum(), 2),
        }

    df_resumen = pd.DataFrame([
        _resumen_par(trades_eur, "EURUSD"),
        _resumen_par(trades_chf, "USDCHF"),
    ])
    df_resumen.loc[len(df_resumen)] = {
        "Par": "TOTAL",
        "Trades": df_resumen["Trades"].sum(),
        "Wins":   df_resumen["Wins"].sum(),
        "Losses": df_resumen["Losses"].sum(),
        "Win Rate": f"{m['win_rate']:.1f}%",
        "Total P&L": round(df_port["Beneficio"].sum(), 2),
    }

    def _color_pnl_port(val):
        if isinstance(val, (int, float)):
            return "color: #00cc66" if val > 0 else "color: #ff4444" if val < 0 else ""
        return ""

    st.dataframe(
        df_resumen.style.map(_color_pnl_port, subset=["Total P&L"]),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Equity Curve ──────────────────────────────────────────────────────────
    st.subheader("📈 Equity Curve — Portafolio")
    st.plotly_chart(
        plot_equity_curve(df_port, title="Portafolio WeMasterTrade — EURUSD + USDCHF"),
        use_container_width=True,
        config={"displayModeBar": True},
    )

    df_eq_port = equity_curve_data(df_port)

    def _color_equity_port(row):
        if row["Evento"] == "Capital Inicial":
            return ["color: #aaaaaa"] * len(row)
        elif row["Evento"] == "Comisión (apertura)":
            return ["color: #ffaa00"] * len(row)
        elif "Ganancia" in row["Evento"]:
            return ["color: #00cc66"] * len(row)
        return ["color: #ff4444"] * len(row)

    st.dataframe(
        df_eq_port.style
            .apply(_color_equity_port, axis=1)
            .format({"Delta ($)": "${:+,.2f}", "Capital ($)": "${:,.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Drawdown ──────────────────────────────────────────────────────────────
    st.subheader("📉 Drawdown Analysis")
    col_dd1, col_dd2 = st.columns(2)
    with col_dd1:
        st.plotly_chart(plot_drawdown_abs(df_port),
                        use_container_width=True, config={"displayModeBar": True})
    with col_dd2:
        st.plotly_chart(plot_drawdown_pct(df_port),
                        use_container_width=True, config={"displayModeBar": True})

    st.divider()

    # ── Trade History ─────────────────────────────────────────────────────────
    st.subheader("📋 Trade History — Portafolio")

    price_cols_p = ["Entrada", "S/L", "T/P", "Cierre"]
    money_cols_p = ["Beneficio", "Capital", "Comisión"]
    fmt_p: dict[str, str] = {col: "{:.5f}" for col in price_cols_p}
    fmt_p.update({col: "${:,.2f}" for col in money_cols_p})
    fmt_p["Volumen"] = "{:.3f}"

    def _color_pnl_p(val: float) -> str:
        return "color: #00cc66" if val > 0 else "color: #ff4444"

    st.dataframe(
        df_port.style
            .map(_color_pnl_p, subset=["Beneficio"])
            .format(fmt_p),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Analytics ─────────────────────────────────────────────────────────────
    st.subheader("📊 Analytics — Portafolio")

    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.plotly_chart(plot_pnl_by_weekday(pnl_by_weekday(df_port)),
                        use_container_width=True, config={"displayModeBar": True})
    with col_a2:
        st.plotly_chart(plot_pnl_by_hour(pnl_by_hour(df_port)),
                        use_container_width=True, config={"displayModeBar": True})

    st.plotly_chart(plot_long_vs_short(long_vs_short(df_port)),
                    use_container_width=True, config={"displayModeBar": True})
    st.plotly_chart(plot_wins_losses_by_day(wins_losses_by_day(df_port)),
                    use_container_width=True, config={"displayModeBar": True})
    st.plotly_chart(plot_trade_duration(trade_duration_minutes(df_port)),
                    use_container_width=True, config={"displayModeBar": True})
    st.plotly_chart(plot_streaks(streak_analysis(df_port)),
                    use_container_width=True, config={"displayModeBar": True})

    st.markdown("**Frecuencia de Rachas por Longitud**")
    df_wins_p, df_losses_p = pnl_frequency(df_port)
    _fmt_freq_p = {"Frec. Relativa (%)": "{:.2f}%", "Frec. Acumulada (%)": "{:.2f}%"}
    col_wp, col_lp = st.columns(2)
    with col_wp:
        st.markdown("Rachas **Ganadoras** (Win)")
        st.dataframe(df_wins_p.style.format(_fmt_freq_p), use_container_width=True, hide_index=True)
    with col_lp:
        st.markdown("Rachas **Perdedoras** (Loss)")
        st.dataframe(df_losses_p.style.format(_fmt_freq_p), use_container_width=True, hide_index=True)
    st.plotly_chart(plot_streak_frequency(df_wins_p, df_losses_p),
                    use_container_width=True, config={"displayModeBar": True})

    st.divider()

    # ── Performance Report ────────────────────────────────────────────────────
    st.subheader("📋 Performance Report — Portafolio")
    adv_p = calculate_advanced_metrics(df_port)
    mp_p  = monthly_performance(df_port)

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Métricas", "📈 Stats", "🔢 Trades", "📅 Monthly P/L"])

    with tab1:
        c = st.columns(5)
        c[0].metric("Total Profit",     f"${adv_p['total_profit']:,.2f}")
        c[1].metric("# of Trades",      adv_p['n_trades'])
        c[2].metric("Sharpe Ratio",     f"{adv_p['sharpe_ratio']:.2f}")
        c[3].metric("Profit Factor",    f"{adv_p['profit_factor']:.2f}")
        c[4].metric("Return/DD Ratio",  f"{adv_p['return_dd_ratio']:.2f}")
        c = st.columns(5)
        c[0].metric("Winning %",        f"{adv_p['winning_pct']:.1f}%")
        c[1].metric("Profit in Pips",   f"{adv_p['profit_in_pips']:,.0f}")
        c[2].metric("Drawdown $",       f"-${adv_p['max_dd_abs']:,.2f}")
        c[3].metric("Drawdown %",       f"-{adv_p['max_dd_pct']:.2f}%")
        c[4].metric("Daily Avg Profit", f"${adv_p['daily_avg_profit']:.2f}")
        c = st.columns(5)
        c[0].metric("Monthly Avg",      f"${adv_p['monthly_avg_profit']:,.2f}")
        c[1].metric("Avg Trade",        f"${adv_p['avg_trade']:.2f}")
        c[2].metric("Yearly Avg $",     f"${adv_p['yearly_avg_profit']:,.2f}")
        c[3].metric("Yearly Avg %",     f"{adv_p['yearly_avg_pct']:.1f}%")
        c[4].metric("Annual Max DD%",   f"-{adv_p['annual_max_dd_pct']:.2f}%")
        c = st.columns(5)
        c[0].metric("R Expectancy",     f"{adv_p['r_expectancy']:.3f}R")
        c[1].metric("R Exp. Score",     f"{adv_p['r_expectancy_score']:.2f}")
        c[2].metric("SQN",              f"{adv_p['sqn']:.2f} — {adv_p['sqn_label']}")
        c[3].metric("CAGR",             f"{adv_p['cagr']:.1f}%")
        c[4].metric("STR Quality",      adv_p['sqn_label'])

    with tab2:
        rows_p = [
            ("Wins / Losses Ratio",  f"{adv_p['wins_losses_ratio']:.2f}"),
            ("Payout Ratio",         f"{adv_p['payout_ratio']:.2f}"),
            ("Avg # Bars in Trade",  f"{adv_p['avg_bars_trade']:.1f}"),
            ("AHPR",                 f"{adv_p['ahpr']:.4f}%"),
            ("Z-Score",              f"{adv_p['z_score']:.2f}"),
            ("Z-Probability",        f"{adv_p['z_probability']:.1f}%"),
            ("Expectancy",           f"${adv_p['expectancy']:.2f}"),
            ("Deviation",            f"${adv_p['deviation']:.2f}"),
            ("Exposure",             f"{adv_p['exposure_pct']:.1f}%"),
            ("Stagnation in Days",   f"{adv_p['stagnation_days']}"),
            ("Stagnation in %",      f"{adv_p['stagnation_pct']:.1f}%"),
        ]
        st.dataframe(pd.DataFrame(rows_p, columns=["Métrica", "Valor"]),
                     hide_index=True, use_container_width=True)

    with tab3:
        rows_p = [
            ("# of Wins",           adv_p['n_wins']),
            ("# of Losses",         adv_p['n_losses']),
            ("Gross Profit",        f"${adv_p['gross_profit']:,.2f}"),
            ("Gross Loss",          f"${adv_p['gross_loss']:,.2f}"),
            ("Average Win",         f"${adv_p['avg_win']:,.2f}"),
            ("Average Loss",        f"${adv_p['avg_loss']:,.2f}"),
            ("Largest Win",         f"${adv_p['largest_win']:,.2f}"),
            ("Largest Loss",        f"${adv_p['largest_loss']:,.2f}"),
            ("Max Consec. Wins",    adv_p['max_consec_wins']),
            ("Max Consec. Losses",  adv_p['max_consec_losses']),
            ("Avg Consec. Wins",    f"{adv_p['avg_consec_wins']:.1f}"),
            ("Avg Consec. Losses",  f"{adv_p['avg_consec_losses']:.1f}"),
        ]
        st.dataframe(pd.DataFrame(rows_p, columns=["Métrica", "Valor"]),
                     hide_index=True, use_container_width=True)

    with tab4:
        st.plotly_chart(plot_monthly_heatmap(mp_p),
                        use_container_width=True, config={"displayModeBar": True})
        def _color_mp(val):
            if isinstance(val, (int, float)):
                return "color: #00cc66" if val > 0 else "color: #ff4444" if val < 0 else ""
            return ""
        st.dataframe(mp_p.style.map(_color_mp).format("${:,.2f}"),
                     use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# MODULE: CORRELACIONES
# ═════════════════════════════════════════════════════════════════════════════
elif modulo == "🔗 Correlaciones":

    st.subheader("🔗 Análisis de Correlaciones")

    # ── Load data ─────────────────────────────────────────────────────────────
    series_dict, error = cargar_datos()

    if error:
        st.error(error)
        st.info(
            "Agrega CSVs exportados desde MetaTrader 5 en la carpeta `data/correlaciones/`.  \n"
            "Formato esperado: separado por tabs, columnas `<DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE>`."
        )
        st.stop()

    assets = list(series_dict.keys())

    # ── Timeframe selector ────────────────────────────────────────────────────
    timeframe = st.radio(
        "Temporalidad:",
        options=list(TIMEFRAMES.keys()),
        index=0,
        horizontal=True,
    )

    with st.sidebar:
        st.markdown("**Activos cargados**")
        for a in assets:
            st.caption(f"• {a}")
        st.divider()
        window = st.slider("Ventana correlación rodante (períodos)", 20, 200, 60, step=10)
        asset_a = st.selectbox("Activo A (scatter / rolling)", assets, index=0)
        asset_b = st.selectbox(
            "Activo B (scatter / rolling)",
            [a for a in assets if a != asset_a],
            index=0,
        )

    series_tf = resamplear_series(series_dict, timeframe)
    df_returns = alinear_retornos(series_tf)

    # ── Stats summary ─────────────────────────────────────────────────────────
    n_assets = len(assets)
    n_candles = len(df_returns)
    date_range = f"{df_returns.index.min().date()}  →  {df_returns.index.max().date()}"

    c1, c2, c3 = st.columns(3)
    c1.metric("Activos", n_assets)
    c2.metric("Períodos alineados", f"{n_candles:,}")
    c3.metric("Rango", date_range)

    st.divider()

    # ── Heatmap ───────────────────────────────────────────────────────────────
    st.plotly_chart(
        plot_heatmap(df_returns),
        use_container_width=True,
        config={"displayModeBar": True},
    )

    st.divider()

    # ── Rolling correlation ───────────────────────────────────────────────────
    if asset_a and asset_b and asset_a != asset_b:
        st.plotly_chart(
            plot_rolling_corr(df_returns, asset_a, asset_b, window),
            use_container_width=True,
            config={"displayModeBar": True},
        )

        st.divider()

        # ── Scatter ───────────────────────────────────────────────────────────
        st.plotly_chart(
            plot_scatter_retornos(df_returns, asset_a, asset_b),
            use_container_width=True,
            config={"displayModeBar": True},
        )

        st.divider()

    # ── Descorrelation ranking table ──────────────────────────────────────────
    st.subheader("📋 Ranking de Descorrelación")
    df_desc = tabla_descorrelacion(df_returns)

    def _color_corr(val):
        if not isinstance(val, (int, float)):
            return ""
        abs_v = abs(val)
        if abs_v < 0.3:
            return "color: #00cc66"
        elif abs_v < 0.7:
            return "color: #ffaa00"
        else:
            return "color: #ff4444"

    st.dataframe(
        df_desc.style
            .map(_color_corr, subset=["Correlación", "|Correlación|"])
            .format({"Correlación": "{:.4f}", "|Correlación|": "{:.4f}"}),
        use_container_width=True,
        hide_index=True,
    )
