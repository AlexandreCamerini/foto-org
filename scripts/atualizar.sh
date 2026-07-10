#!/bin/bash
# Atualiza o Foto Organizer para a versão mais recente do repositório.
# Seguro: o catálogo migra sozinho no próximo boot; fotos nunca são tocadas.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Foto Organizer — atualização =="

if [ ! -d .venv ]; then
    echo "ERRO: .venv não existe — rode scripts/instalar.sh primeiro."
    exit 1
fi

ANTES=$(git rev-parse HEAD)

# 1. Código novo (só avanço linear; nunca sobrescreve trabalho local).
if git remote get-url origin >/dev/null 2>&1; then
    echo "Buscando código novo…"
    git pull --ff-only
else
    echo "(sem remoto configurado — usando o código local como está)"
fi

DEPOIS=$(git rev-parse HEAD)
if [ "$ANTES" != "$DEPOIS" ]; then
    echo ""
    echo "Novidades:"
    git log --oneline "$ANTES..$DEPOIS" | sed 's/^/  /'
    echo ""
fi

# 2. Dependências em sincronia com o pyproject.
echo "Sincronizando dependências…"
EXTRAS="dev"
.venv/bin/python -c "import anthropic" 2>/dev/null && EXTRAS="dev,llm"
.venv/bin/pip install --quiet -e ".[$EXTRAS]"

# 3. Verificação.
echo "Rodando testes…"
.venv/bin/python -m pytest -q --no-header 2>&1 | tail -1

echo ""
echo "✅ Atualizado. O catálogo migra automaticamente ao abrir o app:"
echo "   scripts/executar.sh"
