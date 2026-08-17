# Empacotamento para macOS (.app) — Tauri + Python embarcado

O app roda de dois modos: em desenvolvimento, `python -m fotoorganizer web`
(uvicorn em 127.0.0.1) + Vite. Para **distribuir**, empacotamos com **Tauri
v2**: um shell nativo (Rust + WKWebView) que embarca o backend Python e o
webapp já construído.

A UI PySide6 foi removida — este documento substitui o caminho PyInstaller/Qt
anterior. A decisão e a análise das alternativas estão resumidas abaixo.

## Decisão: python-build-standalone + venv congelado (não PyInstaller)

O gargalo do empacotamento não é "embarcar Python" — é **assinar e notarizar
as bibliotecas nativas** (libraw via `rawpy`, libheif via `pillow-heif`, os
`.so` de Pillow/numpy) sob hardened runtime. Num runtime
[python-build-standalone](https://github.com/astral-sh/python-build-standalone)
(PBS) a árvore é um Python "normal": um único loop `codesign` sobre
`*.dylib/*.so` cobre tudo. O PyInstaller esconde essas libs no seu próprio
layout e reincide em falhas de notarização com `externalBin` (Tauri #11992).

Alternativas descartadas:
- **PyInstaller sidecar** — funciona, mas cada dep nativa nova pode exigir
  hook/`--collect`, e a assinatura das dylibs aninhadas é mais frágil.
- **venv no 1º boot** — baixa wheels em runtime → código nativo não assinado
  sob hardened runtime (Gatekeeper/notarização quebram) e fura o invariante
  local-first (o núcleo tem de funcionar offline). Inviável no modelo assinado.

## Como a arquitetura simplifica o Tauri

O front (`webapp/src/api.ts`) usa **só URLs relativas**, e o FastAPI já serve
`webapp/dist` via `StaticFiles`. O shell Tauri sobe o backend numa **porta
efêmera** e abre a janela em `http://127.0.0.1:<porta>`; o front herda essa
origem e descobre a porta sozinho, e o **guard de origem local**
(`server/app.py`) passa intacto (Host/Origin = 127.0.0.1). O Tauri fica
reduzido ao essencial: janela nativa, ciclo de vida do processo e
assinatura/DMG. Nenhuma mudança na comunicação front↔back.

Peças já no repositório:
- `fotoorganizer/cli.py` `cmd_web`: `--porta 0` liga porta efêmera, anuncia
  `FOTOORG_READY http://127.0.0.1:<porta>` no stdout e serve via
  `uvicorn.Server` (SIGINT/SIGTERM → shutdown limpo, checkpoint WAL).
- `src-tauri/`: projeto Tauri v2. `src/main.rs` spawna o Python embarcado,
  lê o anúncio, cria a janela na URL e, em `ExitRequested`, manda SIGTERM ao
  backend. `tauri.conf.json` embarca `resources/runtime/**` e assina com
  `Entitlements.plist`.
- `scripts/empacotar_runtime.sh`: baixa o CPython PBS (arm64), instala o
  projeto no runtime e prova que rawpy/pillow-heif importam dele.
- `scripts/assinar_runtime.sh`: loop `codesign -o runtime` sobre as dylibs.

## Build — passo a passo

Pré-requisito **não** coberto pelo repo: **toolchain Rust** (`rustup`) e o
Tauri CLI. Instale com:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cargo install tauri-cli --version '^2'
```

Depois:

```bash
# 1. Front de produção
(cd webapp && npm ci && npm run build)

# 2. Runtime Python embarcado (baixa o PBS e instala o projeto nele)
scripts/empacotar_runtime.sh            # gera src-tauri/resources/runtime/

# 3. Ícones (a partir do placeholder ou da arte final)
(cd src-tauri && cargo tauri icon icons/icon.png)

# 4a. Build sem assinar (uso pessoal — Gatekeeper: clique-direito → Abrir)
(cd src-tauri && cargo tauri build)

# 4b. OU: assinar o runtime ANTES do build (distribuição notarizada)
scripts/assinar_runtime.sh "Developer ID Application: SEU NOME (TEAMID)"
(cd src-tauri && cargo tauri build)
xcrun notarytool submit "src-tauri/target/release/bundle/dmg/*.dmg" \
      --keychain-profile <perfil> --wait
xcrun stapler staple "src-tauri/target/release/bundle/dmg/*.dmg"
```

O que **exige você** (não automatizável aqui): o certificado *Developer ID
Application* no keychain e as credenciais de notarização (Apple ID/perfil).
Sem eles, o passo 4a entrega um `.app` funcional para uso pessoal.

## Marcos

- **Marco 1 (sem assinatura):** `.app` que sobe o backend embarcado, abre a
  janela no webapp e encerra o backend ao fechar. Aceite: abrir num catálogo
  novo, escanear fixtures, ver a grade; ao fechar, nenhum processo Python
  órfão (`ps` / `~/.claude/scripts/portas.py`).
- **Marco 2 (assinado/notarizado):** `assinar_runtime.sh` + `cargo tauri
  build` + `notarytool`. Aceite: `spctl -a -vvv "Foto Organizer.app"` e
  `codesign -vvv --deep` sem erro; notarização verde.

## Aceite do Marco 1 — 2026-08-17

Critério exercido pela primeira vez (plano `05-03`) contra o bundle construído
no plano `05-02`, num catálogo descartável e depois confirmado visualmente
pelo dono. Ferramentas usadas: `tauri-cli 2.11.4`; runtime Python
`python-build-standalone 3.12.14` (`aarch64-apple-darwin`).

**Identidade de assinatura efetivamente aplicada** (resolve a suposição A1 da
pesquisa da Fase 5: o default do `cargo tauri build` já assina ad-hoc, sem
precisar de `"signingIdentity": "-"` explícito em `tauri.conf.json`) —
transcrito de `codesign -dv --verbose=4` sobre o binário do bundle:

```
Executable=/Users/.../src-tauri/target/release/bundle/macos/Foto Organizer.app/Contents/MacOS/foto-organizer
Identifier=foto_organizer-317d535e0bb0f816
CodeDirectory v=20400 size=84184 flags=0x20002(adhoc,linker-signed) hashes=2627+0 location=embedded
Signature=adhoc
Info.plist=not bound
TeamIdentifier=not set
Sealed Resources=none
Internal requirements=none
```

`tauri.conf.json` não foi alterado — a assinatura ad-hoc automática já
satisfaz o Marco 1.

Os quatro elementos do aceite (`docs/EMPACOTAMENTO.md` § Marcos), cada um
provado por comando contra o `.app` empacotado (não contra o `.venv` de
dev), num diretório de catálogo descartável (`FOTOORG_DATA_DIR=$(mktemp -d)/marco1`)
com fixtures JPEG sintéticas geradas por Pillow — o
`~/Library/Application Support/FotoOrganizer/catalog.db` real permaneceu com
o mtime intocado durante todo o teste:

1. **Abrir num catálogo novo:** binário nativo lançado diretamente (não via
   `open -a`, que entregaria o processo ao LaunchServices e perderia o
   `FOTOORG_DATA_DIR` do shell) com o env descartável exportado; anúncio
   `FOTOORG_READY` capturado no stdout; `GET /api/job` respondeu 200 no
   backend embarcado.
2. **Escanear fixtures, ver a grade:** `POST /api/scan` com
   `{"caminho": "<pasta de fixtures>"}` disparou a varredura; `GET /api/job`
   confirmou a saída do estado "em andamento"; `GET /api/midia` devolveu
   exatamente a mesma quantidade de itens que os JPEGs sintéticos criados;
   `GET /api/pastas` devolveu a árvore com as subpastas das fixtures.
3. **Sem processo Python órfão ao fechar (caminho normal):** encerramento via
   `osascript -e 'quit app "Foto Organizer"'` (equivalente ao Sair/⌘Q que o
   dono também exerceu no Finder) — `pgrep -f "fotoorganizer web"` saiu sem
   nenhum processo e a porta efêmera anterior deixou de aparecer em
   `lsof -nP -iTCP:<porta> -sTCP:LISTEN`. Prova o lado Rust do desenho de
   duas camadas (`RunEvent::ExitRequested` → SIGTERM → `child.wait()`).
4. **Sem processo Python órfão mesmo pulando o handler do Rust:** numa
   segunda execução, `kill -9` direto no shell nativo (sem passar pelo
   `ExitRequested`) — o Python embarcado se auto-encerrou sozinho em poucos
   segundos, provando o `_vigia_pai` (poll de `os.getppid()` a cada 2s,
   auto-SIGTERM quando o pai some) como rede de segurança independente do
   lado Rust.

**Defeitos encontrados:** nenhum. O caminho crítico completo — subida do
backend embarcado, anúncio `FOTOORG_READY`, API servida, varredura,
população da grade e os dois caminhos de encerramento — funcionou de
primeira contra o bundle já construído no plano `05-02`, sem exigir mudança
em `src-tauri/src/main.rs` nem em `fotoorganizer/cli.py` (D-03: nada a
corrigir nesta fase).

**Confirmação visual do dono** (Task 2, checkpoint humano): o dono abriu
`Foto Organizer.app` pelo Finder com clique-direito → Abrir, passou pelo
diálogo do Gatekeeper ("desenvolvedor não identificado", esperado no Marco 1
sem assinatura paga), viu a janela abrir com a UI do webapp carregada (não
página em branco, não erro de conexão), usou "Adicionar pasta…" apontando
para uma pasta pequena de fotos reais e confirmou que a varredura rodou e a
grade respondeu com os itens. Fechou pelo menu (Foto Organizer → Sair/⌘Q).
Aprovação registrada textualmente na sessão de execução do plano `05-03`:
"aprovado", sem ressalvas.

**Fora de escopo — Marco 2 (assinatura Developer ID + notarização):**
continua bloqueado pelo custo recorrente do Apple Developer Program
(US$99/ano), decisão do dono já registrada em `PROJECT.md` § Constraints e
em D-01 (`.planning/phases/05-prepara-o-para-lan-amento/05-CONTEXT.md`).
Nada neste aceite pede esse custo; o Marco 1 (uso pessoal, sem assinatura
paga) é o que a Fase 5 exige para LANC-01.

## Contingências documentadas

- **Se** o front passar a ser servido pelos assets embutidos do Tauri
  (origem `tauri://localhost`), o guard bloquearia por `Origin`. Ajuste
  cirúrgico: adicionar `"tauri.localhost"` a `_HOSTS_LOCAIS`
  (`server/app.py`) — só o hostname, sem wildcard. Não é necessário na
  arquitetura atual (janela aponta para o uvicorn).
- **Catálogo/cache:** continuam em `~/Library/Application Support/
  FotoOrganizer` e `~/Library/Caches/FotoOrganizer` — derivam de
  `Path.home()`, independem de onde o `.app` mora (distribuição Developer-ID
  fora da App Store, sem sandbox). O `Info.plist` precisa de
  `NSPhotoLibraryUsageDescription`; ler pastas arbitrárias depende de Acesso
  Total ao Disco (o app já sinaliza isso ao importar do Apple Fotos).
- **exiftool:** fica como dependência de sistema opcional (o fallback
  puro-Python já cobre); embarcá-lo assinado é release futuro.
