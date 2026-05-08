"""
Servicio NFC — punto de entrada principal.

Uso:
    # Modo stub (sin hardware, para pruebas):
    python main.py

    # Modo hardware (lector USB HID conectado):
    set USE_STUB=false && python main.py

    # Con backend remoto:
    set BACKEND_URL=http://192.168.1.10:8000 && set USE_STUB=false && python main.py
"""

import sys
import uuid
from datetime import datetime, timezone

import requests

from config import settings
import local_store
import nfc_reader
import sync_service

_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_RESET  = "\033[0m"


def process_uid(uid: str) -> None:
    detected_at = datetime.now(timezone.utc)
    idempotency_key = str(uuid.uuid4())

    payload = {
        "nfc_uid": uid,
        "device_id": settings.device_id,
        "detected_at": detected_at.isoformat(),
        "idempotency_key": idempotency_key,
    }

    try:
        resp = requests.post(
            f"{settings.backend_url}/api/v1/checkins",
            json=payload,
            headers={"Authorization": f"Bearer {settings.device_api_key}"},
            timeout=2.0,
        )

        if resp.status_code == 200:
            data = resp.json()
            evento = data["event_type"].upper()
            nombre = data["worker_name"]
            print(f"\n{_GREEN}✓  {evento}: {nombre}{_RESET}\n")

        elif resp.status_code == 403:
            error = resp.json().get("detail", {}).get("error", "")
            if error == "token_desconocido":
                print(f"\n{_RED}✗  Token no registrado: {uid}{_RESET}\n")
            else:
                print(f"\n{_RED}✗  Fichaje rechazado ({error}){_RESET}\n")

        else:
            print(f"\n{_YELLOW}⚠  Respuesta inesperada: {resp.status_code}{_RESET}\n")

    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        local_store.add_pending(uid, settings.device_id, detected_at, idempotency_key)
        print(f"\n{_YELLOW}⚠  Sin conexión — fichaje guardado localmente{_RESET}\n")


def main() -> None:
    local_store.init_db()
    sync_service.start_sync_loop()

    modo = "STUB (teclado manual)" if settings.use_stub else "HARDWARE (lector USB HID)"
    print(f"\n{_CYAN}{'='*45}")
    print(f"  Servicio NFC  [{modo}]")
    print(f"{'='*45}{_RESET}")
    print(f"  Backend  : {settings.backend_url}")
    print(f"  Dispositivo: {settings.device_id}")
    pendientes = local_store.pending_count()
    if pendientes:
        print(f"  {_YELLOW}Fichajes pendientes de sync: {pendientes}{_RESET}")
    print(f"\n  Acercar tarjeta NFC al lector... (Ctrl+C para salir)\n")

    while True:
        try:
            uid = nfc_reader.read_uid()
            if uid:
                process_uid(uid)
        except KeyboardInterrupt:
            print(f"\n{_CYAN}Servicio NFC detenido.{_RESET}\n")
            sys.exit(0)
        except Exception as e:
            print(f"{_RED}Error inesperado: {e}{_RESET}")


if __name__ == "__main__":
    main()
