#!/bin/bash
# Verificação de fatia: roda tudo que precisa estar verde antes de um commit.
#
# Uso:
#   scripts/verificar.sh          # tudo
#   scripts/verificar.sh --rapido # só testes (pula build do webapp)
#
# Não faz commit, não altera arquivos: só reporta. Sai com código != 0 se
# qualquer verificação falhar, para poder ser usado em hook ou CI.
set -uo pipefail
cd "$(dirname "$0")/.."

RAPIDO=0
[ "${1:-}" = "--rapido" ] && RAPIDO=1

FALHAS=()
ok()    { printf '  \033[32m✓\033[0m %s\n' "$1"; }
falha() { printf '  \033[31m✗\033[0m %s\n' "$1"; FALHAS+=("$1"); }

if [ ! -x .venv/bin/python ]; then
    echo "ERRO: .venv não existe — rode scripts/instalar.sh primeiro."
    exit 1
fi

echo "== Verificação de fatia =="

# 1. Suíte de testes (invariantes, motor, API, UI offscreen).
echo "[1/3] Testes"
SAIDA_TESTES=$(.venv/bin/python -m pytest -q --no-header 2>&1)
if [ $? -eq 0 ]; then
    ok "$(echo "$SAIDA_TESTES" | tail -1)"
else
    echo "$SAIDA_TESTES" | tail -15
    falha "pytest falhou"
fi

# 2. Qualidade das sugestões: o benchmark de cenários rotulados não pode
#    regredir. Regra do projeto (docs/AGRUPAMENTO.md): erro novo de
#    classificação vira cenário AQUI antes de qualquer ajuste de limiar.
echo "[2/3] Benchmark de agrupamento"
SAIDA_BENCH=$(.venv/bin/python scripts/avaliar_agrupamento.py 2>&1)
MELHOR=$(echo "$SAIDA_BENCH" | grep '^MELHOR:' | tail -1)
ACERTOS=$(echo "$MELHOR" | sed -n 's/.*(\([0-9]*\)\/\([0-9]*\)).*/\1/p')
TOTAL=$(echo "$MELHOR" | sed -n 's/.*(\([0-9]*\)\/\([0-9]*\)).*/\2/p')
if [ -n "$ACERTOS" ] && [ "$ACERTOS" = "$TOTAL" ]; then
    ok "$ACERTOS/$TOTAL cenários"
else
    echo "$SAIDA_BENCH" | tail -12
    falha "benchmark abaixo do total (${ACERTOS:-?}/${TOTAL:-?})"
fi

# 3. UI web compila (a interface é o entregável — build quebrado é fatia
#    quebrada, mesmo com o Python verde).
echo "[3/3] Build da UI web"
if [ "$RAPIDO" = "1" ]; then
    ok "pulado (--rapido)"
elif ! command -v npm >/dev/null 2>&1; then
    ok "pulado (npm ausente)"
elif [ ! -d webapp/node_modules ]; then
    falha "webapp/node_modules ausente — rode 'cd webapp && npm install'"
else
    SAIDA_BUILD=$( (cd webapp && npm run build 2>&1) )
    if [ $? -eq 0 ]; then
        ok "$(echo "$SAIDA_BUILD" | grep -E '^✓ built' | tail -1)"
    else
        echo "$SAIDA_BUILD" | tail -15
        falha "build do webapp falhou"
    fi
fi

echo
if [ ${#FALHAS[@]} -eq 0 ]; then
    echo "✅ Fatia verde — pode commitar."
    exit 0
fi
echo "❌ ${#FALHAS[@]} verificação(ões) falharam:"
printf '   - %s\n' "${FALHAS[@]}"
echo "Não commite antes de resolver (docs/METODO_DE_TRABALHO.md)."
exit 1
