"""
nfc_reader.py - captura UIDs del lector NFC mediante WH_KEYBOARD_LL.

Estrategia (tras dos rondas de diagnostico):
  Ni RIDEV_NOLEGACY suprime las legacy keys en este Windows, ni el LL hook
  convive con Raw Input. Vamos con LL hook puro + deteccion por timing:

    1) Instalamos un Low-Level Keyboard Hook global.
    2) Para teclas no-objetivo (letras, espacios, etc) → pasan al sistema
       sin tocar (latencia 0).
    3) Para teclas objetivo (digitos 0-9 y Enter) → suprimimos y metemos
       en un buffer con timestamp.
    4) Un hilo procesador analiza el buffer cuando lleva SETTLE_MS sin
       nuevas teclas, y decide:
         - 10 digitos + Enter con gaps todos < BURST_GAP_MS → lector → UID
         - cualquier otro caso → usuario → re-inyectamos las teclas
           via SendInput con INJECTION_MAGIC en dwExtraInfo. El propio LL
           hook ve esta marca y deja pasar las re-inyecciones (este flag
           SI se preserva en KBDLLHOOKSTRUCT, al contrario que en Raw
           Input).
    5) Si el usuario tiene un modificador pulsado (Shift/Ctrl/Alt/Win),
       las teclas objetivo NO se suprimen → asi atajos como Alt+1 o
       Shift+8 funcionan sin perder estado.

CONSECUENCIA: los digitos y Enter cuando el usuario teclea numeros en
otras apps tendran ~30ms de latencia. Para texto normal (letras) la
latencia es 0.

CRITICO: si el proceso muere sin cleanup, Windows desinstala el hook al
destruir el proceso. Un reinicio siempre devuelve el teclado al estado
normal.

Modos (settings en config.py):
  - USE_STUB=true            → entrada manual por input()
  - USE_KEYBOARD_GLOBAL=true → libreria 'keyboard' (compatibilidad)
  - default (HARDWARE)       → LL hook + timing

Test aislado:
    python nfc_reader.py
"""

import atexit
import collections
import ctypes
import queue
import signal
import sys
import threading
import time
from ctypes import wintypes

from config import settings


# ===================== Constantes Windows =====================

WH_KEYBOARD_LL = 13

WM_KEYDOWN     = 0x0100
WM_KEYUP       = 0x0101
WM_SYSKEYDOWN  = 0x0104
WM_SYSKEYUP    = 0x0105

VK_RETURN              = 0x0D
VK_SHIFT               = 0x10
VK_CONTROL             = 0x11
VK_MENU                = 0x12   # Alt
VK_LWIN                = 0x5B
VK_RWIN                = 0x5C
VK_0, VK_9             = 0x30, 0x39
VK_NUMPAD0, VK_NUMPAD9 = 0x60, 0x69

# KBDLLHOOKSTRUCT.flags
LLKHF_EXTENDED = 0x01
LLKHF_INJECTED = 0x10
LLKHF_ALTDOWN  = 0x20
LLKHF_UP       = 0x80

# SendInput
INPUT_KEYBOARD         = 1
KEYEVENTF_EXTENDEDKEY  = 0x0001
KEYEVENTF_KEYUP        = 0x0002
KEYEVENTF_SCANCODE     = 0x0008

# Valor magico para marcar nuestras re-inyecciones
INJECTION_MAGIC = 0xC4F32A1B

# Heuristica de deteccion
BURST_GAP_MS = 15    # max gap entre teclas dentro de la rafaga del lector
SETTLE_MS    = 30    # tiempo sin nuevas teclas para procesar el buffer
UID_LENGTH   = 10


# ===================== Estructuras Windows =====================

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode",      wintypes.DWORD),
        ("scanCode",    wintypes.DWORD),
        ("flags",       wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd",    wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam",  wintypes.WPARAM),
        ("lParam",  wintypes.LPARAM),
        ("time",    wintypes.DWORD),
        ("pt",      wintypes.POINT),
    ]


# --- SendInput ---

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         wintypes.WORD),
        ("wScan",       wintypes.WORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          wintypes.LONG),
        ("dy",          wintypes.LONG),
        ("mouseData",   wintypes.DWORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg",    wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u",    _INPUT_UNION),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM,
)


# ===================== Win32 APIs =====================

user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.SetWindowsHookExW.restype  = ctypes.c_void_p
user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD,
]
user32.CallNextHookEx.restype  = ctypes.c_ssize_t
user32.CallNextHookEx.argtypes = [
    ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM,
]
user32.UnhookWindowsHookEx.restype  = wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]

