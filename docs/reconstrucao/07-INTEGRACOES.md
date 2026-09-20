# 07 — Integrações externas

> Parte do mapa de reconstrução. **A — arquivos/plataforma** (exiftool, osxphotos, Takeout,
> Lightroom, Tauri + runtime embarcado, Keychain, SQLite/Alembic) e **B — imagem/inferência**
> (reverse_geocode, API Anthropic, rawpy/libraw, pillow-heif, imagehash, exifread/Pillow,
> defusedxml). Para cada: versão, como é chamada, o que acontece sem ela, riscos.

---

# Parte A — Arquivos e plataforma

# 07 — Integrações externas do domínio ARQUIVOS

Tudo que o app chama fora do próprio processo Python: binários, bibliotecas
opcionais, o Keychain, o runtime embarcado e o SQLite/Alembic. Para cada
um: como é chamado, versão/requisito, o que acontece sem ele, riscos.

Princípio que atravessa todas: **nenhuma é pré-requisito para catalogar**.
O núcleo funciona offline e degrada com menos sinal, nunca com erro fatal.

---

## 1. exiftool (`fotoorganizer/metadata/exiftool.py`)

### Como é chamado — processo persistente

`ExifToolExtractor` (`:288-…`) sobe **um** processo vivo:

```
subprocess.Popen([binario, "-stay_open", "True", "-@", "-"],
                 stdin=PIPE, stdout=PIPE, stderr=DEVNULL,
                 text=True, encoding="utf-8", errors="replace", bufsize=1)
```
(`:318-329`, `_garantir`)

Por quê: um `exiftool arquivo` por foto paga ~200 ms de partida do Perl. Num
scan de dezenas de milhares, é a diferença entre minutos e horas (`:11-13`).

**Protocolo por arquivo** (`_conversar`, `:349-389`), escrito no stdin,
uma linha por argumento, terminado por `-execute`:

```
-j
-G
-c
%+.8f
-charset
filename=utf8
<caminho>
-execute
```

- `-j` JSON; `-G` nome do grupo junto da chave; `-c %+.8f` coordenada em
  grau decimal **com sinal** (sem isso o GPS volta formatado e o diff vira
  comparação de string).
- A resposta é lida linha a linha até o sentinela `_FIM = "{ready}"`
  (`:43`). `readline()` vazio = processo morreu → `self._proc = None` e
  devolve `None`.
- **A única espera potencialmente infinita do scan inteiro** (`:376-380`):
  se o exiftool emudecer diante de um arquivo, o `readline` não tem fim e a
  fila congela em `RODANDO`. Guarda: `threading.Timer(_TIMEOUT_S=30.0,
  proc.kill)` (`:44`, `:381-82`), cancelado no `finally`. O kill devolve
  EOF, o chamador recebe `None`, e o **fallback puro-Python** responde pelo
  arquivo.
- JSON inválido ou vazio → `None`, sem levantar.

Fechamento (`close`, `:330-340`): escreve `-stay_open\nFalse\n` no stdin,
`wait(timeout=5)`, e `kill()` em qualquer falha. O processo **não morre
sozinho** — use como context manager ou chame `close()` (`:289-291`).

**Não é thread-safe por desenho**; um `threading.Lock` serializa o acesso
porque o protocolo do `-stay_open` é uma conversa única por stdin/stdout
(`:292-294`, `:305`).

### Guardas de segurança (invariante 5)

- Argumentos sempre em **lista**, nunca `shell=True`.
- Caminho com `\n` ou `\r` **romperia o protocolo** (delimitado por linha):
  vai direto para o fallback em vez de arriscar (`:393-396`).
- Caminho que não é arquivo comum vira `MediaMetadata(erro=…)`, não exceção.

### `disponivel()`

`shutil.which(binario or "exiftool") is not None` (`:308-309`).
Mesma função existe, separada, em
`exif_write/writer.py:74-75` (`ExifToolWriter.disponivel`).

### Quem decide usar

`criar_extrator(preferir_exiftool=True)`
(`fotoorganizer/metadata/__init__.py:20-35`): **a escolha mora aqui, e não
em cada chamador, para não existirem quatro versões da mesma decisão
divergindo com o tempo**. Com exiftool disponível → `ExifToolExtractor`;
senão → `PurePythonExtractor`, com `log.info` dizendo qual foi.

### Sem exiftool — o que se perde

O app funciona igual, **com menos sinal** (`metadata/__init__.py:26`):

| | com exiftool | sem (puro-Python) |
|---|---|---|
| Tags lidas num CR3 real | 361-386 | 8 |
| `Make`/`Model` de CR3 | sim | **não** — 2.949 CR3 ficaram sem câmera num acervo real |
| Consequência | — | sem câmera não há correção de deriva de relógio nem "outra origem" na herança de GPS; a lacuna se propaga para a classificação inteira |
| Vídeo (`.mov`/`.mp4`) | `CreateDate`, `ImageWidth/Height` do QuickTime | `MediaMetadata()` vazio, **sem `erro`** — o arquivo não está corrompido, só não há extração local (`purepython.py:265-271`) |
| Escrita EXIF (`exif_write/`) | funciona | **impossível** — não há caminho alternativo |

O fallback usa Pillow + exifread + pillow-heif + rawpy
(`metadata/purepython.py`). As extensões aceitas pela descoberta são
**sempre** as do fallback, mesmo com exiftool instalado
(`exiftool.py:311-315`) — para o scanner não passar a descobrir arquivo que
o resto do sistema não sabe tratar.

### Escrita (`exif_write/writer.py`)

Deliberadamente **não** usa `-stay_open` (`:60-68`): o volume de escrita é
um plano revisado (dezenas a milhares), ~200 ms de partida por chamada é
aceitável, e assim não se disputa o lock do processo do leitor
compartilhado. Um `subprocess.run(args, capture_output=True, text=True,
check=False)` por escrita.

Verificação usa invocações próprias, `check=False`, timeout 30 s:
`dump` → `exiftool -j -G1 -a -n -charset filename=utf8 <arquivo>`
(`verificacao.py:314-337`); `dump_lote` → o mesmo com até 200 caminhos
(`:342-376`); `avisos` → saída em **texto plano**, porque `-j` colapsa
`Warning`/`Error` repetidas.

### Riscos

1. **O exit code mente.** Verificado em 13.55: `exiftool
   -GPSLatitude=notanumber -City=X -Country=Y <file>` pula só a tag
   malformada, escreve o resto, reporta "1 image files updated" e sai 0
   (`verificacao.py:3-10`). Todo design que use exit code ou
   mensagem-resumo como critério perde exatamente o caso que EXIF-03 existe
   para pegar. Mitigação: o veredito é **sempre** o diff de tags.
2. **Versão não é fixada.** `shutil.which("exiftool")` pega o que estiver no
   PATH. As medições de D-076/D-077 e o texto de `formatos.py` foram feitos
   contra **13.55**; nada no código verifica a versão em runtime.
3. **`-stay_open` congelando** — mitigado pelo `Timer` de 30 s, mas o custo
   é a morte do processo persistente (recriado na chamada seguinte).
4. **Não empacotado**: `scripts/empacotar_runtime.sh` não embarca o
   exiftool. Num `.app` distribuído, ele só existe se o usuário tiver
   instalado — o app degrada para puro-Python e a escrita EXIF fica
   indisponível.

---

## 2. osxphotos (`fotoorganizer/sources/apple_photos.py`)

### Instalação

Extra opcional `apple` no `pyproject.toml:39-42`: `osxphotos>=0.70`.
`scripts/empacotar_runtime.sh:22` inclui `apple` nos `EXTRAS` padrão do
runtime empacotado (`xmp,apple`).

### Como é chamado

`import osxphotos` **dentro** de `iter_assets` (`:131-137`), não no topo do
módulo — o módulo importa e o app sobe mesmo sem o extra.
`osxphotos.PhotosDB(str(biblioteca))` (`:140`), depois
`db.photos(movies=True)` (`:157`).

Biblioteca padrão: `~/Pictures/Photos Library.photoslibrary` (`:28-30`);
`ApplePhotosProvider(biblioteca)` aceita outra.

**Somente leitura.** Nada é escrito na biblioteca; nada de rede.

### Permissões TCC (Acesso Total ao Disco)

O macOS concede Acesso Total ao Disco **por app**, e quem precisa estar na
lista é o app **no topo da árvore de processos** — não o script Python.

