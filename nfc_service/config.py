import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    device_id: str = os.getenv("DEVICE_ID", "device-001")
    device_api_key: str = os.getenv("DEVICE_API_KEY", "device-secret-token")
    # True → lee UID desde teclado manual (sin hardware); False → lector USB HID real
    use_stub: bool = os.getenv("USE_STUB", "true").lower() == "true"
    # True → captura global con hooks de teclado (necesario para funcionar en background sin ventana)
    use_keyboard_global: bool = os.getenv("USE_KEYBOARD_GLOBAL", "false").lower() == "true"
    sync_interval: int = int(os.getenv("SYNC_INTERVAL", "30"))


settings = Settings()
