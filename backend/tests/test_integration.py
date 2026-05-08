"""
Tests de integración — flujos end-to-end multi-recurso.
Usan la misma base de datos SQLite en memoria del conftest.
"""

import uuid
from datetime import datetime, timezone
from app.config import settings
from app.models.checkin_record import CheckinRecord
from app.models.failed_attempt import FailedAttempt

DEVICE_H = {"Authorization": f"Bearer {settings.device_api_key}"}
WORKER   = {"full_name": "Carmen López", "employee_id": "EMP010", "nfc_uid": "04:CA:FF:EE:11"}
WORKER2  = {"full_name": "Pedro Ruiz",   "employee_id": "EMP011", "nfc_uid": "04:PE:DR:00:22"}


def _checkin_payload(nfc_uid: str) -> dict:
    return {
        "nfc_uid": nfc_uid,
        "device_id": "device-001",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "idempotency_key": str(uuid.uuid4()),
    }


def _login(client, admin_user) -> dict:
    return {"Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'secreto123'}).json()['access_token']}"}


class TestFlujoCompletoFichaje:
    def test_fichaje_valido_crea_registro_en_db(self, client, auth_headers, db):
        """Flujo: crear trabajador → fichar → verificar registro en DB."""
        client.post("/api/v1/workers", json=WORKER, headers=auth_headers)

        resp = client.post("/api/v1/checkins", json=_checkin_payload(WORKER["nfc_uid"]), headers=DEVICE_H)
        assert resp.status_code == 200
        assert resp.json()["event_type"] == "entrada"
        assert resp.json()["worker_name"] == "Carmen López"

        assert db.query(CheckinRecord).count() == 1

    def test_alternancia_completa_tres_fichajes(self, client, auth_headers, db):
        """Flujo: 3 fichajes consecutivos → entrada/salida/entrada."""
        client.post("/api/v1/workers", json=WORKER, headers=auth_headers)

        tipos = [
            client.post("/api/v1/checkins", json=_checkin_payload(WORKER["nfc_uid"]), headers=DEVICE_H).json()["event_type"]
            for _ in range(3)
        ]
        assert tipos == ["entrada", "salida", "entrada"]
        assert db.query(CheckinRecord).count() == 3

    def test_token_desconocido_403_y_failed_attempt(self, client, auth_headers, db):
        """Flujo: token desconocido → 403 + registro en failed_attempts."""
        resp = client.post("/api/v1/checkins", json=_checkin_payload("UID:FANTASMA"), headers=DEVICE_H)
        assert resp.status_code == 403
        assert db.query(FailedAttempt).count() == 1
        assert db.query(CheckinRecord).count() == 0

    def test_worker_desactivado_no_genera_registro(self, client, auth_headers, db):
        """Flujo: desactivar trabajador → intentar fichar → rechazado sin registro."""
        w = client.post("/api/v1/workers", json=WORKER, headers=auth_headers).json()
        client.patch(f"/api/v1/workers/{w['id']}/deactivate", headers=auth_headers)

        resp = client.post("/api/v1/checkins", json=_checkin_payload(WORKER["nfc_uid"]), headers=DEVICE_H)
        assert resp.status_code == 403
        assert db.query(CheckinRecord).count() == 0

    def test_dos_trabajadores_alternan_independientemente(self, client, auth_headers):
        """Flujo: dos trabajadores fichan, sus estados son independientes."""
        client.post("/api/v1/workers", json=WORKER,  headers=auth_headers)
        client.post("/api/v1/workers", json=WORKER2, headers=auth_headers)

        r1 = client.post("/api/v1/checkins", json=_checkin_payload(WORKER["nfc_uid"]),  headers=DEVICE_H).json()
        r2 = client.post("/api/v1/checkins", json=_checkin_payload(WORKER2["nfc_uid"]), headers=DEVICE_H).json()
        r3 = client.post("/api/v1/checkins", json=_checkin_payload(WORKER["nfc_uid"]),  headers=DEVICE_H).json()

        assert r1["event_type"] == "entrada"
        assert r2["event_type"] == "entrada"   # independiente del trabajador 1
        assert r3["event_type"] == "salida"


