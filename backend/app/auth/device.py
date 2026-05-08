from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

_bearer = HTTPBearer()


def get_device(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    if credentials.credentials != settings.device_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "device_no_autorizado", "message": "Token de dispositivo inválido"},
        )
    return credentials.credentials
