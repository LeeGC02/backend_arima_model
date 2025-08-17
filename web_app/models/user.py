"""
Tabla de usuarios con roles. Se usa para autenticación y autorización.
- Role: Enum de roles admitidos.
- User: modelo/tabla users.
"""

from sqlalchemy import String, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum
from ..db import Base

class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    SUPERUSER = "SUPERUSER"
    OPERATOR = "OPERATOR"
    CONSULTANT = "CONSULTANT"

class User(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column("id", primary_key=True)
    email: Mapped[str] = mapped_column("correo", String(120), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column("contrasena_hash", String(255))
    full_name: Mapped[str | None] = mapped_column("nombre_completo", String(120))
    role: Mapped[Role] = mapped_column("rol", SAEnum(Role), default=Role.OPERATOR)
    is_active: Mapped[bool] = mapped_column("activo", Boolean, default=True)

