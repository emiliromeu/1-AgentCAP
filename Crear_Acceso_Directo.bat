@echo off
:: ============================================================
::  CREAR ACCESO DIRECTO EN EL ESCRITORIO - Generador CAP
:: ============================================================
title Crear acceso directo - Generador CAP

echo.
echo ============================================================
echo   Creando el acceso directo en el escritorio...
echo ============================================================
echo.

:: Comprobamos que el programa principal existe (ruta relativa
:: al propio script, con %~dp0, para que funcione en cualquier
:: carpeta donde este el proyecto)
if not exist "%~dp02_Abrir_CAP.bat" (
    echo [ERROR] No se encuentra "2_Abrir_CAP.bat" en esta carpeta:
    echo   %~dp0
    echo.
    echo   Este script debe estar en la misma carpeta que el programa
    echo   (junto a 1_Instalar_CAP.bat y 2_Abrir_CAP.bat).
    echo.
    pause
    exit /b 1
)
echo [OK] Encontrado 2_Abrir_CAP.bat

:: Comprobamos el icono. Si falta, avisamos pero seguimos
set "HAY_ICONO=1"
if not exist "%~dp0assets\olivella.ico" (
    echo [AVISO] No se encuentra "assets\olivella.ico".
    echo El acceso directo se creara igualmente, con el icono por defecto.
    set "HAY_ICONO=0"
) else (
    echo [OK] Encontrado assets\olivella.ico
)

:: Detectamos el escritorio REAL del usuario con PowerShell.
:: [Environment]::GetFolderPath('Desktop') respeta OneDrive si
:: el escritorio esta redirigido ahi.
echo.
echo Detectando la carpeta del escritorio...
set "DESKTOP="
for /f "usebackq delims=" %%D in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP=%%D"

if not defined DESKTOP (
    echo [ERROR] No se ha podido detectar la carpeta del escritorio.
    echo Comprueba que PowerShell esta disponible en este PC.
    echo.
    pause
    exit /b 1
)
echo Escritorio detectado en: %DESKTOP%

set "ENLACE=%DESKTOP%\Generador CAP - Autoescola Olivella.lnk"

echo.
echo Creando el acceso directo:
echo   %ENLACE%
echo   -> apunta a: %~dp02_Abrir_CAP.bat
echo.

:: Creamos el acceso directo con PowerShell, en una sola linea
:: (sin generar ningun archivo intermedio, para evitar errores
:: de escritura/lectura de ficheros temporales)
if "%HAY_ICONO%"=="1" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$s = New-Object -ComObject WScript.Shell; $l = $s.CreateShortcut('%ENLACE%'); $l.TargetPath = '%~dp02_Abrir_CAP.bat'; $l.WorkingDirectory = '%~dp0'; $l.IconLocation = '%~dp0assets\olivella.ico'; $l.Description = 'Generador de Horarios CAP - Autoescola Olivella'; $l.Save()"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$s = New-Object -ComObject WScript.Shell; $l = $s.CreateShortcut('%ENLACE%'); $l.TargetPath = '%~dp02_Abrir_CAP.bat'; $l.WorkingDirectory = '%~dp0'; $l.Description = 'Generador de Horarios CAP - Autoescola Olivella'; $l.Save()"
)

:: Verificamos el resultado comprobando si el archivo existe
:: de verdad, en vez de confiar solo en el codigo de salida
:: de PowerShell (puede devolver 0 aunque algo fallara)
if not exist "%ENLACE%" (
    echo.
    echo ============================================================
    echo   [ERROR] No se ha creado el acceso directo.
    echo ============================================================
    echo.
    echo   Guarda una captura de pantalla de este mensaje y de la
    echo   ventana de PowerShell si ha aparecido alguna, y contacta
    echo   con soporte.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Listo! Se ha creado el acceso directo en tu escritorio:
echo.
echo       "Generador CAP - Autoescola Olivella"
echo.
echo   A partir de ahora, usa ese icono para abrir el programa.
echo ============================================================
echo.
pause
