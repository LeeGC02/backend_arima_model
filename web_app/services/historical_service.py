# web_app/services/historical_service.py
from __future__ import annotations

import unicodedata
import pandas as pd

from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..models.medicine import Medicine
from ..models.historical import Historical


# ---------------------------
# Utilidades de normalización
# ---------------------------
def _strip_accents(s: str) -> str:
    """Quita acentos de un string (para uniformizar encabezados/valores)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def _norm_txt(s) -> str:
    """Normaliza texto: a string, sin acentos, sin espacios dobles."""
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = _strip_accents(s)
    s = " ".join(s.split())
    return s

def _norm_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Pasa encabezados a minúsculas, sin acentos, y mapea a nombres internos."""
    df = df.copy()
    df.columns = [_strip_accents(c).strip().lower() for c in df.columns]

    mapping = {
        # columnas de medicamento
        "codigo": "code",
        "código": "code",
        "medicamento e insumo": "name",
        "nombre": "name",
        "concentracion": "concentration",
        "concentración": "concentration",
        "forma farmaceutica": "dosage_form",
        "forma_farmaceutica": "dosage_form",
        "unidad de medida": "unit_measure",
        "unidad_de_medida": "unit_measure",

        # columnas de historico
        "fecha": "date",
        "salidas - cantidad": "outflow_qty",
        "salidas_cantidad": "outflow_qty",

        "saldo gestion anterior - cantidad": "prev_balance_qty",
        "saldo gestion anterior - valor (bs.)": "prev_balance_value_bs",
        "ingresos - cantidad": "inflow_qty",
        "ingresos - valor (bs.)": "inflow_value_bs",
        "salidas - valor (bs.)": "outflow_value_bs",
        "saldos totales - cantidad": "total_balance_qty",
        "saldos totales - valor (bs.)": "total_balance_value_bs",

        "archivo_origen": "source_file",
    }
    df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
    return df


# ---------------------------
# Conversión numérica robusta
# ---------------------------
def _to_num(x):
    """Convierte '1.234,56' / '1,234.56' / 'Bs 1.234' a float o None."""
    if pd.isna(x):
        return None
    s = str(x).strip()
    s = s.replace("Bs", "").replace("bs", "").replace("$", "").strip()
    # quitar miles y normalizar decimal a '.'
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


# ----------------------------------------
# UPSERT de medicamentos (4 columnas clave)
# ----------------------------------------
def upsert_medicines_from_df(db: Session, df: pd.DataFrame) -> int:
    """
    Inserta/actualiza medicamentos a partir de las columnas:
    name, concentration, dosage_form, unit_measure, (opcional) code.
    """
    df = _norm_headers(df)

    # Normaliza los textos clave para identidad
    for c in ["name", "concentration", "dosage_form", "unit_measure"]:
        if c in df.columns:
            df[c] = df[c].map(_norm_txt)

    cols = ["name", "concentration", "dosage_form", "unit_measure", "code"]
    meds = df[[c for c in cols if c in df.columns]].drop_duplicates(
        subset=["name", "concentration", "dosage_form", "unit_measure"]
    )

    if meds.empty:
        return 0

    stmt = pg_insert(Medicine.__table__).values([
        dict(
            nombre=row["name"],
            concentracion=row["concentration"],
            forma_farmaceutica=row["dosage_form"],
            unidad_medida=row["unit_measure"],
            codigo=(str(row["code"]) if ("code" in meds.columns and pd.notna(row["code"])) else None),
            estado=True,
        )
        for _, row in meds.iterrows()
    ])

    # En conflicto por las 4 columnas únicas → actualiza 'codigo' solo si viene no-nulo
    on_conflict = stmt.on_conflict_do_update(
        index_elements=["nombre", "concentracion", "forma_farmaceutica", "unidad_medida"],
        set_={"codigo": func.coalesce(stmt.excluded.codigo, Medicine.__table__.c.codigo)}
    )
    res = db.execute(on_conflict)
    db.commit()
    return res.rowcount


