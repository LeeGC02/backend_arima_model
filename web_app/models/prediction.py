"""
Tabla donde se guardan predicciones generadas por el microservicio.
"""

from sqlalchemy import String, Date, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base

class Prediction(Base):
    __tablename__ = "predicciones"

    id: Mapped[int] = mapped_column("id", primary_key=True)
    medicine_id: Mapped[int] = mapped_column("medicamento_id", ForeignKey("medicamentos.id"), index=True)
    horizon_date: Mapped[Date] = mapped_column("fecha_objetivo", Date, index=True)
    predicted_qty: Mapped[float] = mapped_column("cantidad_prevista", Float)
    model_name: Mapped[str] = mapped_column("modelo", String(200))  # nombre exacto del .pkl
    params: Mapped[dict | None] = mapped_column("parametros", JSON)
    created_by: Mapped[int | None] = mapped_column("creado_por", ForeignKey("usuarios.id"))
