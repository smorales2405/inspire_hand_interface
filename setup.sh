#!/usr/bin/env bash
set -e

PYTHON=${PYTHON:-python3}

if [ ! -d ".venv" ]; then
    echo "[setup] Creando entorno virtual en .venv ..."
    $PYTHON -m venv .venv
fi

echo "[setup] Instalando dependencias ..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt

echo ""
echo "[setup] Listo. Para ejecutar la interfaz:"
echo "  source .venv/bin/activate"
echo "  python3 main.py"