# --------------------------------------
# UPSERT masivo de históricos (completo)
# --------------------------------------
def bulk_upsert_historical(db: Session, df_raw: pd.DataFrame, source_file: str | None = None):
    # 1) normaliza encabezados y valida requeridos
    df = _norm_headers(df_raw)

    REQUIRED = {"name", "concentration", "dosage_form", "unit_measure", "date", "outflow_qty"}
    faltan = [c for c in REQUIRED if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas requeridas: {faltan}")

    # 2) limpieza de claves y tipos
    for c in ["name", "concentration", "dosage_form", "unit_measure"]:
        df[c] = df[c].map(_norm_txt)

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["outflow_qty"] = pd.to_numeric(df["outflow_qty"].apply(_to_num))

    # opcionales
    opt_cols = [
        "prev_balance_qty", "prev_balance_value_bs",
        "inflow_qty", "inflow_value_bs",
        "outflow_value_bs",
        "total_balance_qty", "total_balance_value_bs",
    ]
    for c in opt_cols:
        if c in df.columns:
            df[c] = df[c].apply(_to_num)

    # descarta filas sin claves mínimas
    df = df.dropna(subset=["name", "concentration", "dosage_form", "unit_measure", "date", "outflow_qty"])

    if df.empty:
        return {"inserted": 0, "skipped": 0}

    # 3) asegura medicamentos (UPSERT) y construye mapa 4 claves → id
    upsert_medicines_from_df(db, df)

    meds = (
        db.query(Medicine)
          .filter(Medicine.name.in_(df["name"].unique().tolist()))
          .all()
    )
    med_map = {(m.name, m.concentration, m.dosage_form, m.unit_measure): m.id for m in meds}

    # 4) payload para UPSERT en historicos
    rows = []
    for _, r in df.iterrows():
        key = (r["name"], r["concentration"], r["dosage_form"], r["unit_measure"])
        mid = med_map.get(key)
        if not mid:
            # Fallback raro: crea y refresca (idempotente)
            m = Medicine(
                name=r["name"], concentration=r["concentration"],
                dosage_form=r["dosage_form"], unit_measure=r["unit_measure"],
                code=(str(r["code"]) if "code" in r and pd.notna(r["code"]) else None),
                status=True
            )
            db.add(m); db.commit(); db.refresh(m)
            mid = m.id
            med_map[key] = mid

        rec = {
            "medicamento_id": mid,
            "fecha": r["date"],
            "salidas_cantidad": float(r["outflow_qty"]),
        }
        if source_file is not None:
            rec["archivo_origen"] = source_file

        # añade opcionales si existen en el DF
        if "prev_balance_qty" in df.columns:       rec["saldo_gestion_anterior_cantidad"] = r.get("prev_balance_qty")
        if "prev_balance_value_bs" in df.columns:  rec["saldo_gestion_anterior_valor_bs"]  = r.get("prev_balance_value_bs")
        if "inflow_qty" in df.columns:             rec["ingresos_cantidad"]                = r.get("inflow_qty")
        if "inflow_value_bs" in df.columns:        rec["ingresos_valor_bs"]                = r.get("inflow_value_bs")
        if "outflow_value_bs" in df.columns:       rec["salidas_valor_bs"]                 = r.get("outflow_value_bs")
        if "total_balance_qty" in df.columns:      rec["saldos_totales_cantidad"]          = r.get("total_balance_qty")
        if "total_balance_value_bs" in df.columns: rec["saldos_totales_valor_bs"]          = r.get("total_balance_value_bs")

        rows.append(rec)

    if not rows:
        return {"inserted": 0, "skipped": 0}

    stmt = pg_insert(Historical.__table__).values(rows)

    # No sobreescribas con NULL: COALESCE(excluded, actual)
    on_conflict = stmt.on_conflict_do_update(
        index_elements=["medicamento_id", "fecha"],
        set_={
            "salidas_cantidad": func.coalesce(stmt.excluded.salidas_cantidad, Historical.__table__.c.salidas_cantidad),
            "saldo_gestion_anterior_cantidad": func.coalesce(stmt.excluded.saldo_gestion_anterior_cantidad, Historical.__table__.c.saldo_gestion_anterior_cantidad),
            "saldo_gestion_anterior_valor_bs": func.coalesce(stmt.excluded.saldo_gestion_anterior_valor_bs, Historical.__table__.c.saldo_gestion_anterior_valor_bs),
            "ingresos_cantidad": func.coalesce(stmt.excluded.ingresos_cantidad, Historical.__table__.c.ingresos_cantidad),
            "ingresos_valor_bs": func.coalesce(stmt.excluded.ingresos_valor_bs, Historical.__table__.c.ingresos_valor_bs),
            "salidas_valor_bs": func.coalesce(stmt.excluded.salidas_valor_bs, Historical.__table__.c.salidas_valor_bs),
            "saldos_totales_cantidad": func.coalesce(stmt.excluded.saldos_totales_cantidad, Historical.__table__.c.saldos_totales_cantidad),
            "saldos_totales_valor_bs": func.coalesce(stmt.excluded.saldos_totales_valor_bs, Historical.__table__.c.saldos_totales_valor_bs),
            "archivo_origen": func.coalesce(stmt.excluded.archivo_origen, Historical.__table__.c.archivo_origen),
        }
    )

    res = db.execute(on_conflict)
    db.commit()
    return {"inserted": res.rowcount, "skipped": 0}