`_app_responsavel()` (`:37-62`) descobre isso: até 8 iterações de
`subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)], timeout=2,
check=False)`, subindo pelo ppid, guardando o último `comm` que contenha
`.app/Contents/MacOS/`. Em qualquer falha devolve `"o app que você usa"` —
a mensagem de erro não pode virar um segundo erro.

A mensagem final (`:142-149`) diz literalmente qual app marcar em
Ajustes → Privacidade e Segurança → Acesso Total ao Disco, e que é preciso
reiniciar o app depois. Saber isso economiza a hora que se perde
autorizando o app errado.

É também por causa do TCC que **existe o comando de CLI**: rodar
`fotoorganizer importar apple` no terminal do usuário usa a permissão do
**terminal**, sem precisar autorizar o app que abriu o servidor
(`cli.py:406-408`).

### Sem osxphotos ou sem permissão

`ApplePhotosError` com instrução acionável:
- sem o pacote → `"osxphotos não instalado — instale com 'pip install
  fotoorganizer[apple]'"` (`:134-136`);
- biblioteca inacessível → a mensagem de TCC acima.

No job (`server/jobs.py:384-399`), `_mensagem_falha_import` preserva a
mensagem do `ApplePhotosError` como está (ela já traz o detalhe) e, para
outras classes de erro, detecta `PermissionError` **em qualquer ponto da
cadeia de causas** (`__cause__`/`__context__`, `_erro_de_permissao`,
`:370-381`) e acrescenta a orientação. Detectar pela cadeia é mais robusto
que caçar substring de mensagem de uma lib.

O resto do app **não cai**: sem Apple Fotos, perde-se a fonte mais rica de
fuso por foto (D-038) e as referências que doam GPS, nada mais.

### Riscos

- `osxphotos` é uma lib que lê o schema interno do Apple Fotos; uma versão
  nova do app da Apple pode quebrá-la. O provider é duck-typed
  (`_asset_de` usa `getattr` para `keywords`, `:105-110`), o que absorve
  campos ausentes, mas não uma mudança de schema.
- Sem teste em CI: `tests/test_apple_photos.py` falha no sandbox (2 dos 26
  erros do run atual), porque depende do ambiente.

---

## 3. Google Takeout (`fotoorganizer/sources/google_takeout.py`)

Não é uma dependência — é um **formato de pasta** no disco. Nenhuma
biblioteca, nenhuma rede.

Por que Takeout e não a API: desde março/2025 a Library API do Google Photos
só acessa mídia criada pelo próprio app, então a exportação oficial é o
caminho que **não fura o invariante de privacidade** (`:3-6`).

Formato esperado (`:8-15`):
```
Takeout/Google Photos/<álbum ou "Photos from 2024">/IMG_001.jpg
Takeout/Google Photos/<…>/IMG_001.jpg.json
```
Qualquer nível acima da pasta indicada também serve — a varredura é
`raiz.rglob("*")`.

Variantes de sidecar cobertas (`_sidecar_de`, `:49-66`):
`<nome>.json`, `<nome>.supplemental-metadata.json`, e para duplicatas
numeradas `IMG_001(1).jpg` também `IMG_001.jpg(1).json` e
`IMG_001.jpg.supplemental-metadata(1).json`.

Chaves lidas do JSON: `photoTakenTime.timestamp` (epoch **UTC**, o instante
absoluto), `geoData` / `geoDataExif` (`latitude`/`longitude`; **`0.0/0.0` é
o "sem GPS" do Takeout**), `description`, `favorited`, `people[].name`.

Extensões aceitas: `_MEDIA_EXTS` (`:39-43`) — 9 de imagem + 7 de vídeo.

Degradação: sidecar ausente → o item entra com o que a entrada de diretório
diz. Sidecar ilegível (`OSError`/`JSONDecodeError`) → `log.warning` e segue
com `{}` (`:148-150`).

Risco: o Google muda o layout do Takeout de tempos em tempos (o
`.supplemental-metadata.json` é ele próprio uma mudança recente); as
variantes cobertas são as conhecidas em 2026-08, não um contrato.

---

## 4. Lightroom Classic (`fotoorganizer/sources/lightroom.py`)

Não é uma dependência — é um **arquivo SQLite** (`.lrcat`) lido com o
`sqlite3` da stdlib.

Abertura: `sqlite3.connect(f"file:{catalogo}?immutable=1", uri=True)`
(`:155-157`). `immutable=1` promete que ninguém está escrevendo: sem lock,
sem journal, sem WAL — é o que permite ler com o Lightroom **aberto ao
lado** (invariante 1). Sanity check imediato:
`select count(*) from Adobe_images`.

Tabelas e colunas lidas:

| Consulta | Tabelas | Campos |
|---|---|---|
| `_CONSULTA` (`:46-63`) | `Adobe_images i`, `AgLibraryFile f`, `AgLibraryFolder fo`, `AgLibraryRootFolder rf`, `AgHarvestedExifMetadata e` (LEFT JOIN) | `f.id_global` (uuid), `rf.absolutePath`, `fo.pathFromRoot`, `f.baseName`, `f.extension`, `i.captureTime`, `e.gpsLatitude`, `e.gpsLongitude`, `i.rating`, `i.pick` |
| `_COLECOES` (`:67-73`) | `AgLibraryCollectionimage`, `AgLibraryCollection`, `Adobe_images`, `AgLibraryFile` | nome da coleção → `albuns` |
| `_PALAVRAS` (`:75-82`) | `AgLibraryKeywordImage`, `AgLibraryKeyword`, … | nome da keyword → `palavras_chave` |

`favorito` = `rating >= 4` (`_NOTA_DE_FAVORITO`, `:86`) **ou** `pick > 0` —
4 e 5 estrelas são o corte usual de portfólio.

Os pedaços do caminho vêm **separados de propósito** (`:38-45`): em SQL,
`a || b` é `NULL` se qualquer parte for `NULL`, e uma extensão ausente
apagava o caminho inteiro — a referência perdia a única pista de lugar que
tinha, sem exceção e sem log.

Por que vale tanto (`:3-10`): **responde com os discos desligados**. Num
acervo real o `.lrcat` conhecia 54.086 fotos, 44.474 num volume externo
desmontado; varrer o disco teria encontrado zero.

Degradação: arquivo ausente ou ilegível → `LightroomError` com instrução
("abra-o uma vez no Lightroom Classic para atualizar o formato",
`:161-166`). Tabela auxiliar ausente numa versão diferente →
`log.warning` e dicionário vazio (`:175-179`) — perde-se o contexto, não o
mapa. Itens sem caminho reconstruível são contados e logados (`:210-217`).

Risco: o schema do `.lrcat` varia entre versões do Lightroom; as consultas
auxiliares já degradam, mas `_CONSULTA` não — se `Adobe_images` ou
`AgLibraryFile` mudarem, a importação inteira falha com `LightroomError`.

Só acessível pela CLI: `fotoorganizer importar lightroom <arquivo.lrcat>`.
**Não há rota HTTP** (`server/app.py:1452-1467` só aceita `apple_photos` e
`google_takeout`).

---

## 5. SQLite e Alembic

### SQLite

Via `sqlalchemy>=2.0` (`pyproject.toml:7`), driver `sqlite3` da stdlib.
Engine e PRAGMAs em `03-DADOS.md` §1.3. Pontos de integração:

- `check_same_thread=False` (`database/engine.py:43-45`) — o scan roda fora
  da thread do servidor; cada thread usa a própria `Session`, e WAL +
  `busy_timeout=5000` cuidam da concorrência.
- `PRAGMA foreign_keys=ON` é o que torna a FK de `audit_log.plan_id` **real
  e ativa** — e é por isso que o domínio de escrita EXIF grava `plan_id=None`
  e leva o id no JSON (`models/exif_write.py:8-14`).
- `PRAGMA case_sensitive_like=ON` é pré-requisito do índice de `pasta`
  (`engine.py:17-31`). Varredura de segurança já feita: `.ilike()` compila
  para `lower(x) LIKE lower(y)` independente do PRAGMA; o único `.like()`
  afetado é o de `pasta`, cujo valor vem de `/api/pastas`, nunca de texto
  digitado livremente.
- Limite de variáveis por statement: atingido duas vezes em produção
  (`repositories/inventario.py`, `scanner/scanner.py:65-68`), e a resposta
  em ambos foi lotear (`_LOTE_SUMICO = 500`).
- Um segundo SQLite é aberto **só para leitura** e fora do ORM: o `.lrcat`
  do Lightroom (§4).

### Alembic

`alembic>=1.13` (`pyproject.toml:8`). Configuração **programática**, sem
`alembic.ini`: `alembic_config(db_path)`
(`database/migrate.py:18-22`) monta um `Config()` em memória com
`script_location` = `fotoorganizer/database/migrations` e
`sqlalchemy.url` = `db_url(db_path)`.

