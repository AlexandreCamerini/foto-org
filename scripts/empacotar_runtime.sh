#!/bin/bash
# Congela um runtime Python autocontido (python-build-standalone) com o
# Foto Organizer e suas dependências, para o app Tauri embarcar e assinar.
#
# Por que PBS (e não PyInstaller): a árvore é um Python "normal", então
# assinar as .dylib nativas (libraw/rawpy, libheif/pillow-heif) para a
# notarização é um loop `codesign` previsível sobre *.dylib/*.so, em vez
# de caçar hooks. Ver docs/EMPACOTAMENTO.md.
#
# Uso:
#   scripts/empacotar_runtime.sh                    # arm64, Python 3.12
#   scripts/empacotar_runtime.sh --destino DIR      # outro destino
#   scripts/empacotar_runtime.sh --extras xmp,llm   # extras opt-in
#
# NÃO assina nada — a assinatura é passo separado (o app Tauri, no build).
set -euo pipefail
cd "$(dirname "$0")/.."

PY_VER="3.12"
ARCH="aarch64-apple-darwin"
DESTINO="src-tauri/resources/runtime"
EXTRAS="xmp"          # dev fica de fora; llm/vision são opt-in de release
while [ $# -gt 0 ]; do
    case "$1" in
        --destino) DESTINO="$2"; shift 2 ;;
        --extras)  EXTRAS="$2";  shift 2 ;;
        --arch)    ARCH="$2";    shift 2 ;;
        -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "argumento desconhecido: $1"; exit 2 ;;
    esac
done

echo "== Runtime python-build-standalone ($PY_VER, $ARCH) =="

# 1. Descobrir o asset install_only mais recente para a versão/arch.
API="https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
URL=$(curl -s --max-time 30 "$API" \
    | grep -oE "https://[^\"]*cpython-${PY_VER}\.[0-9]+%2B[0-9]+-${ARCH}-install_only\.tar\.gz" \
    | head -1)
[ -n "$URL" ] || { echo "✗ não encontrei asset PBS para $PY_VER/$ARCH"; exit 1; }
echo "  asset: ${URL##*/}"

# 2. Baixar e extrair (cria \$DESTINO/python/).
rm -rf "$DESTINO"; mkdir -p "$DESTINO"
TARBALL="$(mktemp -t pbs-XXXX).tar.gz"
curl -fsSL --max-time 300 "$URL" -o "$TARBALL"
tar -xzf "$TARBALL" -C "$DESTINO"
rm -f "$TARBALL"
PYBIN="$DESTINO/python/bin/python3"
[ -x "$PYBIN" ] || { echo "✗ python do PBS ausente em $PYBIN"; exit 1; }
echo "  $("$PYBIN" --version) em $DESTINO/python"

# 3. Instalar o projeto + deps DENTRO do runtime (não no venv de dev).
"$PYBIN" -m pip install --quiet --upgrade pip
"$PYBIN" -m pip install --quiet ".[$EXTRAS]"

# 4. Provar que as deps nativas importam a partir do runtime congelado.
echo "== Imports nativos a partir do runtime =="
"$PYBIN" - <<'PY'
import importlib, sys
for m in ("rawpy", "pillow_heif", "reverse_geocoder", "PIL", "fotoorganizer"):
    importlib.import_module(m)
    print(f"  ok {m}")
print("  prefix:", sys.prefix)
PY

echo "✅ runtime congelado: $DESTINO/python"
echo "   próximo: assinar *.dylib/*.so (Developer ID) antes do tauri build."
