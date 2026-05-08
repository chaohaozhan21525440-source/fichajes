"""
Crea el admin inicial si no existe ninguno en la base de datos.
Se ejecuta automáticamente en cada arranque del backend (Railway start command).
Es idempotente: no hace nada si ya hay un admin.

Variables de entorno:
    ADMIN_USERNAME  (default: admin)
    ADMIN_PASSWORD  (si no se define, se genera una contraseña aleatoria y se imprime en logs)
"""
import secrets
import sys

from app.database import SessionLocal
from app.models.admin import Admin
from app.auth.security import hash_password
from app.config import settings


def seed():
    db = SessionLocal()
    try:
        existing = db.query(Admin).filter(Admin.username == settings.admin_username).first()

        if existing:
            if settings.admin_password:
                existing.password_hash = hash_password(settings.admin_password)
                db.commit()
                print(f"Contraseña de '{settings.admin_username}' actualizada.", flush=True)
            else:
                print("Admin ya existe, no se modifica.", flush=True)
            return

        password = settings.admin_password
        if not password:
            password = secrets.token_urlsafe(16)
            print(
                f"\n*** ADMIN CREADO ***\n"
                f"  Usuario:    {settings.admin_username}\n"
                f"  Contraseña: {password}\n"
                f"  Guárdala ahora — no se volverá a mostrar.\n",
                flush=True,
            )

        admin = Admin(
            username=settings.admin_username,
            password_hash=hash_password(password),
        )
        db.add(admin)
        db.commit()
        print(f"Admin '{settings.admin_username}' creado.", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
