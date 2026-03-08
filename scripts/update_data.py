"""
Concatena todos los CSVs de data/alpha/ en data/alpha/EURUSD_M15.csv.

Uso:
    python scripts/update_data.py

Ejecutar cada vez que agregues un nuevo CSV a data/alpha/.
Los archivos fuente deben tener el patron EURUSD*_*_*.csv (exportacion MT5).
El archivo de salida EURUSD_M15.csv NO se usa como fuente (se excluye).
"""

from pathlib import Path
import pandas as pd
import sys

SOURCE_DIR = Path("data/alpha")
OUTPUT_FILE = SOURCE_DIR / "EURUSD_M15.csv"


def main() -> None:
    # Toma todos los CSVs de la carpeta excepto el archivo de salida
    csv_files = sorted(
        f for f in SOURCE_DIR.glob("EURUSD*.csv")
        if f.resolve() != OUTPUT_FILE.resolve()
    )

    if not csv_files:
        print(f"ERROR: No se encontraron CSVs fuente en {SOURCE_DIR}/")
        sys.exit(1)

    print(f"Archivos a combinar: {len(csv_files)}")
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

    first = combined["<DATE>"].iloc[0]
    last = combined["<DATE>"].iloc[-1]
    print(f"Rango: {first}  →  {last}")


if __name__ == "__main__":
    main()
