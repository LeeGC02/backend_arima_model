# scripts/import_excel_staging.py
import sys
import pandas as pd
from sqlalchemy import create_engine, text

# ⬇️ PON tu cadena de conexión ENTRE COMILLAS
# Ejemplo válido:
# "postgresql+psycopg://postgres:chibola2@localhost:5432/hmmc_meds_db"
DATABASE_URL = "postgresql+psycopg://postgres:chibola2@localhost:5432/hmmc_meds_db"


def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra encabezados del Excel a nombres internos esperados."""
    rename = {
        "Código": "code",
        "Codigo": "code",
        "Medicamento e Insumo": "name",
        "Nombre": "name",
        "Concentración": "concentration",
        "Concentracion": "concentration",
        "Forma Farmaceutica": "dosage_form",
        "Forma Farmacéutica": "dosage_form",
        "Unidad de Medida": "unit_measure",
        "Fecha": "date",
        "Salidas - Cantidad": "outflow_qty",
        "Saldo Gestión Anterior - Cantidad": "prev_balance_qty",
        "Saldo Gestión Anterior - Valor (Bs.)": "prev_balance_value_bs",
        "Ingresos - Cantidad": "inflow_qty",
        "Ingresos - Valor (Bs.)": "inflow_value_bs",
        "Salidas - Valor (Bs.)": "outflow_value_bs",
        "Saldos Totales - Cantidad": "total_balance_qty",
        "Saldos Totales - Valor (Bs.)": "total_balance_value_bs",
    }
    df.columns = [c.strip() for c in df.columns]
    return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})


def to_float(x):
    """Convierte '1.234,56' / '1,234.56' / 'Bs 1.234' a float o None."""
    if pd.isna(x):
        return None
    s = str(x).strip().replace("Bs", "").replace("bs", "").replace("$", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def main(xlsx_path: str):
    engine = create_engine(DATABASE_URL)

    # 1) Lee Excel
    df = pd.read_excel(xlsx_path, dtype=str)
    df = norm_cols(df)

    # 2) Normaliza textos mínimos
    for c in ["name", "concentration", "dosage_form", "unit_measure", "code"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.strip()

    # 3) Tipos: fecha y numéricos
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    for c in [
        "outflow_qty",
        "prev_balance_qty",
        "prev_balance_value_bs",
        "inflow_qty",
        "inflow_value_bs",
        "outflow_value_bs",
        "total_balance_qty",
        "total_balance_value_bs",
    ]:
        if c in df.columns:
            df[c] = df[c].apply(to_float)

    # 4) Deja solo columnas conocidas para staging
    keep = [
        "code", "name", "concentration", "dosage_form", "unit_measure", "date",
        "outflow_qty", "prev_balance_qty", "prev_balance_value_bs",
        "inflow_qty", "inflow_value_bs", "outflow_value_bs",
        "total_balance_qty", "total_balance_value_bs",
    ]
    keep = [c for c in keep if c in df.columns]
    df = df[keep]

    with engine.begin() as conn:
        # 5) Tabla staging limpia
        conn.execute(text("""
            DROP TABLE IF EXISTS stg_historicos;
            CREATE TABLE stg_historicos (
              code text,
              name text,
              concentration text,
              dosage_form text,
              unit_measure text,
              date date,
              outflow_qty double precision,
              prev_balance_qty double precision,
              prev_balance_value_bs double precision,
              inflow_qty double precision,
              inflow_value_bs double precision,
              outflow_value_bs double precision,
              total_balance_qty double precision,
              total_balance_value_bs double precision
            );
        """))

        # 6) Sube el DataFrame a staging
        df.to_sql("stg_historicos", con=conn, if_exists="append", index=False)

        # 7) UPSERT a medicamentos (4 columnas clave)
        conn.execute(text("""
            INSERT INTO public.medicamentos
            (nombre, concentracion, forma_farmaceutica, unidad_medida, codigo, estado)
            SELECT
            nombre,
            concentracion,
            forma_farmaceutica,
            unidad_medida,
            MAX(codigo) AS codigo,   -- elige un código no nulo/“máximo” si hay varios
            TRUE AS estado
            FROM (
            SELECT
                trim(name)               AS nombre,
                trim(concentration)      AS concentracion,
                trim(dosage_form)        AS forma_farmaceutica,
                trim(unit_measure)       AS unidad_medida,
                NULLIF(trim(code), '')   AS codigo
            FROM stg_historicos
            WHERE COALESCE(trim(name),'') <> ''
                AND COALESCE(trim(concentration),'') <> ''
                AND COALESCE(trim(dosage_form),'') <> ''
                AND COALESCE(trim(unit_measure),'') <> ''
            ) x
            GROUP BY nombre, concentracion, forma_farmaceutica, unidad_medida
            ON CONFLICT (nombre,concentracion,forma_farmaceutica,unidad_medida)
            DO UPDATE SET codigo = COALESCE(EXCLUDED.codigo, medicamentos.codigo);
        """))


        # 8) Constraint única de historicos (si faltara)
        conn.execute(text("""
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_historicos_medicamento_fecha'
          ) THEN
            ALTER TABLE public.historicos
              ADD CONSTRAINT uq_historicos_medicamento_fecha
              UNIQUE (medicamento_id, fecha);
          END IF;
        END$$;
        """))

        # 9) Asegura columnas opcionales (si faltaran)
        conn.execute(text("""
        ALTER TABLE public.historicos
          ADD COLUMN IF NOT EXISTS saldo_gestion_anterior_cantidad double precision,
          ADD COLUMN IF NOT EXISTS saldo_gestion_anterior_valor_bs  double precision,
          ADD COLUMN IF NOT EXISTS ingresos_cantidad                double precision,
          ADD COLUMN IF NOT EXISTS ingresos_valor_bs                double precision,
          ADD COLUMN IF NOT EXISTS salidas_valor_bs                 double precision,
          ADD COLUMN IF NOT EXISTS saldos_totales_cantidad          double precision,
          ADD COLUMN IF NOT EXISTS saldos_totales_valor_bs          double precision,
          ADD COLUMN IF NOT EXISTS archivo_origen                   varchar(255);
        """))

        # 10) UPSERT a historicos (join por 4 columnas → medicamento_id)
        conn.execute(text("""
            WITH s AS (
            SELECT
                trim(name)          AS nombre,
                trim(concentration) AS concentracion,
                trim(dosage_form)   AS forma_farmaceutica,
                trim(unit_measure)  AS unidad_medida,
                date,
                MAX(outflow_qty)              AS outflow_qty,
                MAX(prev_balance_qty)         AS prev_balance_qty,
                MAX(prev_balance_value_bs)    AS prev_balance_value_bs,
                MAX(inflow_qty)               AS inflow_qty,
                MAX(inflow_value_bs)          AS inflow_value_bs,
                MAX(outflow_value_bs)         AS outflow_value_bs,
                MAX(total_balance_qty)        AS total_balance_qty,
                MAX(total_balance_value_bs)   AS total_balance_value_bs
            FROM stg_historicos
            WHERE date IS NOT NULL
                AND outflow_qty IS NOT NULL
            GROUP BY 1,2,3,4,5
            )
            INSERT INTO public.historicos (
            medicamento_id, fecha, salidas_cantidad,
            saldo_gestion_anterior_cantidad, saldo_gestion_anterior_valor_bs,
            ingresos_cantidad, ingresos_valor_bs, salidas_valor_bs,
            saldos_totales_cantidad, saldos_totales_valor_bs, archivo_origen
            )
            SELECT
            m.id,
            s.date,
            s.outflow_qty,
            s.prev_balance_qty,
            s.prev_balance_value_bs,
            s.inflow_qty,
            s.inflow_value_bs,
            s.outflow_value_bs,
            s.total_balance_qty,
            s.total_balance_value_bs,
            :fname
            FROM s
            JOIN public.medicamentos m
            ON m.nombre = s.nombre
            AND m.concentracion = s.concentracion
            AND m.forma_farmaceutica = s.forma_farmaceutica
            AND m.unidad_medida = s.unidad_medida
            ON CONFLICT (medicamento_id, fecha) DO UPDATE SET
            salidas_cantidad                 = COALESCE(EXCLUDED.salidas_cantidad,                 historicos.salidas_cantidad),
            saldo_gestion_anterior_cantidad = COALESCE(EXCLUDED.saldo_gestion_anterior_cantidad, historicos.saldo_gestion_anterior_cantidad),
            saldo_gestion_anterior_valor_bs  = COALESCE(EXCLUDED.saldo_gestion_anterior_valor_bs,  historicos.saldo_gestion_anterior_valor_bs),
            ingresos_cantidad                = COALESCE(EXCLUDED.ingresos_cantidad,                historicos.ingresos_cantidad),
            ingresos_valor_bs                = COALESCE(EXCLUDED.ingresos_valor_bs,                historicos.ingresos_valor_bs),
            salidas_valor_bs                 = COALESCE(EXCLUDED.salidas_valor_bs,                 historicos.salidas_valor_bs),
            saldos_totales_cantidad          = COALESCE(EXCLUDED.saldos_totales_cantidad,          historicos.saldos_totales_cantidad),
            saldos_totales_valor_bs          = COALESCE(EXCLUDED.saldos_totales_valor_bs,          historicos.saldos_totales_valor_bs),
            archivo_origen                   = COALESCE(EXCLUDED.archivo_origen,                   historicos.archivo_origen);
        """), {"fname": xlsx_path.split("/")[-1]})

    print("✅ Carga completada.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_excel_staging.py RUTA_AL_EXCEL")
        sys.exit(1)
    main(sys.argv[1])
