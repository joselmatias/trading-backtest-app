"""
Concatena todos los CSVs de data/bt_eurusd/ en data/EURUSD_M15.csv.

Uso:
    python scripts/update_data.py

Ejecutar cada vez que agregues un nuevo CSV a data/bt_eurusd/.
"""

from pathlib import Path
import pandas as pd
import sys

SOURCE_DIR = Path("data/bt_eurusd")
OUTPUT_FILE = Path("data/EURUSD_M15.csv")


def main() -> None:
    csv_files = sorted(SOURCE_DIR.glob("EURUSD_M15_*.csv"))

    if not csv_files:
        print(f"ERROR: No se encontraron CSVs en {SOURCE_DIR}/")
        sys.exit(1)

    print(f"Archivos encontrados: {len(csv_files)}")
    for f in csv_files:
        print(f"  {f.name}")

    frames = []
    for f in csv_files:
        df = pd.read_csv(f, sep="\t", encoding="utf-8-sig")
        frames.append(df)
        print(f"  {f.name}: {len(df):,} filas")

    combined = pd.concat(frames, ignore_index=True)

    # Eliminar duplicados por fecha+hora (por si hay solapamiento entre archivos)
    combined.drop_duplicates(subset=["<DATE>", "<TIME>"], keep="last", inplace=True)
    combined.sort_values(["<DATE>", "<TIME>"], inplace=True)
    combined.reset_index(drop=True, inplace=True)

    combined.to_csv(OUTPUT_FILE, sep="\t", index=False)

    print(f"\nResultado guardado en: {OUTPUT_FILE}")
    print(f"Total filas: {len(combined):,}")

    # Mostrar rango de fechas
    first = combined["<DATE>"].iloc[0]
    last = combined["<DATE>"].iloc[-1]
    print(f"Rango: {first}  →  {last}")


if __name__ == "__main__":
    main()
