#!/bin/bash
# ============================================================
#  GENERADOR DE HORARIOS CAP - doble clic para abrir la app (macOS)
# ============================================================

# Nos situamos en la carpeta del proyecto (la misma carpeta donde
# esta este .command), sea cual sea la ruta desde la que Finder
# lo haya lanzado.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || {
    echo "[ERROR] No se ha podido entrar en la carpeta del proyecto: $DIR"
    read -p "Pulsa Enter para cerrar..."
    exit 1
}

echo "============================================================"
echo "  Generador de Horarios CAP - Autoescola Olivella"
echo "============================================================"
echo

# Comprobamos que el entorno virtual esta instalado
if [ ! -x ".venv/bin/streamlit" ]; then
    echo "[ERROR] No se encuentra .venv/bin/streamlit en esta carpeta:"
    echo "  $DIR"
    echo
    echo "  Instala el entorno virtual antes de usar este acceso directo:"
    echo "    cd \"$DIR\""
    echo "    python3 -m venv .venv"
    echo "    .venv/bin/pip install -r requirements.txt"
    echo
    read -p "Pulsa Enter para cerrar..."
    exit 1
fi

# Comprobamos que existe el archivo con la clave de la API
if [ ! -f ".env" ]; then
    echo "[AVISO] No se encuentra el archivo .env con la clave de API."
    echo "  La app no podra conectar con Anthropic hasta que lo añadas"
    echo "  en: $DIR/.env"
    echo
fi

echo "Iniciando la aplicacion..."
echo "Se abrira en el navegador en unos segundos."
echo "Para cerrar la app, cierra esta ventana (o pulsa Ctrl+C)."
echo
echo "============================================================"
echo

.venv/bin/streamlit run app.py

echo
echo "La aplicacion se ha cerrado."
read -p "Pulsa Enter para cerrar esta ventana..."
