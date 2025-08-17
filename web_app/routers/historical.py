"""
Módulo 2: Carga de históricos (CSV/XLSX).
- Requiere instalar python-multipart para UploadFile.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path

from ..db import get_db
from .auth import require_roles
from ..models.user import Role, User
from ..utils.file_parsers import read_any_table, save_upload
from ..services.historical_service import upsert_medicines_from_df, bulk_insert_historical
from ..schemas import UploadSummary

router = APIRouter(prefix="/historical", tags=["Historicals"])
UPLOAD_DIR = Path("storage/uploads")

SPANISH_TO_INTERNAL = {
    "código": "code",
    "medicamento e insumo": "name",
    "concentración": "concentration",
    "forma farmaceutica": "dosage_form",
    "unidad de medida": "unit_measure",
    "fecha": "date",
    "salidas - cantidad": "outflow_qty",
    # opcionales:
    "saldo gestión anterior - cantidad": "prev_balance_qty",
    "saldo gestión anterior - valor (bs.)": "prev_balance_value_bs",
    "ingresos - cantidad": "inflow_qty",
    "ingresos - valor (bs.)": "inflow_value_bs",
    "salidas - valor (bs.)": "outflow_value_bs",
    "saldos totales - cantidad": "total_balance_qty",
    "saldos totales - valor (bs.)": "total_balance_value_bs",
}

REQUIRED = {"name","concentration","dosage_form","unit_measure","date","outflow_qty"}

@router.post("/upload", response_model=UploadSummary)
def upload(file: UploadFile = File(...),
           db: Session = Depends(get_db),
           user: User = Depends(require_roles(Role.ADMIN, Role.SUPERUSER, Role.OPERATOR))):
    saved = save_upload(file, UPLOAD_DIR)
    try:
        df = read_any_table(str(saved))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Archivo inválido: {e}")

    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={k:v for k,v in SPANISH_TO_INTERNAL.items() if k in df.columns})

    missing = REQUIRED - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"Faltan columnas: {sorted(missing)}")

    upsert_medicines_from_df(db, df)
    inserted = bulk_insert_historical(db, df, saved.name)
    return {"rows_inserted": inserted, "file_saved_as": saved.name}

