@echo off
setlocal

set TASK_NAME=FichajesNFC
set NFC_DIR=%~dp0

echo ============================================
echo   Instalador Servicio NFC - Fichajes
echo ============================================
echo.

REM Verificar que existe el .env
if not exist "%NFC_DIR%.env" (
    echo [ERROR] No se encuentra el archivo .env
    echo.
    echo  1. Copia .env.example a .env
    echo  2. Abre .env y configura BACKEND_URL y DEVICE_API_KEY
    echo  3. Vuelve a ejecutar este script como Administrador
    echo.
    pause
    exit /b 1
)

REM Verificar Python
where pythonw >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pythonw.exe no encontrado en PATH.
    echo Instala Python 3 desde python.org y marca "Add to PATH".
    pause
    exit /b 1
)

REM Instalar dependencias
echo Instalando dependencias Python...
cd /d "%NFC_DIR%"
python -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [ERROR] Fallo al instalar dependencias.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas.
echo.

REM Eliminar tarea anterior si existe
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

REM Crear tarea: se ejecuta al iniciar sesion, con permisos elevados (necesario para keyboard hooks)
schtasks /create /tn "%TASK_NAME%" ^
  /tr "\"%NFC_DIR%run_nfc.bat\"" ^
  /sc ONLOGON ^
  /ru "%USERDOMAIN%\%USERNAME%" ^
  /rl HIGHEST ^
  /f

if %errorlevel% neq 0 (
    echo [ERROR] No se pudo crear la tarea.
    echo Ejecuta este script haciendo clic derecho ^> Ejecutar como administrador.
    pause
    exit /b 1
)

echo [OK] Tarea "%TASK_NAME%" instalada.
echo      Se iniciara automaticamente al abrir sesion en Windows.
echo.

REM Iniciar ahora mismo
schtasks /run /tn "%TASK_NAME%"
echo [OK] Servicio NFC iniciado en segundo plano.
echo.
echo Para verificar: Administrador de tareas ^> Detalles ^> buscar pythonw.exe
echo Para desinstalar: ejecuta desinstalar_tarea.bat

pause
