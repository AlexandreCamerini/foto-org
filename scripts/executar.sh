#!/bin/bash
# Abre o Foto Organizer (ou roda a CLI).
#
# Uso:
#   scripts/executar.sh web                    # UI web local (recomendada)
#   scripts/executar.sh                        # UI nativa (PySide6)
#   scripts/executar.sh scan ~/Pictures/2026   # varredura headless
#   scripts/executar.sh bench -n 1000          # benchmark de indexação
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
    echo "ERRO: .venv não existe — rode scripts/instalar.sh primeiro."
    exit 1
fi

# UI web: garante o build do frontend e abre o navegador junto.
if [ "${1:-}" = "web" ]; then
    if [ ! -f webapp/dist/index.html ]; then
        if command -v npm >/dev/null 2>&1; then
            echo "Construindo a UI web (primeira vez)…"
            (cd webapp && npm install --silent && npm run build --silent)
        else
            echo "ERRO: UI web não construída e npm ausente (instale Node 18+)."
            exit 1
        fi
    fi
    (sleep 1.5 && open "http://127.0.0.1:8765") &
fi

exec .venv/bin/python -m fotoorganizer "$@"
