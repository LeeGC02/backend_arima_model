from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base

class Medicine(Base):
    __tablename__ = "medicamentos"

    id: Mapped[int] = mapped_column("id", primary_key=True)
    code: Mapped[str | None] = mapped_column("codigo", String(60), nullable=True)

    # Semántica de tus 4 atributos:
    # - name: "Medicamento e Insumo" (ej. "Paracetamol")
    # - concentration: número como texto (ej. "500")  ← dejamos texto para flexibilidad y naming del PKL
    # - dosage_form: unidad del número (ej. "mg")
    # - unit_measure: presentación (ej. "compr", "inyeccion")
    name: Mapped[str] = mapped_column("nombre", String(200), index=True)
    concentration: Mapped[str] = mapped_column("concentracion", String(60))
    dosage_form: Mapped[str] = mapped_column("forma_farmaceutica", String(80))
    unit_measure: Mapped[str] = mapped_column("unidad_medida", String(30))

    __table_args__ = (
        UniqueConstraint("nombre","concentracion","forma_farmaceutica","unidad_medida",
                         name="uq_medicamento_por_atributos"),
    )
