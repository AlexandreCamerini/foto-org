# Empacotamento para macOS (.app)

O protótipo roda direto do venv (`python -m fotoorganizer`). Para
distribuir como aplicativo nativo, o caminho recomendado é PyInstaller.

## PyInstaller

```bash
source .venv/bin/activate
pip install pyinstaller

pyinstaller \
  --name "Foto Organizer" \
  --windowed \
  --noconfirm \
  --collect-data reverse_geocode \
  --collect-submodules pillow_heif \
  --collect-submodules rawpy \
  --add-data "fotoorganizer/database/migrations:fotoorganizer/database/migrations" \
  fotoorganizer/app/main.py
```

Pontos de atenção:

- `--collect-data reverse_geocode`: o dataset offline de geocodificação
  (GeoNames) precisa ir junto — sem ele o app cairia no fallback sem geo.
- As migrações Alembic (`fotoorganizer/database/migrations`) são lidas em
  runtime; o `--add-data` acima as embute no bundle.
- `--windowed` gera o bundle `.app` sem janela de terminal.
- Teste o bundle com um catálogo NOVO (`dist/Foto Organizer.app`) antes de
  distribuir: o primeiro boot precisa criar diretórios e migrar o banco.

## Assinatura e notarização (distribuição fora da máquina)

```bash
codesign --deep --force --options runtime \
  --sign "Developer ID Application: SEU NOME (TEAM)" "dist/Foto Organizer.app"
xcrun notarytool submit "Foto Organizer.zip" --keychain-profile perfil --wait
xcrun stapler staple "dist/Foto Organizer.app"
```

Sem assinatura, o Gatekeeper exige clique-direito → Abrir na primeira
execução (aceitável para uso pessoal).

## Alternativa: Briefcase (BeeWare)

Para um pipeline mais "app-store-like" (ícones, Info.plist, dmg), o
Briefcase automatiza o scaffold — ao custo de mais configuração inicial.
Para o roadmap atual, PyInstaller cobre o uso pessoal.
