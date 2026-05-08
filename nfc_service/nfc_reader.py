"""
Captura el UID del lector NFC USB HID.

El lector actúa como teclado: escribe el UID como caracteres seguidos de Enter.
- Modo STUB (USE_STUB=true): el operador escribe el UID manualmente, útil para pruebas.
- Modo HARDWARE (USE_STUB=false): el lector escribe automáticamente el UID al detectar
  una tarjeta. El terminal debe tener el foco (ejecutar en ventana dedicada).

Para captura global sin foco de ventana se puede activar el modo 'keyboard' (requiere
ejecutar Python como Administrador en Windows):
    USE_KEYBOARD_GLOBAL=true
"""

import sys
from config import settings


def read_uid() -> str | None:
    """
    Espera un UID del lector NFC.
    Devuelve el UID como string limpio, o None si la entrada está vacía.
    """
    if settings.use_stub:
        try:
            raw = input("[STUB] UID (Enter para saltar): ").strip()
        except EOFError:
            return None
    elif settings.use_keyboard_global:
        return read_uid_keyboard_global()
    else:
        try:
            # El lector USB HID envía el UID + Enter al terminal activo
            raw = input().strip()
        except EOFError:
            return None

    return raw if raw else None


def read_uid_keyboard_global() -> str | None:
    """
    Captura UID globalmente con la librería `keyboard` (requiere admin en Windows).
    Acumula pulsaciones hasta recibir Enter.
    Usar solo si el servicio necesita funcionar sin foco de terminal.
    """
    try:
        import keyboard as kb
    except ImportError:
        print("Instala 'keyboard': pip install keyboard", file=sys.stderr)
        return None

    buffer: list[str] = []

    def on_key(event):
        if event.event_type == "down":
            if event.name == "enter" and buffer:
                kb.unhook_all()
            elif len(event.name) == 1:
                buffer.append(event.name)

    kb.hook(on_key, suppress=True)
    kb.wait("enter")
    return "".join(buffer).strip() or None
