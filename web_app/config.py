"""
Configura la app leyendo variables del archivo .env.
"""

from pydantic import BaseModel
from dotenv import load_dotenv 
import os


# busca .env en la raiz del proyecto y lo carga
load_dotenv()  

class Settings(BaseModel):
    # Cadena de conexión para SQLAlchemy con el driver psycopg (PostgreSQL)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Config JWT (autenticación)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "cambiame")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

settings = Settings()