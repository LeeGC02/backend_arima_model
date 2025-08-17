"""
Módulo 3: Visualización simple de históricos con paginación básica.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .auth import require_roles
from ..models.user import Role
from ..models.historical import Historical
from ..models.medicine import Medicine
from ..models.prediction import Prediction

router = APIRouter(prefix="/visualize", tags=["Visualize"])

@router.get("/historical")
def list_historical(name: str, concentration: str, dosage_form: str, unit_measure: str,
                    date_from: str | None = None, date_to: str | None = None,
                    limit: int = 200, skip: int = 0,
                    db: Session = Depends(get_db),
                    _: any = Depends(require_roles(Role.ADMIN, Role.SUPERUSER, Role.OPERATOR, Role.CONSULTANT))):
    m = (db.query(Medicine)
            .filter(Medicine.name==name, Medicine.concentration==concentration,
                    Medicine.dosage_form==dosage_form, Medicine.unit_measure==unit_measure)
            .first())
    if not m: return {"total": 0, "items": []}
    q = db.query(Historical).filter(Historical.medicine_id==m.id)
    if date_from: q = q.filter(Historical.date >= date_from)
    if date_to: q = q.filter(Historical.date <= date_to)
    total = q.count()
    rows = q.order_by(Historical.date).offset(skip).limit(limit).all()
    return {"total": total, "items": [
        {"date": r.date, "outflow_qty": r.outflow_qty,
         "inflow_qty": r.inflow_qty, "total_balance_qty": r.total_balance_qty}
        for r in rows
    ]}

@router.get("/predictions")
def list_predictions(name: str, concentration: str, dosage_form: str, unit_measure: str,
                     db: Session = Depends(get_db),
                     _: any = Depends(require_roles(Role.ADMIN, Role.SUPERUSER, Role.OPERATOR, Role.CONSULTANT))):
    m = (db.query(Medicine)
            .filter(Medicine.name==name, Medicine.concentration==concentration,
                    Medicine.dosage_form==dosage_form, Medicine.unit_measure==unit_measure)
            .first())
    if not m: return []
    rows = db.query(Prediction).filter(Prediction.medicine_id==m.id).order_by(Prediction.horizon_date).all()
    return [{"date": r.horizon_date, "yhat": r.predicted_qty, "model": r.model_name} for r in rows]
