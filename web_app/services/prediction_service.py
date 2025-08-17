import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from ..models.medicine import Medicine
from ..models.prediction import Prediction

def _extract_forecast(model, steps: int):
    dates, values = None, None

    if hasattr(model, "get_forecast"):
        fc = model.get_forecast(steps=steps)
        mean = getattr(fc, "predicted_mean", None)
        if mean is not None:
            values = np.asarray(mean)
            try:
                from pandas import DatetimeIndex
                dates = DatetimeIndex(mean.index)
            except Exception:
                dates = None

    if values is None and hasattr(model, "forecast"):
        y = model.forecast(steps=steps)
        values = np.asarray(y)
        try:
            from pandas import DatetimeIndex
            dates = DatetimeIndex(getattr(y, "index", None))
        except Exception:
            dates = None

    if values is None and hasattr(model, "predict"):
        y = model.predict(steps)
        values = np.asarray(y)

    if values is None:
        raise ValueError("El modelo PKL no expone get_forecast/forecast/predict.")

    if dates is None or len(dates) != len(values):
        start = pd.Timestamp.today().to_period("M").to_timestamp() + pd.offsets.MonthBegin(1)
        dates = pd.date_range(start, periods=steps, freq="MS")

    return [pd.to_datetime(d).date() for d in dates], [float(v) for v in values]

def ensure_medicine(db: Session, name: str, concentration: str | int, dosage_form: str, unit_measure: str, code: str | None = None) -> Medicine:
    conc = str(concentration)
    m = (db.query(Medicine)
            .filter(Medicine.name==name,
                    Medicine.concentration==conc,
                    Medicine.dosage_form==dosage_form,
                    Medicine.unit_measure==unit_measure)
            .first())
    if not m:
        m = Medicine(name=name, concentration=conc,
                     dosage_form=dosage_form, unit_measure=unit_measure,
                     code=code)
        db.add(m); db.commit(); db.refresh(m)
    return m

def predict_and_persist(db: Session, model_key: str, model, medicine: Medicine, periods: int, user_id: int | None):
    dates, values = _extract_forecast(model, periods)
    out = []
    for d, y in zip(dates, values):
        p = Prediction(
            medicine_id=medicine.id,
            horizon_date=d,
            predicted_qty=y,
            model_name=model_key + ".pkl",
            params={"source": "pkl"},
            created_by=user_id,
        )
        db.add(p); out.append((d, y))
    db.commit()
    return out
