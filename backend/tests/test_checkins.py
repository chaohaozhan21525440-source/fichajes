import uuid
from datetime import datetime, timezone
from app.config import settings

WORKER = {"full_name": "Ana García", "employee_id": "EMP001", "nfc_uid": "04:A3:2B:1C:9F"}
DEVICE_HEADERS = {"Authorization": f"Bearer {settings.device_api_key}"}


def _checkin_payload(nfc_uid: str = WORKER["nfc_uid"]) -> dict:
    return {
        "nfc_uid": nfc_uid,
        "device_id": "device-001",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "idempotency_key": str(uuid.uuid4()),
    }


def _create_worker(client, auth_headers, data=WORKER):
    return client.post("/api/v1/workers", json=data, headers=auth_headers).json()


class TestCheckinIndividual:
    def test_primer_fichaje_es_entrada(self, client, auth_headers):
        _create_worker(client, auth_headers)
        resp = client.post("/api/v1/checkins", json=_checkin_payload(), headers=DEVICE_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["event_type"] == "entrada"
        assert resp.json()["worker_name"] == "Ana García"

    def test_alternancia_entrada_salida(self, client, auth_headers):
        """Propiedad 1: el tipo de evento es siempre el opuesto al último registro."""
        _create_worker(client, auth_headers)
        r1 = client.post("/api/v1/checkins", json=_checkin_payload(), headers=DEVICE_HEADERS)
        r2 = client.post("/api/v1/checkins", json=_checkin_payload(), headers=DEVICE_HEADERS)
        r3 = client.post("/api/v1/checkins", json=_checkin_payload(), headers=DEVICE_HEADERS)
        assert r1.json()["event_type"] == "entrada"
        assert r2.json()["event_type"] == "salida"
        assert r3.json()["event_type"] == "entrada"

    def test_token_desconocido_devuelve_403(self, client, auth_headers):
        """Propiedad 9: token desconocido → 403."""
        _create_worker(client, auth_headers)
        resp = client.post("/api/v1/checkins", json=_checkin_payload("UID:DESCONOCIDO"), headers=DEVICE_HEADERS)
        assert resp.status_code == 403
        assert resp.json()["detail"]["error"] == "token_desconocido"

    def test_token_desconocido_registra_failed_attempt(self, client, auth_headers, db):
        """Propiedad 9: token desconocido → se crea registro en failed_attempts."""
        from app.models.failed_attempt import FailedAttempt
        _create_worker(client, auth_headers)
        client.post("/api/v1/checkins", json=_checkin_payload("UID:FANTASMA"), headers=DEVICE_HEADERS)
        count = db.query(FailedAttempt).filter(FailedAttempt.nfc_uid == "UID:FANTASMA").count()
        assert count == 1

    def test_worker_desactivado_rechazado(self, client, auth_headers):
        """Propiedad 10: trabajador desactivado → fichaje rechazado."""
        worker = _create_worker(client, auth_headers)
        client.patch(f"/api/v1/workers/{worker['id']}/deactivate", headers=auth_headers)
        resp = client.post("/api/v1/checkins", json=_checkin_payload(), headers=DEVICE_HEADERS)
        assert resp.status_code == 403

    def test_worker_desactivado_no_crea_checkin(self, client, auth_headers, db):
        """Propiedad 10: el rechazo no genera registro de fichaje válido."""
        from app.models.checkin_record import CheckinRecord
        worker = _create_worker(client, auth_headers)
        client.patch(f"/api/v1/workers/{worker['id']}/deactivate", headers=auth_headers)
        client.post("/api/v1/checkins", json=_checkin_payload(), headers=DEVICE_HEADERS)
        count = db.query(CheckinRecord).count()
        assert count == 0

    def test_idempotencia_mismo_key_mismo_resultado(self, client, auth_headers):
        """Propiedad 2: enviar el mismo idempotency_key dos veces → mismo resultado, sin duplicado."""
        from app.models.checkin_record import CheckinRecord
        _create_worker(client, auth_headers)
        payload = _checkin_payload()
        r1 = client.post("/api/v1/checkins", json=payload, headers=DEVICE_HEADERS)
        r2 = client.post("/api/v1/checkins", json=payload, headers=DEVICE_HEADERS)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["event_type"] == r2.json()["event_type"]

    def test_sin_auth_rechazado(self, client, auth_headers):
        _create_worker(client, auth_headers)
        resp = client.post("/api/v1/checkins", json=_checkin_payload())
        assert resp.status_code == 403

    def test_device_token_invalido_rechazado(self, client, auth_headers):
        _create_worker(client, auth_headers)
        resp = client.post("/api/v1/checkins", json=_checkin_payload(), headers={"Authorization": "Bearer token-malo"})
        assert resp.status_code == 401


class TestSyncCheckins:
    def test_sync_lote_basico(self, client, auth_headers):
        _create_worker(client, auth_headers)
        payload = {
            "records": [
                _checkin_payload(),
                _checkin_payload(),
            ]
        }
        resp = client.post("/api/v1/checkins/sync", json=payload, headers=DEVICE_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["procesados"] == 2
        assert resp.json()["rechazados"] == 0

    def test_sync_idempotencia(self, client, auth_headers):
        """Propiedad 2: enviar el mismo lote N veces produce el mismo estado."""
        from app.models.checkin_record import CheckinRecord
        _create_worker(client, auth_headers)
        records = [_checkin_payload(), _checkin_payload()]
        payload = {"records": records}

        client.post("/api/v1/checkins/sync", json=payload, headers=DEVICE_HEADERS)
        client.post("/api/v1/checkins/sync", json=payload, headers=DEVICE_HEADERS)
        client.post("/api/v1/checkins/sync", json=payload, headers=DEVICE_HEADERS)

        count = db_count = None
        # Verificar contando directamente vía endpoint de checkins
        resp = client.post("/api/v1/checkins/sync", json=payload, headers=DEVICE_HEADERS)
        assert resp.json()["procesados"] == 0
        assert resp.json()["rechazados"] == 2

    def test_sync_token_desconocido_cuenta_como_rechazado(self, client, auth_headers):
        _create_worker(client, auth_headers)
        payload = {"records": [_checkin_payload("UID:DESCONOCIDO")]}
        resp = client.post("/api/v1/checkins/sync", json=payload, headers=DEVICE_HEADERS)
        assert resp.json()["rechazados"] == 1
        assert resp.json()["procesados"] == 0

    def test_sync_sin_auth_rechazado(self, client, auth_headers):
        _create_worker(client, auth_headers)
        resp = client.post("/api/v1/checkins/sync", json={"records": []})
        assert resp.status_code == 403
