"""
Combina CSVs de datos históricos de MT5 en un único archivo por carpeta.

Uso:
    python scripts/update_data.py

Carpetas gestionadas:
    data/alpha/      → data/alpha/EURUSD_M15.csv
    data/bt_eurusd/  → data/bt_eurusd/EURUSD_M15.csv

Ejecutar cada vez que agregues un nuevo CSV a cualquiera de esas carpetas.
Los archivos fuente deben tener el patron EURUSD*_*_*.csv (exportación MT5).
El archivo de salida EURUSD_M15.csv NO se usa como fuente (se excluye).
"""

from pathlib import Path
import pandas as pd
import sys


JOBS = [
    {
        "source_dir":  Path("data/alpha"),
        "output_file": Path("data/alpha/EURUSD_M15.csv"),
        "pattern":     "EURUSD*.csv",
    },
    {
        "source_dir":  Path("data/bt_eurusd"),
        "output_file": Path("data/bt_eurusd/EURUSD_M15.csv"),
        "pattern":     "EURUSD*.csv",
    },
]


def merge(source_dir: Path, output_file: Path, pattern: str) -> None:
    csv_files = sorted(
        f for f in source_dir.glob(pattern)
        if f.resolve() != output_file.resolve()
    )

    if not csv_files:
        print(f"  ERROR: No se encontraron CSVs fuente en {source_dir}/")
        return

    print(f"  Archivos a combinar: {len(csv_files)}")
    frames = []
    for f in csv_files:
        df = pd.read_csv(f, sep="\t", encoding="utf-8-sig")
        frames.append(df)
        print(f"    {f.name}: {len(df):,} filas")

    combined = pd.concat(frames, ignore_index=True)

    # Eliminar duplicados por fecha+hora (por si hay solapamiento entre archivos)
    combined.drop_duplicates(subset=["<DATE>", "<TIME>"], keep="last", inplace=True)
    combined.sort_values(["<DATE>", "<TIME>"], inplace=True)
    combined.reset_index(drop=True, inplace=True)
    combined.to_csv(output_file, sep="\t", index=False)

    first = combined["<DATE>"].iloc[0]
    last  = combined["<DATE>"].iloc[-1]
    print(f"  → {output_file}  |  {len(combined):,} filas  |  {first} → {last}")


def main() -> None:
    for job in JOBS:
        print(f"\n[{job['source_dir']}]")
        merge(job["source_dir"], job["output_file"], job["pattern"])
    print("\nListo.")


if __name__ == "__main__":
    main()
