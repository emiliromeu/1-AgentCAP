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
    echo   Este script debe estar en la misma carpeta que el programa,
    echo   junto a 1_Instalar_CAP.bat y 2_Abrir_CAP.bat.
    echo.
    pause
    exit /b 1
)
echo [OK] Encontrado 2_Abrir_CAP.bat

:: Comprobamos el icono. Si falta, avisamos pero seguimos.
:: (if de una sola linea, sin bloque, para evitar cualquier
:: problema de parentesis)
set "HAY_ICONO=1"
if not exist "%~dp0assets\olivella.ico" set "HAY_ICONO=0"
if "%HAY_ICONO%"=="1" echo [OK] Encontrado assets\olivella.ico
if "%HAY_ICONO%"=="0" echo [AVISO] No se encuentra assets\olivella.ico -- se creara sin icono.

:: Detectamos el escritorio REAL del usuario con PowerShell.
:: [Environment]::GetFolderPath('Desktop') respeta OneDrive si
:: el escritorio esta redirigido ahi.
:: IMPORTANTE: usamos redireccion ">" a un archivo temporal en vez
:: de "for /f ... in ('comando')" -- ese comando de PowerShell tiene
:: sus propios parentesis, y meterlo dentro de un "in (...)" de
:: batch puede romper el conteo de parentesis del propio batch.
echo.
echo Detectando la carpeta del escritorio...
set "TMP_DESKTOP=%TEMP%\cap_desktop_%RANDOM%.txt"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::GetFolderPath('Desktop')" > "%TMP_DESKTOP%"
set "DESKTOP="
set /p DESKTOP=<"%TMP_DESKTOP%"
del "%TMP_DESKTOP%" >nul 2>&1

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
echo   -^> apunta a: %~dp02_Abrir_CAP.bat

:: Montamos el comando de PowerShell en una variable, con un "set"
:: normal en una linea suelta (NO dentro de ningun bloque if/for de
:: batch). CreateShortcut(...) y Save() tienen parentesis propios de
:: PowerShell -- puestos asi, en una linea suelta, el batch los trata
:: como texto normal y no intenta interpretarlos como bloque.
set "ICON_PART="
if "%HAY_ICONO%"=="1" set "ICON_PART=$l.IconLocation = '%~dp0assets\olivella.ico'; "

set "PSCMD=$s = New-Object -ComObject WScript.Shell; $l = $s.CreateShortcut('%ENLACE%'); $l.TargetPath = '%~dp02_Abrir_CAP.bat'; $l.WorkingDirectory = '%~dp0'; %ICON_PART%$l.Description = 'Generador de Horarios CAP - Autoescola Olivella'; $l.Save()"

powershell -NoProfile -ExecutionPolicy Bypass -Command "%PSCMD%"

:: Verificamos el resultado comprobando si el archivo existe de
:: verdad, en vez de confiar solo en el codigo de salida de
:: PowerShell (puede devolver 0 aunque algo fallara).
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
