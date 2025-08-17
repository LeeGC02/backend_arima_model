"""
Módulo 1: Autenticación.
- /auth/token  (form-data: username/password)  -> devuelve JWT para Swagger Authorize
- /auth/login: devuelve JWT si las credenciales son correctas.
- /auth/register: crea un usuario (solo ADMIN/SUPERUSER).
"""

# web_app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import LoginIn, Token, UserCreate, UserOut
from ..services.auth_service import authenticate, create_user
from ..models.user import Role, User
import web_app.security as security

router = APIRouter(prefix="/auth", tags=["Auth"])

# ¡OJO! Debe ser /auth/token
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token")

def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    payload = security.decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    u = db.query(User).filter(User.email == payload["sub"]).first()
    if not u:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return u

def require_roles(*roles: Role):
    def inner(u: User = Depends(current_user)):
        if u.role not in roles:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return u
    return inner

@router.post("/token", response_model=Token)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    result = authenticate(db, form.username, form.password)  # username = email
    if not result:
        raise HTTPException(status_code=400, detail="Credenciales inválidas")
    tok, _ = result
    return {"access_token": tok}

@router.post("/login", response_model=Token)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    result = authenticate(db, payload.email, payload.password)
    if not result:
        raise HTTPException(status_code=400, detail="Credenciales inválidas")
    tok, _ = result
    return {"access_token": tok}

@router.post("/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db),
             _: User = Depends(require_roles(Role.ADMIN, Role.SUPERUSER))):
    return create_user(db, payload.email, payload.password, payload.role, payload.full_name)
