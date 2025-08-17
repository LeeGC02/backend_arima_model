"""
Metadatos de reportes exportados (por ejemplo, ruta del XLSX generado).
"""

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from ..db import Base

class Report(Base):
    __tablename__ = "reportes"

    id: Mapped[int] = mapped_column("id", primary_key=True)
    title: Mapped[str] = mapped_column("titulo", String(200))
    file_path: Mapped[str] = mapped_column("ruta_archivo", String(255))
    created_at: Mapped[datetime] = mapped_column("creado_en", DateTime, default=datetime.utcnow)
