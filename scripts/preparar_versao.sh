#!/bin/bash
# Prepara o ambiente para a versão nova, do zero ou a partir de uma anterior.
#
# Diferente de instalar.sh (que instala) e de atualizar.sh (que sincroniza
# dependências), este script cuida do que muda ENTRE versões e do que pode
# doer: migrações de esquema num catálogo com anos de trabalho dentro.
#
# Uso:
#   scripts/preparar_versao.sh                    # catálogo padrão do app
#   scripts/preparar_versao.sh --catalogo ~/teste # outro catálogo (ensaio)
#   scripts/preparar_versao.sh --sem-verificacao  # pula a suíte (mais rápido)
#
# Regras que este script não quebra:
#   - o catálogo é copiado ANTES de qualquer migração;
#   - nenhuma dependência de sistema é instalada em silêncio — ele avisa e
#     você decide;
#   - roda de novo sem estragar nada (idempotente);
#   - sai com código != 0 se algo essencial falhar.
#
# Se algo der errado depois, a volta é: `alembic downgrade` até a revisão
# anterior (todas as migrações desta versão revertem limpo), ou simplesmente
# usar a cópia que este script deixou ao lado do catálogo.
#
# As fotos originais nunca são tocadas, aqui nem em lugar nenhum do app.
set -uo pipefail
cd "$(dirname "$0")/.."

CATALOGO=""
VERIFICAR=1
while [ $# -gt 0 ]; do
    case "$1" in
        --catalogo) CATALOGO="${2:-}"; shift 2 ;;
        --sem-verificacao) VERIFICAR=0; shift ;;
        -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "argumento desconhecido: $1"; exit 2 ;;
    esac
done

FALHAS=()
ok()     { printf '  \033[32m✓\033[0m %s\n' "$1"; }
aviso()  { printf '  \033[33m!\033[0m %s\n' "$1"; }
falha()  { printf '  \033[31m✗\033[0m %s\n' "$1"; FALHAS+=("$1"); }
etapa()  { printf '\n\033[1m%s\033[0m\n' "$1"; }

echo "== Foto Organizer — preparação da versão =="

# ---------------------------------------------------------------- 1. Python
etapa "[1/6] Ambiente Python"
if [ ! -x .venv/bin/python ]; then
    aviso ".venv não existe aqui — criando (é um worktree novo ou primeira vez)"
    PYTHON=""
    for candidato in python3.12 python3.13 python3; do
        command -v "$candidato" >/dev/null 2>&1 || continue
        v=$("$candidato" -c 'import sys;print(sys.version_info[0]*100+sys.version_info[1])')
        [ "$v" -ge 312 ] && { PYTHON=$candidato; break; }
    done
    if [ -z "$PYTHON" ]; then
        falha "nenhum Python 3.12+ encontrado (brew install python@3.12)"
        printf '\n❌ Sem Python não dá para seguir.\n'; exit 1
    fi
    "$PYTHON" -m venv .venv || { falha "criação do venv falhou"; exit 1; }
fi
PY=.venv/bin/python
ok "$($PY --version)"

# ------------------------------------------------------- 2. Dependências
etapa "[2/6] Dependências Python"
# [xmp] é novo nesta versão: sem defusedxml o Pillow não analisa XMP, e
# palavras-chave, autor e direitos de arquivo editado ficam invisíveis. É
# pequeno e puro-Python, então entra por padrão.
EXTRAS="dev,xmp"
$PY -c "import anthropic" 2>/dev/null && EXTRAS="$EXTRAS,llm" \
    && aviso "extra [llm] detectado — mantido (advisor continua opt-in no config)"
$PY -m pip install --quiet --upgrade pip
if $PY -m pip install --quiet -e ".[$EXTRAS]"; then
    ok "instaladas: $EXTRAS"
else
    falha "pip install falhou"
fi
$PY -c "import defusedxml" 2>/dev/null \
    && ok "XMP disponível (defusedxml)" \
    || aviso "XMP indisponível — EXIF e IPTC seguem normais"

# --------------------------------------------------- 3. Dependência opcional
etapa "[3/6] exiftool (opcional)"
if command -v exiftool >/dev/null 2>&1; then
    ok "exiftool $(exiftool -ver) — MakerNotes e ICC disponíveis"
    aviso "meça o ganho real: $PY scripts/medir_exiftool.py <pasta>"
else
    aviso "exiftool ausente. O app funciona sem ele; o que fica de fora é"
    aviso "MakerNotes (lente exata, modo de foco, rajada) e ICC."
    aviso "Para instalar, VOCÊ roda:  brew install exiftool"
fi

# ------------------------------------------------------------ 4. UI web
etapa "[4/6] UI web"
if command -v npm >/dev/null 2>&1; then
    (cd webapp && npm install --silent && npm run build --silent) \
        && ok "webapp/dist construído" \
        || falha "build da UI web falhou"
else
    falha "npm ausente — a UI web é a interface principal (instale Node 18+)"
