from datetime import datetime, timedelta, timezone
from uuid import uuid4
import bcrypt
from jose import JWTError, jwt
from app.config import settings

# Blacklist en memoria para tokens revocados (válido para despliegue de instancia única)
_revoked_jtis: set[str] = set()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(admin_id: str, username: str) -> str:
    jti = str(uuid4())
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": admin_id, "username": username, "jti": jti, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    if payload.get("jti") in _revoked_jtis:
        raise JWTError("token_revocado")
    return payload


def revoke_token(token: str) -> None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if jti := payload.get("jti"):
            _revoked_jtis.add(jti)
    except JWTError:
        pass
