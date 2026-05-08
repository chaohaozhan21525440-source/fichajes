from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.admin import Admin
from app.schemas.auth import LoginRequest, TokenResponse
from app.auth.security import verify_password, create_access_token, revoke_token
from app.auth.ip_lockout import is_ip_locked, record_failed_attempt, reset_failed_attempts
from app.auth.dependencies import get_current_admin, bearer_scheme

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_ERROR_CREDENCIALES = {
    "error": "credenciales_invalidas",
    "message": "Credenciales incorrectas",
}


@router.post("/login", response_model=TokenResponse)
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"

    if is_ip_locked(db, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "ip_bloqueada", "message": "Demasiados intentos fallidos. Inténtelo más tarde."},
        )

    admin = db.query(Admin).filter(Admin.username == body.username, Admin.is_active == True).first()

    if not admin or not verify_password(body.password, admin.password_hash):
        record_failed_attempt(db, client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_ERROR_CREDENCIALES)

    reset_failed_attempts(db, client_ip)
    token = create_access_token(str(admin.id), admin.username)
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    _admin: Admin = Depends(get_current_admin),
):
    revoke_token(credentials.credentials)
