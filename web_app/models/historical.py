"""
Históricos de consumo por medicamento. Se llenan al subir CSV/XLSX.
"""

from sqlalchemy import Integer, String, Date, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base

class Historical(Base):
    __tablename__ = "historicos"

    id: Mapped[int] = mapped_column("id", primary_key=True)
    medicine_id: Mapped[int] = mapped_column("medicamento_id", ForeignKey("medicamentos.id"), index=True)
    date: Mapped[Date] = mapped_column("fecha", Date, index=True)

    # Demanda: "Salidas - Cantidad"
    outflow_qty: Mapped[float] = mapped_column("salidas_cantidad", Float)

    # Resto del dataset (opcionales):
    name: Mapped[str | None] = mapped_column("medicamento_e_insumo", String(200), nullable=True)
    concentration: Mapped[str | None] = mapped_column("concentracion", String(60), nullable=True)
    dosage_form: Mapped[str | None] = mapped_column("forma_farmaceutica", String(80), nullable=True)
    unit_measure: Mapped[str | None] = mapped_column("unidad_de_medida", String(30), nullable=True)
    prev_balance_qty:      Mapped[float | None] = mapped_column("saldo_gestion_anterior_cantidad", Float, nullable=True)
    prev_balance_value_bs: Mapped[float | None] = mapped_column("saldo_gestion_anterior_valor_bs", Float, nullable=True)
    inflow_qty:            Mapped[float | None] = mapped_column("ingresos_cantidad", Float, nullable=True)
    inflow_value_bs:       Mapped[float | None] = mapped_column("ingresos_valor_bs", Float, nullable=True)
    outflow_value_bs:      Mapped[float | None] = mapped_column("salidas_valor_bs", Float, nullable=True)
    total_balance_qty:     Mapped[float | None] = mapped_column("saldos_totales_cantidad", Float, nullable=True)
    total_balance_value_bs:Mapped[float | None] = mapped_column("saldos_totales_valor_bs", Float, nullable=True)
    source_file:           Mapped[str | None] = mapped_column("archivo_origen", String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("medicamento_id","fecha", name="uq_historicos_medicamento_fecha"),
    )
