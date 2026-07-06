@echo off
:: ============================================================
::  INSTAL·LACIÓ DEL GENERADOR CAP  —  executa UNA SOLA VEGADA
:: ============================================================
title Instalacion Generador CAP

:: Situa't a la carpeta del .bat (funciona des de qualsevol lloc)
cd /d "%~dp0"

echo.
echo ============================================================
echo   GENERADOR DE HORARIOS CAP - Autoescola Olivella
echo   Instalacion (solo es necesario hacer esto una vez)
echo ============================================================
echo.

:: ── Comprova que Python estigui instal·lat ────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se ha encontrado Python en este ordenador.
    echo.
    echo   Por favor, descarga e instala Python desde:
    echo   https://www.python.org/downloads/
    echo.
    echo   IMPORTANTE: durante la instalacion de Python, marca la
    echo   casilla "Add Python to PATH" antes de hacer clic en Install.
    echo.
    pause
    exit /b 1
)

echo Python encontrado:
python --version
echo.

:: ── Crea l'entorn virtual si no existeix ─────────────────────
if exist ".venv\Scripts\activate.bat" (
    echo El entorno virtual ya existe. Actualizando dependencias...
) else (
    echo Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo Entorno virtual creado correctamente.
)
echo.

:: ── Instal·la les dependències (sempre amb la ruta del .venv, ─
::    per no dependre del PATH ni d'una activació correcta) ─────
echo Instalando dependencias (puede tardar unos minutos)...
echo.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Hubo un problema instalando las dependencias.
    echo Guarda una captura de pantalla de este error y contacta con soporte.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Instalacion completada correctamente.
echo   Ya puedes cerrar esta ventana.
echo   Para abrir la aplicacion, usa el archivo:
echo   "2_Abrir_CAP.bat"
echo ============================================================
echo.
pause