`upgrade_to_head(db_path)` (`:25-28`) cria o diretório pai e roda
`command.upgrade(cfg, "head")`. Chamado em **todo** caminho de entrada:
`cli._abrir_catalogo:183`, `cli._build_scanner:201`, `cli.cmd_web:646`.

`NAMING_CONVENTION` em `models/base.py:9-15` dá nomes determinísticos a
índices/uniques/checks/FKs/PKs — pré-requisito para o autogenerate não
produzir diff espúrio.

Risco: o app **migra ao iniciar**, sem backup automático e sem
`downgrade` exercitado. Uma migração destrutiva rodaria no catálogo de
produção do dono na primeira abertura. A mitigação em uso é o rigor do
processo (migração versionada, nunca editar à mão) e `--data-dir` para
testar isolado.

---

## 6. Keychain do macOS (`fotoorganizer/security/crypto.py`)

Só para a chave Fernet dos **embeddings faciais** (recurso stub hoje:
`people`, `face_embeddings` e `face_occurrences` estão vazias).

Dois subprocessos, argumentos em lista, sem shell, timeout 10 s:

```
security find-generic-password -a embeddings-key -s FotoOrganizer -w
security add-generic-password  -a embeddings-key -s FotoOrganizer -w <chave> -U
```
(`:51-66`; `_SERVICE = "FotoOrganizer"`, `_ACCOUNT = "embeddings-key"`,
`:22-23`)

`keystore_padrao(data_dir)` (`:70-78`) tenta o Keychain **de fato** (chama
`obter_ou_criar_chave()`); em `OSError`/`SubprocessError`, loga aviso e cai
para `FileKeyStore` — arquivo `<data_dir>/embeddings.key` criado com
`touch(mode=0o600)` + `chmod(0o600)` (CI, testes, ambientes sem Keychain).

`EmbeddingCipher` (`:81-89`): `Fernet` (de `cryptography>=42.0`) sobre
`json.dumps(vetor)`.

Limitação documentada em `docs/PRIVACIDADE.md` e repetida na docstring
(`:5-7`): protege o banco **em repouso**, não contra código rodando na
sessão desbloqueada do usuário.

Riscos: o fallback de arquivo é silencioso para o usuário (só `log.warning`)
e degrada a proteção; e o caminho inteiro é **sem teste** (achado **B5**).

---

## 7. Tauri + runtime Python embarcado

Milestone de empacotamento. Detalhes em `docs/EMPACOTAMENTO.md`.

### 7.1 Decisão: python-build-standalone, não PyInstaller

