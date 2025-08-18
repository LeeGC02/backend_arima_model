from sqlalchemy import String, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base

class Medicine(Base):
    __tablename__ = "medicamentos"

    id: Mapped[int] = mapped_column("id", primary_key=True)
    code: Mapped[str | None] = mapped_column("codigo", String(60), nullable=True)

    # Claves de identidad del medicamento (mapeadas a tu BD)
    name: Mapped[str] = mapped_column("nombre", String(200), index=True)
    concentration: Mapped[str] = mapped_column("concentracion", String(60))
    dosage_form: Mapped[str] = mapped_column("forma_farmaceutica", String(80))
    unit_measure: Mapped[str] = mapped_column("unidad_medida", String(30))

    # Campo que vi en tu captura
    status: Mapped[bool] = mapped_column("estado", Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint(
            "nombre", "concentracion", "forma_farmaceutica", "unidad_medida",
            name="uq_medicamento_por_atributos"
        ),
    )