user32.GetMessageW.restype  = wintypes.BOOL
user32.GetMessageW.argtypes = [
    ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT,
]
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]

user32.SendInput.restype  = wintypes.UINT
user32.SendInput.argtypes = [
    wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int,
]

user32.GetAsyncKeyState.restype  = wintypes.SHORT
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]

kernel32.GetModuleHandleW.restype  = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]


# ===================== Estado =====================

_uid_queue: queue.Queue = queue.Queue()
_key_buffer: list       = []   # (vk, scan, flags, ts_ns)
_buf_lock               = threading.Lock()
_buf_cv                 = threading.Condition(_buf_lock)

_hook_handle            = None
_hook_proc_ref          = None
_thread_started         = False
_start_lock             = threading.Lock()


# ===================== Helpers =====================

def _vk_to_digit(vk):
    if VK_0 <= vk <= VK_9:
        return chr(ord("0") + (vk - VK_0))
    if VK_NUMPAD0 <= vk <= VK_NUMPAD9:
        return chr(ord("0") + (vk - VK_NUMPAD0))
    return None


def _is_target_vk(vk):
    return _vk_to_digit(vk) is not None or vk == VK_RETURN


def _is_modifier_held():
    """True si Shift/Ctrl/Alt/Win esta pulsado ahora mismo."""
    for vk in (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN):
        if user32.GetAsyncKeyState(vk) & 0x8000:
            return True
    return False


def _reinject_key(vk, scan, flags):
    """Re-inyecta una tecla (keydown + keyup) marcandola con INJECTION_MAGIC
    para que el LL hook la deje pasar."""
    send_flags = KEYEVENTF_SCANCODE
    if flags & LLKHF_EXTENDED:
        send_flags |= KEYEVENTF_EXTENDEDKEY

    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = 0
    inp.ki.wScan = scan
    inp.ki.dwFlags = send_flags
    inp.ki.time = 0
    inp.ki.dwExtraInfo = INJECTION_MAGIC
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    inp.ki.dwFlags = send_flags | KEYEVENTF_KEYUP
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


# ===================== LL Hook =====================

def _low_level_keyboard_proc(nCode, wParam, lParam):
    global _hook_handle

    if nCode < 0:
        return user32.CallNextHookEx(_hook_handle, nCode, wParam, lParam)

    kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT))[0]

    # 1) Nuestras propias re-inyecciones: dejar pasar
    if kbd.dwExtraInfo == INJECTION_MAGIC:
        return user32.CallNextHookEx(_hook_handle, nCode, wParam, lParam)

    is_keydown = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
    is_keyup   = wParam in (WM_KEYUP, WM_SYSKEYUP)
    vk         = kbd.vkCode

    if not _is_target_vk(vk):
        return user32.CallNextHookEx(_hook_handle, nCode, wParam, lParam)

    # 2) Si hay modificador pulsado (Shift/Ctrl/Alt/Win) → es usuario
    #    con atajo, dejar pasar para no romper estado
    if _is_modifier_held():
        return user32.CallNextHookEx(_hook_handle, nCode, wParam, lParam)

    # 3) Tecla objetivo sin modificador: SIEMPRE suprimimos en LL hook
    #    (tanto keydown como keyup) para que no llegue a ninguna ventana.
    #    Solo encolamos los KEYDOWN para analisis.
    if is_keydown:
        with _buf_lock:
            _key_buffer.append((vk, kbd.scanCode, kbd.flags, time.monotonic_ns()))
            _buf_cv.notify()

    return 1  # SUPPRESS


def _hook_thread():
    """Hilo que mantiene la message loop necesaria para que el LL hook funcione."""
    global _hook_handle, _hook_proc_ref

    _hook_proc_ref = HOOKPROC(_low_level_keyboard_proc)
    _hook_handle = user32.SetWindowsHookExW(
        WH_KEYBOARD_LL, _hook_proc_ref,
        kernel32.GetModuleHandleW(None), 0,
    )
    if not _hook_handle:
        err = ctypes.get_last_error()
        raise OSError(f"SetWindowsHookExW fallo: {err}")

    msg = MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


# ===================== Procesador =====================

def _decide(keys):
    """Decide si una rafaga es del lector o del usuario."""
    if not keys:
        return

    # ¿Patron del lector? 10 digitos + Enter con gaps todos pequenos
    if len(keys) == UID_LENGTH + 1 and keys[-1][0] == VK_RETURN:
        digits = keys[:-1]
        all_digits = all(_vk_to_digit(k[0]) is not None for k in digits)
        if all_digits:
            max_gap_ns = 0
            for i in range(1, len(keys)):
                gap = keys[i][3] - keys[i-1][3]
                if gap > max_gap_ns:
                    max_gap_ns = gap
            if max_gap_ns < BURST_GAP_MS * 1_000_000:
                # Lector confirmado
                uid = "".join(_vk_to_digit(k[0]) for k in digits)
                if uid.isdigit():
                    _uid_queue.put(uid)
                return  # NO re-inyectar

    # En cualquier otro caso → usuario tecleando, re-inyectar
    for vk, scan, flags, _ts in keys:
        _reinject_key(vk, scan, flags)


