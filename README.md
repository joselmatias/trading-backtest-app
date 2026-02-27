# Trading Backtest Analyzer — EURUSD M15

Backtest de estrategia Bollinger Bands sobre datos OHLC de 15 minutos.

## Requisitos

- Python 3.9+
- pip

## Instalación

```bash
cd trading-backtest-app
pip install -r requirements.txt
```

## Configuración de datos

Coloca tu archivo CSV en `data/EURUSD_M15.csv`.

**Formato esperado** (exportación MetaTrader 5, separado por tabulaciones):

```
<DATE>	<TIME>	<OPEN>	<HIGH>	<LOW>	<CLOSE>	<TICKVOL>	<VOL>	<SPREAD>
2026.01.15	08:45:00	1.16298	1.16338	1.16297	1.16329	466	0	5
```

## Ejecutar la app

```bash
streamlit run app.py
```

## Parámetros de la estrategia

| Parámetro        | Valor        |
|------------------|--------------|
| Capital inicial  | $5,000       |
| Volumen          | 0.25 lotes   |
| Comisión         | $2.50/trade  |
| Pip value        | $2.50/pip    |
| BB período       | 20           |
| BB desviación    | 2.0          |
| Body mínimo      | 7 pips       |
| Wick máximo      | 4 pips       |
| Stop Loss        | 20 pips      |
| Take Profit      | 100 pips     |

## Estructura del proyecto

```
trading-backtest-app/
├── app.py                  # UI Streamlit (solo layout)
├── requirements.txt
├── data/
│   └── EURUSD_M15.csv      # Actualizar manualmente
└── utils/
    ├── data_loader.py      # Carga CSV + Bollinger Bands
    ├── strategy.py         # Motor de backtest
    ├── metrics.py          # Métricas de performance
    └── charts.py           # Gráficos Plotly
```
