#!/bin/bash
# Assina cada binário nativo do runtime Python embarcado com Developer ID
# + hardened runtime, ANTES do `cargo tauri build`. Sem isto a notarização
# falha ("signature invalid") nas .dylib de libraw/libheif e nos .so das
# extensões — o Tauri assina o .app externo, mas não os binários aninhados.
#
# Uso:
#   scripts/assinar_runtime.sh "Developer ID Application: SEU NOME (TEAMID)"
#
# Requer: certificado Developer ID no keychain (é SEU — este script não o
# cria nem o instala). Rode `security find-identity -v -p codesigning` para
# ver as identidades disponíveis.
set -euo pipefail
cd "$(dirname "$0")/.."

IDENT="${1:?informe a identidade, ex.: 'Developer ID Application: NOME (TEAMID)'}"
RUNTIME="src-tauri/resources/runtime"
ENT="src-tauri/Entitlements.plist"

[ -d "$RUNTIME" ] || { echo "✗ runtime ausente — rode scripts/empacotar_runtime.sh"; exit 1; }
[ -f "$ENT" ]     || { echo "✗ Entitlements.plist ausente em $ENT"; exit 1; }

echo "== Assinando binários nativos em $RUNTIME =="
N=0
while IFS= read -r bin; do
    codesign --force --timestamp --options runtime \
        --entitlements "$ENT" --sign "$IDENT" "$bin"
    N=$((N + 1))
done < <(find "$RUNTIME" \
    \( -name '*.dylib' -o -name '*.so' -o -path '*/bin/python*' \) -type f)

echo "✅ $N binários assinados."
echo "   Próximo:  (cd src-tauri && cargo tauri build)"
echo "   Depois:   xcrun notarytool submit <app>.dmg --keychain-profile <perfil> --wait"
echo "             xcrun stapler staple <app>.dmg"
