from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path

from ..db import get_db
from .auth import require_roles
from ..models.user import Role, User
from ..utils.file_parsers import read_any_table, save_upload
from ..services.historical_service import upsert_medicines_from_df, bulk_upsert_historical
from ..schemas import UploadSummary
from ..services import historical_service as hs

router = APIRouter(prefix="/historical", tags=["Historicals"])
UPLOAD_DIR = Path("storage/uploads")

@router.post("/upload", response_model=UploadSummary)
def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ADMIN, Role.SUPERUSER, Role.OPERATOR))
):
    saved = save_upload(file, UPLOAD_DIR)
    try:
        df = read_any_table(str(saved))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Archivo inválido: {e}")

    # 1) UPSERT Medicamentos
    upsert_medicines_from_df(db, df)

    # 2) UPSERT Históricos (no se corta por duplicados, devuelve métricas)
    stats = hs.bulk_upsert_historical(db, df, source_file=saved.name)
    return {"rows_inserted": stats["inserted"], "file_saved_as": saved.name}

