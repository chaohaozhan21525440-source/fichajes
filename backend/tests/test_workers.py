import pytest
from app.models.checkin_record import CheckinRecord
from datetime import datetime, timezone
import uuid


WORKER_1 = {"full_name": "Ana García", "employee_id": "EMP001", "nfc_uid": "04:A3:2B:1C:9F"}
WORKER_2 = {"full_name": "Luis Pérez", "employee_id": "EMP002", "nfc_uid": "04:B4:3C:2D:0A"}


class TestListWorkers:
    def test_lista_vacia_inicial(self, client, auth_headers):
        resp = client.get("/api/v1/workers", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_lista_trabajadores_creados(self, client, auth_headers):
        client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        client.post("/api/v1/workers", json=WORKER_2, headers=auth_headers)
        resp = client.get("/api/v1/workers", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_sin_auth_rechazado(self, client):
        resp = client.get("/api/v1/workers")
        assert resp.status_code in (401, 403)


class TestCreateWorker:
    def test_crear_trabajador_nuevo(self, client, auth_headers):
        resp = client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["full_name"] == "Ana García"
        assert data["employee_id"] == "EMP001"
        assert data["is_active"] is True

    def test_employee_id_duplicado_rechazado(self, client, auth_headers):
        client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        duplicado = {**WORKER_1, "nfc_uid": "04:FF:FF:FF:FF"}
        resp = client.post("/api/v1/workers", json=duplicado, headers=auth_headers)
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "employee_id_duplicado"

    def test_token_nfc_duplicado_rechazado(self, client, auth_headers):
        """Propiedad 3: no puede haber dos trabajadores activos con el mismo token."""
        client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        duplicado = {"full_name": "Otro", "employee_id": "EMP999", "nfc_uid": WORKER_1["nfc_uid"]}
        resp = client.post("/api/v1/workers", json=duplicado, headers=auth_headers)
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "token_ya_asignado"

    def test_crear_genera_entrada_audit_log(self, client, auth_headers, db):
        from app.models.audit_log import AuditLog
        client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        entry = db.query(AuditLog).filter(AuditLog.operation == "worker.create").first()
        assert entry is not None
        assert entry.entity_type == "worker"


class TestUpdateWorker:
    def test_actualizar_nombre(self, client, auth_headers):
        create = client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        worker_id = create.json()["id"]
        resp = client.put(f"/api/v1/workers/{worker_id}", json={"full_name": "Ana López"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Ana López"

    def test_actualizar_worker_inexistente_404(self, client, auth_headers):
        resp = client.put(f"/api/v1/workers/{uuid.uuid4()}", json={"full_name": "X"}, headers=auth_headers)
        assert resp.status_code == 404


class TestDeactivateWorker:
    def test_desactivar_trabajador(self, client, auth_headers):
        create = client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        worker_id = create.json()["id"]
        resp = client.patch(f"/api/v1/workers/{worker_id}/deactivate", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_desactivar_dos_veces_409(self, client, auth_headers):
        create = client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        worker_id = create.json()["id"]
        client.patch(f"/api/v1/workers/{worker_id}/deactivate", headers=auth_headers)
        resp = client.patch(f"/api/v1/workers/{worker_id}/deactivate", headers=auth_headers)
        assert resp.status_code == 409

    def test_desactivar_conserva_historico_fichajes(self, client, auth_headers, db):
        """Propiedad 7: desactivar un trabajador no elimina sus registros de fichaje."""
        create = client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        worker_id = create.json()["id"]

        # Insertar fichajes directamente en DB
        from app.models.checkin_record import CheckinRecord
        import uuid as uuid_mod
        worker_uuid = uuid_mod.UUID(worker_id)
        for _ in range(3):
            db.add(CheckinRecord(
                worker_id=worker_uuid,
                nfc_uid=WORKER_1["nfc_uid"],
                event_type="entrada",
                recorded_at=datetime.now(timezone.utc),
                device_id="device-001",
                idempotency_key=uuid_mod.uuid4(),
            ))
        db.commit()

        client.patch(f"/api/v1/workers/{worker_id}/deactivate", headers=auth_headers)

        count = db.query(CheckinRecord).filter(CheckinRecord.worker_id == worker_uuid).count()
        assert count == 3

    def test_desactivar_genera_audit_log(self, client, auth_headers, db):
        """Propiedad 11: cada operación genera exactamente una entrada en audit_log."""
        from app.models.audit_log import AuditLog
        create = client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        worker_id = create.json()["id"]
        client.patch(f"/api/v1/workers/{worker_id}/deactivate", headers=auth_headers)
        entries = db.query(AuditLog).filter(AuditLog.operation == "worker.deactivate").all()
        assert len(entries) == 1


class TestAssignNfcToken:
    def test_asignar_token_nuevo(self, client, auth_headers):
        create = client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        worker_id = create.json()["id"]
        resp = client.post(f"/api/v1/workers/{worker_id}/nfc-tokens", json={"nfc_uid": "04:NEW:11:22:33"}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["nfc_uid"] == "04:NEW:11:22:33"

    def test_token_duplicado_409(self, client, auth_headers):
        """Propiedad 3: token ya asignado a trabajador activo → 409."""
        w1 = client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers).json()
        w2 = client.post("/api/v1/workers", json=WORKER_2, headers=auth_headers).json()
        resp = client.post(f"/api/v1/workers/{w2['id']}/nfc-tokens", json={"nfc_uid": WORKER_1["nfc_uid"]}, headers=auth_headers)
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "token_ya_asignado"

    def test_asignar_token_a_worker_inactivo_409(self, client, auth_headers):
        create = client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        worker_id = create.json()["id"]
        client.patch(f"/api/v1/workers/{worker_id}/deactivate", headers=auth_headers)
        resp = client.post(f"/api/v1/workers/{worker_id}/nfc-tokens", json={"nfc_uid": "04:XX:YY:ZZ"}, headers=auth_headers)
        assert resp.status_code == 409

    def test_asignar_genera_audit_log(self, client, auth_headers, db):
        from app.models.audit_log import AuditLog
        create = client.post("/api/v1/workers", json=WORKER_1, headers=auth_headers)
        worker_id = create.json()["id"]
        client.post(f"/api/v1/workers/{worker_id}/nfc-tokens", json={"nfc_uid": "04:NEW:AA:BB"}, headers=auth_headers)
        entry = db.query(AuditLog).filter(AuditLog.operation == "worker.assign_token").first()
        assert entry is not None