O gargalo não é embarcar Python — é **assinar e notarizar as bibliotecas
nativas** (libraw via `rawpy`, libheif via `pillow-heif`, os `.so` de
Pillow/numpy) sob hardened runtime. No PBS a árvore é um Python "normal":
um único loop `codesign` sobre `*.dylib/*.so` cobre tudo. O PyInstaller
esconde essas libs no seu layout e reincide em falhas de notarização com
`externalBin` (Tauri #11992).

Descartados: **PyInstaller sidecar** (cada dep nativa nova pode exigir
hook/`--collect`) e **venv no 1º boot** (baixa wheels em runtime → código
nativo não assinado sob hardened runtime, e fura o invariante local-first).

### 7.2 Como o shell conversa com o backend (`src-tauri/src/main.rs`)

89 linhas. O webview carrega de `http://127.0.0.1:<porta>` servido pelo
próprio FastAPI — o front usa só URLs relativas, descobre a porta sozinho, e
o guard de origem local passa intacto. O Tauri fica reduzido a janela, ciclo
de vida e assinatura.

1. Resolve o Python embarcado em
   `resource_dir()/resources/runtime/python/bin/python3` (`:26-29`).
2. `Command::new(&py).args(["-m","fotoorganizer","web","--porta","0",
   "--encerrar-com-pai"]).stdout(Stdio::piped()).spawn()` (`:34-41`).
   Nenhum `--data-dir`: o catálogo fica no padrão.
3. Guarda o `Child` num `Mutex<Option<Child>>` gerenciado
   (`struct Backend`, `:16`), para encerrá-lo depois.
4. Thread lê o stdout linha a linha até `FOTOORG_READY ` e então cria a
   janela em `WebviewUrl::External(url)` — 1280×800, mínimo 960×640
   (`:47-66`).
5. Em `RunEvent::ExitRequested` (`:72-87`): `libc::kill(pid, SIGTERM)` —
   **SIGTERM, não SIGKILL**, para o uvicorn drenar e fazer o checkpoint WAL
   — e depois `child.wait()`. Sem netos: os workers são threads.

Rede de segurança dupla: `--encerrar-com-pai` faz o backend se auto-encerrar
se este processo morrer de qualquer forma (inclusive um sinal que não passa
pelo handler) — nunca deixa órfão.

### 7.3 `src-tauri/tauri.conf.json`

```
productName  "Foto Organizer"
identifier   app.acamerini.fotoorganizer
version      0.1.0
build.frontendDist  ../webapp/dist
app.windows  []                      # a janela nasce em runtime, na URL anunciada
app.security.csp  null
bundle.targets    ["app", "dmg"]
bundle.resources  ["resources/runtime/**/*"]
bundle.macOS.entitlements  Entitlements.plist
bundle.macOS.minimumSystemVersion  12.0
```

`windows: []` é intencional: a janela só pode nascer depois que a porta for
conhecida.
Achado **B2**: `csp: null` e o FastAPI não envia header CSP (o webview é
`External`).

### 7.4 `src-tauri/Entitlements.plist`

| Chave | Valor | Justificativa no arquivo |
|---|---|---|
| `com.apple.security.cs.disable-library-validation` | `true` | carregar as `.dylib` nativas embarcadas (libraw/rawpy, libheif/pillow-heif) assinadas com o mesmo Developer ID — sem isto o hardened runtime recusa por validação de biblioteca |
| `com.apple.security.cs.allow-unsigned-executable-memory` | `true` | "alguns módulos nativos do Python fazem mmap executável" |

> **Achado M7 (MÉDIO)**: o comentário do segundo entitlement diz "**comece
> sem esta chave; ative só se um dep quebrar**", e o valor está `true`.
> Junto com `disable-library-validation`, isso derruba boa parte da
> proteção do hardened runtime.

### 7.5 `scripts/empacotar_runtime.sh`

Congela um runtime autocontido. **Não assina nada** — assinatura é passo
separado.

Defaults: `PY_VER=3.12`, `ARCH=aarch64-apple-darwin`,
`DESTINO=src-tauri/resources/runtime`, `EXTRAS="xmp,apple"` (`:19-23`).
`dev` fica de fora; `llm` (que envia dados) é **opt-in de release**.
Flags: `--destino`, `--extras`, `--arch`.

Passos:
1. descobre o asset `install_only` mais recente na API do GitHub de
   `astral-sh/python-build-standalone` (`:37-42`);
2. baixa e extrai em `$DESTINO/python/` (`:45-52`);
3. `pip install ".[$EXTRAS]"` **dentro** do runtime, não no venv de dev
   (`:55-56`);
4. **3b** copia `webapp/dist` para `site-packages/webapp/dist` (`:58-71` do
   arquivo): é onde `_WEBAPP_DIST = parents[2]/webapp/dist` resolve dentro
   do runtime. Sem isto o backend empacotado não serve a UI e `/` dá 404.
   Ausência do build vira aviso, não erro;
5. **prova** que as deps nativas importam a partir do runtime congelado:
   `rawpy`, `pillow_heif`, `reverse_geocode`, `osxphotos`, `PIL`,
   `fotoorganizer` (`:72-80` do arquivo).

Riscos: depende de **rede** (API do GitHub + download do tarball) no momento
do build, e o asset é resolvido por regex sobre a resposta da API — mudança
de nomenclatura do PBS quebra o script com "não encontrei asset".

### 7.6 `scripts/assinar_runtime.sh`

```
codesign --force --timestamp --options runtime \
         --entitlements src-tauri/Entitlements.plist \
         --sign "<identidade>" <cada binário>
```
sobre `find src-tauri/resources/runtime \( -name '*.dylib' -o -name '*.so'
-o -path '*/bin/python*' \) -type f` (`:25-30`).

Roda **antes** de `cargo tauri build`: o Tauri assina o `.app` externo, mas
não os binários aninhados; sem isto a notarização falha com "signature
invalid" nas `.dylib` de libraw/libheif e nos `.so` das extensões.

O certificado Developer ID é do usuário — o script não o cria nem instala.
Depois: `cargo tauri build`, `xcrun notarytool submit … --wait`,
`xcrun stapler staple`.

### 7.7 Pré-requisitos fora do repositório

Toolchain Rust (`rustup`) e `cargo install tauri-cli --version '^2'`;
`(cd webapp && npm ci && npm run build)`; ícones via
`cargo tauri icon icons/icon.png`; certificado Developer ID no keychain.

---

## 8. Bibliotecas Python (resumo do que é externo ao processo)

De `pyproject.toml`:

| Pacote | Versão | Papel no domínio arquivos | Sem ele |
|---|---|---|---|
| `SQLAlchemy` | `>=2.0` | ORM e engine | nada funciona |
| `alembic` | `>=1.13` | migrações | schema não sobe |
| `xxhash` | `>=3.4` | `quick_signature` (`xxh3_64`) | scan incremental e cache de thumbnail perdem a chave |
| `cryptography` | `>=42.0` | Fernet dos embeddings | faces (stub) |
| `fastapi` | `>=0.115` | servidor local | UI web |
| `uvicorn` | `>=0.30` | ASGI | idem |
| `Pillow` | `>=11.0` | extração puro-Python, thumbnails | fallback de metadado |
| `pillow-heif` | `>=0.20` | `.heic/.heif/.hif` | essas extensões **somem da descoberta** |
| `rawpy` | `>=0.27` | RAW (libraw) | `.dng/.cr2/.cr3/.nef/.arw/.raf/.orf/.rw2` somem da descoberta |
| `exifread` | `>=3.0` | EXIF no fallback | menos tags |
| `ImageHash` | `>=4.3` | phash (duplicata visual) | níveis 2-5 de duplicata |
| `reverse-geocode` | `>=1.6` | geocodificação offline | domínio imagem/geo |

Extras: `xmp` (`defusedxml>=0.7` — o Pillow só analisa o pacote XMP com um
parser de XML endurecido, e com razão: é XML de origem não confiável dentro
do arquivo do usuário; sem ele o extrator **degrada em silêncio**, EXIF e
IPTC seguem e XMP não é lido); `dev` (`pytest`, `httpx`, `defusedxml`);
`llm` (`anthropic>=0.116` — opt-in); `apple` (`osxphotos>=0.70`).

`requires-python = ">=3.12"`.

---

## Lacunas e incertezas

1. **Versão do exiftool não é verificada em runtime.** As medições de
   D-076/D-077 valem para 13.55; não achei código que cheque a versão nem
   docs que fixem um mínimo. Se o reconstrutor rodar com outra versão, a
   allowlist de `formatos.py` pode estar medindo outro programa.
2. **`metadata/purepython.py`** foi lido só nas partes que definem
   extensões e o caminho de vídeo/RAW; o corpo de `_extract_pillow` e
   `_extract_raw` não foi verificado (domínio imagem).
3. **`fotoorganizer/security/http_seguro.py`** (445 linhas) não tem
   consumidor em produção — não determinei qual provider externo ele foi
   escrito para servir, nem se a intenção é usá-lo no adaptador de
   geocodificação opt-in.
4. **`scripts/empacotar_runtime.sh` linhas ~84 em diante** (após o bloco de
   prova de imports) não foram lidas — li o início e o trecho 58-83. Pode
   haver passos posteriores que não documentei.
5. **`src-tauri/capabilities/` e `build.rs`** não foram abertos; descrevi
   `main.rs`, `tauri.conf.json` e `Entitlements.plist`. Permissões do Tauri
   v2 declaradas em `capabilities/` ficam como lacuna.
6. **Nunca verifiquei um build real**: tudo sobre notarização, `stapler` e
   o comportamento do hardened runtime vem de `docs/EMPACOTAMENTO.md` e dos
   comentários dos scripts, não de execução.
7. **`reverse-geocode` × `reverse_geocoder`**: o `pyproject.toml` declara
   `reverse-geocode>=1.6` e o CLAUDE.md fala em `reverse_geocoder` como
   exemplo. Não confirmei qual módulo `geolocation/offline.py` importa de
   fato — é domínio imagem/geo.


---

# Parte B — Imagem e inferência

# 07 — Integrações do domínio IMAGEM / INFERÊNCIA

Toda biblioteca e todo serviço externo que este domínio toca. Para cada um:
como é chamado, o que acontece sem ele, e qual versão está declarada.

Versões declaradas em `pyproject.toml`; versões **instaladas** verificadas em
`.venv` (`importlib.metadata`) no commit `524903d`.

| Pacote | `pyproject.toml` | Instalada | Onde é declarado |
|---|---|---|---|
| `Pillow` | `>=11.0` | 11.0.0 | `pyproject.toml:11` (core) |
| `pillow-heif` | `>=0.20` | 0.20.0 | `pyproject.toml:12` (core) |
| `rawpy` | `>=0.27` | 0.27.0 | `pyproject.toml:13` (core) |
| `exifread` | `>=3.0` | 3.5.1 | `pyproject.toml:14` (core) |
| `ImageHash` | `>=4.3` | 4.3.1 | `pyproject.toml:15` (core) |
| `xxhash` | `>=3.4` | 3.8.1 | `pyproject.toml:16` (core) |
| `reverse-geocode` | `>=1.6` | 1.6.6 | `pyproject.toml:17` (core) |
| `cryptography` | `>=42.0` | 49.0.0 | `pyproject.toml:18` (core) |
| `defusedxml` | `>=0.7` | 0.7.1 | `pyproject.toml:29` (extra `xmp`) **e** `:34` (extra `dev`) |
| `anthropic` | `>=0.116` | 0.116.0 | `pyproject.toml:38` (extra `llm`) |
| `exiftool` | — (binário externo) | 13.55 (`/opt/homebrew/bin/exiftool`) | não declarado; descoberto por `shutil.which` |

Transitivas relevantes (não declaradas, chegam por dependência):
`numpy` 2.5.1 e `scipy` 1.18.0 (exigidas por `reverse-geocode` **e** por
`ImageHash`), `PyWavelets` (por `ImageHash`).

---

## 1. `reverse_geocode` — geocodificação reversa offline

**Versão**: `>=1.6` declarada; **1.6.6** instalada. Licença **LGPL** (classifier
`GNU Library or Lesser General Public License`). ⚠️ É a única dependência
copyleft do domínio — relevante para o empacotamento (`docs/EMPACOTAMENTO.md`).

**Dataset**: o pacote embarca `geocode.gz` (**3.458.676 bytes**) e
`countries.csv`, derivados de **GeoNames `cities1000`**
(`GEOCODE_URL = "http://download.geonames.org/export/dump/cities1000.zip"`).
`cities1000` = localidades com população ≥ 1.000. GeoNames é CC BY 4.0 na
origem; **o pacote não declara a data do snapshot** (ver Lacunas).

**Como é chamado** (`fotoorganizer/geolocation/offline.py`):

```python
# import LAZY — offline.py:31-37
def _carregar(self):
    if self._modulo is None:
        log.info("geocoding offline: carregando dataset local…")
        import reverse_geocode
        self._modulo = reverse_geocode
    return self._modulo

# offline.py:39-57
resultado = rg.search([(lat, lon)])[0]
```

O import é lazy porque o pacote monta uma `scipy.spatial.KDTree` sobre todas as
coordenadas na primeira consulta (alguns segundos) — o resolver **deve rodar
fora da thread da UI** (`offline.py:1-5`).

Resposta de `search` (medida com `(-22.95, -43.18)`):
```python
{'country_code': 'BR', 'city': 'Rio de Janeiro',
 'latitude': -22.90642, 'longitude': -43.18223,
 'population': 6747815, 'state': 'Rio de Janeiro', 'country': 'Brazil'}
```

**Precisão**: é o **vizinho mais próximo** entre as cidades do dataset, não um
polígono administrativo. Não há raio máximo: uma coordenada no meio do oceano
devolve a cidade costeira mais próxima. Não há nível de rua nem bairro. O app
não expõe `population` nem a distância ao centroide.

**Tradução aplicada pelo app** (`offline.py:44-56`):
- `pais` ← `pais_por_codigo(country_code)` (`geolocation/paises.py:151-155`,
  tabela ISO→pt-BR estática), com fallback para `country` em inglês;
- `regiao` ← `limpar_regiao(state)` (`paises.py:227-233`, tira sufixo/prefixo
  administrativo em inglês);
- `cidade` ← `city` **sem tradução** — "Hoi An" e "Chiang Mai" são os nomes
  certos dos lugares.

**Cache**: `LocationResolver` (`geolocation/resolver.py`) arredonda a coordenada
a 3 casas (`_PRECISAO = 3`, ≈ 110 m) para formar `cache_key`, e o dataset só é
consultado uma vez por lugar. A linha em cache carrega `fonte =
"offline:reverse_geocode/2"`; trocar essa string faz o resolver **reescrever**
as linhas antigas (`resolver.py:27-33,46-54`).

**Sem ele**: `_carregar()` levanta `ImportError`, capturado pelo
`except Exception` de `resolve` (`offline.py:41-45`) → `log.warning` + `None`.
O `LocationResolver` devolve o que já estava em cache, ou `None`. A cascata
perde os passos 1 e 1b de `_evidencias_geo` e **cai para nome de pasta e
vizinhança de sessão** — nenhuma exceção sobe, nenhuma sugestão é inventada.
Também: `SuggestionEngine` aceita `resolver=None` (`engine.py:249`) e
`_geo_da_sessao` devolve `(None, (), ())` (`engine.py:669-670`), o que desliga
as regras 4 e 5 da cascata de sessão.

**Rede**: nenhuma. O pacote só baixaria de GeoNames se o `geocode.gz` fosse
removido do diretório de instalação (`GeocodeData.__init__` comenta "remove
geocode_filename to get updated data"). Invariante 4 preservado.

---

## 2. API da Anthropic (`anthropic`) — três caminhos, todos opt-in

**Versão**: `>=0.116` no extra `llm` (`pyproject.toml:36-38`); **0.116.0**
instalada. Instalação: `pip install -e ".[llm]"`.

**Credencial**: sempre do ambiente — `anthropic.Anthropic()` sem argumentos
resolve `ANTHROPIC_API_KEY` ou perfil `ant auth`. **Nunca do código nem do
repositório** (`advisor.py:107-110`, `lexico.py:132-135`,
`location_advisor.py:180-183`).

**Import é sempre tardio e dentro de `try`** — o app roda sem o pacote:
`server/jobs.py:336-346`, `genai_pasta.py:161-175`.

### 2.1 Modelo por caminho

| Caminho | Modelo | `max_tokens` | `thinking` | Unidade da chamada |
|---|---|---:|---|---|
| Advisor de cluster (`classification/advisor.py:29,136-152`) | `claude-sonnet-5` | 1024 | `{"type":"disabled"}` | uma por sessão neutra |
| GenAI de pasta (`classification/location_advisor.py:41,45,196-226`) | `claude-sonnet-5` | 16000 | `{"type":"disabled"}` | **uma por sessão inteira** (D-03) |
| Léxico de nomes (`classification/lexico.py:39,50,155-170`) | `claude-opus-5` | 16000 | `{"type":"disabled"}` | uma por lote de 200 nomes |

**`thinking` é sempre explícito**, e a razão está no código
(`advisor.py:139-145`): no Opus 4.8 omitir já significava não pensar; no Opus 5
o padrão passou a ser pensar, e `max_tokens` cobre raciocínio **mais** resposta
— com 1024 o JSON truncaria no meio. Nas três chamadas a tarefa é rotular em
poucas categorias; não é onde raciocínio longo paga.

**Todas usam structured outputs**: `output_config={"format": {"type":
"json_schema", "schema": _SCHEMA}}` com `additionalProperties: false` e todos os
campos em `required`.

**Escolha de modelo, medida** (D-048/D-049/D-060): em 104 clusters reais, Haiku
4.5 afirmava categoria onde Opus recusava por falta de evidência em **≥ 19 de 31
discordâncias**; Sonnet 5, medido depois nos mesmos 104 clusters, cai nesse
padrão **7 vezes**. Para o GenAI de pasta o argumento vale *a fortiori*
(`location_advisor.py:33-40`): um nome de pasta sozinho é entrada mais esparsa
que o cluster inteiro medido. Para o léxico, Opus **apesar** de
`docs/PLANO_IA_E_PRODUTO.md` §3 recomendar Haiku para rotulagem barata: a
recomendação vale quando a chamada é por sessão, e aqui é **uma só para o acervo
inteiro** — o custo não é o critério, a qualidade da distinção lugar × ocasião é
(`lexico.py:36-38`).

### 2.2 Contagem de tokens (`messages.count_tokens`)

**A única chamada de rede que não é `messages.create`**:
`custo_genai.contar_exato(client, corpo)` (`classification/custo_genai.py:120-146`).
Remove `max_tokens` do corpo (é parâmetro de geração, não de contagem) e devolve
`.input_tokens`. Qualquer exceção → `warning` + `0`.

**Ela transmite o payload inteiro**, e é por isso que D-079 a proibiu na prévia:
o critério "nada sai da máquina antes de confirmar" seria violado mesmo sem
gastar dinheiro. A prévia usa contagem **local** (`estimar`, `:74-117`);
`contar_exato` só roda imediatamente antes de `messages.create`, aproveitando a
mesma transmissão consentida.

### 2.3 Custo — o que está no código

`classification/custo_genai.py:26-34`:
```python
PRECO_ENTRADA_USD_POR_MTOK = 2.0
PRECO_SAIDA_USD_POR_MTOK   = 10.0
CAMBIO_USD_BRL_PADRAO      = 5.0    # taxa de referência fixa, 2026-08
```
São os preços de **Sonnet 5 promocional** (o promocional de `$2,00/$10,00`
listado em `docs/PLANO_IA_E_PRODUTO.md` §3 como válido até 31/08/2026). ⚠️ Hoje
(2026-09-19) essa janela já passou — ver Lacunas.

Estimativa de entrada, local e deliberadamente conservadora
(`custo_genai.py:41-56`): `ceil(len(json) / 3.0)` caracteres por token. O fator
3,0 é **menor** que a razão nominal de ~4 de propósito — a Anthropic desaconselha
tokenizador genérico, que subconta 15-20% em texto típico e mais em PT-BR
(acentuação) e JSON (aspas, escapes). Um custo mostrado **abaixo** do real é a
falha que importa.

Teto de saída = o `max_tokens` do corpo real (`:101`), nunca um palpite solto:
se `location_advisor.py` mudar o teto, a estimativa acompanha.

**Custo por chamada** (aritmética, não medição):
- **GenAI de pasta**: teto de saída 16.000 tokens → `16000/1e6 × $10 = $0,16` de
  teto por sessão, mais a entrada (poucos milhares de tokens → centavos). O teto
  é o número que a UI mostra; o gasto real é menor.
- **Advisor de cluster** (`docs/PLANO_IA_E_PRODUTO.md` §3, aritmética sobre
  contagem de tokens, ~400 tokens de entrada e ~120 de saída por cluster,
  1 consulta por 200 fotos num acervo desorganizado):

  | Acervo | Consultas | Opus 5 | Haiku 4.5 |
  |---|---:|---:|---:|
  | 10 mil fotos | 50 | $0,02 | $0,004 |
  | 100 mil fotos | 500 | $0,16 | $0,04 |

  Desprezível nos dois casos. A recomendação de descer de modelo **não era sobre
  dinheiro, era sobre proporção** — e foi revertida por D-060, que mediu
  qualidade.
- **Léxico**: uma chamada para o acervo inteiro (100 nomes distintos no acervo
  real). Custo de uma chamada de Opus com teto de 16.000 tokens de saída.
- **Visão remota** (**não implementada, recomendação explícita de NÃO fazer**,
  `docs/PLANO_IA_E_PRODUTO.md` §3): ~1.600 tokens de entrada por foto →
  $23–$690 por 10–100 mil fotos. Recusada não pelo custo, mas porque mandar 100
  mil fotos pessoais para fora contraria o invariante 4 "de forma que nenhum
  consentimento bem escrito compensa".

**Nenhuma medição com dinheiro real está registrada** — D-081 mediu qualidade
(4 pastas) e os relatórios de custo do script são estimativas.

### 2.4 Scripts que chamam a API (rodados pelo dono, no terminal dele)

| Script | O que mede | Protocolo |
|---|---|---|
| `scripts/medir_qualidade_advisor.py` | compara pares de modelos nos 104 clusters reais (D-048/D-049/D-059/D-060) | `clusters_neutra_104.json` no repo |
| `scripts/medir_score_llm_pasta.py` | acerto/abstenção/erro do classificador de pasta contra a verdade determinística do catálogo (D-081) | `--dry-run` primeiro, **sempre**: monta a amostra e imprime o custo sem chamar a API |
| `scripts/classificar_nomes.py` | classifica os nomes do acervo (léxico) | `--listar` mostra exatamente o que sairia, sem enviar; `--enviar` é ação separada |

Os três seguem o mesmo protocolo de D-048/D-049/D-059, escrito no cabeçalho de
`medir_score_llm_pasta.py:20-32`: **a sessão de desenvolvimento nunca manuseia
nem menciona a credencial**; `anthropic.Anthropic()` resolve o segredo sozinho a
partir do ambiente do dono; nada lê, guarda ou registra em log o valor dela; os
scripts são **somente leitura** sobre o catálogo.

### 2.5 Sem o pacote / sem credencial / sem rede

| Situação | Comportamento |
|---|---|
| `anthropic` não instalado | `from ... import ClaudeAdvisor` levanta `ImportError`, capturado → `log.warning("advisor indisponível (%s); seguindo local")` → advisor `None` (`server/jobs.py:341-346`). GenAI de pasta idem → `ClassificacaoDePastaNula` (`genai_pasta.py:167-175`) |
| `servicos_externos = false` | advisor nunca é construído (`jobs.py:337-339`); GenAI de pasta reprova no gate e levanta `RecursoDesligado` → HTTP 409 |
| Credencial ausente / rede caída / rate limit | `except Exception` em cada cliente → `warning` + `None`/`[]` (`advisor.py:153-155`, `lexico.py:172-174`, `location_advisor.py:231-234`). **A geração nunca cai** |
| `stop_reason == "refusal"` | `log.info` + `None`/`[]` (`advisor.py:158-161`, `lexico.py:176-178`, `location_advisor.py:236-238`) |
| JSON inválido | `log.warning` + `None`/`[]` (`advisor.py:166-170`, `lexico.py:183-186`, `location_advisor.py:244-248`) |
| Classificador escapa do contrato never-crash | `genai_pasta.rodar` captura e levanta `ClassificacaoIndisponivel` → HTTP 502 com cópia amigável; **o servidor continua respondendo** (`genai_pasta.py:300-308`, `server/app.py:1578-1587`) |

O resultado prático: **o app funciona 100% sem a Anthropic**. Sessões neutras
ficam sem rótulo, pastas ambíguas ficam sem proposta, e a cascata determinística
decide tudo o que consegue decidir.

---

## 3. `rawpy` / libraw — RAW e CR3

**Versão**: `>=0.27` declarada; **0.27.0** instalada. Exige `numpy>=1.26`.
`rawpy` é o binding Python de **LibRaw** (C++); a versão da LibRaw embarcada no
wheel não é exposta pelo pacote.

**Três usos, todos com o mesmo padrão de import condicional:**

### 3.1 Metadados (`metadata/purepython.py:342-398`)

```python
with rawpy.imread(str(path)) as raw:
    raw.other.timestamp   # → data_capturada        :347-348
    raw.sizes.width/height                           :349-350
    raw.lens.model        # → lente                 :356-357
    raw.sizes.flip        # → orientacao via _FLIP_PARA_ORIENTACAO  :358-359
    raw.other.iso_speed / aperture / shutter_speed / focal_length /
        artist / shot_order                          :363-373
    raw.lens.min_focal / max_focal                   :371-372
```

**É a única fonte de data para CR3**: o CR3 é ISO-BMFF e o `exifread` falha
silenciosamente nele (`purepython.py:6-11`); o libraw entende todas as
variantes. Por isso `.cr3` retorna cedo sem tentar exifread
(`purepython.py:380-382`) — economiza uma segunda leitura de ~25 MB por foto.

Medido: 65% de 300 arquivos reais ficavam sem lente e sem orientação, e **todos
eram RAW** (`docs/COBERTURA_METADADOS.md`).

**O libraw não expõe o fabricante** — daí `make`/`model` em branco nos 99 CR3 da
amostra. Inferir "Canon" do prefixo `EF` da lente seria adivinhação disfarçada de
evidência e contaminaria o modelo de confiança.

### 3.2 Miniatura (`thumbnails/generator.py:29-41`)

```python
with rawpy.imread(str(path)) as raw:
    thumb = raw.extract_thumb()
    if thumb.format == rawpy.ThumbFormat.JPEG:   return Image.open(BytesIO(thumb.data))
    if thumb.format == rawpy.ThumbFormat.BITMAP: return Image.fromarray(thumb.data)
```
**Usa a miniatura JPEG embutida**, nunca revela o RAW — revelar custaria segundos
por arquivo.

### 3.3 phash (`duplicates/phash.py:84-97`) — mesma rotina duplicada

**Sem ele** (`_HAS_RAW = False`, `purepython.py:34-41`):
- `RAW_EXTENSIONS` sai de `supported_extensions()` (`purepython.py:253-254`) e
  o scanner **nem descobre** arquivos RAW — invisíveis, sem erro;
- se `_extract_raw` for chamado assim mesmo, devolve
  `erro = "suporte RAW indisponível (rawpy/exifread não instalados)"`
  (`purepython.py:343-345`);
- `_open_source` e `_abrir` devolvem `None` (`generator.py:31-32`,
  `phash.py:86-87`) → sem miniatura, sem phash.

O import é `try/except ImportError` conjunto com `exifread`
(`purepython.py:34-41`), então **os dois caem juntos** mesmo que só um falte.
`thumbnails/generator.py:19-23` e `duplicates/phash.py:88` importam `rawpy` só
sob `if _HAS_RAW`, reutilizando a flag.

---

## 4. `pillow-heif` — HEIC/HEIF do iPhone

**Versão**: `>=0.20` declarada; **0.20.0** instalada. Licença declarada
`BSD-3-Clause`, com classifier `GPLv2` (⚠️ contradição no metadado do próprio
pacote — herda `libheif`/`libde265`, relevante para empacotamento).

**Como é chamado** (`metadata/purepython.py:25-30`):
```python
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    _HAS_HEIF = True
except ImportError:
    _HAS_HEIF = False
```

É um **plugin do Pillow**, não uma API própria: depois do `register_heif_opener`,
`Image.open("foto.heic")` funciona em todo o app. O registro acontece **uma vez,
no import de `fotoorganizer.metadata.purepython`** — e é por isso que
`thumbnails/generator.py:1-5` documenta "HEIC/HEIF registrados por pillow_heif
no import de `fotoorganizer.metadata`". Uma reconstrução que quebre essa cadeia
de import perde HEIC nas miniaturas sem nenhum erro visível.

**Sem ele**: `HEIF_EXTENSIONS = {".heic",".heif",".hif"}` sai de
`supported_extensions()` (`purepython.py:251-252`) e os arquivos ficam
invisíveis ao scanner. Nenhum erro, nenhuma linha no banco.

---

## 5. `ImageHash` — phash perceptual

**Versão**: `>=4.3` declarada; **4.3.1** instalada. Licença **2-clause BSD**.
Exige `PyWavelets`, `numpy`, `scipy`, `pillow`.

**Como é chamado** (`duplicates/phash.py:65-81`):
```python
import imagehash                      # import LOCAL, dentro da função
...
return str(imagehash.phash(img))      # :75
```
Import dentro da função de propósito — o pacote puxa `scipy` e `PyWavelets`, e o
custo só é pago quando a detecção de duplicatas roda.

`imagehash.phash` = DCT sobre a imagem reduzida a 32×32, 64 bits, devolvido em
hex por `str()`. É gravado em `MediaFile.hash_perceptual`
(`models/catalog.py:266`) e reconvertido com `int(hash, 16)` para entrar no
BK-tree (`duplicates/detector.py:209,216`).

**Fonte da imagem** (`phash.py:69-80`): tenta a **miniatura em cache** primeiro,
depois o original. A justificativa escrita é que "o phash reduz para 32×32 de
qualquer forma — o resultado é o mesmo, a leitura é menor". ⚠️ **É falso quando a
orientação EXIF importa** (M4): a miniatura passou por `exif_transpose`
(`thumbnails/generator.py:51`) e o original, não (`phash.py:97`).

**Sem ele**: `ImportError` dentro de `calcular_phash` não é capturado — o
`try/except Exception` está **dentro** do loop de fontes (`:71-80`), depois do
import na linha 67. Um `ImportError` aqui subiria para
`DuplicateDetector._completar_phashes` (`detector.py:159-167`), que **não tem
try/except**, e derrubaria o job de duplicatas. O resto do app não é afetado —
`hash_perceptual` também é usado por `estimar_offsets`
(`grouping/correlacao.py:181-183`) como chave de par-âncora, mas ali só lê a
coluna já gravada.

---

## 6. `Pillow` — decodificação de imagem

**Versão**: `>=11.0` declarada; **11.0.0** instalada.

Seis pontos de uso:

| Uso | Onde |
|---|---|
| `Image.open` + `img.size` + `img.getexif()` + `get_ifd` | `metadata/purepython.py:275-325` |
| `ExifTags.Base.*`, `ExifTags.IFD.Exif`, `ExifTags.IFD.GPSInfo`, `ExifTags.TAGS`, `ExifTags.GPSTAGS` | `metadata/purepython.py:18,285-323` |
| `IptcImagePlugin.getiptcinfo` | `metadata/purepython.py:171-198` |
| `img.getxmp()` (exige `defusedxml`) | `metadata/purepython.py:153-168` |
| `ImageOps.exif_transpose`, `img.thumbnail`, `img.convert`, `img.save` | `thumbnails/generator.py:51-62` |
| `Image.open` / `Image.fromarray` para o phash | `duplicates/phash.py:84-97` |

**`DateTimeOriginal` mora na sub-IFD Exif**, não na IFD0 — `exif.get_ifd(
ExifTags.IFD.Exif)` (`purepython.py:295`). É o erro clássico: `exif.get(
DateTimeOriginal)` na IFD0 devolve `None` em quase todo arquivo real.

**Sem ele**: o app não sobe — `Pillow` é importado no topo de
`metadata/purepython.py:18`, `thumbnails/generator.py:20` e
`duplicates/phash.py:14`, sem `try`. É dependência dura.

---

## 7. `exifread` — GPS e câmera em RAW não-CR3

**Versão**: `>=3.0` declarada; **3.5.1** instalada. Sem dependências próprias.

**Como é chamado** (`metadata/purepython.py:383-398`), apenas no ramo RAW e
apenas quando a extensão **não** é `.cr3`:
```python
with path.open("rb") as fh:
    tags = exifread.process_file(fh, details=False)
_coletar(meta.extras, "exif", tags.items())
make, model = tags.get("Image Make"), tags.get("Image Model")
lat, lat_ref = tags.get("GPS GPSLatitude"), tags.get("GPS GPSLatitudeRef")
lon, lon_ref = tags.get("GPS GPSLongitude"), tags.get("GPS GPSLongitudeRef")
```
`details=False` pula makernotes e miniaturas. Conversão DMS→decimal por
`_dms_to_decimal(lat.values, str(lat_ref))` (`:236-241`).

**Silenciado no import** (`purepython.py:36-38`):
```python
logging.getLogger("exifread").setLevel(logging.ERROR)
```
O exifread avisa "File format not recognized" para **cada** CR3; num scan grande
isso inundaria o log. A falha já é tratada por arquivo.

Todo o bloco está sob `try/except Exception: pass` (`:397-398`) — é
best-effort puro.

**Sem ele**: `_HAS_RAW = False` (import conjunto com `rawpy`,
`purepython.py:34-41`) e RAW inteiro sai do `supported_extensions`. Ou seja:
faltar só o `exifread` derruba **todo** o suporte a RAW, inclusive o que o
`rawpy` sozinho resolveria.

---

## 8. `defusedxml` — XMP embutido

**Versão**: `>=0.7` no extra `xmp` **e** no extra `dev`
(`pyproject.toml:25-34`); **0.7.1** instalada.

**Não é chamado diretamente pelo app.** O Pillow só analisa o pacote XMP quando
`defusedxml` está importável — é XML de origem não confiável dentro do arquivo
do usuário, e com razão (`pyproject.toml:25-28`). O app apenas **detecta a
presença**:

```python
# metadata/purepython.py:139-152
try:
    import defusedxml  # noqa: F401
    _HAS_XMP = True
except ImportError:
    _HAS_XMP = False
    log.info("XMP indisponível: instale 'defusedxml' para ler palavras-chave, "
             "direitos e legenda de arquivos editados. IPTC e EXIF seguem normais.")
```

E `_coletar_xmp` retorna imediatamente quando `_HAS_XMP` é falso
(`:156-160`) — o motivo é explícito: sem o guard, o Pillow avisa **por arquivo**,
e em 500 mil fotos isso é meio milhão de linhas dizendo a mesma coisa.

**Sem ele**: XMP embutido não é lido. Perde-se `xmp:Rating` (2.727 ocorrências
no acervo), `dc:creator` (658), `dc:subject`/`lr:hierarchicalSubject` (638) e os
campos `crs:` de revelação do Lightroom (`docs/INVENTARIO_DE_SINAIS.md` §2). EXIF
e IPTC seguem normais. **A degradação é silenciosa** por construção — um log no
import, nada por arquivo.

Nota: com o `ExifToolExtractor` ativo, o XMP vem pelo exiftool e não depende de
`defusedxml`. A dependência só morde no caminho puro-Python.

---

## 9. `exiftool` — binário externo, não é dependência Python

**Versão**: não declarada em lugar nenhum. Instalada nesta máquina:
**13.55** em `/opt/homebrew/bin/exiftool`. Descoberto em runtime por
`shutil.which("exiftool")` (`metadata/exiftool.py:284,308`).

**Como é chamado** (`metadata/exiftool.py:322-332`): processo **persistente**
```
exiftool -stay_open True -@ -
```
com os argumentos de cada leitura escritos no stdin, um por linha, terminados
por `-execute`; a resposta termina em `{ready}` (`_FIM`, `:43`).

Argumentos por arquivo (`:351-358`): `-j` (JSON), `-G` (grupo na chave),
`-c %+.8f` (coordenada decimal com sinal), `-charset filename=utf8`,
`<caminho>`, `-execute`.

**Por que `-stay_open`** (`:13-17`): um `exiftool <arquivo>` por foto paga
~200 ms de partida do Perl. Num scan de dezenas de milhares é a diferença entre
minutos e horas.

**Segurança (invariante 5)** (`:19-23`): sem `shell=True`, argumentos em lista,
`stderr=DEVNULL`, caminho validado com `is_file()` (`:396-400`), e caminho com
`\n`/`\r` **rejeitado antes** — quebraria o protocolo delimitado por linha
(`:393-395`). Um lock de instância serializa o acesso.

**Timeout**: `_TIMEOUT_S = 30.0`, imposto por `threading.Timer(30, proc.kill)`
(`:44,368-369`). É a única espera potencialmente infinita do scan inteiro: se o
exiftool emudecer diante de um arquivo, o `readline` não tem fim e a fila
congela em RODANDO. O vigia mata, o readline devolve EOF, e o fallback
puro-Python responde por aquele arquivo.

**Ganho medido** (`metadata/__init__.py:22-30`, `exiftool.py:5-11`): num CR3 de
acervo real, **361 tags** (386 em outra medição no docstring) contra 8 do
libraw; e é o exiftool quem entrega `Make`/`Model` nos 2.949 CR3 que ficavam sem
— sem câmera não há correção de deriva de relógio nem "outra origem" na herança
de GPS.

**Sem ele**: `criar_extrator` escolhe o `PurePythonExtractor`
(`metadata/__init__.py:31-34`) e loga `"metadados: exiftool ausente — usando
extrator puro-Python"`. **O app funciona igual, com menos sinal**: perde sidecar
XMP, palavras-chave unificadas dos quatro formatos, `OffsetTimeOriginal` →
`data_capturada_utc`, subsegundo, `identidade_de_captura` de Live Photo, e
`make`/`model` em CR3.

⚠️ **Sem CI, três suítes passam verde sem executar** (M6 da auditoria):
`tests/test_exif_write_executor.py:47-49`, `tests/test_exif_write_writer.py:31`
e `tests/test_exiftool_extractor.py:17` usam `skipif` quando o binário não
existe.

`supported_extensions()` do `ExifToolExtractor` **delega ao fallback**
(`:311-316`): o exiftool entende mais formatos do que o app trata, e alargar
aqui faria o scanner descobrir arquivo que o resto do sistema não sabe tratar.

---

## 10. `xxhash` — assinatura rápida

**Versão**: `>=3.4` declarada; **3.8.1** instalada. Sem dependências.

**Como é chamado** (`security/hashing.py:20-30`):
```python
h = xxhash.xxh3_64()
h.update(size.to_bytes(8, "little"))
h.update(primeiros 64 KiB)
if size > 128 KiB: h.update(últimos 64 KiB)
return f"xxh3:{h.hexdigest()}"
```

Não é criptográfico e não pretende ser: serve para detectar mudança e apontar
**candidatos** a duplicata. Igualdade de conteúdo só é afirmada com SHA-256
completo (`hashlib`, stdlib, `:33-38`), calculado sob demanda.

**É a chave do cache de miniaturas** (`thumbnails/cache.py:22-24` recebe
`media.hash_rapido`) e o índice de par-âncora da correlação
(`grouping/correlacao.py:181`).

**Sem ele**: `security/hashing.py:13` importa no topo, sem `try` — o app não
sobe.

---

## 11. `cryptography` (Fernet) — embeddings faciais

**Versão**: `>=42.0` declarada; **49.0.0** instalada.

**Como é chamado** (`security/crypto.py:19,37,56`): `Fernet.generate_key()` e
o par cifra/decifra. A chave vive no **Keychain do macOS** via
`subprocess.run(["security", "find-generic-password", ...])` — argumentos em
lista, `timeout=10`, **nunca `shell=True`** (`crypto.py:44-60`), com fallback
para arquivo `0600` no diretório de dados (`FileKeyStore`, `:30-42`). Serviço
`FotoOrganizer`, conta `embeddings-key` (`:23-24`).

**Estado**: pronto e **sem consumidor** — não há detector facial, as tabelas
`face_embeddings`/`face_occurrences`/`people` estão vazias, e
`PrivacySettings.reconhecimento_facial` (`config/settings.py:63`) nunca é lida
por nenhum código. B5 da auditoria registra `crypto.py:47-78` sem teste próprio
(há cobertura indireta em `tests/test_faces_privacy.py`).

**Limitação declarada** (`docs/PRIVACIDADE.md`, "Limitações honestas"): protege o
banco em repouso (backup copiado, disco acessado por outra conta), **não** contra
código rodando na sessão desbloqueada do usuário. Proteções complementares reais:
FileVault e senha de sessão. "O app não promete mais do que isso."

---

## 12. Transitivas que importam

| Pacote | Versão | Quem exige | Por que importa |
|---|---|---|---|
| `numpy` | 2.5.1 | `reverse-geocode`, `ImageHash`, `rawpy>=1.26` | peso no empacotamento (~30 MB) |
| `scipy` | 1.18.0 | `reverse-geocode` (KDTree do geocoder), `ImageHash` | peso grande (~60 MB); **é o que faz o geocoder demorar alguns segundos no primeiro uso** |
| `PyWavelets` | — | `ImageHash` | só para `whash`, que o app não usa |

Nenhuma delas é declarada em `pyproject.toml`. Uma reconstrução que troque
`reverse-geocode` por outro geocoder e `ImageHash` por um phash próprio
eliminaria `scipy` e `PyWavelets` do bundle.

---

## 13. O que NÃO é integração deste domínio

Registro explícito para a reconstrução não procurar o que não existe:

- **Nenhum modelo de visão local.** `vision/` é `Protocol` + `NullVisionProvider`
  (`vision/stub.py`). O extra `[visao]` (~150–400 MB) é decisão em aberto
  (`docs/AUDITORIA_IA.md`, "O que fica em aberto para o dono").
- **Nenhum detector facial.** `faces/` é `Protocol` + `NullFaceProvider`. Nenhuma
  dependência de detecção (`dlib`, `insightface`, `face_recognition`) está no
  `pyproject.toml`.
- **Nenhum provider de geocodificação externo.** A origem
  `geocoding_externo: 0.75` está na tabela de confiança
  (`classification/confidence.py:17`) e o `Protocol` está pronto
  (`geolocation/base.py:26-36`), mas **nenhuma classe além de `OfflineGeocoder`
  o implementa**. Nenhum cliente HTTP de geocodificação existe.
- **Nenhuma biblioteca de fuso horário.** `timezonefinder`, `pytz` e `geo-tz`
  foram explicitamente descartados (D-07, `geolocation/timezones.py:7-9`) — a
  tabela `TZ_POR_PAIS` é estática, e `zoneinfo` (stdlib) só aparece no teste que
  valida os identificadores (`tests/test_timezones.py:18`).
- **Nenhuma telemetria, nenhuma verificação de atualização, nenhuma conta.**
  `docs/PRIVACIDADE.md`: "O app não coleta uso, não liga para casa, não tem
  conta."

---

## Lacunas e incertezas

1. **Data do snapshot do dataset GeoNames é desconhecida.** `reverse-geocode
   1.6.6` embarca `geocode.gz` (3.458.676 bytes) sem declarar quando foi gerado.
   `FONTE = "offline:reverse_geocode/2"` versiona a *nomenclatura do app*, não o
   dataset — atualizar a lib mudaria respostas de geocodificação **sem
   invalidar o cache** em `locations`. Não sei se a reconstrução deve embutir a
   versão do pacote na string `fonte`.

2. **Licença LGPL do `reverse-geocode` vs. empacotamento.** É a única dependência
   copyleft do domínio. `docs/EMPACOTAMENTO.md` não foi lido nesta auditoria.
   Não sei se há avaliação registrada sobre distribuir um `.app` assinado com
   ela embutida. `pillow-heif` tem contradição no próprio metadado
   (`License: BSD-3-Clause` × classifier `GPLv2`, herdado de `libheif`) e merece
   a mesma checagem.

3. **Preços da API estão em valores promocionais possivelmente vencidos.**
   `PRECO_ENTRADA_USD_POR_MTOK = 2.0` / `PRECO_SAIDA_USD_POR_MTOK = 10.0`
   (`custo_genai.py:26-27`) são o promocional de Sonnet 5 que
   `docs/PLANO_IA_E_PRODUTO.md` §3 datou como "até 31/08/2026". Hoje é
   2026-09-19. Se o preço de tabela voltou a $3,00/$15,00, **a prévia mostra 33%
   a menos do que o real** — exatamente a falha que o fator conservador de
   tokens existe para evitar. Não verifiquei o preço vigente (não consultei
   rede) e **não sei** se alguém já revisou.

4. **`CAMBIO_USD_BRL_PADRAO = 5.0` é fixo e datado de 2026-08.** O módulo não
   busca cotação (decisão consciente: não abrir uma segunda saída de rede). O
   parâmetro `cambio_usd_brl` de `estimar()` existe para o endpoint repassar uma
   taxa mais recente, mas `genai_pasta.estimar_custo` sempre passa
   `CAMBIO_USD_BRL_PADRAO` (`genai_pasta.py:245-248`). O ponto de extensão nunca
   foi usado.

5. **Nenhuma medição de custo real registrada.** Todos os números de custo do
   domínio são aritmética sobre contagem estimada de tokens. `contar_exato`
   existe e alimenta o resumo pós-execução, mas não há registro de execução real
   com o total gasto. O `custo_real` só é calculado quando o classificador expõe
   `_client` (`genai_pasta.py:250-286`, acesso a atributo privado).

6. **Versão mínima do exiftool não é verificada.** O código assume `-stay_open`,
   `-j`, `-G`, `-c %+.8f`, `-charset filename=utf8` e os nomes de grupo
   `XMPSidecar`/`Composite`/`MakerNotes`. `shutil.which` só testa existência
   (`exiftool.py:307-309`). Um exiftool muito antigo passaria no teste e
   falharia no protocolo, caindo no fallback silenciosamente a cada arquivo. Não
   sei qual é a versão mínima real.

7. **Versão da LibRaw embarcada não é rastreável.** `rawpy 0.27.0` não expõe a
   versão da LibRaw, e o suporte a CR3 (e a modelos de câmera novos) depende
   dela. O comportamento de `raw.other.timestamp` em CR3 — que é a base da data
   de 63% do acervo no caminho puro-Python — está preso a essa versão invisível.

8. **`ImportError` de `imagehash` não é tratado.** O import é local a
   `calcular_phash` (`phash.py:67`), **fora** do `try/except` que cobre o loop de
   fontes (`:71-80`), e `DuplicateDetector._completar_phashes`
   (`detector.py:159-167`) não tem guarda. Num ambiente sem `ImageHash`, o job de
   duplicatas quebra com traceback em vez de degradar. Como o pacote é core (não
   extra), isso só aconteceria numa instalação quebrada — mas o contrato
   "never-crash" dos outros integrantes não vale aqui.

9. **Quem depende de quem no import de HEIC não está documentado.**
   `pillow_heif.register_heif_opener()` roda no import de
   `fotoorganizer.metadata.purepython`, e `thumbnails/generator.py` depende disso
   implicitamente (importa `RAW_EXTENSIONS` e `_HAS_RAW` do mesmo módulo, o que
   por acaso dispara o registro). Um refactor que quebre essa cadeia perde HEIC
   nas miniaturas **sem nenhum erro** — só placeholders. Não há teste que prenda
   esse acoplamento.
