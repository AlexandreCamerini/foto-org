#!/bin/bash
# Instala o Foto Organizer do zero (macOS).
#
# Uso:
#   scripts/instalar.sh          # instalação padrão (100% local)
#   scripts/instalar.sh --llm    # inclui o advisor LLM opcional (Claude)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Foto Organizer — instalação =="

# 1. Encontrar um Python 3.12+ (macOS não tem 'python', só 'python3').
PYTHON=""
for candidato in python3.12 python3.13 python3; do
    if command -v "$candidato" >/dev/null 2>&1; then
        versao=$("$candidato" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
        maior=${versao%%.*}; menor=${versao##*.}
        if [ "$maior" -eq 3 ] && [ "$menor" -ge 12 ]; then
            PYTHON=$candidato
            break
        fi
    fi
done
if [ -z "$PYTHON" ]; then
    echo "ERRO: nenhum Python 3.12+ encontrado."
    echo "Instale com:  brew install python@3.12  (ou baixe em python.org)"
    exit 1
fi
echo "Python: $PYTHON ($($PYTHON --version))"

# 2. Ambiente virtual.
if [ ! -d .venv ]; then
    echo "Criando ambiente virtual em .venv/…"
    "$PYTHON" -m venv .venv
else
    echo "Reutilizando .venv/ existente."
fi

# 3. Dependências.
EXTRAS="dev"
if [ "${1:-}" = "--llm" ]; then
    EXTRAS="dev,llm"
    echo "Incluindo o extra [llm] (advisor via Claude — opt-in no config)."
fi
echo "Instalando dependências (pode demorar na primeira vez)…"
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e ".[$EXTRAS]"

# 4. Verificação: suíte de testes completa.
echo "Verificando a instalação (testes)…"
.venv/bin/python -m pytest -q --no-header 2>&1 | tail -1

echo ""
echo "✅ Instalado. Para abrir o app:"
echo "   scripts/executar.sh"
echo ""
echo "Dados do app: ~/Library/Application Support/FotoOrganizer/"
echo "As fotos originais nunca são modificadas."
