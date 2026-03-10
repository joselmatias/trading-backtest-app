"""Simulador de prueba de fondeo (Prop Firm Challenge) por fases."""

import numpy as np
import pandas as pd

# ── Defaults ──────────────────────────────────────────────────────────────────
START_CAPITAL        = 5_000.0
DAILY_LOSS           = 0.05
OVERALL_LOSS         = 0.08
TARGET_STEP1         = 0.08
TARGET_STEP2         = 0.05
MIN_WIN_TRADES       = 3
WITHDRAW_PCT_LIVE    = 0.03
FEE_PER_TRIAL        = 50.0


def simulate_prop(
    df: pd.DataFrame,
    start_capital:     float = START_CAPITAL,
    daily_loss:        float = DAILY_LOSS,
    overall_loss:      float = OVERALL_LOSS,
    target_step1:      float = TARGET_STEP1,
    target_step2:      float = TARGET_STEP2,
    min_win_trades:    int   = MIN_WIN_TRADES,
    withdraw_pct_live: float = WITHDRAW_PCT_LIVE,
    fee_per_trial:     float = FEE_PER_TRIAL,
    benef_col:         str   = "Beneficio",
    fecha_col:         str   = "Fecha Apertura",
) -> tuple[pd.DataFrame, dict]:
    """
    Simula el plan por fases (Fase 1 → Fase 2 → Live) con reinicios y retiros.

    Reglas:
    - Fase 1: alcanzar +target_step1 (8%) sin romper drawdown diario/total.
    - Fase 2: alcanzar +target_step2 (5%) bajo los mismos límites.
    - Live (Fase 3): retirar excedente cuando (capital/5000 - 1) > withdraw_pct_live.
    - Breach: pérdida diaria > daily_loss × capital_fase ó capital < overall_floor.
      Reinicia a Fase 1 con nueva cuenta.

    Parámetros:
        df             DataFrame de trades con columnas Beneficio y Fecha Apertura.
        start_capital  Capital inicial por fase/ciclo (default 5000).
        daily_loss     Límite de pérdida diaria como fracción (default 0.05 = 5%).
        overall_loss   Límite de drawdown total como fracción (default 0.08 = 8%).
        target_step1   Objetivo de ganancia Fase 1 (default 0.08 = 8%).
        target_step2   Objetivo de ganancia Fase 2 (default 0.05 = 5%).
        min_win_trades Mínimo de trades ganadores por fase (default 3).
        withdraw_pct_live Umbral de retiro en live como fracción (default 0.03 = 3%).
        fee_per_trial  Costo por prueba en USD (default $50).
        benef_col      Nombre columna Beneficio en df.
        fecha_col      Nombre columna fecha en df.

    Retorna:
        (sim DataFrame fila-por-trade, resumen dict con métricas globales)
    """
    data = df[[benef_col, fecha_col]].copy()
    data[benef_col] = pd.to_numeric(data[benef_col], errors="coerce").fillna(0)
    data[fecha_col] = pd.to_datetime(data[fecha_col], errors="coerce")
    data = data.sort_values(fecha_col).reset_index(drop=True)

    benef  = data[benef_col].to_numpy()
    fechas = data[fecha_col]

    rows = []
    ciclo               = 1
    phase               = 1
    phase_start_capital = start_capital
    current_capital     = start_capital
    overall_floor       = phase_start_capital * (1 - overall_loss)
    wins_in_phase       = 0
    breach_happened     = False
    restarts_to_phase1  = 0

    for i in range(len(data)):
        cb    = current_capital
        p     = float(benef[i])
        w     = 0.0
        note  = ""
        ca    = cb + p

        if p > 0:
            wins_in_phase += 1

        daily_breach   = p   < -daily_loss * phase_start_capital
        overall_breach = ca  < overall_floor

        if daily_breach or overall_breach:
            parts = []
            if daily_breach:   parts.append(f"DD diario >{daily_loss*100:.0f}%")
            if overall_breach: parts.append(f"DD total  >{overall_loss*100:.0f}%")
            note = "🔴 Breach: " + " & ".join(parts) + " → reinicio Fase 1"

            rows.append([fechas.iloc[i], ciclo, phase, cb, p, ca, w, start_capital, wins_in_phase, note])

            breach_happened     = True
            restarts_to_phase1 += 1
            ciclo              += 1
            phase               = 1
            phase_start_capital = start_capital
            current_capital     = start_capital
            overall_floor       = phase_start_capital * (1 - overall_loss)
            wins_in_phase       = 0
            continue

        if phase == 1:
            target = phase_start_capital * (1 + target_step1)
            if ca >= target and wins_in_phase >= min_win_trades:
                note = f"✅ Fase 1 superada ({wins_in_phase} wins) → Fase 2"
                rows.append([fechas.iloc[i], ciclo, phase, cb, p, ca, w, start_capital, wins_in_phase, note])
                phase               = 2
                phase_start_capital = start_capital
                current_capital     = start_capital
                overall_floor       = phase_start_capital * (1 - overall_loss)
                wins_in_phase       = 0
                continue
            current_capital = ca

        elif phase == 2:
            target = phase_start_capital * (1 + target_step2)
            if ca >= target and wins_in_phase >= min_win_trades:
                note = f"✅ Fase 2 superada ({wins_in_phase} wins) → Live"
                rows.append([fechas.iloc[i], ciclo, phase, cb, p, ca, w, start_capital, wins_in_phase, note])
                phase               = 3
                phase_start_capital = start_capital
                current_capital     = start_capital
                overall_floor       = phase_start_capital * (1 - overall_loss)
                wins_in_phase       = 0
                continue
            current_capital = ca

        else:  # Fase 3 — Live
            benef_pct = (ca / start_capital - 1.0) * 100.0
            umbral    = withdraw_pct_live * 100.0
            if benef_pct > umbral:
                w    = max(0.0, ca - start_capital)
                note = f"💸 Retiro ${w:,.2f} ({benef_pct:.2f}% > {umbral:.0f}%)"
            else:
                note = f"🔒 Sin retiro ({benef_pct:.2f}% ≤ {umbral:.0f}%)"
            current_capital = ca - w

        rows.append([fechas.iloc[i], ciclo, phase, cb, p, ca, w, current_capital, wins_in_phase, note])

    sim = pd.DataFrame(rows, columns=[
        fecha_col, "Ciclo", "Fase", "Capital Antes", benef_col,
        "Capital Después", "Retiro", "Capital Sig. Op.", "Wins en Fase", "Estado",
    ])

    total_retirado    = float(sim["Retiro"].sum())
    costo_fees        = float(fee_per_trial) * ciclo
    roi_neto          = total_retirado - costo_fees
    roi_pct           = (roi_neto / costo_fees * 100.0) if costo_fees > 0 else np.nan

    fechas_validas = sim[fecha_col].dropna()
    meses = int(fechas_validas.dt.to_period("M").nunique()) if not fechas_validas.empty else 0

    resumen = {
        "ciclos_totales":      ciclo,
        "fase_final":          int(sim["Fase"].iloc[-1]) if len(sim) else 1,
        "reinicios":           restarts_to_phase1,
        "retiros_realizados":  int((sim["Retiro"] > 0).sum()),
        "total_retirado":      total_retirado,
        "costo_fees":          costo_fees,
        "roi_neto":            roi_neto,
        "roi_pct":             roi_pct,
        "meses":               meses,
        "roi_por_mes":         roi_neto / meses if meses > 0 else np.nan,
        "capital_final":       float(sim["Capital Sig. Op."].iloc[-1]) if len(sim) else start_capital,
    }
    return sim, resumen
