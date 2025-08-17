# seed_admin.py (en la raíz, al lado de web_app/)
from web_app.db import SessionLocal, Base, engine
from web_app.models.user import User, Role
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "admin@example.com").first():
            print("Admin ya existe.")
            return
        u = User(
            email="admin@example.com",
            hashed_password=pwd_ctx.hash("admin123"),  # ← hasheamos aquí
            role=Role.SUPERUSER,
            full_name="Administrador",
        )
        db.add(u)
        db.commit()
        print("Admin creado: admin@example.com / admin123")
    finally:
        db.close()

if __name__ == "__main__":
    run()
