"""
Define la conexión a la BD, el creador de sesiones y la clase Base para los modelos.
"""

from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

# Crea el motor usando la URL de conexión 
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Crea el motor usando la URL de conexión
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase): 
    # clase base para todas las tablas (modelos)
    pass

def get_db():
    # dependencia para fastapi: inyecta una sesión de BD en los endpoints.
    # Uso: db: Session = Depends(get_db)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

