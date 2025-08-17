"""
Servicios (lógica) de autenticación: crear usuario y autenticar.
"""

# web_app/services/auth_service.py
from sqlalchemy.orm import Session
from ..models.user import User, Role
import web_app.security as security

def create_user(db: Session, email: str, password: str, role: str, full_name: str | None):
    u = User(email=email,
             hashed_password=security.hash_password(password),
             role=Role(role),
             full_name=full_name)
    db.add(u); db.commit(); db.refresh(u)
    return u

def authenticate(db: Session, email: str, password: str):
    u = db.query(User).filter(User.email == email).first()
    if not u or not security.verify_password(password, u.hashed_password):
        return None
    token = security.create_access_token({"sub": u.email, "role": u.role.value})
    return token, u