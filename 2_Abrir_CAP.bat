@echo off
:: ============================================================
::  GENERADOR DE HORARIOS CAP  —  doble clic per obrir la app
:: ============================================================
title Generador CAP - Autoescola Olivella

:: Situa't a la carpeta del .bat (funciona des de qualsevol lloc)
cd /d "%~dp0"

:: ── Comprova que la instal·lació s'hagi fet ───────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo [ERROR] El entorno virtual no esta instalado.
    echo.
    echo   Por favor, ejecuta primero el archivo:
    echo   "1_Instalar_CAP.bat"
    echo.
    pause
    exit /b 1
)

:: ── Comprova que el .env existeixi ───────────────────────────
if not exist ".env" (
    echo.
    echo [ERROR] No se encuentra el archivo .env con la clave de API.
    echo.
    echo   Contacta con soporte para obtener el archivo .env
    echo   y coloca el archivo en esta carpeta.
    echo.
    pause
    exit /b 1
)

:: ── Activa l'entorn i arrenca la app ─────────────────────────
call .venv\Scripts\activate.bat

echo.
echo ============================================================
echo   Iniciando Generador de Horarios CAP...
echo   La aplicacion se abrira en el navegador en unos segundos.
echo   Para cerrar la app, cierra esta ventana.
echo ============================================================
echo.

streamlit run app.py

:: Si streamlit acaba (per error o per Ctrl+C), es mostra el missatge
if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion se ha cerrado inesperadamente.
    echo Guarda una captura de pantalla de este error y contacta con soporte.
    echo.
)
pause
