"""
Script para crear el primer administrador en la base de datos.

Uso:
    python create_admin.py <username> <password>

Ejemplo:
    python create_admin.py admin MiPassword123
"""

import sys
from app.database import SessionLocal
from app.models.admin import Admin
from app.auth.security import hash_password


def create_admin(username: str, password: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(Admin).filter(Admin.username == username).first()
        if existing:
            print(f"Ya existe un administrador con el nombre '{username}'.")
            sys.exit(1)

        admin = Admin(username=username, password_hash=hash_password(password))
        db.add(admin)
        db.commit()
        print(f"Administrador '{username}' creado correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python create_admin.py <username> <password>")
        sys.exit(1)
    create_admin(sys.argv[1], sys.argv[2])