def _processor_thread():
    """Espera a que el buffer de teclas "se asiente" (sin nuevas teclas
    durante SETTLE_MS) y entonces decide y procesa."""
    while True:
        with _buf_lock:
            while not _key_buffer:
                _buf_cv.wait(timeout=1.0)

            # Esperar hasta que la rafaga este asentada
            while _key_buffer:
                now = time.monotonic_ns()
                last_ts = _key_buffer[-1][3]
                age_ms = (now - last_ts) / 1_000_000
                if age_ms >= SETTLE_MS:
                    break
                remaining_s = max(0.001, (SETTLE_MS - age_ms) / 1000.0)
                _buf_cv.wait(timeout=remaining_s)

            keys = list(_key_buffer)
            _key_buffer.clear()

        # Decidir fuera del lock para no bloquear nuevas teclas
        try:
            _decide(keys)
        except Exception as e:
            print(f"[nfc_reader] error en _decide: {e}", file=sys.stderr)


# ===================== Cleanup =====================

def _cleanup():
    global _hook_handle
    h = _hook_handle
    if h:
        try:
            user32.UnhookWindowsHookEx(h)
        except Exception:
            pass
        _hook_handle = None


atexit.register(_cleanup)


def _signal_handler(signum, frame):
    _cleanup()
    sys.exit(0)


try:
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
except (ValueError, AttributeError):
    pass


# ===================== API publica =====================

def _ensure_started():
    global _thread_started
    with _start_lock:
        if _thread_started:
            return
        threading.Thread(target=_processor_thread, daemon=True,
                         name="nfc-processor").start()
        threading.Thread(target=_hook_thread, daemon=True,
                         name="nfc-ll-hook").start()
        # Pequeno margen para que el hook se registre
        for _ in range(50):
            if _hook_handle:
                break
            time.sleep(0.02)
        _thread_started = True


def read_uid():
    if settings.use_stub:
        try:
            raw = input("[STUB] UID (Enter para saltar): ").strip()
            return raw if raw else None
        except EOFError:
            return None

    if settings.use_keyboard_global:
        return _read_uid_keyboard_global_legacy()

    _ensure_started()
    while True:
        try:
            return _uid_queue.get(timeout=0.5)
        except queue.Empty:
            continue


def _read_uid_keyboard_global_legacy():
    try:
        import keyboard as kb
    except ImportError:
        print("Instala 'keyboard': pip install keyboard", file=sys.stderr)
        return None
    buf: list[str] = []
    def on_key(event):
        if event.event_type == "down":
            if event.name == "enter" and buf:
                kb.unhook_all()
            elif len(event.name) == 1:
                buf.append(event.name)
    kb.hook(on_key, suppress=True)
    kb.wait("enter")
    return "".join(buf).strip() or None


# ===================== Test aislado =====================

if __name__ == "__main__":
    print("=" * 60)
    print("  nfc_reader.py - test aislado (LL hook + timing)")
    print("=" * 60)
    print(f"  BURST_GAP_MS = {BURST_GAP_MS}   SETTLE_MS = {SETTLE_MS}")
    print()
    print("  Validaciones a hacer:")
    print("    1) Escribir letras en Notepad → 0 latencia, 1 letra por tecla.")
    print("    2) Escribir digitos en Notepad → ~30ms de retraso, 1 digito.")
    print("    3) Atajos Shift+1, Alt+Tab, Ctrl+A → funcionan normal.")
    print("    4) Pasa una tarjeta → UID aparece AQUI, NO en Notepad.")
    print()
    print("  Si algo se cuelga: matar python.exe con Task Manager.")
    print("  Ctrl+C para salir.")
    print("-" * 60)
    print()

    _ensure_started()
    print("[OK] LL hook instalado. Esperando tarjetas...", flush=True)
    print()

    try:
        while True:
            try:
                uid = _uid_queue.get(timeout=0.5)
                print(f"  >> UID capturado: {uid}", flush=True)
            except queue.Empty:
                continue
    except KeyboardInterrupt:
        print()
        print("Servicio detenido. Desinstalando hook...", flush=True)
        _cleanup()
        print("OK.", flush=True)
