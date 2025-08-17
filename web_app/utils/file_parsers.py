import pandas as pd
from pathlib import Path

def read_any_table(path: str) -> pd.DataFrame:
    if path.lower().endswith((".xlsx",".xls")): return pd.read_excel(path)
    if path.lower().endswith(".csv"): return pd.read_csv(path)
    raise ValueError("Formato no soportado (CSV/XLSX)")

def save_upload(file, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / file.filename
    with out.open("wb") as f: f.write(file.file.read())
    return out
