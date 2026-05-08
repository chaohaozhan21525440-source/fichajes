import pytest
from app.auth.security import create_access_token, revoke_token, _revoked_jtis
from app.auth.ip_lockout import MAX_ATTEMPTS


class TestLogin:
    def test_login_exitoso(self, client, admin_user):
        resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secreto123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_credenciales_incorrectas_usuario_malo(self, client, admin_user):
        resp = client.post("/api/v1/auth/login", json={"username": "noexiste", "password": "secreto123"})
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "credenciales_invalidas"

    def test_credenciales_incorrectas_password_mala(self, client, admin_user):
        resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "mala"})
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "credenciales_invalidas"

    def test_mensaje_error_generico_igual_en_ambos_casos(self, client, admin_user):
        """Propiedad 12: el mensaje de error nunca revela qué campo es incorrecto."""
        resp_usuario = client.post("/api/v1/auth/login", json={"username": "noexiste", "password": "secreto123"})
        resp_password = client.post("/api/v1/auth/login", json={"username": "admin", "password": "mala"})
        assert resp_usuario.json()["detail"]["message"] == resp_password.json()["detail"]["message"]

    def test_bloqueo_ip_tras_cinco_fallos(self, client, admin_user):
        """Propiedad 6: exactamente 5 fallos consecutivos activan bloqueo de 15 min."""
        for _ in range(MAX_ATTEMPTS):
            resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "mala"})
            assert resp.status_code == 401

        # El intento 6 (incluso con credenciales correctas) debe estar bloqueado
        resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secreto123"})
        assert resp.status_code == 429
        assert resp.json()["detail"]["error"] == "ip_bloqueada"

    def test_login_exitoso_resetea_contador(self, client, admin_user):
        # 4 fallos seguidos no bloquean
        for _ in range(MAX_ATTEMPTS - 1):
            client.post("/api/v1/auth/login", json={"username": "admin", "password": "mala"})

        # Login correcto resetea el contador
        resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secreto123"})
        assert resp.status_code == 200

        # Ahora se pueden hacer otros 4 fallos sin bloqueo
        for _ in range(MAX_ATTEMPTS - 1):
            resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "mala"})
            assert resp.status_code == 401


class TestLogout:
    def test_logout_invalida_token(self, client, admin_user):
        login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secreto123"})
        token = login.json()["access_token"]

        resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204

        # El mismo token ya no es válido
        resp2 = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp2.status_code == 401

    def test_logout_sin_token_rechazado(self, client, admin_user):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 403


class TestEndpointsProtegidos:
    def test_sin_token_devuelve_401_o_403(self, client, admin_user):
        """Propiedad 13: endpoints protegidos rechazan peticiones sin JWT."""
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code in (401, 403)

    def test_token_malformado_rechazado(self, client, admin_user):
        resp = client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer tokenbasura"})
        assert resp.status_code == 401

    def test_token_valido_permite_acceso(self, client, admin_user):
        login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secreto123"})
        token = login.json()["access_token"]
        resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204
