import time
import threading
import requests
from config import settings
import local_store

_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RESET = "\033[0m"


def sync_once() -> tuple[int, int]:
    """
    Envía todos los fichajes pendientes al backend.
    Devuelve (procesados, rechazados).
    """
    pending = local_store.get_pending()
    if not pending:
        return 0, 0

    records = [
        {
            "nfc_uid": r["nfc_uid"],
            "device_id": r["device_id"],
            "detected_at": r["detected_at"],
            "idempotency_key": r["idempotency_key"],
        }
        for r in pending
    ]

    try:
        resp = requests.post(
            f"{settings.backend_url}/api/v1/checkins/sync",
            json={"records": records},
            headers={"Authorization": f"Bearer {settings.device_api_key}"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            for r in pending:
                local_store.mark_synced(r["idempotency_key"])
            print(
                f"{_GREEN}[SYNC] {data['procesados']} procesados, "
                f"{data['rechazados']} rechazados{_RESET}"
            )
            return data["procesados"], data["rechazados"]
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        pass  # Backend no disponible, reintento en el siguiente ciclo

    return 0, 0


def start_sync_loop() -> None:
    """Lanza el bucle de sincronización en un hilo daemon."""

    def _loop():
        while True:
            time.sleep(settings.sync_interval)
            try:
                count = local_store.pending_count()
                if count > 0:
                    print(f"{_YELLOW}[SYNC] {count} fichajes pendientes, sincronizando...{_RESET}")
                    sync_once()
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True, name="sync-loop")
    t.start()
