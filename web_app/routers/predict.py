"""
Módulo 4: Microservicio predictivo.
- Lista modelos .pkl cargados desde /modelos
- Genera predicciones y las guarda en la tabla predictions
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import pandas as pd

from ..db import get_db
from .auth import require_roles
from ..models.user import Role, User
from ..schemas import PredictByAttrs, PredictResponse, ForecastPoint
from ..models_loader import ModelRegistry, build_model_basename
from ..services.prediction_service import ensure_medicine, predict_and_persist

router = APIRouter(prefix="/predict", tags=["Predict"])

MODELOS_DIR = Path(__file__).resolve().parents[1].parent / "modelos"
registry = ModelRegistry(MODELOS_DIR); registry.load_all()

@router.get("/models")
def list_models():
    return {"loaded": registry.keys()}

@router.post("", response_model=PredictResponse)
def predict(req: PredictByAttrs,
            db: Session = Depends(get_db),
            user: User = Depends(require_roles(Role.ADMIN, Role.SUPERUSER, Role.OPERATOR))):
    key = build_model_basename(req.name, req.concentration, req.dosage_form, req.unit_measure)
    got = registry.get_by_attrs(req.name, req.concentration, req.dosage_form, req.unit_measure)
    if not got:
        raise HTTPException(status_code=404, detail=f"No se encontró PKL: {key}.pkl")
    model_key, model = got

    med = ensure_medicine(db, req.name, req.concentration, req.dosage_form, req.unit_measure)

    result = predict_and_persist(db, model_key, model, med, req.periods, user.id)
    points = [ForecastPoint(date=pd.to_datetime(d).date(), yhat=float(y)) for d, y in result]
    return {"modelo": model_key + ".pkl", "points": points}
