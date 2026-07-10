#!/bin/bash
# Abre o Foto Organizer (ou roda a CLI).
#
# Uso:
#   scripts/executar.sh                        # interface gráfica
#   scripts/executar.sh scan ~/Pictures/2026   # varredura headless
#   scripts/executar.sh bench -n 1000          # benchmark de indexação
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
    echo "ERRO: .venv não existe — rode scripts/instalar.sh primeiro."
    exit 1
fi

exec .venv/bin/python -m fotoorganizer "$@"