fi

# --------------------------------------------------------- 5. Catálogo
etapa "[5/6] Catálogo e migrações"
DB=$($PY - "$CATALOGO" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, ".")
from fotoorganizer.config import paths
arg = sys.argv[1] if len(sys.argv) > 1 else ""
raiz = Path(arg).expanduser() if arg else None
print(paths.default_db_path(raiz))
PY
)
echo "  catálogo: $DB"

if [ -f "$DB" ]; then
    TAM=$(du -h "$DB" | cut -f1)
    BACKUP="${DB%.db}-backup-$(date +%Y%m%d-%H%M%S).db"
    # sqlite3 .backup respeita transação em curso; cp de um WAL aberto pode
    # copiar um arquivo inconsistente.
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$DB" ".backup '$BACKUP'" && ok "cópia de segurança ($TAM): $BACKUP"
    else
        cp "$DB" "$BACKUP" && aviso "cópia por cp ($TAM) — feche o app antes de rodar isto"
    fi
    [ -f "$BACKUP" ] || { falha "não consegui copiar o catálogo — parando antes de migrar"; }
else
    ok "catálogo ainda não existe — será criado vazio"
fi

if [ ${#FALHAS[@]} -eq 0 ]; then
    ANTES=$($PY - "$DB" <<'PY' 2>/dev/null || echo "novo"
import sqlite3, sys
try:
    c = sqlite3.connect(sys.argv[1])
    print(c.execute("select version_num from alembic_version").fetchone()[0])
except Exception:
    print("novo")
PY
)
    if $PY -c "
import sys; sys.path.insert(0,'.')
from pathlib import Path
from fotoorganizer.database import upgrade_to_head
upgrade_to_head(Path('$DB'))
" 2>/dev/null; then
        DEPOIS=$($PY - "$DB" <<'PY'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
print(c.execute("select version_num from alembic_version").fetchone()[0])
PY
)
        if [ "$ANTES" = "$DEPOIS" ]; then
            ok "esquema já em dia (revisão $DEPOIS)"
        else
            ok "esquema migrado: $ANTES → $DEPOIS"
        fi
    else
        falha "migração falhou — o catálogo original está intacto e a cópia está ao lado"
    fi
fi

# ------------------------------------------------------- 6. Verificação
etapa "[6/6] Verificação"
if [ "$VERIFICAR" = "0" ]; then
    aviso "pulada (--sem-verificacao)"
else
    if SAIDA=$($PY -m pytest -q --no-header 2>&1); then
        ok "$(echo "$SAIDA" | tail -1)"
    else
        echo "$SAIDA" | tail -12
        falha "pytest falhou"
    fi

    # O benchmark de agrupamento só passa quando a variante vencedora acerta
    # TODOS os cenários rotulados (docs/AGRUPAMENTO.md).
    BENCH=$($PY scripts/avaliar_agrupamento.py 2>&1 | grep '^MELHOR:' | tail -1)
    ACERTOS=$(echo "$BENCH" | sed -n 's/.*(\([0-9]*\)\/\([0-9]*\)).*/\1/p')
    TOTAL=$(echo "$BENCH" | sed -n 's/.*(\([0-9]*\)\/\([0-9]*\)).*/\2/p')
    if [ -n "$ACERTOS" ] && [ "$ACERTOS" = "$TOTAL" ]; then
        ok "agrupamento: $ACERTOS/$TOTAL cenários"
    else
        falha "benchmark de agrupamento abaixo do total (${ACERTOS:-?}/${TOTAL:-?})"
    fi

    if command -v npm >/dev/null 2>&1 && [ -d webapp/node_modules ]; then
        if SAIDA_UI=$(cd webapp && npm test 2>&1); then
            ok "UI: $(echo "$SAIDA_UI" | grep -E '^ *Tests ' | tail -1 | xargs)"
        else
            echo "$SAIDA_UI" | tail -15
            falha "testes da UI falharam"
        fi
    fi
fi

# ------------------------------------------------------------- resumo
echo ""
if [ ${#FALHAS[@]} -ne 0 ]; then
    echo "❌ ${#FALHAS[@]} etapa(s) com problema:"
    printf '   - %s\n' "${FALHAS[@]}"
    echo "   O catálogo não foi perdido: há uma cópia ao lado dele."
    exit 1
fi

cat <<FIM
✅ Ambiente pronto.

Abrir:
   scripts/executar.sh web

Nesta versão, três coisas só aparecem DEPOIS de regerar as sugestões
(botão "Gerar/atualizar sugestões" na aba Revisão):

   · o lugar estimado herdado de outra câmera, com quem doou e o Δt;
   · a separação entre foto, captura de tela, recebida e baixada;
   · a fila "classificação a confirmar" no Panorama.

Regerar não altera nada que você já aprovou ou rejeitou.
As fotos originais continuam intocadas — o catálogo é somente leitura
sobre elas.
FIM