class TestFlujoOfflineSync:
    def test_sync_batch_crea_registros_correctos(self, client, auth_headers, db):
        """Flujo offline: enviar lote de 3 fichajes → 3 registros en DB."""
        client.post("/api/v1/workers", json=WORKER, headers=auth_headers)

        records = [_checkin_payload(WORKER["nfc_uid"]) for _ in range(3)]
        resp = client.post("/api/v1/checkins/sync", json={"records": records}, headers=DEVICE_H)
        assert resp.status_code == 200
        assert resp.json()["procesados"] == 3
        assert db.query(CheckinRecord).filter(CheckinRecord.synced_from_local == True).count() == 3

    def test_sync_idempotencia_mismo_lote_tres_veces(self, client, auth_headers, db):
        """Flujo offline: enviar el mismo lote 3 veces → estado idéntico."""
        client.post("/api/v1/workers", json=WORKER, headers=auth_headers)

        records = [_checkin_payload(WORKER["nfc_uid"]), _checkin_payload(WORKER["nfc_uid"])]

        for _ in range(3):
            client.post("/api/v1/checkins/sync", json={"records": records}, headers=DEVICE_H)

        # Solo deben existir 2 registros, no 6
        assert db.query(CheckinRecord).count() == 2

    def test_sync_mixto_validos_e_invalidos(self, client, auth_headers):
        """Flujo: lote con tokens válidos e inválidos → se procesan solo los válidos."""
        client.post("/api/v1/workers", json=WORKER, headers=auth_headers)

        records = [
            _checkin_payload(WORKER["nfc_uid"]),   # válido
            _checkin_payload("UID:NO_EXISTE"),       # inválido
            _checkin_payload(WORKER["nfc_uid"]),    # válido
        ]
        resp = client.post("/api/v1/checkins/sync", json={"records": records}, headers=DEVICE_H)
        assert resp.json()["procesados"] == 2
        assert resp.json()["rechazados"] == 1


class TestFlujoAutenticacion:
    def test_login_acceso_logout_deniega(self, client, admin_user):
        """Flujo: login → acceso protegido OK → logout → mismo token rechazado."""
        login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secreto123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        assert client.get("/api/v1/workers", headers=headers).status_code == 200

        client.post("/api/v1/auth/logout", headers=headers)

        assert client.get("/api/v1/workers", headers=headers).status_code == 401

    def test_bloqueo_ip_restaura_tras_login_exitoso(self, client, admin_user):
        """Flujo: 4 fallos → login OK → contador reseteado → 4 fallos más sin bloqueo."""
        from app.auth.ip_lockout import MAX_ATTEMPTS

        for _ in range(MAX_ATTEMPTS - 1):
            client.post("/api/v1/auth/login", json={"username": "admin", "password": "mala"})

        assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "secreto123"}).status_code == 200

        for _ in range(MAX_ATTEMPTS - 1):
            r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "mala"})
            assert r.status_code == 401  # sigue siendo 401, no 429


class TestFlujoCSVFidelidad:
    def test_csv_coincide_exactamente_con_consulta_filtrada(self, client, auth_headers):
        """Propiedad 8: CSV exportado contiene exactamente los mismos registros que la consulta."""
        client.post("/api/v1/workers", json=WORKER,  headers=auth_headers)
        client.post("/api/v1/workers", json=WORKER2, headers=auth_headers)

        # 2 fichajes de WORKER, 1 de WORKER2
        for _ in range(2):
            client.post("/api/v1/checkins", json=_checkin_payload(WORKER["nfc_uid"]), headers=DEVICE_H)
        client.post("/api/v1/checkins", json=_checkin_payload(WORKER2["nfc_uid"]), headers=DEVICE_H)

        # Filtrar solo entradas
        consulta = client.get("/api/v1/checkins?event_type=entrada", headers=auth_headers).json()
        csv_resp = client.get("/api/v1/export/checkins.csv?event_type=entrada", headers=auth_headers)

        contenido = csv_resp.text.lstrip("﻿")
        filas = [l for l in contenido.splitlines() if l.strip()]
        assert len(filas) - 1 == consulta["total"]

    def test_csv_sin_filtros_incluye_todos(self, client, auth_headers):
        """CSV sin filtros incluye todos los registros."""
        client.post("/api/v1/workers", json=WORKER, headers=auth_headers)
        for _ in range(4):
            client.post("/api/v1/checkins", json=_checkin_payload(WORKER["nfc_uid"]), headers=DEVICE_H)

        consulta = client.get("/api/v1/checkins?size=100", headers=auth_headers).json()
        csv_resp  = client.get("/api/v1/export/checkins.csv", headers=auth_headers)

        contenido = csv_resp.text.lstrip("﻿")
        filas = [l for l in contenido.splitlines() if l.strip()]
        assert len(filas) - 1 == consulta["total"]
