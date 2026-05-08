@echo off
setlocal

set TASK_NAME=FichajesNFC

echo Desinstalando tarea "%TASK_NAME%"...

schtasks /end /tn "%TASK_NAME%" >nul 2>&1
schtasks /delete /tn "%TASK_NAME%" /f

if %errorlevel% equ 0 (
    echo [OK] Tarea eliminada. El servicio NFC ya no arrancara automaticamente.
) else (
    echo La tarea no existia o ya fue eliminada.
)

pause
