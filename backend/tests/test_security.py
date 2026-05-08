"""
Tests de seguridad — Propiedad 4, 12, 13.
"""

import uuid
from datetime import datetime, timezone
from app.config import settings

DEVICE_H = {"Authorization": f"Bearer {settings.device_api_key}"}
WORKER   = {"full_name": "Test User", "employee_id": "SEC001", "nfc_uid": "04:SE:CU:RE:01"}


class TestProteccionJWT:
    """Propiedad 13: endpoints protegidos rechazan JWT ausente, malformado, expirado o con firma inválida."""

    PROTECTED = [
        ("GET",   "/api/v1/workers"),
        ("GET",   "/api/v1/checkins"),
        ("GET",   "/api/v1/audit"),
        ("GET",   "/api/v1/export/checkins.csv"),
    ]

    def test_sin_token_todos_los_endpoints_rechazan(self, client, admin_user):
        for method, url in self.PROTECTED:
            resp = getattr(client, method.lower())(url)
            assert resp.status_code in (401, 403), f"{method} {url} debería rechazar sin token"

    def test_token_malformado_rechazado(self, client, admin_user):
        bad = {"Authorization": "Bearer esto.no.es.un.jwt"}
        for method, url in self.PROTECTED:
            resp = getattr(client, method.lower())(url, headers=bad)
            assert resp.status_code == 401, f"{method} {url} debería rechazar token malformado"

    def test_token_firma_invalida_rechazado(self, client, admin_user):
        # Token válido en estructura pero firmado con otra clave
        from jose import jwt as jose_jwt
        from datetime import timedelta
        fake_token = jose_jwt.encode(
            {"sub": str(uuid.uuid4()), "jti": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
            "clave-incorrecta",
            algorithm="HS256",
        )
        bad = {"Authorization": f"Bearer {fake_token}"}
        for method, url in self.PROTECTED:
            resp = getattr(client, method.lower())(url, headers=bad)
            assert resp.status_code == 401, f"{method} {url} debería rechazar firma inválida"

    def test_token_valido_permite_acceso(self, client, admin_user):
        token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secreto123"}).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/v1/workers", headers=headers).status_code == 200


class TestMensajeErrorGenerico:
    """Propiedad 12: mensaje de error idéntico independientemente del campo incorrecto."""

    def test_usuario_malo_vs_password_mala_mismo_mensaje(self, client, admin_user):
        r1 = client.post("/api/v1/auth/login", json={"username": "noexiste",  "password": "secreto123"})
        r2 = client.post("/api/v1/auth/login", json={"username": "admin",     "password": "mala"})
        r3 = client.post("/api/v1/auth/login", json={"username": "noexiste",  "password": "mala"})

        msgs = {r.json()["detail"]["message"] for r in [r1, r2, r3]}
        assert len(msgs) == 1, "El mensaje de error debe ser siempre idéntico"

    def test_error_no_revela_campo_incorrecto(self, client, admin_user):
        resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "mala"})
        msg = resp.json()["detail"]["message"].lower()
        assert "usuario" not in msg
        assert "contraseña" not in msg
        assert "password" not in msg


class TestInmutabilidadFichajes:
    """Propiedad 4: los registros de fichaje no pueden ser modificados ni eliminados."""

    def test_no_existe_endpoint_delete_checkins(self, client, auth_headers):
        """No debe haber endpoint DELETE en /api/v1/checkins."""
        client.post("/api/v1/workers", json=WORKER, headers=auth_headers)
        client.post("/api/v1/checkins", json={
            "nfc_uid": WORKER["nfc_uid"],
            "device_id": "device-001",
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": str(uuid.uuid4()),
        }, headers=DEVICE_H)

        checkin_id = client.get("/api/v1/checkins", headers=auth_headers).json()["items"][0]["id"]

        resp_del   = client.delete(f"/api/v1/checkins/{checkin_id}", headers=auth_headers)
        resp_put   = client.put(f"/api/v1/checkins/{checkin_id}", json={}, headers=auth_headers)
        resp_patch = client.patch(f"/api/v1/checkins/{checkin_id}", json={}, headers=auth_headers)

        assert resp_del.status_code   in (404, 405)
        assert resp_put.status_code   in (404, 405)
        assert resp_patch.status_code in (404, 405)
