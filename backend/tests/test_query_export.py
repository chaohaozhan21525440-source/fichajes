import uuid
from datetime import datetime, timezone
from app.config import settings

WORKER_1 = {"full_name": "Ana García", "employee_id": "EMP001", "nfc_uid": "04:AA:BB:CC:DD"}
WORKER_2 = {"full_name": "Luis Pérez", "employee_id": "EMP002", "nfc_uid": "04:11:22:33:44"}
DEVICE_HEADERS = {"Authorization": f"Bearer {settings.device_api_key}"}


def _checkin(client, nfc_uid: str) -> dict:
    return client.post("/api/v1/checkins", json={
        "nfc_uid": nfc_uid,
        "device_id": "device-001",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "idempotency_key": str(uuid.uuid4()),
    }, headers=DEVICE_HEADERS).json()


def _setup(client, auth_headers):
    client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
    client.post("/api/v1/workers", json=WORKER_2, headers=auth_headers)
    _checkin(client, WORKER_1["nfc_uid"])  # entrada
    _checkin(client, WORKER_1["nfc_uid"])  # salida
    _checkin(client, WORKER_2["nfc_uid"])  # entrada


class TestListCheckins:
    def test_lista_todos_los_registros(self, client, auth_headers):
        _setup(client, auth_headers)
        resp = client.get("/api/v1/checkins", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_orden_descendente_por_fecha(self, client, auth_headers):
        _setup(client, auth_headers)
        resp = client.get("/api/v1/checkins", headers=auth_headers)
        items = resp.json()["items"]
        fechas = [item["recorded_at"] for item in items]
        assert fechas == sorted(fechas, reverse=True)

    def test_filtro_por_worker_id(self, client, auth_headers):
        w1 = client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers).json()
        client.post("/api/v1/workers", json=WORKER_2, headers=auth_headers)
        _checkin(client, WORKER_1["nfc_uid"])
        _checkin(client, WORKER_2["nfc_uid"])

        resp = client.get(f"/api/v1/checkins?worker_id={w1['id']}", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["worker_name"] == "Ana García"

    def test_filtro_por_event_type(self, client, auth_headers):
        _setup(client, auth_headers)
        resp = client.get("/api/v1/checkins?event_type=salida", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert all(i["event_type"] == "salida" for i in data["items"])

    def test_paginacion(self, client, auth_headers):
        _setup(client, auth_headers)
        resp = client.get("/api/v1/checkins?page=1&size=2", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1

        resp2 = client.get("/api/v1/checkins?page=2&size=2", headers=auth_headers)
        assert len(resp2.json()["items"]) == 1

    def test_incluye_worker_name(self, client, auth_headers):
        _setup(client, auth_headers)
        resp = client.get("/api/v1/checkins", headers=auth_headers)
        for item in resp.json()["items"]:
            assert "worker_name" in item
            assert item["worker_name"] != ""

    def test_sin_auth_rechazado(self, client):
        resp = client.get("/api/v1/checkins")
        assert resp.status_code in (401, 403)


class TestExportCSV:
    def test_exportacion_csv_basica(self, client, auth_headers):
        _setup(client, auth_headers)
        resp = client.get("/api/v1/export/checkins.csv", headers=auth_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_csv_contiene_cabeceras_correctas(self, client, auth_headers):
        _setup(client, auth_headers)
        resp = client.get("/api/v1/export/checkins.csv", headers=auth_headers)
        # Quitar BOM si existe
        content = resp.text.lstrip("﻿")
        primera_linea = content.splitlines()[0]
        assert "worker_name" in primera_linea
        assert "employee_id" in primera_linea
        assert "event_type" in primera_linea
        assert "recorded_at" in primera_linea
        assert "device_id" in primera_linea

    def test_csv_fidelidad_respecto_a_consulta(self, client, auth_headers):
        """Propiedad 8: CSV contiene exactamente los mismos registros que la consulta."""
        _setup(client, auth_headers)
        consulta = client.get("/api/v1/checkins", headers=auth_headers).json()
        csv_resp = client.get("/api/v1/export/checkins.csv", headers=auth_headers)
        content = csv_resp.text.lstrip("﻿")
        lineas = [l for l in content.splitlines() if l.strip()]
        # 1 cabecera + N registros
        assert len(lineas) - 1 == consulta["total"]

    def test_csv_filtro_event_type(self, client, auth_headers):
        _setup(client, auth_headers)
        resp = client.get("/api/v1/export/checkins.csv?event_type=entrada", headers=auth_headers)
        content = resp.text.lstrip("﻿")
        lineas = [l for l in content.splitlines() if l.strip()]
        # Sólo los de entrada (2)
        assert len(lineas) - 1 == 2

    def test_sin_auth_rechazado(self, client):
        resp = client.get("/api/v1/export/checkins.csv")
        assert resp.status_code in (401, 403)


class TestAuditLog:
    def test_log_auditoria_vacio_inicial(self, client, auth_headers):
        resp = client.get("/api/v1/audit", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_operaciones_generan_entradas(self, client, auth_headers):
        client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        resp = client.get("/api/v1/audit", headers=auth_headers)
        assert len(resp.json()) >= 1

    def test_orden_descendente(self, client, auth_headers):
        client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        w2 = client.post("/api/v1/workers", json=WORKER_2, headers=auth_headers).json()
        client.patch(f"/api/v1/workers/{w2['id']}/deactivate", headers=auth_headers)
        resp = client.get("/api/v1/audit", headers=auth_headers)
        fechas = [e["performed_at"] for e in resp.json()]
        assert fechas == sorted(fechas, reverse=True)

    def test_sin_auth_rechazado(self, client):
        resp = client.get("/api/v1/audit")
        assert resp.status_code in (401, 403)
