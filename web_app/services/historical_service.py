"""
Inserta en bloque los registros históricos leídos desde el DataFrame.
"""

from sqlalchemy.orm import Session
from ..models.medicine import Medicine
from ..models.historical import Historical
import pandas as pd

def upsert_medicines_from_df(db: Session, df: pd.DataFrame):
    cols = ["name","concentration","dosage_form","unit_measure","code"]
    meds = df[[c for c in cols if c in df.columns]].drop_duplicates(subset=["name","concentration","dosage_form","unit_measure"])
    for _, r in meds.iterrows():
        name = str(r["name"]); conc = str(r["concentration"]); form = str(r["dosage_form"]); unit = str(r["unit_measure"])
        m = (db.query(Medicine)
                .filter(Medicine.name==name,
                        Medicine.concentration==conc,
                        Medicine.dosage_form==form,
                        Medicine.unit_measure==unit)
                .first())
        if not m:
            m = Medicine(name=name, concentration=conc, dosage_form=form, unit_measure=unit,
                         code=str(r["code"]) if "code" in r and pd.notna(r["code"]) else None)
            db.add(m)
        else:
            if "code" in r and pd.notna(r["code"]):
                m.code = str(r["code"])
    db.commit()

def bulk_insert_historical(db: Session, df: pd.DataFrame, source_file: str):
    count = 0
    for _, r in df.iterrows():
        name = str(r["name"]); conc = str(r["concentration"]); form = str(r["dosage_form"]); unit = str(r["unit_measure"])
        m = (db.query(Medicine)
                .filter(Medicine.name==name,
                        Medicine.concentration==conc,
                        Medicine.dosage_form==form,
                        Medicine.unit_measure==unit)
                .first())
        if not m:
            m = Medicine(name=name, concentration=conc, dosage_form=form, unit_measure=unit,
                         code=str(r["code"]) if "code" in r and pd.notna(r["code"]) else None)
            db.add(m); db.commit(); db.refresh(m)

        h = Historical(
            medicine_id=m.id,
            date=pd.to_datetime(r["date"]).date(),
            outflow_qty=float(r["outflow_qty"]),
            name=name, concentration=conc, dosage_form=form, unit_measure=unit,
            prev_balance_qty=float(r["prev_balance_qty"]) if "prev_balance_qty" in r and pd.notna(r["prev_balance_qty"]) else None,
            prev_balance_value_bs=float(r["prev_balance_value_bs"]) if "prev_balance_value_bs" in r and pd.notna(r["prev_balance_value_bs"]) else None,
            inflow_qty=float(r["inflow_qty"]) if "inflow_qty" in r and pd.notna(r["inflow_qty"]) else None,
            inflow_value_bs=float(r["inflow_value_bs"]) if "inflow_value_bs" in r and pd.notna(r["inflow_value_bs"]) else None,
            outflow_value_bs=float(r["outflow_value_bs"]) if "outflow_value_bs" in r and pd.notna(r["outflow_value_bs"]) else None,
            total_balance_qty=float(r["total_balance_qty"]) if "total_balance_qty" in r and pd.notna(r["total_balance_qty"]) else None,
            total_balance_value_bs=float(r["total_balance_value_bs"]) if "total_balance_value_bs" in r and pd.notna(r["total_balance_value_bs"]) else None,
            source_file=source_file
        )
        db.add(h); count += 1
    db.commit()
    return count
