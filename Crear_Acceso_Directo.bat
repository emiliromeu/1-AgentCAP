@echo off
:: ============================================================
::  CREAR ACCESO DIRECTO EN EL ESCRITORIO — Generador CAP
:: ============================================================
title Crear acceso directo - Generador CAP

:: Situa't a la carpeta del .bat (funciona des de qualsevol lloc)
cd /d "%~dp0"

echo.
echo ============================================================
echo   Creando el acceso directo en el escritorio...
echo ============================================================
echo.

:: ── Comprova que el programa principal existeixi ─────────────
if not exist "2_Abrir_CAP.bat" (
    echo [ERROR] No se encuentra "2_Abrir_CAP.bat" en esta carpeta.
    echo.
    echo   Este script debe estar en la misma carpeta que el programa
    echo   (junto a 1_Instalar_CAP.bat y 2_Abrir_CAP.bat).
    echo.
    pause
    exit /b 1
)

:: ── Icono: si no existe, se crea igual pero con el icono por defecto ──
set "ICONO=%cd%\assets\olivella.ico"
if not exist "%ICONO%" (
    echo [AVISO] No se encuentra "assets\olivella.ico".
    echo El acceso directo se creara igualmente, con el icono por defecto.
    echo.
    set "ICONO="
)

:: ── Generamos un script de PowerShell temporal para crear el acceso
::    directo (los .bat no pueden crear .lnk por si solos). Se borra
::    despues de usarlo.
set "TEMP_PS1=%TEMP%\crear_acceso_cap_%RANDOM%.ps1"

> "%TEMP_PS1%" (
    echo $ws = New-Object -ComObject WScript.Shell
    echo $desktop = $ws.SpecialFolders^('Desktop'^)
    echo $lnk = $ws.CreateShortcut^("$desktop\Generador CAP - Autoescola Olivella.lnk"^)
    echo $lnk.TargetPath = "%cd%\2_Abrir_CAP.bat"
    echo $lnk.WorkingDirectory = "%cd%"
    if defined ICONO echo $lnk.IconLocation = "%ICONO%"
    echo $lnk.Description = "Generador de Horarios CAP - Autoescola Olivella"
    echo $lnk.Save^(^)
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP_PS1%"
set "RESULTADO=%errorlevel%"

del "%TEMP_PS1%" >nul 2>&1

if not "%RESULTADO%"=="0" (
    echo.
    echo [ERROR] No se ha podido crear el acceso directo.
    echo Guarda una captura de pantalla de este error y contacta con soporte.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Listo! Ya tienes el acceso directo en tu escritorio:
echo.
echo       "Generador CAP - Autoescola Olivella"
echo.
echo   A partir de ahora, usa ese icono para abrir el programa.
echo ============================================================
echo.
pause
