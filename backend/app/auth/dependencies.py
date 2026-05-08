from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.security import decode_access_token
from app.models.admin import Admin

bearer_scheme = HTTPBearer()


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        admin_id: str | None = payload.get("sub")
        if not admin_id:
            raise JWTError("sin sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "sesion_expirada", "message": "Token inválido o expirado"},
        )

    admin = db.get(Admin, UUID(admin_id))
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "sesion_expirada", "message": "Token inválido o expirado"},
        )
    return admin
