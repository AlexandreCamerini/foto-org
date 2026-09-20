# 04 — Pipelines: como o dado flui

> Parte do mapa de reconstrução. Duas partes escritas por agentes de domínio distintos:
> **A — arquivos** (scan, alcance, fontes externas, duplicatas por hash, operações físicas,
> escrita EXIF, segurança, jobs) e **B — imagem e inferência** (metadados, thumbnails,
> evidências e confiança, cascata de classificação, agrupamento, herança de GPS, geolocalização,
> duplicatas visuais, GenAI, stubs). Constantes numéricas estão com nome e valor em cada etapa.

---

# Parte A — Arquivos

# 04 — Pipelines do domínio ARQUIVOS

Contrato por etapa: entrada → processamento → saída, limites numéricos,
checkpoint/retomada, degradação e audit log. Escopo: `scanner/`, `sources/`,
`duplicates/` (níveis 1-2), `operations/`, `exif_write/`, `security/`,
`server/jobs.py`.

Os cinco invariantes que **nenhuma** etapa abaixo viola:
1. catalogação é somente leitura;
2. operação física só existe como plano até aprovação explícita, e a
   execução é copiar, nunca mover;
3. nunca sobrescrever destino; hash antes e depois; tudo no audit log;
4. subprocesso sem `shell=True`, argumentos em lista, caminho validado;
5. erro de leitura nunca derruba a varredura — registrar e continuar.

A única escrita autorizada em arquivo original é a de localização em campo
vazio (D-075), etapa 6.

---

## 1. Descoberta (`fotoorganizer/scanner/discovery.py`)

**Entrada**: `root: Path`, `DiscoveryConfig(extensoes, incluir_ocultos,
seguir_symlinks, padroes_ignorados)` (`:119-124`), e opcionalmente uma
lista `erros: list[Path]` passada por referência.

**Saída**: `Iterator[Path]` de arquivos elegíveis, em ordem de
`sorted(os.scandir(dir))` por nome dentro de cada diretório, com a pilha
consumida por `pop()` (ou seja, profundidade, ordem inversa por nível).

### Extensões aceitas

Vêm de `extractor.supported_extensions()`
(`scanner/scanner.py:209`). O `ExifToolExtractor` **delega ao fallback**
(`metadata/exiftool.py:311-315`) de propósito: o exiftool entende mais
formatos do que o app sabe tratar, e a lista de quem manda continua sendo a
do fallback.

| Grupo | Extensões | Condição |
|---|---|---|
| Pillow (`purepython.py:43`) | `.jpg .jpeg .png .tif .tiff .webp .bmp .gif` | sempre |
| Vídeo (`:51`) | `.mov .mp4 .m4v .avi` | sempre — o `.mov` é metade de cada Live Photo e doa GPS |
| HEIF (`:44`) | `.heic .heif .hif` | só com `pillow-heif` importável (`_HAS_HEIF`) |
| RAW (`:45`) | `.dng .cr2 .cr3 .nef .arw .raf .orf .rw2` | só com `rawpy` importável (`_HAS_RAW`) |

Degradação: sem `pillow-heif` ou sem `rawpy`, aqueles arquivos **somem da
descoberta** — não entram no catálogo com erro, simplesmente não são
oferecidos.

### Regras de travessia

| Regra | Onde | Comportamento |
|---|---|---|
| Symlinks | `:174-182` | `entry.is_dir(follow_symlinks=config.seguir_symlinks)` e, redundante, `if is_symlink and not seguir_symlinks: continue`. **Desligado por padrão** (invariante 5) |
| Ciclos | `:147,153-157` | conjunto de `(st_dev, st_ino)` já visitados |
| Ocultos | `:168-169` | nome começando com `.` é pulado, salvo `incluir_ocultos` |
| `padroes_ignorados` | `:170-171,127-131` | `fnmatch` contra o **nome** e contra o **caminho relativo à raiz** |
| Lixo de sistema | `:20,183-184` | arquivos `thumbs.db`, `desktop.ini`, `.ds_store` |
| Diretórios-lixo | `:21,177` | `@eadir`, `.thumbnails` |
| Pastas de código | `:29-46,91-94,177` | nomes `node_modules, bower_components, __pycache__, site-packages, deriveddata, pods, venv, vendor, target, cache, caches` e sufixos `.xcassets .imageset .appiconset .colorset .dataset .xcodeproj .xcworkspace .playground .lproj .framework .bundle .app`. **Não se desce** neles: um ícone de app não tem data nem GPS para doar, e num acervo real `BoraChurrascoRio.imageset` batizou um evento com 1.314 fotos de verdade |

### Pacotes de biblioteca de foto

`SUFIXOS_DE_PACOTE` (`:56-70`): `.photoslibrary`, `.photolibrary`,
`.migratedphotolibrary`, `.aplibrary`, `.lrdata`.

Casamento **por sufixo**, não por nome exato — o nome real é
`<Qualquer Nome>.photoslibrary`, e enquanto estavam em `JUNK_DIRS`
(comparação exata) nunca casavam: um acervo real entrou com 45.822
miniaturas internas catalogadas como foto.

**Desce-se** neles de propósito: os derivados carregam GPS que o catálogo
externo não reporta. O que muda é o **papel** — entram como testemunha
(`MediaRole.SINAL`), não como acervo (invariante 8, D-024).

`dentro_de_pacote(caminho)` (`:97-116`) olha o caminho **inteiro**, não só o
pai (os derivados ficam em `.../resources/derivatives/masters/`). Exceção:
em `SUFIXOS_COM_ORIGINAL_PROPRIO` (`:76-81`, todos menos `.lrdata`), se o
segmento **imediatamente** abaixo da raiz do pacote for `originals` ou
`masters` (`_PASTAS_DE_ORIGINAL_NO_PACOTE`, `:88`), o arquivo é **original**
e volta a ser acervo. Sem essa exceção, 21.387 arquivos eram rebaixados a
testemunha, 8.419 deles sem cópia em lugar nenhum.

`.lrdata` fica fora dessa exceção: por dentro é sempre pré-visualização
(14.755 Smart Previews eram 57% do que o app dizia ser organizável, todos
ilegíveis; rebaixados e não pulados porque carregam 1.113 coordenadas).
`.lrlibrary` **não** entra na lista — aquele guarda original.

### Degradação

`OSError` ao `stat()`/`scandir()` de um diretório: `log.warning`, append em
`erros` (se passado) e **`continue`** (`:159-163`). `OSError` por entrada:
idem (`:187-190`).

O parâmetro `erros` existe porque o generator **só para de produzir** dali
pra frente, sem levantar exceção: um NAS que cai ou uma subpasta que perde
permissão é indistinguível de "a árvore acabou" — e um scan que confia
nisso marcaria arquivo de verdade como offline (`:137-145`).

Testes: `tests/test_discovery.py::test_nao_atravessa_symlink_e_evita_ciclo`,
`::test_diretorio_com_erro_e_reportado_em_erros`,
`::test_pacote_reconhecido_em_qualquer_nivel_do_caminho`,
`::test_original_dentro_do_pacote_nao_e_rebaixado`,
`::test_smart_previews_do_lightroom_entram_como_testemunha`,
`::test_pasta_de_codigo_nao_e_varrida`.

---

## 2. Scan / indexação (`fotoorganizer/scanner/scanner.py`)

**Entrada**: `CatalogScanner(session_factory, extractor, ScannerSettings,
thumb_cache=None).scan_source(caminho, progress=None, control=None,
padroes_ignorados=(), reprocessar=False)` (`:160-196`).

**Saída**: `(ScanSession, ScanMetrics)`. No banco: linhas em `media_files`
e `metadata_entries`, `ScanSession` fechada, `MediaFile.arquivo_offline`
atualizado. No disco: **nada** (invariante 1) — exceto miniaturas no cache.

### Limites numéricos

| Constante | Valor | Onde | Significado |
|---|---|---|---|
| `SCANNER_VERSION` | `"1.0"` | `:57` | gravado em `ScanSession.versao_scanner` |
| `_BATCH_SIZE` | `200` | `:58` | itens entre commits/checkpoints |
| `_MTIME_TOLERANCE` | `1e-6` s | `:59` | tolerância do mtime na comparação incremental |
| `_EXTRACAO_TIMEOUT_S` | `120.0` | `:60-64` | teto por arquivo para EXIF+hash+thumbnail. Folgado: um RAW de 25 MB num NAS frio leva segundos. O que passar vira erro de leitura — a foto entra sem metadado e a varredura segue |
| `_LOTE_SUMICO` | `500` | `:65-68` | tamanho do lote do `UPDATE ... IN (...)` que marca sumiço (o limite de variáveis do SQLite estoura com tudo de uma vez) |
| `janela` | `max(workers*2, 4)` | `:231` | extrações em voo simultâneas |
| `max_workers` | `max(settings.workers, 1)` | `:258` | pool `scan-extract` |

### Paralelismo com escritor único

`ThreadPoolExecutor(thread_name_prefix="scan-extract")` (`:257-260`) roda
`_extrair` (`:404-419`) — **só leitura de arquivo, nada de DB**: extrai
metadado, calcula `quick_signature` e, se houver `thumb_cache` **e o
arquivo não estiver dentro de pacote**, deixa a miniatura pronta.

Justificativa: ler EXIF/RAW e hashear é o custo dominante do primeiro scan
(libraw ~0,4 s por RAW) e Pillow/libraw/xxhash soltam o GIL. **O banco
continua sendo escrito por uma única thread** (a do scan), na ordem de
descoberta (`:9-12`).

`consumir(max_restantes)` (`:234-255`) drena a `deque` de pendentes:
`futuro.result(timeout=_EXTRACAO_TIMEOUT_S)` → `_gravar` → contadores. Toda
exceção vira `metrics.erros += 1` + `log.error`, **nunca** derruba o scan.
A cada `_BATCH_SIZE` itens, `_checkpoint`.

Testemunha **não** ganha miniatura (`:414-418`): ela nunca aparece na grade,
e a miniatura era quase só custo — 2 GB de cache e RAW inteiro lido pelo SMB
no acervo real. O phash das duplicatas ainda a alcança sob demanda.

### Incremental

`_carregar_conhecidos` (`:384-402`) traz **numa query só** o índice
`caminho → (tamanho, mtime_ts, inode)` de toda a fonte. Em 30 mil fotos
isso substituiu 30 mil SELECTs.
`_unchanged_sig` (`:525-534`): igual se `tamanho`, `inode` e `mtime`
(tolerância `1e-6`) baterem. `mtime` nulo nunca conta como inalterado.
`reprocessar=True` (`:168-171`) ignora a assinatura e relê tudo — porta
necessária quando a extração passa a capturar algo novo.

### `_ts` e as datas

`_ts(epoch)` (`:117-119`) = `datetime.fromtimestamp(epoch,
tz=timezone.utc).replace(tzinfo=None)` — **UTC naive**, forma canônica do
SQLite. Usado em `mtime` e `ctime` (este a partir de `st_birthtime` no
macOS, com fallback `st_ctime`, `:448-450`).

`data_capturada_utc` (`:463-466`): `None` se não há hora de parede; senão
`meta.data_capturada_utc or meta.data_capturada`. Sem fuso vindo do arquivo
— o caso de todo scan hoje — os dois ficam iguais, e a igualdade é como se
diz "não sei o fuso".

> **Achado M1 (MÉDIO)**: o motor de classificação usa `data_capturada or
> mtime` em quatro pontos (`engine.py:469,501,571,585`), misturando hora de
> parede local com UTC naive. 33,3% de 53.967 registros têm delta múltiplo
> exato de 1 h.

### Checkpoint, pausa e cancelamento

`ScanControl` (`:89-111`): dois `threading.Event`. `aguardar_se_pausado()`
dorme em fatias de 50 ms enquanto pausado e não cancelado. Consultado no
topo do laço (`:264-267`).

`_checkpoint` (`:342-355`) grava contadores + `{"ultimo_caminho": …}` e faz
`session.commit()`. Ao final, um checkpoint com `checkpoint_path=None`.

Cancelamento: `scan.status = PAUSADO` (`:296`), mas **drena o que já estava
em voo** (`consumir(0)`, `:292-294`) para não jogar fora extração já paga.
Retomada = novo scan no mesmo caminho: re-varre e pula os inalterados ao
custo de um `stat()` cada.

Morte do processo: a sessão fica `RODANDO` para sempre e o catálogo mente.
`reconciliar_orfas` (`:122-144`), chamado no boot do servidor, carimba
`INTERROMPIDO` + `finalizado_em`. Seguro por construção: nenhum job pode
estar rodando antes de o servidor existir.

### Marcação de sumiço — três guardas

No fim da passada (`:302-334`), o que estava em `conhecidos` e não em
`vistos` seria "sumiu". Três guardas antes de escrever:

1. **cancelado** → não marca nada (`:302-303`). Um scan interrompido viu
   poucos caminhos; a diferença explodiria.
2. **`diretorios_com_erro` não vazio** → não marca nada, só `log.warning`
   (`:304-316`). O walk não viu a árvore inteira. A reconciliação cobre
   depois.
3. **filtro de referência externa + `Path(c).exists()`** (`:318-330`): um
   caminho pode ter saído do walk porque `padroes_ignorados` ou a lista de
   extensões mudou. Só marca quem de fato não existe. **Não substitui** a
   guarda 2: sob pasta sem permissão de leitura, `exists()` também devolve
   `False`.

`_marcar_sumidos` (`:357-382`) faz `UPDATE ... SET arquivo_offline=True` em
lotes de 500, com `arquivo_ausente.is_(False)` e
`caminho NOT LIKE '%://%'` **redundantes de propósito** — última linha de
defesa contra marcar uma referência de catálogo externo como sumida.

Caminho de volta: `_gravar` põe `arquivo_offline=False` (`:479`) — chegar
ali prova que o arquivo existe agora.

### Identidade de fonte

`_get_or_create_source` (`:536-551`): busca por caminho exato; se não
achar, `_fonte_equivalente` (`:553-575`) compara por `samefile` (dispositivo
+ inode), que resolve caixa, symlink e caminho equivalente de uma vez. O
APFS não distingue maiúscula, e varrer `/users/acamerini` depois de
`/Users/acamerini` criava duas fontes "acamerini" (93.400 e 695 fotos) lado
a lado. Fonte cujo caminho não existe agora é **pulada**: criar uma fonte a
mais é recuperável, fundir duas pastas distintas num registro só não é.

### Métricas

`ScanMetrics` (`:71-86`): `vistos, indexados, pulados, erros,
bytes_processados`, `segundos_decorridos`, `arquivos_por_segundo`.
Callback `progress(metrics, caminho)` a cada item consumido ou pulado.

### Fonte indisponível

`scan_source` checa `caminho.is_dir()` antes de tudo (`:184-191`): se falso,
`ScanSession.status = ERRO`, `checkpoint = {"motivo": "volume ou pasta
indisponível"}`, `log.warning`, e devolve sem tocar em nada.

### Audit log

O scan **não** escreve em `audit_log` — a trilha dele é a `ScanSession`.

Testes-chave: `tests/test_scanner.py::test_corrompido_nao_interrompe_scan`,
`::test_extracao_que_excede_o_teto_vira_erro_e_o_scan_segue`,
`::test_cancelamento_e_retomada`,
`::test_scan_cancelado_nao_marca_sumico_em_massa`,
`::test_diretorio_ilegivel_no_meio_do_walk_nao_marca_sumico`,
`::test_subpasta_sem_permissao_real_nao_marca_sumico`,
`::test_referencia_externa_no_mesmo_source_nunca_vira_offline`,
`::test_sessao_rodando_orfa_vira_interrompida_no_boot`,
`::test_testemunha_nao_ganha_thumbnail`.

---

## 3. Reconciliação de alcance (`fotoorganizer/scanner/reconciliacao.py`)

Laço independente que mantém `arquivo_offline` honesto sem esperar por um
re-scan manual. Mais barato que um scan completo: só `Path.exists()` por
linha, **sem reler metadado nem recalcular hash**.

**Entrada**: `reconciliar(session_factory, *, orcamento_segundos=30.0,
orcamento_percentual=0.20, control=None)` (`:100-238`).
**Saída**: `ResultadoReconciliacao(verificados, marcados_offline,
marcados_online, ciclo_concluido, cancelado)` (`:61-73`).

### Nota sobre `ALCANCES`

`ALCANCES` **não** vive aqui — é o mapa de filtros de alcance da grade, em
`fotoorganizer/repositories/media.py:90-94`, com três chaves:

| Chave | Rótulo | Significado |
|---|---|---|
| `tudo` | acervo inteiro, ao alcance ou não | sem filtro |
| `organizaveis` | acervo com o arquivo ao alcance agora | `MediaFile.organizavel` + fonte disponível |
| `faltantes` | o resto: sem arquivo, fora de alcance ou não é acervo | complemento |

Validado nas rotas `/api/midia`, `/api/midia/linha-do-tempo` (422 quando
desconhecido) e exposto por `/api/midia/alcances`.

### Elegibilidade

`_condicoes_elegiveis()` (`:76-87`), em SQL:
`Source.disponivel IS TRUE` **e** `MediaFile.arquivo_ausente IS FALSE`
**e** `MediaFile.caminho NOT LIKE '%://%'`.

O padrão `'%://%'` vem de `PADRAO_SQL_REFERENCIA_EXTERNA`
(`scanner/elegibilidade.py:22`) — **um só símbolo** para os dois lados
(Python no scan, SQL aqui) nunca saírem de sincronia. Referência de
catálogo externo não é caminho de filesystem; `Path.exists()` nela não tem
sentido, e tratá-la como se tivesse já causou bug real
(`elegibilidade.py:1-14`).

### Orçamento

| Constante | Valor | Onde |
|---|---|---|
| `_ORCAMENTO_SEGUNDOS_PADRAO` | `30.0` s | `:53` |
| `_ORCAMENTO_PERCENTUAL_PADRAO` | `0.20` (20% do elegível) | `:54` |
| `_TETO_DURO_POR_CHAMADA` | `20_000` linhas | `:55-58` |

`teto_linhas = min(20_000, max(1, int(total_elegivel * percentual)))`
(`:145-148`). A consulta pede `teto_linhas + 1` (`:152-160`) para saber, sem
uma segunda contagem, se sobrou trabalho além do teto.

O laço para pelo que vier primeiro: tempo (`:187-189`), cancelamento
(`:190-192`) ou fim do lote.

### Checagem barata de fonte

Antes de gastar um `exists()` por arquivo, confere **uma vez por fonte
presente no lote** (não por linha) se a raiz responde (`:165-176`).
`Source.disponivel` já filtra o que o scan sabe; esta checagem cobre o
buraco entre passadas — um HD que caiu **depois** do último scan e ainda
consta `disponivel=True`.

Quando a raiz não responde, as linhas daquela fonte são puladas **e o
checkpoint trava** (`checkpoint_travado`, `:185,193-195,204-205`): elas
continuam elegíveis na próxima passada em vez de ficarem presas atrás do
cursor, ao custo de raramente reconferir o que veio depois delas.

### Checkpoint e ciclo

Cursor = `MediaFile.id`, ordem crescente, começando em `id > ultimo_id`.
Guardado em `application_settings["reconciliacao_checkpoint"]` via
`SettingsRepository` — **de propósito não** em `ScanSession`
(`:12-19`): `RetomarScan.tsx` lista sessão `PAUSADO` como "varredura
interrompida, clique para retomar" e dispara um scan de PASTA de verdade;
uma passada parcial de reconciliação ali chamaria o comando errado.

`ciclo_concluido = not (ha_mais_depois_deste_lote or
sobrou_no_lote_por_tempo or checkpoint_travado)` (`:211-215`). Quando
concluído, grava `{"ultimo_media_id": 0, "concluido_em": <iso>}` — a próxima
chamada recomeça o ciclo em vez de ficar presa no fim para sempre.

### Marcação

Por linha (`:196-203`): existe e estava offline → `arquivo_offline=False`,
`marcados_online++`; não existe e não estava offline → `True`,
`marcados_offline++`. **Nunca apaga registro nem metadado** (invariante 8).
Um único `session.commit()` no fim do lote (`:209`).

**Audit log**: nenhum. A trilha é o `log.info` final (`:225-231`) e o
resultado devolvido ao chamador.

Gatilhos: `POST /api/reconciliacao` (sem consumidor na UI hoje — achado B8)
e `fotoorganizer verificar-arquivos [--segundos N]`.

Testes: `tests/test_reconciliacao.py::test_referencia_de_catalogo_externo_nunca_e_tocada`,
`::test_checkpoint_processa_parte_e_retoma_na_proxima_chamada`,
`::test_orcamento_de_tempo_para_a_passada_no_meio`,
`::test_cancelamento_no_meio_da_passada_salva_checkpoint_parcial`,
`::test_fonte_sumida_no_meio_do_lote_nao_gasta_exists_por_linha`.

---

## 4. Fontes externas (`fotoorganizer/sources/`)

### 4.1 Contrato (`base.py`)

`ExternalCatalogProvider` é `Protocol` (`:71-85`): `tipo: SourceType`,
`raiz: Path`, `apelido: str`, `iter_assets() -> Iterator[ExternalAsset]`.

`ExternalAsset` (`:21-68`) — campos e o que significam:
`caminho` (aponta para o arquivo real **quando ele deve ser LIDO**; `None`
= é REFERÊNCIA e nenhum byte de imagem é aberto) · `referencia` (identidade
estável no lugar do caminho) · `caminho_original` (onde o catálogo externo
acredita que o arquivo está — a única pista de LUGAR numa referência; não é
aberto) · `nome`, `tamanho` (informação **do** arquivo, da entrada de
diretório, não conteúdo dele) · `data_capturada` (parede, naive) ·
`data_capturada_utc` · `gps_lat`, `gps_lon` · `titulo`, `descricao`,
`favorito`, `albuns`, `pessoas`, `palavras_chave`.

### 4.2 Apple Fotos (`apple_photos.py`)

**Entrada**: `ApplePhotosProvider(biblioteca=None)`; default
`~/Pictures/Photos Library.photoslibrary` (`:28-30`).
**Processamento**: `import osxphotos`; `osxphotos.PhotosDB(str(biblioteca))`;
itera `db.photos(movies=True)`.

`movies=True` de propósito (`:152-156`): numa biblioteca de iPhone o vídeo é
metade de cada Live Photo e carrega GPS e horário quando a foto ao lado não
carrega — doador de correlação. Excluí-lo descartava sinal e quebrava o par
foto+vídeo.

`_asset_de(photo)` (`:65-111`), duck-typed (testável com fakes):
- sem `path` **e** sem `uuid` → descartado (`sem_identidade`);
- sem `path` mas com `uuid` → **referência** (numa biblioteca em "Otimizar
  armazenamento" isso é a maioria, e é delas que vem o GPS que localiza as
  fotos de câmera);
- `photo.date` vem **com fuso** (o Apple Fotos guarda `ZTIMEZONEOFFSET`/
  `ZTIMEZONENAME` por foto): `data_capturada_utc` recebe o absoluto e
  `data_capturada` a hora de parede naive. É o único fuso medido que este
  acervo tem, e fuso descartado não volta por inferência (D-038);
- importa `title`, `description`, `favorite`, `albums`, `persons`,
  `keywords` (via `getattr`, porque o provider é duck-typed).

**Nunca escreve** na biblioteca; nada de rede.

**Degradação**:
- `osxphotos` ausente (extra `apple` não instalado) → `ApplePhotosError`
  com a instrução `pip install fotoorganizer[apple]` (`:133-137`).
- Biblioteca inacessível → `ApplePhotosError` que **nomeia o app
  responsável pelo TCC**: `_app_responsavel()` (`:37-62`) sobe a árvore de
  processos com `ps -o ppid=,comm= -p <pid>` (subprocesso em lista, sem
  shell, timeout 2 s, até 8 níveis) e devolve o app `.app/Contents/MacOS/`
  no topo. Em qualquer falha, cai numa descrição genérica — a mensagem de
  erro não pode virar um segundo erro. Saber isso economiza a hora que se
  perde autorizando o app errado.
- No job, `_mensagem_falha_import` (`server/jobs.py:384-399`) acrescenta a
  orientação quando o erro é um `PermissionError` cru em qualquer ponto da
  cadeia de causas.

### 4.3 Google Takeout (`google_takeout.py`)

**Formato esperado** (`:8-10`): `Takeout/Google Photos/<álbum ou "Photos
from 2024">/IMG_001.jpg` + sidecar JSON ao lado. Qualquer nível acima também
serve (`rglob("*")`, `:139`).

Sidecar (`_sidecar_de`, `:49-66`) — variantes cobertas:
`IMG.jpg.json`, `IMG.jpg.supplemental-metadata.json`, e para
`IMG_001(1).jpg` também `IMG_001.jpg(1).json` e
`IMG_001.jpg.supplemental-metadata(1).json`.

Extensões (`_MEDIA_EXTS`, `:39-43`): `.jpg .jpeg .png .gif .webp .tif .tiff
.bmp .heic .heif .mp4 .mov .m4v .avi .mkv .3gp .webm`.

O que é lido do JSON:
- `photoTakenTime.timestamp` → `_data` (`:79-104`): o epoch **é** o instante
  absoluto. Converter com `fromtimestamp(n)` sem fuso era defeito de duas
  faces (a hora dependia do fuso da MÁQUINA que rodou a importação, e o
  absoluto pronto era descartado). Os dois instantes saem **iguais**, que é
  como este catálogo diz "não sei o fuso".
- `geoData` / `geoDataExif` → `_gps` (`:69-76`). **`0.0/0.0` é o "sem GPS"
  do Takeout**, não uma coordenada real.
- `description`, `favorited`, `people[].name`.
- Nome da pasta pai vira álbum, **exceto** pasta de ano
  (`_RE_PASTA_ANO`, `:46`: `^(photos from|fotos de)\s+\d{4}$`, case-insensitive).

**Por padrão não abre as imagens** (`:108-120`): o Takeout é uma exportação,
quase sempre de fotos que o dono já tem em outro lugar, com dezenas de GB.
Os itens entram como **referência** (nome, tamanho via `stat()` — entrada de
diretório, não conteúdo — e o que o Google sabe). `ler_arquivos=True`
restaura a catalogação de verdade, para quando o Takeout *for* o acervo.

Degradação: sidecar ilegível → `log.warning` e segue com `dados={}`
(`:148-150`); `stat()` falhando → `tamanho=None`.

### 4.4 Lightroom (`lightroom.py`)

Por que é a fonte mais valiosa de um acervo espalhado (`:3-10`): **ele
responde com os discos desligados**. Num acervo real o `.lrcat` conhecia
54.086 fotos, 44.474 num volume externo desmontado; varrer o disco teria
encontrado zero.

Abertura (`_abrir`, `:147-166`): `sqlite3.connect(f"file:{cat}?immutable=1",
uri=True)`. `immutable=1` = sem lock, sem journal, sem escrita — o Lightroom
pode estar aberto ao lado (invariante 1). Sanity check
`select count(*) from Adobe_images`.

O que lê (`_CONSULTA`, `:46-63`): `f.id_global` (uuid),
`rf.absolutePath`, `fo.pathFromRoot`, `f.baseName`, `f.extension`,
`i.captureTime`, `e.gpsLatitude`, `e.gpsLongitude`, `i.rating`, `i.pick`.
Consultas auxiliares: coleções (`_COLECOES`, `:67-73` → `albuns`) e
palavras-chave (`_PALAVRAS`, `:75-82`).

Os pedaços do caminho vêm **separados de propósito** (`:38-45`): em SQL,
`a || b` é `NULL` se qualquer parte for `NULL`, e uma extensão ausente
apagava o caminho inteiro — a referência perdia a única pista de lugar que
tinha, sem exceção e sem log. `_nome_e_caminho` (`:103-126`) tolera cada
pedaço ausente com consequência diferente e degrada por partes.

`favorito` = `rating >= 4` (`_NOTA_DE_FAVORITO`, `:86`) **ou** `pick > 0`.
`_data` (`:89-100`) tenta quatro cortes progressivos de `captureTime`.

**Todo item entra como referência** (`caminho=None`, `:198`): o arquivo pode
estar inacessível, e mesmo acessível é o scanner quem cataloga arquivo. O
valor aqui é saber que a foto existe, onde estava e o que se sabe dela.

Degradação: tabela auxiliar ausente numa versão diferente do Lightroom →
`log.warning` e dicionário vazio, nunca derruba a importação (`:175-179`).
Itens sem caminho reconstruível são contados e logados no fim (`:210-217`) —
antes isso acontecia calado.
Só via CLI: `fotoorganizer importar lightroom <.lrcat>`.

### 4.5 Importador (`importer.py`)

**Regra de fusão** (`:3-11`): o **ARQUIVO manda** (EXIF lido por extração
normal); o catálogo externo preenche o que o arquivo não tem e contribui
contexto que só ele conhece — gravado em `metadata_entries` com o namespace
da fonte (`apple`, `google`, `lightroom`, `:44-48`), para toda informação
continuar respondendo "de onde veio?".

Estrutura idêntica à do scan: `deque` de pendentes, `janela =
max(workers*2, 4)`, `ThreadPoolExecutor("import-extract")`,
`_BATCH_SIZE = 200`, escritor único.

Dois caminhos por asset:
- `asset.caminho is None` → `_gravar_referencia` (`:265-323`): **nenhum byte
  de imagem é aberto**. Sempre `arquivo_ausente=True` e
  `papel=MediaRole.SINAL` (uma referência é testemunha por definição — sem
  isso o registro dizia duas coisas contraditórias, e foi o que aconteceu
  com as 54.086 do Lightroom na primeira importação). `caminho` vira
  `"{namespace}://{referencia}"`. `pasta` recebe
  `asset.caminho_original.parent` — o que responde "onde estava esta foto?"
  com o volume desmontado.
- caso contrário → `stat()` + `_extrair` no pool + `_gravar` (`:201-263`).

`_inalterado` (`:185-192`) usa **só tamanho + mtime**, com tolerância de
**2,0 s** (mais frouxa que a do scan) e sem inode.

**Fuso emprestado** (`_com_o_fuso_do_catalogo`, `:400-427`): quando o
ARQUIVO diz a hora e o CATÁLOGO EXTERNO diz o fuso, empresta-se o **offset**
(`utc - local` do catálogo) aplicado à hora do arquivo — nunca o absoluto do
catálogo direto, porque os dois medem o mesmo momento com precisão diferente
(Apple Fotos guarda subsegundo, EXIF trunca no segundo). A concordância se
mede com `_TOLERANCIA_DE_PAREDE = 1 s` (`:41`) e não por igualdade exata:
65% das 44.661 linhas do Apple Fotos têm microssegundo e nenhuma das 120.448
de EXIF tem — exigir igualdade descartaria o fuso medido em quase toda foto,
em silêncio.

Data implausível de referência (`data_plausivel`, `:306-308`) sai das **duas**
colunas junto — o `.lrcat` do dono trazia um registro datado de 2100.

Idempotência: upsert por `(source_id, caminho)`; `_gravar_metadados_externos`
(`:325-360`) **apaga e regrava** o namespace daquela fonte a cada import.
`_unificar_curadoria` (`:363-398`) junta a palavra-chave do catálogo à do
arquivo **sem repetir**: o mesmo "Selected" chega pelo `.lrcat` e pelo
`.xmp` que o mesmo fluxo gravou ao lado — mesma afirmação, mesma origem, e
somar as duas inflaria a confiança.

Degradação por item: `OSError` no `stat()` → `erros++` + log + `continue`
(`:134-138`); exceção no consumo → `erros++` + log (`:103-105`).

Testes: `tests/test_sources_importer.py::test_exif_do_arquivo_vence_o_catalogo_externo`,
`::test_fuso_do_catalogo_vale_quando_a_hora_de_parede_bate_com_o_exif`,
`::test_hora_de_parede_divergente_nao_empresta_o_fuso_do_catalogo`,
`::test_fronteira_da_tolerancia_de_um_segundo`,
`::test_referencia_aparece_na_biblioteca_e_fica_fora_do_organizavel`,
`::test_data_implausivel_de_referencia_sai_das_duas_colunas_junto`,
`::test_curadoria_do_catalogo_externo_nao_duplica_a_do_arquivo`.

### 4.6 Reapontar fonte (`reapontar.py`)

`sources/disponibilidade.py` detecta que um volume remontou noutro ponto e
**recusa-se, por desenho, a reescrever o caminho** — mover 45 mil linhas é
operação do usuário, não efeito colateral de uma verificação. Este módulo é
essa operação. **Nunca toca em arquivo**: só reescreve `Source.caminho` e
`MediaFile.caminho`.

Duas camadas de propósito (`:11-20`):
- `previa`/`aplicar` — operação pura sobre **dois prefixos explícitos**. Não
  sabe nada sobre volumes montados. É isso que dá reversibilidade de graça.
- `prefixos_do_estado(estado)` (`:118-146`) — deriva os prefixos do estado
  ao vivo, com a guarda de segurança: só age quando `estado.caminho` é uma
  raiz `/Volumes/<nome>...` (`len(partes) >= 3 and partes[1] == "Volumes"`).
  Disco interno, ou identidade `caminho:` frágil, não são caso deste
  mecanismo — um replace genérico ali arriscaria reescrever o caminho errado.

Filtro crítico (`:22-30`): `MediaFile.caminho` **nem sempre é um caminho de
filesystem** — fontes externas guardam `apple://<uuid>`,
`lightroom://<uuid>`. Fatiar essas strings pelo mesmo prefixo destruiria a
referência em silêncio (invariante 8). Por isso as duas funções filtram por
`caminho.startswith(prefixo_antigo)` antes de qualquer coisa; o resto fica
bit-a-bit intocado e é contado em `total_ignoradas_sem_prefixo`.

| Limite | Valor | Onde |
|---|---|---|
| `_TAMANHO_AMOSTRA` | 10 | amostra exibida no dry-run (`:50`) |
| `_TAMANHO_VALIDACAO` | 20 | amostra **validada no disco** antes de escrever — maior porque aqui o custo é `Path.exists()`, não pixel de tela (`:53`) |
| `_ACAO_AUDITORIA` | `"reapontar_fonte"` | `:54` |

`aplicar` (`:186-307`), tudo-ou-nada numa transação:
1. recusa se `source.caminho != prefixo_antigo` (`:212-217`) — abortar para
   não reescrever linhas da fonte errada;
2. amostragem espaçada (`passo = len//20`) e `Path.exists()` em cada caminho
   novo; qualquer ausente → `ValidacaoFalhou`, nada escrito (`:234-243`);
3. **colisão proativa** (`:255-263`): duas linhas caindo no mesmo caminho,
   ou uma reapontada caindo sobre uma intocada → `ColisaoDeCaminho` com
   mensagem que diz qual caminho colidiu, em vez de deixar o `UNIQUE`
   estourar `IntegrityError` cru;
4. `UPDATE Source.caminho` + N `MediaFile.caminho`;
5. `AuditLog(plan_id=None, acao="reapontar_fonte", detalhe={source_id,
   prefixo_antigo, prefixo_novo, linhas_media_files}, resultado="ok")`;
6. `IntegrityError` no commit → rollback + `ColisaoDeCaminho` (`:288-295`).

`desfazer_por_auditoria(factory, audit_log_id)` (`:310-343`): lê a entrada,
confere `acao`, e **chama `aplicar` de novo com os prefixos trocados** —
mesma validação, mesma trilha, e a chamada cria uma entrada nova, para
desfazer-o-desfazer funcionar pelo mesmo caminho. Só existe como recuperação
na CLI; não há superfície de API/UI.

Testes: `tests/test_reapontar.py::test_fonte_mista_execucao_so_reescreve_o_que_tem_o_prefixo`,
`::test_validacao_aborta_a_operacao_inteira_se_um_caminho_novo_nao_existe`,
`::test_colisao_de_caminho_aborta_sem_escrever_nada`,
`::test_desfazer_por_auditoria_reverte_bit_a_bit`,
`::test_aplicar_recusa_prefixo_antigo_que_nao_bate_com_a_fonte`;
`tests/test_server_reapontar.py::test_reapontar_ignora_referencias_de_catalogo_externo`.

---

## 5. Duplicatas — níveis 1 e 2 (`fotoorganizer/duplicates/detector.py`)

**Somente leitura, nada é excluído** (`:1`). Cinco níveis; os dois primeiros
são deste domínio (o phash em si é do domínio imagem).

**Entrada**: `DuplicateDetector(session_factory, thumb_cache).detectar(progress=None)`.
**Saída**: `dict` com `{exato, conteudo, visual, sequencia, variante,
preservados}` e, no banco, `duplicate_groups` + `duplicate_members`.

### Sequência de `detectar()` (`:120-156`)

1. carrega todas as mídias com `tamanho > 0`, com
   `selectinload(MediaFile.source)` — a resolução automática olha
   `media.source.tipo` por membro, e sem isso cada grupo dispara um SELECT
   extra;
2. `_completar_phashes` + `_completar_sha256`, commit;
3. `_limpar_grupos_sem_decisao` → `preservados`;
4. `_grupos_exatos` → devolve os **não-representantes**;
5. `_grupos_por_phash` excluindo já agrupados ∪ não-representantes;
6. commit.

### Hash rápido → SHA-256 sob demanda

`quick_signature` (`security/hashing.py:20-29`): O(1) por arquivo —
`xxh3_64` sobre o **tamanho em 8 bytes little-endian** + os primeiros 64 KiB
+ (se `size > 128 KiB`) os últimos 64 KiB. Prefixo `xxh3:`. É o que detecta
mudança e aponta candidatos.

`sha256_full` (`:32-37`): stream em blocos de 256 KiB, prefixo `sha256:`.
Igualdade de conteúdo **só** é afirmada com ele.

`_completar_sha256` (`:168-183`): agrupa por `(tamanho, hash_rapido)` e
calcula SHA-256 **só** para grupos com 2+ membros — nunca para o acervo
inteiro. `OSError` vira `log.warning` e segue.

### Nível 1 — EXATO

`_grupos_exatos` (`:186-200`): agrupa por `hash_sha256`, cria grupo quando
há 2+ membros, e devolve `{m.id for m in membros[1:]}`. O **primeiro** de
cada grupo continua elegível para a passada de phash — assim uma
recompressão da mesma foto agrupa com ele em vez de ficar órfã
(`:145-147`).

### Resolução automática (`duplicates/resolucao.py`)

Só para `EXATO` (`detector.py:253-264`): bytes idênticos não deixam
ambiguidade sobre o CONTEÚDO — só resta decidir qual caminho é a referência.
Os outros níveis dependem de julgamento sobre o conteúdo e ficam
`INDEFINIDO` até um clique humano.

`escolher_principal_automatico` = `min` por `_pontuacao` (`:33-55`), em
ordem de desempate:
1. **fonte própria** (`SourceType.PASTA` = 0) antes de catálogo externo (1);
2. **caminho mais organizado** (mais segmentos: `-_profundidade`);
3. **nome descritivo** antes de genérico —
   `^(img|dsc|dscn|dcim|pxl|mvimg|vid|mov|p|photo|foto)[_-]?\d+$` ou
   puramente numérico (`:18-26`);
4. **riqueza de metadados** (`-count` de `metadata_entries`, uma consulta
   agregada por grupo em `_riqueza_de_metadados`, `detector.py:94-108`).
   Ideia vinda do Immich; o tamanho em bytes não serve aqui (num grupo
   EXATO os bytes são idênticos), a contagem serve — neste acervo o
   metadado É o ativo;
5. **`id` menor**, para o resultado ser estável entre execuções.

Quando resolve, grava `grupo.resolvido_automaticamente = True` e
`PRINCIPAL`/`VERSAO` nos membros.

### Nível 2 — CONTEUDO (e a classificação completa)

`_grupos_por_phash` (`:202-246`) monta uma `BKTree` e busca vizinhos a
`LIMIAR_VISUAL = 8`. Ordem de decisão, **que importa**:
1. `_eh_variante_de_revelacao` (`:68-91`) → `VARIANTE`. Critério: **um só
   nome base** entre os membros, **pelo menos duas extensões distintas**, e
   ao menos uma em `RAW_EXTENSIONS`. Vem **antes** da rajada porque um par
   RAW+JPEG é sempre da mesma câmera no mesmo segundo e casaria como rajada
   também — e "rajada" convida a escolher o melhor frame, que aqui não é a
   pergunta;
2. `_eh_rajada` (`:55-65`) → `SEQUENCIA`. Exige **todas** com
   `data_capturada`, **uma só** `(make, model)` não-nula, e todos os frames
   consecutivos a ≤ `GAP_RAJADA = 10 s`;
3. distância 0 → `CONTEUDO`;
4. distância 1..8 → `VISUAL`.

### Preservação de decisões

`_limpar_grupos_sem_decisao` (`:279-299`): grupo é **decidido** só quando
`not resolvido_automaticamente and any(papel != INDEFINIDO)`. Ou seja,
`resolvido_automaticamente` **não conta** como decisão: se contasse, um
grupo EXATO resolvido sozinho travaria para sempre no tamanho de quando foi
criado, e uma terceira cópia idêntica descoberta depois nunca se juntaria a
ele. Só decisão **humana** fecha o grupo. O resto é `session.delete(grupo)`,
com cascade removendo os membros.

### Decisões do usuário (`repositories/duplicates.py`)

`escolher_principal(group_id, media_id)` (`:149`),
`ignorar_grupo` (`:170`), `desfazer_grupo` (`:174`). As três chamam
`_marcar_decisao_humana` (`:187`), que zera `resolvido_automaticamente`.

Consequência a jusante, em `operations/planner.py:72-82`:
- `VERSAO` = cópia redundante de um grupo com PRINCIPAL definido →
  **não entra** no plano de cópia;
- `IGNORADO` = o dono olhou e decidiu que não são duplicatas de fato
  ("nenhum arquivo será tocado") → **continua entrando** normalmente.

`GroupRow` expõe `bytes_recuperaveis` e `n_fontes` calculados
(`repositories/duplicates.py:51,57`), e `_herdar_metadados` (`:63`) passa
para o principal o metadado que só a versão tinha
(`tests/test_duplicates.py::test_principal_herda_o_metadado_que_so_a_versao_tinha`).

**Audit log**: nenhum. Detecção e decisão de duplicata não escrevem em
`audit_log` — não tocam o filesystem.

Testes: `tests/test_duplicates.py::test_deteccao_nao_modifica_arquivos`,
`::test_sha256_calculado_so_para_candidatos`,
`::test_redeteccao_preserva_decisao`,
`::test_nova_copia_identica_se_junta_a_grupo_resolvido_automaticamente`,
`::test_decisao_humana_substitui_resolucao_automatica`,
`::test_raw_e_jpeg_do_mesmo_clique_sao_variante_nao_duplicata`,
`::test_variante_vence_rajada_na_classificacao`.

---

## 6. Operações físicas (`fotoorganizer/operations/`)

O único domínio autorizado a escrever fora do catálogo.
Fluxo obrigatório: **plano → dry-run → aprovação → cópia verificada**.

### 6.1 Planner (`planner.py`)

**Entrada**: `OperationPlanner(factory).criar_plano(raiz_destino, nome=None)`.
**Saída**: `plan_id: int | None` (`None` = não havia nada a planejar).
**Nenhum arquivo é tocado** — só leitura para detectar colisão.

Seleção (`:58-86`):
- join `Suggestion × MediaFile × Source` com
  `status in (APROVADA, EDITADA)`, ordenado por
  `(destino_sugerido, MediaFile.nome)`;
- exclui `media_id` já em `OperationItem.status == CONCLUIDA` (não refaz
  cópia de plano anterior);
- exclui `media_id` em `DuplicateMember.papel == VERSAO`.

Destino por item (`:98-124`):
1. `resolver_destino(raiz, sugestao.destino_sugerido)` →
   `security/paths.py:37-44`: sanitiza cada segmento e, **depois de
   resolver**, exige `destino.is_relative_to(raiz_resolvida)` (defesa em
   profundidade contra path traversal);
2. `destino = pasta_destino / media.nome`;
3. `destino_recursivo(Path(fonte.caminho), raiz)` →
   conflito `"raiz de destino dentro da árvore de origem"` (copiar para
   dentro da própria origem faria o próximo scan indexar as cópias);
4. `_destino_livre(destino, usados)` (`:37-45`): resolve colisão **com o
   disco e com o próprio plano**, sufixando **antes da extensão** —
   `IMG_1 (2).jpg`. Nunca sobrescreve nome ocupado. Renomeou → conflito
   `"destino ocupado; renomeado para X"`;
5. `CaminhoInvalido` → conflito `"caminho inválido: …"` e `destino = ""`
   (string vazia é o sinal de "sem destino calculado" para o dry-run e o
   executor).

Audit: `AuditLog(plan_id, "plano_criado", {"raiz", "itens"}, "ok")`.

### 6.2 Dry-run (`executor.py:67-120`) — obrigatório

Só lê. Por item não-concluído:
- sem `destino` → problema `"{nome}: {conflito}"`;
- origem não é arquivo → `"{origem}: origem indisponível"`;
- destino já existe → `"{nome}: destino já existe (nunca será sobrescrito)"`;
- caso contrário: soma `origem.stat().st_size` e `prontos++`.

Espaço livre: sobe os `parents` do destino do **primeiro** item até achar
um que exista e chama `shutil.disk_usage(...).free` (`:96-101`).

Grava `plano.dry_run_em` e
`AuditLog(plan_id, "dry_run", {prontos, problemas, bytes_necessarios,
bytes_livres}, "ok")`.
Devolve `{prontos, problemas, bytes_necessarios, bytes_livres,
espaco_suficiente}`.

### 6.3 Execução (`executor.py:138-194`)

Duas portas antes de qualquer byte:
1. `plano.dry_run_em is None` → `DryRunObrigatorio` (`:147-150`);
2. `_prontos_no_ultimo_dry_run(...) == 0` → `DryRunObrigatorio` com
   mensagem própria (`:151-161`). Exigir que o dry-run tenha acontecido não
   basta: um plano com todas as origens num volume desmontado passava na
   porta antiga e "executava" 97 itens sem copiar nenhum. `None` (plano de
   versão anterior, sem veredito) **não é executável pela UI** — `executavel = dry_run_em is not None and bool(prontos)` (`repositories/operations.py:38-40`), e `prontos=None` dá `False`; o executor, por sua vez, exige dry-run e `prontos > 0` no último audit (`operations/executor.py:155-161`). Plano de versão anterior precisa de um dry-run novo antes de executar.

`plano.status = EXECUTANDO` + audit `execucao_iniciada`, commit.
Pendentes = itens com `status != CONCLUIDA`.
`stats = {copiados, erros, pulados, cancelado, inventario_falhou}`.
Laço: checa `control.cancelado` no topo, `progress(n, total, origem)`,
`_executar_item`, **commit por item** (retomada segura).

Status final: `CANCELADA` se cancelado, `ERRO` se houve erro, senão
`CONCLUIDA`; audit `execucao_finalizada` com `dict(stats)`.

### 6.4 `_executar_item` (`:196-252`) — a cópia verificada

```
hash_pre = sha256_full(origem)          # antes
destino.parent.mkdir(parents=True, exist_ok=True)
_copiar_exclusivo(origem, destino)      # open('xb')
hash_pos = sha256_full(destino)         # depois
if hash_pos != hash_pre:
    destino.unlink(missing_ok=True)     # remove a CÓPIA, nunca o original
    raise OSError("verificação de hash falhou após a cópia")
shutil.copystat(origem, destino)
```

`_copiar_exclusivo` (`:254-267`): stream em blocos de `_CHUNK = 1 MiB`
(`:39`) com `destino.open("xb")` — **criação exclusiva**: se o destino
existir, o SO recusa, e sobrescrever é impossível por construção. Falha no
meio remove o parcial (nunca o original).

Tratamento de erro:
- `FileExistsError` → `status=ERRO`, `erro="destino já existe — sobrescrita
  bloqueada"`, audit `copia/bloqueada_sobrescrita`;
- `OSError` → `status=ERRO`, `erro = "disco cheio"` quando
  `errno == ENOSPC`, senão `str(exc)`; audit `copia/erro: …`.

`copystat` preserva mtime/permissões do original **na cópia**.

Audit por item: `_audit_item` (`:276-283`) com
`{origem, destino, hash_pre, hash_pos}`.

### 6.5 Inventário por pasta (`operations/inventario.py`, D-062)

Roda **só depois** que a cópia já foi verificada por hash. Um par
`inventario.json` + `INVENTARIO.md` por **PASTA de destino**, **aditivo**
entre execuções de planos diferentes — nunca um par por foto nem por plano.

Nunca decide se a cópia é válida: só registra o que já foi verificado
(`:8-10`).

Escrita atômica (`_escrever_atomico`, `:38-46`): grava num `.tmp` no mesmo
diretório e faz `os.replace` — `write_text` trunca antes de escrever, e um
crash no meio corromperia o arquivo para a **próxima** leitura, travando o
inventário da pasta inteira.

JSON corrompido de execução anterior (`_carregar`, `:49-66`): renomeia para
`inventario.json.corrompido-<epoch>`, loga, e recomeça — o MD é sempre
regenerado do JSON inteiro, então não se perde nada que não já estivesse
perdido, e o arquivo ruim fica ao lado para inspeção.

Idempotente: se `arquivo` já está no inventário, não duplica (`:155-156`).

Entrada gravada (`_montar_entrada`, `:78-109`): `arquivo, origem, tamanho`
(do arquivo **realmente copiado**, não o do catálogo — os dois divergem se o
original mudou entre o scan e esta execução), `hash_sha256` (= `hash_pos`),
`copiado_em`, `data_capturada`, `camera`, `lugar{pais,regiao,cidade}`,
`evidencias[]` e `versao_logica`.

**Nunca bloqueante** (`executor.py:221-241`): envolvido em `except
Exception` genérico de propósito — não só `OSError`, porque um
`inventario.json` corrompido levanta `json.JSONDecodeError` (`ValueError`),
e qualquer outra falha inesperada não pode abortar o PLANO INTEIRO no meio.
Incrementa `stats["inventario_falhou"]` e grava audit `inventario`.

### 6.6 Cancelamento e retomada

`ExecutionControl` (`:42-51`): um `Event`, sem pausa. Checado no topo do
laço de itens. O item em curso **termina**; o plano vira `CANCELADA`.
Retomada = chamar `executar` de novo: itens `CONCLUIDA` viram `pulados` e
não são refeitos.

> **Achado M3 (MÉDIO)**: um `OSError` **depois** da verificação de hash
> (`:210,215` — `sha256_full(destino)` ou `copystat`) deixa o destino órfão.
> Na retomada, `FileExistsError` → "sobrescrita bloqueada" **permanente**.

### 6.7 Estados

`OperationPlan.status`: `planejada` → `executando` →
`concluida` | `erro` | `cancelada`.
`OperationItem.status`: `planejada` → `concluida` | `erro`.

Testes: `tests/test_operations.py::test_execucao_exige_dry_run`,
`::test_copia_verificada_preserva_originais`,
`::test_sobrescrita_impossivel`, `::test_cancelamento_e_retomada`,
`::test_origem_indisponivel_nao_para_o_resto`,
`::test_execucao_recusa_plano_sem_nada_copiavel`,
`::test_falha_no_inventario_nao_desfaz_copia_verificada`,
`::test_inventario_corrompido_recupera_em_vez_de_travar_o_plano`;
`tests/test_server_api.py::test_execucao_nunca_sobrescreve_destino_que_surgiu_depois`.
Achados **A3** (ramo de hash divergente sem teste) e **B6** (ENOSPC sem
teste).

---

## 7. Escrita EXIF de localização (`fotoorganizer/exif_write/`, D-075)

Módulo **paralelo**, não filho, de `operations/`. Nada é herdado — nem
classe, nem exceção, nem convenção de status; só `ExecutionControl`
(cancelamento genérico) é reusado.

Por que o modelo de segurança é outro (`__init__.py:1-16`): a cópia se
protege criando um caminho novo que ainda não existe (`open('xb')`).
**Mutação in-place não tem equivalente disso.** Então o critério de sucesso
é o **diff completo de tags antes/depois**, e o backup `_original` do
próprio exiftool é a rede de recuperação durante a janela entre escrita e
verificação.

### 7.1 Allowlist de formatos (`formatos.py`) — medida, não suposta

Medido em 2026-08-18 por `scripts/testar_escrita_exif.py` contra o
`catalog.db` de produção (1.399 arquivos: 1.384 `.jpg`, 12 `.cr2`, 2 `.dng`,
1 `.tif`). D-076 = medição original; D-077 = remedição byte a byte.

```
FORMATOS_APROVADOS = {".jpg", ".jpeg", ".cr2"}     # formatos.py:48
MEDIDO_EM = "2026-08-18"                            # :40
```

| Extensão | Situação | Motivo (`MOTIVOS_NAO_SUPORTADO`, `:54-78`) |
|---|---|---|
| `.jpg`, `.jpeg`, `.cr2` | **aprovado** | 20/20 e 12/12 amostras; todo deslocamento medido é relocação comprovada |
| `.dng` | reprovado | `SubIFD:TileOffsets`/`SubIFD3:TileOffsets` têm tiles demais para o exiftool expor como lista de inteiros (`"(Binary data N bytes…)"`), então a prova byte a byte não parseia e fica **fail-safe** |
| `.tif` / `.tiff` | reprovado | tag `IPTC:EnvelopeRecordVersion` nova + 2 avisos novos — motivo não relacionado a offset |
| `.cr3`, `.heic`, `.heif` | **não testado** | zero arquivos no catálogo (D-09) — categoria diferente de "reprovado" |
| qualquer outra | não testado | `motivo()` (`:86-97`) **nunca** devolve string vazia (D-05 exige motivo visível em toda linha não suportada) |

Formato reprovado ou não testado cai no **sidecar XMP** (D-06/EXIF-05):
`caminho_sidecar(origem)` = `foto.<ext>.xmp` (`:100-128`) — a convenção
Adobe, que `metadata/exiftool.py::_sidecar_de` já procura **primeiro** ao
ler. Um sidecar novo é pego pela próxima varredura sem nenhuma mudança do
lado da leitura.

### 7.2 Planner (`planner.py`)

**Entrada**: `ExifWritePlanner(factory).criar_plano_exif(nome=None)`.
Escopo **global** — uma linha por arquivo catalogado elegível, **sem**
recorte por fonte (ao contrário de `operations/planner.py`).
**Nada toca o disco aqui** (`:1-10`); a checagem de "campo vazio" deste
módulo é a barata, baseada só no catálogo. A autoritativa é do dry-run.

Candidatos (`:69-86`): `MediaFile.organizavel` **e**
(`gps_lat IS NULL AND gps_lat_estimado IS NOT NULL`
**ou** `Location.cidade IS NOT NULL OR Location.pais IS NOT NULL`),
com `outerjoin(Location)`, ordenado por caminho.

Exclusão (`:88-102`): mídia cujos **três** campos já estão em
`_RESOLVIDOS = (GRAVADO, PULADO, SEM_VALOR)` (`:46`). Sem isso, todo plano
novo renasceria com centenas de linhas "nada a gravar" e a tela perderia o
sinal. Item com qualquer campo em `FALHA` ou `PENDENTE` **continua
elegível** — replanejar depois de falha parcial é o caminho de recuperação.

Campos já presentes no arquivo: **uma** consulta agregada (não N+1,
T-06-13) sobre `metadata_entries` com `namespace in ('iptc','xmp')` e
`chave in ('City','Country','Country-PrimaryLocationName')` (`:109-126`).
O valor concreto vira o motivo de `PULADO`:
`"já preenchido: {valor} — não sobrescrito"` (`:51-53`).

Status inicial por campo (`:146-174`): `PULADO` se já preenchido,
`SEM_VALOR` se o motor não inferiu, senão `PENDENTE`.

`incluido` nasce `True`, **exceto** para linha de sidecar (formato não
suportado), que nasce `False` — D-06 é opt-in, D-02 é opt-out (`:205-207`).

Audit: `AuditLog(plan_id=None, "plano_exif_criado",
{exif_plan_id, itens, nao_suportados, sincronizados}, "ok")`.

### 7.3 Detecção de pasta sincronizada (`sync_detect.py`, D-07)

**Aviso, nunca bloqueio**: o dono decide pelo mesmo checkbox de D-02.
Checagem pura de caminho, O(1), sem processo externo: "está materializado
agora" é transitório; "este caminho vive numa pasta gerida por sync" é fato
estável (`:1-9`).

Raízes (`:15-24`): `~/Library/Mobile Documents` → `"iCloud Drive"`;
`~/Library/CloudStorage` → `"Nuvem (File Provider)"` (cobre OneDrive,
Google Drive, Box e o Dropbox atual); `~/Dropbox` → `"Dropbox (legado)"`.

Resolve symlinks **antes** de comparar (`:44`) — cobre o redirecionamento
de Desktop/Documents do iCloud. `OSError` no `resolve()` devolve `None`, a
resposta segura. Nunca levanta.

### 7.4 Dry-run (`executor.py:143-237`) — autoritativo

O plano foi montado a partir do catálogo, que pode estar desatualizado.
Aqui o **disco é lido ao vivo, em lote**: `verificacao.dump_lote(caminhos)`
— 1.400 invocações a ~200 ms seriam ~5 min; em lote são segundos.

Por item:
- recomputa `pasta_sincronizada` **sempre**, mesmo se a origem sumiu (é
  checagem pura de caminho);
- origem não é arquivo → problema, **nenhum campo muda de status**;
- formato não suportado e o sidecar **já existe** → todos os três campos
  viram `PULADO` com `_MOTIVO_SIDECAR_EXISTE = "sidecar já existe — nunca
  será sobrescrito"`;
- por campo: sem valor inferido → `SEM_VALOR`; já preenchido no dump →
  `PULADO` com o valor legível; `validar_campos` falhou → `FALHA`; senão
  `PRONTO`.

`prontos` conta **itens** com `incluido` e ≥1 campo pronto;
`campos_a_gravar` conta campos.
Grava `dry_run_em` e audit `dry_run_exif` com
`{exif_plan_id, prontos, problemas, campos_a_gravar, sidecars,
nao_suportados, sincronizados}`.

`_campo_ja_preenchido` (`:107-135`) monta o valor legível de GPS juntando
`GPSLatitude`+`GPSLatitudeRef` (escrita direta grava o Ref separado; sidecar
grava o valor já assinado).

### 7.5 Seleção (`aplicar_selecao`, `:258-278`)

Materializa D-02. Persiste `ExifWriteItem.incluido` **antes** de
`executar()` começar — a execução relê do banco, então passar a seleção só
como argumento perderia o registro de auditoria e a fonte de verdade da
retomada. `itens is None` não muda nada, só devolve a contagem atual.
Audit: `selecao_exif` com `{exif_plan_id, incluidos, excluidos}`.

### 7.6 Writer (`writer.py`) — os argumentos exatos

`ExifToolWriter` usa **um `subprocess.run` curto por escrita, não
`-stay_open`** (`:60-68`): o leitor persistente serve um scan inteiro; aqui
o volume é um plano revisado (dezenas a milhares), então ~200 ms de partida
é aceitável e evita disputar o lock do processo `-stay_open` do leitor.

`validar_campos(campos)` (`:32-57`) — **única fronteira de validação do
pacote**, porque `exiftool -GPSLatitude=999` é aceito em silêncio, exit 0:
- lat finita em `[-90, 90]`, lon finita em `[-180, 180]`;
- cidade/país: `str` não vazio, sem `\n`/`\r`, ≤ `_TAMANHO_MAXIMO_TEXTO =
  200` caracteres.
Violação → `ValorInvalido`, **antes de qualquer subprocesso**
(`tests/test_exif_write_writer.py::test_validar_campos_nao_chama_subprocesso`).

Argumentos montados (`escrever`, `:82-138`), lista, sem shell:

```
[exiftool,
 -GPSLatitude=<abs(lat)>, -GPSLatitudeRef=<N|S>,
 -GPSLongitude=<abs(lon)>, -GPSLongitudeRef=<E|W>,
 -IPTC:City=<cidade>,      -XMP:City=<cidade>,
 -IPTC:Country-PrimaryLocationName=<pais>, -XMP:Country=<pais>,
 -charset, filename=utf8, <alvo>]
```

- Os **dois grupos** de cidade/país são sempre gravados explicitamente:
  `-City` sem prefixo cai em IPTC e `-Country` sem prefixo cai em
  XMP-photoshop (assimetria verificada, Pitfall 3) — gravar só um deixaria
  o dado invisível para metade dos consumidores.
- Quando o alvo é `.xmp`, os argumentos `-IPTC:` são **omitidos**: IPTC é
  segmento binário de container de imagem, não existe num `.xmp` autônomo.
- **Sem `-overwrite_original`**, de propósito: o backup `_original` que o
  exiftool cria por padrão é a cópia literal de recuperação durante a janela
  entre escrita e verificação (Pitfall 7). Quem apaga esse backup é o
  executor, depois que o diff aprovar, como passo deliberado e auditado.
  `caminho_backup(alvo)` = `Path(str(alvo) + "_original")` (`:77-80`).
- O `CompletedProcess` devolvido **nunca** é o sinal de sucesso.

> **Achado A2 (ALTO)**: no caminho de **sidecar**, o writer grava
> `abs(lat)` + `-GPSLatitudeRef`, e `GPSLatitudeRef` não é gravável em XMP
> (exiftool 13.55 `-listx`: `writable='false'`). `(-22.95, -43.18)` vira
> `22,57.0N`. A verificação só checa presença, então o campo é marcado
> `GRAVADO`, e o estado é sticky. Alcance: `.dng/.tif/.cr3/.heic`.

### 7.7 Verificação por diff (`verificacao.py`) — o único sinal confiável

Verificado empiricamente (exiftool 13.55): `exiftool
-GPSLatitude=notanumber -City="X" -Country="Y" <file>` imprime um warning,
**pula só a tag malformada**, escreve City e Country, ainda reporta
"1 image files updated" e ainda sai 0 (`:1-11`).

`dump(caminho)` (`:314-337`): `exiftool -j -G1 -a -n -charset filename=utf8
<arquivo>`, timeout 30 s, `check=False`. `-n` (valor decimal, não
`23 deg 33' 1.87" S`), `-G1` (grupo de família 1, distingue
`XMP-photoshop:City` de `IPTC:City`), `-a` (tags duplicadas em grupos
diferentes). **Nunca levanta**: `{}` em qualquer falha.
`dump_lote` (`:342-376`): mesma invocação, `tamanho_lote=200` caminhos por
chamada (evita `ARG_MAX`); caminho sem resposta entra com `{}`.

`avisos(caminho)` (`:379-…`): texto plano, **não** `-j` — a saída JSON
**colapsa** `Warning`/`Error` repetidas em uma só (um TIFF com 6 warnings
devolve 1, silenciando 5). `Validate` (o resumo agregado) é descartado: ele
muda de valor inclusive quando **melhora**. O critério de D-04 é **delta**
de avisos, não "zero avisos depois".

Tags por campo:

| Campo | Escrita direta (`TAGS_POR_CAMPO`, `:33-42`) | Sidecar (`TAGS_POR_CAMPO_SIDECAR`, `:47-51`) |
|---|---|---|
| `gps` | `GPS:GPSLatitude`, `GPS:GPSLatitudeRef`, `GPS:GPSLongitude`, `GPS:GPSLongitudeRef` | `XMP-exif:GPSLatitude`, `XMP-exif:GPSLongitude` |
| `cidade` | `IPTC:City`, `XMP-photoshop:City` | `XMP-photoshop:City` |
| `pais` | `IPTC:Country-PrimaryLocationName`, `XMP-photoshop:Country` | `XMP-photoshop:Country` |

`TAGS_ESTRUTURAIS_ESPERADAS` (`:70-103`) — andaime inevitável ao criar um
bloco GPS/IPTC/XMP pela primeira vez, **cada entrada justificada
individualmente** (isentar o prefixo `IPTC:`/`XMP:` inteiro mascararia
escrita real fora de escopo): `GPS:GPSVersionID`,
`IPTC:ApplicationRecordVersion`, `File:CurrentIPTCDigest`,
`XMP-x:XMPToolkit`, `IPTC:EnvelopeRecordVersion` (D-078),
`File:FileType`, `File:FileTypeExtension`, `File:MIMEType` (as três últimas
só descrevem "este arquivo é um .xmp", para o caso de sidecar novo).

`TAGS_VOLATEIS` (`:109-120`): `SourceFile`, `File:FileSize`,
`File:FileModifyDate`, `File:FileAccessDate`, `File:FileInodeChangeDate`,
`File:FilePermissions`, `File:Directory`, `File:FileName`,
`ExifTool:ExifToolVersion`, `ExifTool:Warning`.
`PREFIXOS_VOLATEIS` (`:124`): `System:`, `Composite:`. `File:` **não** entra
como prefixo inteiro — `File:ImageWidth`/`Height` mudando É sinal real de
corrupção.

`diferenca(antes, depois)` (`:438-…`) classifica em 4 baldes, **nesta
ordem**: `estruturais` → volátil (descartado) → `esperadas` (tag de
localização que **entrou**) → `inesperadas`. Tag de localização que
**sumiu** vai para `inesperadas` com `(valor, None)` — "esperada" significa
"entrou", e sumir é o oposto.

`campo_gravado(campo, diff, sidecar)` (`:479-…`): `True` só quando **todas**
as tags do campo estão em `diff.esperadas`. Esse "todas" é o detector de
falha parcial de EXIF-03 — cidade no IPTC mas não no XMP é falha.

`reclassificar_deslocamentos_de_offset(diff, antes, depois, arquivo_antes,
arquivo_depois)` (`:241-…`, D-077): rebaixa de `inesperadas` para
`esperadas_condicionais` toda tag de offset cujo deslocamento é
**relocação pura comprovada** — o conteúdo binário que o par offset+tamanho
aponta é sha256-idêntico antes e depois. Mapa fechado
`_SUFIXOS_OFFSET_PARA_TAMANHO` (`:138-146`), seis pares:
`ThumbnailOffset→ThumbnailLength`, `PreviewImageStart→PreviewImageLength`,
`StripOffsets→StripByteCounts`, `TileOffsets→TileByteCounts`,
`JpgFromRawStart→JpgFromRawLength`, `MPImageStart→MPImageLength`.
**Fail-safe**: qualquer condição que falhe (tag fora do mapa, tag que sumiu,
tamanho mudou junto, valor não parseável, leitura além do fim do arquivo)
mantém a tag em `inesperadas`. Nunca promove por omissão.

### 7.8 Execução (`executor.py:287-352` e `_executar_item:354-530`)

Portas (`:295-307`), iguais em espírito às da cópia: `dry_run_em is None` →
`DryRunObrigatorioExif`; último dry-run com `prontos == 0` → idem.

Pendentes = itens com `incluido` **e** algum campo em `PRONTO`. Item não
incluído entra direto em `pulados` — **nenhuma chamada de escrita acontece
para ele**, e é isso que prova o opt-out.

`stats = {gravados, sidecars, pulados, falhas_parciais, erros, cancelado}`.
Commit **por item**.

Por item (`_executar_item`):
1. origem não é arquivo → `erro`, audit, `return` — **nenhum campo muda de
   status**, então rerodar depois retoma;
2. sidecar cujo destino já existe → `erro`, `return`;
3. `antes_alvo = dump(alvo)` e `avisos_antes` (ou `{}`/`set()` se o alvo
   ainda não existe);
4. **reconferência TOCTOU ao vivo** (`:374-392`): só entra na lista quem
   continua `PRONTO` **e** cujas tags continuam ausentes **agora**. Campo
   que passou a estar preenchido entre o dry-run e agora vira `PULADO` sem
   tocar em nada. É isto que torna rerodar idempotente sem depender de o
   dry-run estar fresco;
5. lista vazia → `pulados++`, audit `pulado`, **nenhum subprocesso**;
6. `validar_campos` de novo; falha → todos os campos tentados viram `FALHA`;
7. `hash_pre = sha256_full(origem)` — **fato de auditoria, não critério**;
8. `ExifToolWriter().escrever(origem, campos, destino=alvo se ≠ origem)`;
9. `depois = dump(alvo)`, `avisos_depois`, `diff = diferenca(...)`;
10. se `diff.inesperadas` e o backup existe → `reclassificar_deslocamentos_de_offset`
    usando o próprio `_original` como o "antes" byte a byte;
11. veredito **por campo** via `campo_gravado` → `GRAVADO` ou `FALHA`;
12. `hash_pos = sha256_full(origem)`;
13. **corrupção** (`diff.inesperadas` ou aviso novo): reprova TUDO que foi
    tentado, grava `item.erro` dizendo qual tag mudou, **preserva o
    backup** em `backup_original`, `erros++`, audit
    `escrita_exif/falha_verificacao` com `tags_gravadas`. **O backup nunca é
    apagado numa falha de verificação** — quem decide restaurar é o dono
    (invariante 8);
14. **todos gravados**: apaga o backup (`unlink`), e se o `unlink` falhar,
    apenas `log.warning` — a limpeza é auxiliar, a escrita já está correta e
    confirmada. Audit `limpeza_backup_exiftool` + `escrita_exif_verificada/ok`;
15. **falha parcial** (algum gravou, algum não, sem tag inesperada):
    `falhas_parciais++`, mantém o backup, audit
    `escrita_exif/falha_parcial`. **Não** derruba o plano para `ERRO`
    (`:345-347`) — parcial é resultado esperado e já está registrado campo a
    campo;
16. `OSError` inesperado → `erro` por item, nunca derruba o plano.

`_audit_item` (`:532-552`) grava sempre `{exif_plan_id, item_id, origem,
alvo, hash_pre, hash_pos, campos:{gps,cidade,pais}, tags_gravadas}` — os
campos + as tags juntos são exatamente o que EXIF-03 pede.

### 7.9 Restauração de backup

**O app nunca desfaz nada sozinho** (`executor.py:39-41`). O que ele faz é
preservar o `_original` e expor o caminho em
`ExifWriteItem.backup_original` (e em `GET /api/exif/{id}` como
`backup_original`). A restauração é ato do dono, fora do app.

Testes: `tests/test_exif_write_executor.py::test_executar_sem_dry_run_levanta`,
`::test_dry_run_nao_escreve`, `::test_nunca_escreve_fora_de_localizacao`,
`::test_diff_detecta_falha_parcial`,
`::test_backup_apagado_so_apos_sucesso_verificado`,
`::test_rerodar_e_idempotente`, `::test_item_desmarcado_nao_e_escrito`,
`::test_formato_nao_suportado_grava_sidecar`,
`::test_sidecar_existente_nunca_e_sobrescrito`,
`::test_audit_de_execucao_nao_viola_fk`,
`::test_executar_nao_regride_por_deslocamento_de_offset`.
Achados **A2**, **A4** (TOCTOU no alvo direto sem teste) e **M6** (esses
testes têm `skipif` sem exiftool e, sem CI, passam verde sem executar).

---

## 8. Segurança (`fotoorganizer/security/`)

### 8.1 `paths.py` — validação de caminhos

`caminho_relativo_seguro(relativo)` (`:18-34`): normaliza `\` → `/`, corta
segmentos vazios e `.`, **rejeita** `..` e qualquer segmento começando com
`~` (`CaminhoInvalido`), passa cada segmento por
`classification.templates.normalizar_segmento` e rejeita o que ficar vazio
depois de normalizar. Caminho inteiro vazio também é rejeitado.

`resolver_destino(raiz, relativo)` (`:37-44`): `raiz.expanduser().resolve()`
+ o relativo sanitizado, e **depois de resolver** exige
`destino.is_relative_to(raiz_resolvida)` — defesa em profundidade.

`destino_recursivo(arvore_origem, raiz_destino)` (`:47-55`): `True` se a
raiz de destino está dentro da árvore da fonte. **Na dúvida (`OSError`),
bloqueia.**

Consumidores: `operations/planner.py:103,105` e
`server/app.py:1192` (o `PATCH` de destino de sugestão usa a mesma
sanitização do planejador). Auditoria de hoje classificou path traversal
como **limpo**.

### 8.2 `hashing.py`

Ver §5. Duas funções, prefixo no valor (`xxh3:`, `sha256:`) — o prefixo é o
que permite trocar de algoritmo sem ambiguidade.

### 8.3 `volumes.py` — identidade de volume

Três níveis de identidade, do mais forte ao mais fraco (`:9-20`):
1. `uuid:<VolumeUUID>` do `diskutil` — sobrevive a remontagem, renomear e
   troca de máquina;
2. `rede:<origem>` para NAS — um SMB não tem UUID, mas
   `//alex@nas/fotos` identifica o mesmo lugar em qualquer sessão;
3. `caminho:<ponto>` como último recurso, com `estavel=False`.

Subprocessos, ambos em lista e sem shell, `_TIMEOUT_S = 10.0`:
`["/sbin/mount"]` (`:99-102`) e
`["diskutil", "info", "-plist", str(ponto)]` (`:117-120`, parseado com
`plistlib`). **Falha nunca levanta** — devolve a identidade mais fraca e
segue; volume de rede não aparece no `diskutil` e isso é esperado, não erro.

`volume_desmontado(caminho)` (`:62-74`): se o caminho pede
`/Volumes/<nome>` e esse ponto não está montado, devolve a raiz. Sem essa
checagem, subir a árvore a partir de um disco desligado chega até `/` e
atribui as fotos dele ao disco de boot — trocando "está na gaveta" por
"está aqui", o erro mais caro possível num acervo espalhado.

`montado_em(identidade)` (`:156-170`): percorre a tabela de montagem e
devolve onde aquele volume está **agora**. É o que permite reencontrar um
disco que voltou noutro ponto — a fonte guarda a identidade, e o caminho é
resolvido a cada uso.

`sources/disponibilidade.verificar(factory)` (`:74-121`) atualiza
`Source.disponivel`, `visto_em` e, **na primeira vez que a fonte é vista**,
grava `volume_id`/`volume_nome`. Quando o volume voltou noutro ponto,
registra `ponto_atual` e **não reescreve o caminho** — mover 45 mil linhas é
operação do usuário. `EstadoDaFonte.resumo()` (`:60-71`) produz as quatro
frases da UI: "mudou de lugar → X", "disponível", "na gaveta (volume
conhecido, não montado)" / "volume não montado", "a pasta não existe mais
neste volume" (esta última não é indisponibilidade: é ausência, e a ação do
usuário é procurar backup, não plugar cabo).

Testes: `tests/test_volumes.py::test_disco_desligado_nao_vira_o_disco_de_boot`,
`::test_uuid_manda_sobre_o_ponto_de_montagem`,
`::test_nas_sem_uuid_usa_servidor_e_compartilhamento`,
`::test_diskutil_quebrado_nao_derruba_a_identificacao`,
`::test_volume_que_voltou_noutro_ponto_e_apontado`,
`::test_pasta_apagada_no_disco_montado_nao_e_gaveta`.

### 8.4 `crypto.py` — chave dos embeddings faciais

`KeyStore` é `Protocol` com um método: `obter_ou_criar_chave() -> bytes`.

- `KeychainKeyStore` (`:47-67`): `security find-generic-password -a
  embeddings-key -s FotoOrganizer -w` e, se não achar,
  `security add-generic-password … -U`. Argumentos em lista, timeout 10 s,
  **nunca** `shell=True`.
- `FileKeyStore` (`:30-44`): fallback `<data_dir>/embeddings.key` com
  `touch(mode=0o600)` + `chmod(0o600)`.
- `keystore_padrao(data_dir)` (`:70-78`): tenta o Keychain; em `OSError`/
  `SubprocessError`, loga aviso e cai no arquivo (CI, testes).
- `EmbeddingCipher` (`:81-89`): Fernet sobre `json.dumps(vetor)`.

Limitação documentada em `docs/PRIVACIDADE.md`: protege o banco **em
repouso**, não contra código rodando na sessão desbloqueada do usuário.
Achado **B5**: sem teste (faces é stub, sem consumidor).

### 8.5 `http_seguro.py`

445 linhas, **sem consumidor em produção hoje** — nenhum módulo de
`fotoorganizer/` o importa. Existe como cliente HTTP endurecido para quando
um provider externo opt-in precisar. Os 23 testes dele
(`tests/test_http_seguro.py`) falham **no sandbox** por restrição de rede,
não por defeito do código.

---

## 9. Jobs — ciclo de vida da thread

Detalhado em `05-API_E_CLI.md` §3. Aqui só o ciclo:

```
POST /api/<algo>  →  JobManager.iniciar_X()
                     ├─ ocupado()?  →  False  →  rota devolve 409
                     └─ _control = ScanControl()          (novo a cada job)
                        _estado = {status:"rodando", tipo, alvo, contadores}
                        Thread(daemon=True, name="job-<tipo>").start()
                                │
                                ├─ _rodar_X() chama o executor real,
                                │  passando `progress` que faz _atualizar(**campos)
                                │  sob o lock
                                │
                                └─ fim: _atualizar(status=..., resultado=...)
                                   ou, em exceção, log.exception +
                                   _atualizar(status="erro", mensagem=str(exc))

GET /api/job        →  cópia do snapshot sob o lock
GET /api/progresso  →  SSE: emite quando o snapshot muda, 0,5 s de intervalo,
                       fecha quando status != "rodando"
POST /api/job/pausar|continuar  →  só `tipo == "scan"` (ScanControl)
POST /api/job/cancelar          →  continuar() e depois cancelar(), + ExecutionControl
```

A thread é **daemon**: o processo não espera por ela ao sair. Quem garante
integridade é o commit por item/lote de cada executor, não o join da thread.

Achados: **A1** (check-then-act fora do lock permite duas threads no mesmo
plano), **B3** (`_exec_control` órfão, nunca limpo), **M8** (cancelamento de
execução e de escrita EXIF sem teste ponta a ponta).

---

## Lacunas e incertezas

1. **`verificacao.py` linhas 148-240 e 379-420** — li as assinaturas, os
   docstrings e a lógica de classificação, mas não o corpo completo de
   `_ler_intervalo`, `_valores_numericos`, `_e_relocacao_comprovada` e
   `avisos`. As condições de fail-safe que listei vêm dos docstrings e dos
   nomes dos testes, não da leitura linha a linha das ~90 linhas dessas
   quatro funções.
2. **`ThumbnailCache`** (`fotoorganizer/thumbnails/`) é domínio imagem:
   descrevi só a interface que o scanner e o servidor usam
   (`get`, `get_or_generate`), não o layout do cache nem a política de
   invalidação.
3. **`GoogleTakeoutProvider` com `ler_arquivos=True`** só é acessível pela
   CLI (`--ler-arquivos`); não confirmei se algum caminho de UI ou de teste
   exercita essa variante de ponta a ponta.
4. **Retomada de escrita EXIF após crash do processo** (não cancelamento):
   o plano fica `EXECUTANDO` no banco e nada o reconcilia no boot — ao
   contrário de `ScanSession`, que tem `reconciliar_orfas`. Não achei
   mecanismo equivalente; pode ser lacuna real ou intencional (o commit por
   item torna rerodar seguro), mas não determinei.
5. **`operations/executor.py` e volume que desmonta no meio da execução**:
   cada item falha isoladamente com "origem indisponível", mas não
   determinei se há algum ponto que aborte o plano inteiro nesse caso.
6. **Ordem de descoberta**: `iter_media_files` usa `stack.pop()` sobre uma
   lista com `sorted(scandir)` — a ordem resultante entre diretórios é
   determinística mas não é alfabética global. Não verifiquei se algum
   consumidor depende da ordem.
7. **Números do "medido no acervo real"** citados nos comentários do código
   (45.822 miniaturas, 14.755 Smart Previews, 1.399 arquivos testados etc.)
   foram reproduzidos como o código os declara; não os remedi contra o
   catálogo atual.


---

# Parte B — Imagem e inferência

# 04 — Pipelines do domínio IMAGEM / INFERÊNCIA

Spec de reconstrução. Tudo aqui foi lido do código do commit `524903d` (main).
Cada afirmação cita `arquivo:linha`. O que não foi possível determinar está em
"Lacunas e incertezas", no fim.

Convenção: quando o texto diz "hoje", quer dizer "no código lido"; quando diz
"prometido", é doc/comentário sem código correspondente — e isso está marcado.

Ordem real de execução no produto:

```
scan  →  (1) extração de metadados  →  (2) miniatura (mesma leitura do arquivo)
                                          ↓
gerar sugestões (SuggestionEngine.gerar)
   (6) correlação entre fontes / herança de GPS
   (7) geocodificação de TODA coordenada efetiva
   (5) sessões temporais → transição casa↔fora → cascata → subdivisão em acontecimentos
   (3)(4) evidências por foto → destino → confiança (elo mais fraco)
                                          ↓
detectar duplicatas (job separado)  →  (8) phash / BKTree / rajada
sessão interativa de GenAI de pasta (opt-in) → (9) → cascata na geração seguinte
```

---

## 1. Extração de metadados

### 1.1 Contrato

`Protocol MetadataExtractor` — `fotoorganizer/metadata/base.py:99-106`:

```python
class MetadataExtractor(Protocol):
    def supported_extensions(self) -> set[str]: ...   # extensões COM ponto, minúsculas
    def extract(self, path: Path) -> MediaMetadata: ...
```

Regra de ouro do módulo (`metadata/base.py:1-5`): **um extrator nunca levanta
exceção por arquivo ruim** — devolve `MediaMetadata` com `erro` preenchido e o
scanner cataloga assim mesmo. É o invariante 4 do agente (erro de decode não
derruba processamento) e o aceite M1 do scanner (`scanner/scanner.py:243-247`).

### 1.2 `MediaMetadata` — a saída completa (`metadata/base.py:55-97`)

| Campo | Tipo | Significado |
|---|---|---|
| `data_capturada` | `datetime \| None` | **hora de parede local**, naive, sem fuso |
| `data_capturada_utc` | `datetime \| None` | mesmo instante em UTC, naive; só o `ExifToolExtractor` preenche, e só quando o arquivo DECLARA o offset |
| `make` | `str \| None` | fabricante |
| `model` | `str \| None` | modelo |
| `lente` | `str \| None` | modelo da lente |
| `orientacao` | `int \| None` | 1..8, vocabulário EXIF |
| `largura`, `altura` | `int \| None` | pixels |
| `gps_lat`, `gps_lon` | `float \| None` | grau decimal COM sinal |
| `extras` | `list[tuple[ns, chave, valor]]` | base bruta → `metadata_entries` |
| `palavras_chave` | `tuple[str, ...]` | curadoria humana unificada (namespace `curadoria`) |
| `identidade_de_captura` | `str \| None` | UUID que amarra `.heic` + `.mov` de uma Live Photo |
| `erro` | `str \| None` | `"{TipoDaExcecao}: {mensagem}"` |

**Por que `data_capturada` é hora de parede** (`models/catalog.py:196-202`): é
ela que ordena a grade e agrupa evento e viagem — "8 da manhã em Roma e 8 da
manhã no Rio são a mesma manhã para quem viveu as duas". O EXIF não tem fuso.
Consequência aceita e documentada: quando o fuso é desconhecido,
`data_capturada_utc == data_capturada`, e **a igualdade é como se diz "não sei o
fuso"**, nunca "foi tirada em UTC" (`models/catalog.py:212-217`). Fuso real
`+00:00` fica indistinguível de desconhecido; a saída prevista é
`tz_estimado IS NOT NULL`, nunca a diferença entre as duas colunas
(`models/catalog.py:218-220`). Não existe coluna de offset — um terceiro lugar
para a mesma verdade poderia divergir em silêncio (D-038,
`models/catalog.py:205-211`).

**Plausibilidade da data** (`metadata/base.py:17-35`): `data_plausivel(quando)`
aceita qualquer data `<= agora + _FOLGA_DE_RELOGIO`, com
`_FOLGA_DE_RELOGIO = timedelta(days=1)`. **Não há piso**: filme digitalizado
com data manual pode ser legitimamente de 1950. O motivo do teto: num acervo
real existia exatamente um registro datado de 2100, e ele dominava o topo da
grade ordenada por data. Data impossível não entra na COLUNA; o valor bruto
continua nos `extras` (`purepython.py:307-308` grava
`("exif", "data_invalida", <bruto>)`).

### 1.3 Escolha do extrator (precedência)

`metadata/__init__.py:20-35` — `criar_extrator(preferir_exiftool=True)`:

1. `ExifToolExtractor.disponivel()` (`shutil.which("exiftool")`,
   `exiftool.py:307-309`) → `ExifToolExtractor`.
2. Senão → `PurePythonExtractor`.

A escolha mora **num lugar só** para não existirem quatro versões da mesma
decisão. Medição que a justifica: num CR3 de acervo real são 361 tags do
exiftool contra 8 do libraw, e é o exiftool quem entrega `Make`/`Model` — sem
os quais não há correção de deriva de relógio nem "outra origem" na herança de
GPS (`metadata/__init__.py:22-30`; D-026).

Chamadores: `server/jobs.py:172,347`, `cli.py:205,450`.

### 1.4 `PurePythonExtractor` (`metadata/purepython.py`)

Extensões (`purepython.py:43-51`, `:249-255`):

```python
PILLOW_EXTENSIONS = {".jpg",".jpeg",".png",".tif",".tiff",".webp",".bmp",".gif"}
HEIF_EXTENSIONS   = {".heic",".heif",".hif"}           # só com pillow-heif
RAW_EXTENSIONS    = {".dng",".cr2",".cr3",".nef",".arw",".raf",".orf",".rw2"}  # só com rawpy+exifread
VIDEO_EXTENSIONS  = {".mov",".mp4",".m4v",".avi"}
```

`supported_extensions()` = Pillow ∪ vídeo, mais HEIF se `_HAS_HEIF`
(`:27-30`), mais RAW se `_HAS_RAW` (`:34-41`). Essa lista **governa a
descoberta** (`scanner/scanner.py:205-206` monta `DiscoveryConfig.extensoes`
a partir dela) — um `.mov` numa pasta de fotos era invisível por completo antes
de `VIDEO_EXTENSIONS` existir (`purepython.py:46-51`).

Três rotas em `extract()` (`:257-263`):

**(a) Vídeo** (`:265-272`): devolve `MediaMetadata()` vazio, **sem `erro`** — o
arquivo não está corrompido, só não há extração local dele. Com exiftool
instalado, o `ExifToolExtractor` já leu `QuickTime:CreateDate`/dimensões antes.

**(b) Pillow/HEIF** (`:273-340`), nesta ordem:
1. `img.size` → largura/altura.
2. XMP (`_coletar_xmp`, `:153-168`) e IPTC (`_coletar_iptc`, `:171-198`) vêm
   **ANTES** do short-circuit do EXIF: arquivo editado no Lightroom pode ter
   palavras-chave sem trazer EXIF nenhum (`:277-280`).
3. `exif.get(Make/Model/Orientation)` na IFD0.
4. **`DateTimeOriginal` vem da sub-IFD Exif** (`exif.get_ifd(ExifTags.IFD.Exif)`,
   `:295-297`), com `DateTime` da IFD0 como fallback menos confiável. Formato
   `_EXIF_DATE_FORMAT = "%Y:%m:%d %H:%M:%S"` (`:53`).
5. `LensModel` da sub-IFD.
6. Base bruta: TODAS as tags de IFD0 e sub-IFD, namespace `exif` (`:304-310`).
7. GPS: `exif.get_ifd(ExifTags.IFD.GPSInfo)`, namespace `gps`; conversão DMS→
   decimal com sinal por `_dms_to_decimal` (`:236-241`); falha grava
   `("exif","gps_invalido",…)` (`:324-325`).
8. `_completar_data` (`:334-339`): sem EXIF, a data vem de IPTC/XMP.

**(c) RAW** (`:342-398`):
- **A data vem do libraw** (`raw.other.timestamp`, `:347-348`), que entende
  todas as variantes **inclusive CR3 (ISO-BMFF)**, onde o exifread falha
  silenciosamente (`purepython.py:6-11`).
- `raw.sizes.width/height`, `raw.lens.model`, `raw.sizes.flip`.
- **Conversão de rotação**: `_FLIP_PARA_ORIENTACAO = {0:1, 3:3, 5:8, 6:6}`
  (`:58`). libraw fala dcraw, o catálogo guarda EXIF. `flip == -1` (não sei) cai
  fora do dict e vira `None` — nunca "sem rotação". Medido: 65% de 300 fotos
  reais ficavam sem lente e sem orientação, e todas eram RAW
  (`docs/COBERTURA_METADADOS.md`).
- Base bruta `libraw`: iso, abertura, obturador, distância focal, artista,
  ordem de disparo, focal mín/máx da lente, flip (`:364-374`).
- **`.cr3` retorna cedo** (`:380-382`): exifread não abre ISO-BMFF, e pular
  economiza uma segunda leitura de ~25 MB por foto. O preço, declarado:
  `make`/`model` em branco no CR3 — o libraw não expõe o fabricante, e inferir
  "Canon" do prefixo `EF` da lente seria adivinhação disfarçada de evidência
  (`docs/COBERTURA_METADADOS.md`, seção "make/model no CR3").
- Demais RAW: exifread best-effort para make/model/GPS (`:383-398`); qualquer
  exceção é engolida (`except Exception: pass`, `:397-398`).

**Filtros da base bruta** (`purepython.py:60-98`):
- `_TAGS_OPACAS` (`:63-67`): `MakerNote, UserComment, ICCProfile,
  InterColorProfile, ThumbnailData, PrintImageMatching, XMLPacket, ExifTool,
  JPEGThumbnail, TIFFThumbnail, ImageResources, Padding`.
- `_VALOR_MAX = 500` caracteres (`:68`); `bytes` sempre descartado
  (`:80-81`). O corte é por tamanho, não por adivinhação de tipo.

**IPTC** (`purepython.py:101-119`): allowlist por `(registro, campo)` —
`(2,5) ObjectName`, `(2,25) Keywords`, `(2,55) DateCreated`, `(2,60)
TimeCreated`, `(2,80) By-line`, `(2,85) By-lineTitle`, `(2,90) City`,
`(2,92) Sub-location`, `(2,95) Province-State`, `(2,101)
Country-PrimaryLocationName`, `(2,105) Headline`, `(2,110) Credit`,
`(2,115) Source`, `(2,116) CopyrightNotice`, `(2,120) Caption-Abstract`.

**XMP na leitura** (`purepython.py:122-168`): a árvore XMP é achatada em chaves
pontuadas (`dc.creator`, `photoshop.City`) por `_achatar_xmp`; lista repetível
vira `"a; b; c"` (índice em chave não sobrevive a reprocessamento, `:132-136`).
**Exige `defusedxml`** — `img.getxmp()` do Pillow só analisa XMP com parser
endurecido (`:139-152`). Sem ele `_HAS_XMP = False` e a função retorna em
silêncio, com UM log informativo no import (não um por arquivo: em 500 mil
fotos seriam meio milhão de linhas iguais).

**Data de captura sobrevivente** (`purepython.py:213-234`): quando o EXIF se
perdeu, `_data_dos_extras` procura nas chaves IPTC/XMP cujo último segmento
esteja em `_CHAVES_DATA_EXTRAS = ("datecreated","datetimeoriginal","createdate")`.
`ModifyDate` fica de fora **de propósito** — data de edição não é data de
captura. Aceita ISO-8601 (`fromisoformat`, com `Z` removido) e o `"20150420"`
compacto do IIM; fallback para `"%Y:%m:%d %H:%M:%S"`. Motivo medido: 7.957 JPGs
de acervo estavam sem data por esse caminho.

### 1.5 `ExifToolExtractor` (`metadata/exiftool.py`)

Processo persistente `-stay_open` (`exiftool.py:322-332`): `exiftool -stay_open
True -@ -`. Motivo: `exiftool <arquivo>` por foto paga ~200 ms de partida do
Perl; num scan de dezenas de milhares é a diferença entre minutos e horas
(`:13-17`).

Segurança (invariante 5): sem `shell=True`, argumentos em lista, `stderr`
descartado, `is_file()` verificado (`:396-400`); caminho com `\n`/`\r` **vai
para o fallback** em vez de arriscar o protocolo delimitado por linha
(`:393-395`).

Argumentos de cada rodada (`:351-358`): `-j` (JSON), `-G` (grupo junto da
chave), `-c %+.8f` (coordenada em grau decimal **com sinal**),
`-charset filename=utf8`, `<caminho>`, `-execute`. Terminador `_FIM = "{ready}"`
(`:43`).

**Timeout**: `_TIMEOUT_S = 30.0` (`:44`), imposto por `threading.Timer` que mata
o processo (`:368-369`). É a única espera potencialmente infinita do scan
inteiro; no estouro o `readline` devolve EOF, `_conversar` devolve `None` e o
fallback puro-Python responde pelo arquivo (`:414-417`). Lock de instância
serializa o acesso — o protocolo é uma conversa única por stdin/stdout
(`:294-297`).

**Sidecar XMP na leitura** (`exiftool.py:161-183`): procura `foto.jpg.xmp`
(padrão Adobe) e depois `foto.xmp` (darktable / parte do Lightroom); **o
primeiro que existir vence** — procurar os dois e fundir arriscaria juntar
curadoria de dois editores. Medido: 605 sidecars no acervo, 599 com curadoria
(`docs/INVENTARIO_DE_SINAIS.md` §2).

**Fusão sidecar × original** (`exiftool.py:186-226`): o sidecar vence onde os
dois falam (ele é mais novo por construção). **Exceção crítica — a data**: se o
sidecar declara QUALQUER data de `_TAGS_DE_DATA_DO_SIDECAR`
(`XMP:DateTimeOriginal`, `XMP:DateCreated`, `XMP:CreateDate`, `:156-159`), então
TODAS as tags de `_TAGS_DE_DATA_DO_ORIGINAL` saem (`:148-154`):
`EXIF:DateTimeOriginal`, `EXIF:CreateDate`, `EXIF:ModifyDate`,
`Composite:SubSecDateTimeOriginal`, `Composite:SubSecCreateDate`,
`QuickTime:CreateDate`, `IPTC:DateCreated`, `EXIF:OffsetTimeOriginal`,
`EXIF:OffsetTimeDigitized`, `EXIF:OffsetTime`. Casar a data do editor com o fuso
da câmera produziria um instante que nunca existiu, e o erro seria invisível.
Tags do sidecar entram com grupo `XMPSidecar` (namespace `xmp_sidecar`) **e**
duplicadas nas chaves `XMP:` normais, para a precedência de `_converter`
funcionar sem saber que existe um arquivo ao lado.

**Precedência da hora de parede** (`exiftool.py:449-456`), primeira não-vazia:

```
Composite:SubSecDateTimeOriginal → EXIF:DateTimeOriginal
→ Composite:SubSecCreateDate     → EXIF:CreateDate
→ QuickTime:CreateDate           → XMP:DateCreated
→ IPTC:DateCreated               → EXIF:ModifyDate
```

As duas primeiras carregam subsegundo — não mudam dia nem hora, **desempatam
rajada**, onde seis fotos dividem o mesmo segundo (1.524 fotos do acervo têm
`SubSecTimeOriginal`, `:434-441`). `IPTC:DateCreated` entra antes de
`ModifyDate` porque é a data em que a foto foi FEITA e sobrevive à edição que
apaga o EXIF. **`Composite:GPSDateTime` NÃO entra nesta lista** (`:442-447`),
apesar de ser a data mais confiável do arquivo: ela é UTC, e esta coluna é hora
de parede — colocá-la aqui repetiria o defeito do Takeout, deslocando a foto
pelo tamanho do fuso.

Formatos aceitos (`_FORMATOS_DE_DATA`, `:96-101`): `%Y:%m:%d %H:%M:%S`,
`%Y:%m:%d %H:%M:%S%z`, `%Y-%m-%dT%H:%M:%S`, `%Y-%m-%dT%H:%M:%S%z`, `%Y:%m:%d`,
`%Y-%m-%d`. Limpeza prévia (`:106-107`): corta subsegundos no `.` e troca `Z`
por `+0000`. O resultado é sempre `.replace(tzinfo=None)`.

**Instante absoluto** (`exiftool.py:458-468`): `_offset()` (`:117-146`) lê
`EXIF:OffsetTimeOriginal` → `OffsetTimeDigitized` → `OffsetTime`, regex
`([+-])(\d{2}):?(\d{2})`, recusa `horas > 14` ou `minutos > 59`. Então
`data_capturada_utc = data_capturada - offset` (o offset diz quanto o relógio
local está À FRENTE de UTC: 14h em +02:00 são 12h UTC). `"+00:00"` é aceito como
fato. Medido: 1.527 fotos do acervo tinham o offset e ele estava sendo
descartado.

Demais campos (`:469-480`):
- `make` ← `EXIF:Make` → `XMP:Make`; `model` ← `EXIF:Model` → `XMP:Model`.
- `lente` ← `EXIF:LensModel` → `MakerNotes:LensType` → `XMP:Lens` →
  `Composite:LensID`.
- `orientacao` ← `EXIF:Orientation` mapeado por `_ORIENTACAO` (`:80-89`), que
  traduz as oito strings por extenso do exiftool para 1..8. Pedir `-n` global
  resolveria isso e estragaria a base bruta, que existe para ser lida por gente.
- `largura` ← `EXIF:ExifImageWidth` → `EXIF:ImageWidth` → `File:ImageWidth` →
  `QuickTime:ImageWidth` (idem altura).
- **GPS** ← `Composite:GPSLatitude` / `Composite:GPSLongitude` (`:482-485`).
  Composite já aplica o hemisfério; a tag crua é sempre positiva e usá-la direto
  põe o Rio no hemisfério errado.

**Palavras-chave** (`exiftool.py:228-269`) — quatro formatos, nesta precedência:

```
XMPSidecar:TagsList, XMP:TagsList,
XMPSidecar:HierarchicalSubject, XMP:HierarchicalSubject,
XMPSidecar:Subject, XMP:Subject,
IPTC:Keywords
```

Os dois primeiros pares carregam hierarquia (`"Viagens|2019|Patagônia"`); os
últimos são lista plana. Cada nível da hierarquia entra separado **além** do
caminho inteiro. Deduplicação por `dict.setdefault` preservando ordem. O motivo
é a regra de confiança: o mesmo "Selected" chega pelo `.lrcat` importado E pelo
`.xmp` gravado ao lado, e contar duas vezes a mesma afirmação de uma pessoa só é
soma indevida de confiança (`metadata/base.py:38-52`, `docs/CONFIANCA.md`).

**Live Photo** (`exiftool.py:487-506`): `identidade_de_captura` ←
`Apple:ContentIdentifier` → `QuickTime:ContentIdentifier` →
`Keys:ContentIdentifier` → `XMP:ContentIdentifier`. Não é coluna: entra em
`metadata_entries` sob `("derivado","identidade_de_captura", …)`
(`scanner/scanner.py:503-509`). O ganho maior não é cosmético: o `.mov` costuma
ter GPS quando o `.heic` não tem, e a correlação precisa saber que os dois são a
MESMA captura para não tratar um como doador do outro a Δt zero, o que inflaria
a confiança da herança.

**Namespaces da base bruta** (`_GRUPOS`, `exiftool.py:50-67`): `EXIF→exif`,
`GPS→gps`, `IPTC→iptc`, `XMP→xmp`, `ICC_Profile→icc`, `QuickTime→quicktime`,
`PNG→png`, `XMPSidecar→xmp_sidecar`. O que não estiver no mapa fica de fora:
`File` repete o filesystem, `ExifTool` fala do próprio exiftool, `Composite` é
derivado. **`MakerNotes` fica fora de propósito** (D-027, `:69-78`): ~259 campos
por CR3, 969 mil linhas, 83% de todo o metadado de um acervo real, sem nada que
ajude a decidir viagem, evento ou lugar. Para reativar: devolver
`"MakerNotes": "makernotes"` ao mapa e rodar `scan --reprocessar`.

Tags opacas do exiftool (`:91-94`): `ThumbnailImage, PreviewImage, JpgFromRaw,
OtherImage, ThumbnailTIFF, PhotoshopThumbnail, DataDump, Padding`. Valor que
começa com `"(Binary data"` é pulado; o resto é truncado em **2000 caracteres**
(`:519`). `dict`/`list` viram JSON (`:515-516`).

`supported_extensions()` do exiftool **delega ao fallback** (`:311-316`): o
exiftool entende mais formatos do que o app trata, e alargar aqui faria o
scanner descobrir arquivo que o resto do sistema não sabe tratar.

### 1.6 Hash rápido

Não é do extrator, mas é gerado na mesma passada e é **a chave de tudo que vem
depois** (`scanner/scanner.py:404-419`). `quick_signature`
(`security/hashing.py:20-30`): `xxh3_64` sobre `tamanho (8 bytes LE) + primeiros
64 KiB + últimos 64 KiB` (quando `size > 2*64KiB`), prefixado: `"xxh3:<hex>"`.
`_SAMPLE = 64*1024`. É O(1) por arquivo.

`sha256_full` (`:33-38`): `"sha256:<hex>"`, chunk de `256*1024`, **sob demanda**
(duplicatas nível exato e verificação de cópia).

### 1.7 Degradação

| Falha | Comportamento | Onde |
|---|---|---|
| Arquivo corrompido | `meta.erro` preenchido, catálogo grava a linha | `purepython.py:327-328`, `scanner.py:475` |
| `defusedxml` ausente | XMP não é lido; EXIF e IPTC seguem; 1 log no import | `purepython.py:139-152` |
| `pillow-heif` ausente | HEIC sai de `supported_extensions` (invisível ao scan) | `purepython.py:27-30,251-252` |
| `rawpy`/`exifread` ausentes | RAW sai de `supported_extensions`; se chamado, `erro` explícito | `purepython.py:34-41,343-345` |
| exiftool ausente | `criar_extrator` escolhe puro-Python | `metadata/__init__.py:31-34` |
| exiftool trava | `Timer` mata em 30 s → fallback puro-Python daquele arquivo | `exiftool.py:360-382,414-417` |
| exiftool morre / JSON inválido | `_conversar` → `None` → fallback | `exiftool.py:373-388` |
| Sidecar ilegível | ignorado, original segue | `exiftool.py:420-428` |
| Data impossível | fora da coluna, bruto nos extras | `base.py:20-35`, `purepython.py:307-308`, `exiftool.py:457` |

---

## 2. Thumbnails

### 2.1 Cache (`thumbnails/cache.py`)

- Raiz: `<cache_dir>/thumbs`, com `cache_dir` = `~/Library/Caches/FotoOrganizer`
  por padrão (`config/settings.py:39,69`).
- **Chave = conteúdo, não caminho**: a chave é o `hash_rapido`
  (`server/app.py:847`, `scanner/scanner.py:418`). Duas cópias do mesmo arquivo
  compartilham a miniatura; arquivo alterado ganha chave nova e o cache se
  invalida sozinho (`cache.py:3-7`).
- Sharding: `path_for_key` (`:22-24`) troca `:` por `_` (o prefixo `xxh3:` não
  pode virar diretório) e usa os 2 primeiros caracteres como subpasta:
  `<cache>/thumbs/xx/xxh3_<hex>.jpg`.
- API: `get(chave)`, `get_or_generate(chave, original)` (`:30-38`),
  `tamanho_bytes()` (`:40-43`, soma `rglob("*.jpg")`), `limpar()` (`:45-46`,
  `rmtree`).

### 2.2 Geração (`thumbnails/generator.py`)

```python
THUMB_SIZE = 320       # generator.py:25 — lado maior, caixa (320, 320)
_JPEG_QUALITY = 82     # generator.py:26
_PREVIEW_SIZE = 2048   # server/app.py:240 — JPEG grande do loupe
```

Passos de `generate_thumbnail(source, destino, size)` (`:43-69`):
1. `_open_source` (`:29-41`): se a extensão está em `RAW_EXTENSIONS`, abre a
   **miniatura JPEG embutida** via `rawpy.extract_thumb()` — `ThumbFormat.JPEG`
   vira `Image.open(BytesIO)`, `ThumbFormat.BITMAP` vira `Image.fromarray`;
   caso contrário `Image.open(path)`. HEIC/HEIF funcionam porque
   `pillow_heif.register_heif_opener()` roda no import de
   `fotoorganizer.metadata` (`purepython.py:26-28`).
2. **`ImageOps.exif_transpose(img)`** (`:51`) — a orientação EXIF é aplicada na
   miniatura.
3. `img.thumbnail((size, size))` — preserva proporção.
4. Converte para RGB se o modo não for `RGB`/`L`.
5. Grava em `.tmp` com **sufixo único por processo+thread**
   (`f".{os.getpid()}-{threading.get_ident()}.tmp"`, `:58-60`) e faz
   `tmp.replace(destino)` — duas cópias idênticas geradas em paralelo têm a
   mesma chave e não podem disputar o mesmo `.tmp`.
6. Qualquer exceção → `log.debug` + `return False`. **Nunca levanta.**

### 2.3 Quando a miniatura é gerada

- **Durante o scan**, na mesma leitura do arquivo (`scanner/scanner.py:404-419`):
  "aproveita que o arquivo já está sendo lido" — em RAW, ~0,4 s a menos por
  arquivo depois. Roda nas threads do pool de extração.
- **Sob demanda** na rota `GET /api/midia/{id}/thumb` (`server/app.py:842-851`),
  com `Cache-Control: max-age=31536000`.
- **Preview do loupe**: `GET /api/midia/{id}/preview` (`server/app.py:853-867`),
  diretório separado `<cache_dir>/previews` (`app.py:491`), mesma função com
  `size=_PREVIEW_SIZE`.

### 2.4 Quando NÃO gera

`scanner/scanner.py:408` — `if self._thumb_cache is not None and not
dentro_de_pacote(path)`. Arquivo **dentro de um pacote** (`.photoslibrary`,
`.imageset` etc.) é rebaixado a `MediaRole.SINAL` (`scanner.py:437-439`) e nunca
aparece na grade: a miniatura dele era quase só custo — 2 GB de cache e RAW
inteiro lido pelo SMB no acervo real (`scanner.py:413-417`). O phash das
duplicatas ainda a alcança sob demanda, lendo o original.

### 2.5 Quem reaproveita a miniatura

- Grade e loupe da UI (rotas acima). **Nunca carregar resolução completa para a
  grade.**
- phash das duplicatas: `DuplicateDetector._completar_phashes`
  (`duplicates/detector.py:159-167`) busca `thumb_cache.get(media.hash_rapido)`
  e passa como primeira fonte a `calcular_phash`.
- Capa de card de viagem/evento prefere foto **com miniatura já em cache**
  (`server/app.py:871-882`), porque volume desconectado não gera imagem agora.

### 2.6 Degradação

Imagem indecodificável → `False`/`None` → a UI mostra placeholder
(`generator.py:44-45`, `cache.py:37-38`, `app.py:848-850`). Disco desligado tira
a miniatura, **não** a coordenada: no mapa a foto continua desenhada com
`motivo_indisponivel` preenchido (`server/app.py:365-368`,
`docs/LOCAL_ESTIMADO.md`).

---

## 3. Modelo de evidências e confiança — a seção central

É o que diferencia o produto: **toda sugestão é auditável até a evidência**.

### 3.1 Estrutura persistida

Tabela `evidence` (`models/inference.py:39-58`):

| Coluna | Tipo | Conteúdo |
|---|---|---|
| `media_id` | FK | a foto |
| `campo` | str | `data \| ano \| pais \| regiao \| cidade \| viagem \| evento \| categoria \| tipo` |
| `origem` | str | chave de `SCORES_REFERENCIA` |
| `valor` | Text | o que se afirma |
| `nivel` | enum `alta \| media \| baixa` | derivado do score |
| `score` | float | score de referência, ou modulado |
| `justificativa` | Text | **uma frase em português que o usuário entende** |
| `versao_logica` | str | `VERSAO_LOGICA = "4.1"` (`engine.py:79`) |
| `criado_em` | datetime | |

Tabela de ligação `suggestion_evidence` (`models/inference.py:31-36`): a
sugestão aponta para as evidências que a sustentam — e apenas para elas.

### 3.2 Tabela de referência (`classification/confidence.py:13-84`)

| Origem | Score | Linha | Razão |
|---|---:|---|---|
| `exif` | 0.95 | `:14` | `DateTimeOriginal` coerente |
| `gps` | 0.95 | `:15` | coordenadas EXIF válidas (chave declarada; ver Lacunas) |
| `geocoding_offline` | 0.85 | `:16` | reverse geocoding do dataset local |
| `geocoding_externo` | 0.75 | `:17` | provider externo (chave declarada, sem produtor) |
| `vizinhanca_temporal` | 0.75 | `:22` | GPS herdado de outra fonte; **multiplicado por `fator ≤ 1.0`** |
| `arquivo` | 0.70 | `:51` | tipo da imagem por sinais de arquivo — piso; o detector manda o score real |
| `agrupamento` | 0.70 | `:39` | viagem por lacuna temporal |
| `nome_arquivo` | 0.65 | `:56` | data carimbada no nome |
| `pasta` | 0.60 | `:18` | país/cidade/evento lido do caminho |
| `lexico` | 0.58 | `:47` | o que a PALAVRA significa (opt-in) |
| `album_externo` | 0.55 | `:31` | nome de álbum de catálogo externo que cobre o período |
| `vizinhanca` | 0.55 | `:23` | país dominante da sessão |
| `curadoria` | 0.55 | `:38` | palavra-chave humana XMP/IPTC |
| `llm` | 0.55 | `:40` | advisor de cluster (opt-in) |
| `llm_pasta` | 0.55 | `:83` | GenAI de pasta (opt-in) |
| `fs` | 0.40 | `:57` | mtime |
| `visao` | 0.30 | `:58` | só análise visual (sem produtor — stub) |
| `usuario` | 1.00 | `:59` | correção manual prevalece sobre tudo |

Ordenações que **não** podem ser invertidas sem quebrar o desenho, com o motivo
escrito no próprio código:

- `album_externo` (0.55) **abaixo** de `pasta` (0.60): a foto *está* na pasta e
  apenas *coincide no tempo* com o álbum — 100% das 27.226 nomeações vivem em
  registros sem arquivo local (`confidence.py:24-31`, D-030/D-034).
- `curadoria` (0.55) mesmo motivo: é palavra do dono, mas não é a organização
  dele em diretório — pode ter vindo de editor de terceiro (`:32-38`).
- `lexico` (0.58) **acima** de `llm` e **abaixo** de `pasta`: a pergunta é muito
  mais estreita (classificar um substantivo em quatro categorias) mas o
  significado é nosso; quando a pasta decide sozinha, ela decide (`:41-47`).
- `nome_arquivo` (0.65) **acima** de `fs` e **abaixo** de `exif`: o nome nasce
  com o arquivo, o mtime muda a cada cópia; mas a data do WhatsApp é a do
  RECEBIMENTO, não a do clique (`:52-56`).
- `llm_pasta` é **chave separada** de `llm` mesmo com o mesmo número: são
  afirmações de natureza diferente (nome de pasta × metadado de mídia), e
  `docs/CONFIANCA.md` proíbe fundir origens distintas (`:60-83`, D-081).

**Níveis** (`confidence.py:86-95`): `_LIMIAR_ALTA = 0.8`, `_LIMIAR_MEDIA = 0.5`.
`score ≥ 0.8 → ALTA`; `≥ 0.5 → MEDIA`; `< 0.5 → BAIXA`. Os níveis são a
interface estável com a UI (badges); os scores são configuráveis no futuro
(`docs/CONFIANCA.md`, última seção).

### 3.3 Regra de combinação — **elo mais fraco, nunca soma**

`elo_mais_fraco(scores)` (`confidence.py:98-103`):

```python
if not scores: return ConfidenceLevel.BAIXA, 0.0
menor = min(scores)
return nivel_para_score(menor), menor
```

Aplicado em `SuggestionEngine._salvar_sugestao` (`engine.py:1276-1290`) **só
sobre `usados`** — as evidências que de fato decidiram o destino. Contexto que
não virou pasta **não** puxa o elo para baixo (`engine.py:1279-1281`).

Três consequências que o código implementa explicitamente e que a reconstrução
não pode perder:

1. **Concordância não sobe score.** O ano lido da pasta que confere com o EXIF é
   registrado como evidência (`engine.py:826-844`) mas é removido de `usados`
   (`engine.py:1266-1274`): "o ano do destino veio do EXIF; o da pasta é
   testemunha, não fonte" — e `docs/CONFIANCA.md` proíbe soma de confianças.
   Idem na herança: uma segunda doadora concordante ganha uma frase extra na
   justificativa e **o mesmo fator de sempre** (`correlacao.py:243-251`,
   `engine.py:952-957`, D-074).
2. **Lugar suprimido do caminho continua vinculado à sugestão.**
   `_contexto_da_sugestao` (`engine.py:1126-1143`) anexa país/região/cidade que
   não viraram pasta — sem vínculo, a justificativa existiria no banco e não
   chegaria a lugar nenhum (`Suggestion.evidencias` é o que a API serializa).
3. **Sem evidência, não se inventa.** `_evidencias_geo` termina com
   `return []  # sem evidência: não inventa localização` (`engine.py:1025`).

### 3.4 Como uma sugestão responde "por quê?"

A justificativa é montada em português, no ponto em que a evidência nasce, e
cita o indício. Exemplos **reais do catálogo** (`SELECT` somente leitura sobre
`~/Library/Application Support/FotoOrganizer/catalog.db`, 102.251 mídias):

| origem | campo | valor | justificativa |
|---|---|---|---|
| `geocoding_offline` | cidade | Traipu | `geocodificação offline das coordenadas GPS do EXIF (-10.0159, -36.9598)` |
| `geocoding_offline` | viagem | Brasil – Bolívia | `2450 fotos entre 15/07/2023 – 22/07/2023 — fotos com GPS em Brasil ao longo de 7 dias` |
| `vizinhanca_temporal` | cidade | Poconé | `GPS herdado de 'ACM_6412.dng' (Canon EOS R6m2) — tirada a 40s de distância` |
| `vizinhanca` | pais | Brasil | `outras fotos da mesma sessão têm GPS em Brasil` |
| `pasta` | viagem | Dubai, Thai & Viet | `2405 fotos entre 01/11/2025 – 21/11/2025 — pasta 'Dubai, Thai & Viet' lista 3 destinos: Emirados Árabes Unidos, Tailândia, Vietnã` |
| `pasta` | ano | 2023 | `'Jul.2023' escrito no nome da pasta — confere com o EXIF` |
| `album_externo` | viagem | Estrada Real | `363 fotos entre 27/03/2025 – 08/04/2025 — fotos com GPS em Brasil ao longo de 13 dias; nome do álbum 'Estrada Real' (Apple Fotos), que cobre 58 fotos deste período` |
| `nome_arquivo` | data | 2014-07-06T00:00:00 | `sem EXIF; '20140706' no nome do arquivo (padrão de câmera de celular)` |
| `fs` | data | 2023-06-10T15:41:31 | `sem EXIF; data de modificação do arquivo (pouco confiável)` |
| `arquivo` | tipo | baixada da web | `está na pasta de downloads e não tem dado de câmera — a confirmar` |

Distribuição real de `evidence` (mesma consulta, 102.251 mídias):

```
data|exif|ALTA                    53967   score 0.95
ano|pasta|MEDIA                   32484   0.60
categoria|geocoding_offline|ALTA  13271   0.85
viagem|geocoding_offline|ALTA     12557   0.85
categoria|pasta|MEDIA             11366   0.60
pais|vizinhanca_temporal|MEDIA    10507   0.505–0.75
evento|pasta|MEDIA                 7673   0.60
pais|vizinhanca|MEDIA              7506   0.55
cidade/pais/regiao|geocoding_offline|ALTA  3648 cada   0.85
cidade|vizinhanca_temporal|BAIXA   2521   0.28–0.499
viagem|pasta|MEDIA                 2405   0.60
viagem|album_externo|MEDIA         1605   0.55
data|fs|BAIXA                      1121   0.40
tipo|arquivo|MEDIA/ALTA            385/37 0.55 / 0.80–0.95
data|nome_arquivo|MEDIA               8   0.65
```

Sugestões por nível: `ALTA 40.747`, `MEDIA 13.044`, `BAIXA 1.305`.
Justificativas com a frase de concordância D-074: 880. Com o aviso de hora de
arquivo: 806. Com o aviso de granularidade ("a essa distância dá para afirmar
o país/a região, não a cidade"): 10.221.

### 3.5 Regeneração e preservação

- `_midias_com_decisao` (`engine.py:1120-1124`): mídia com `Suggestion.status !=
  PENDENTE` é **pulada inteira** na geração — decisão do usuário é preservada.
  `SuggestionStatus = pendente | aprovada | rejeitada | editada`
  (`models/inference.py:24-28`).
- `_persistir_sugestao` (`engine.py:1181-1194`): apaga as PENDENTES antigas da
  mídia, os vínculos e **todas** as `Evidence` daquela mídia, depois recria.
- `_descartar_sugestoes_orfas` (`engine.py:1144-1179`): apaga sugestões
  **PENDENTES** de mídia que deixou de ser acervo (rebaixada a testemunha). Num
  catálogo real foram 45.822 sugestões que ficariam pedindo decisão sobre
  miniatura. Aprovada e rejeitada **não** são apagadas. O alvo é uma
  `scalar_subquery`, não uma lista de ids: `IN (?, ?, …)` com 45.822 valores
  estoura o limite de variáveis do SQLite.
- `trips`/`events` são **recriados do zero** a cada `gerar()`
  (`engine.py:745-758`): `media.trip_id = media.event_id = None` para TODAS as
  mídias (inclusive as rebaixadas, senão o `DELETE` esbarra na FK), depois
  `delete(Trip)`, `delete(Event)`.

---

## 4. Cascata de classificação (`classification/engine.py`, 1289 linhas)

### 4.1 Construtor

```python
SuggestionEngine(
    session_factory,
    resolver: LocationResolver | None = None,
    template: str = TEMPLATE_PADRAO,
    advisor: ClassificationAdvisor | None = None,
    config: ConfigClassificacao = ConfigClassificacao(),
    lexico: dict[str, str] | None = None,              # {nome: categoria}
    pastas_classificadas: dict[str, PropostaDePasta] | None = None,
)   # engine.py:246-272
```

`lexico` e `pastas_classificadas` são lidos **do cache local, em lote, uma vez
por rodada** — nada sai da máquina em `gerar()` (`engine.py:262-272`,
`server/jobs.py:207-224`). Vazios = a cascata decide exatamente como decidia
antes.

Wiring de produção (`server/jobs.py:196-234`): template de
`SettingsRepository.obter_template(TEMPLATE_PADRAO)`, resolver
`LocationResolver(OfflineGeocoder())`, advisor de `_advisor()`
(`jobs.py:335-346`, `None` sem `servicos_externos`), léxico de
`LexicoRepository.conhecidos()`, propostas de
`ClassificacaoPastaRepository.aprovadas()`.

### 4.2 `gerar()` passo a passo (`engine.py:275-348`)

```
 1. midias      = todas as MediaFile                                    :277
 2. decididas   = ids com Suggestion.status != PENDENTE                 :278
 3. curadoria   = {media_id: (palavras-chave,)} numa consulta só        :280,116-134
 4. herancas    = _correlacionar(TODAS as mídias)                       :287
      ↑ inclusive referências sem arquivo local: são elas que trazem
        GPS de celular numa biblioteca em iCloud
 5. _persistir_herancas(midias, herancas)                               :288,350-372
 6. _resolver_locations(session, midias)                                :300,374-409
      ↑ geocodifica TODA foto com coordenada efetiva ANTES de sessão/
        categoria (regra "geo-first", D-051/D-052/D-058)
 7. organizaveis = [m for m in midias if m.organizavel]                 :306
 8. orfas       = _descartar_sugestoes_orfas(session)                   :307
 9. sessoes, sessao_da_media = _montar_sessoes(...)                     :309-311
10. _persistir_agrupamentos(...)  → cria Trip/Event                     :312-314
11. _atualizar_tz_estimado(...)   → para TODA organizável (CR-01)       :323-325
12. para cada organizável NÃO decidida:
       drafts = _evidencias_para(...)                                   :331-336
       _persistir_sugestao(...)                                         :337
       commit a cada 500                                                :339-340
13. retorna {sugestoes, viagens, eventos, herancas_gps, preservadas,
             descartadas}                                               :343-348
```

Dois recálculos são **incondicionais** (rodam mesmo para mídia com sugestão já
decidida, que nunca passa pelo laço 12), porque senão congelariam para sempre no
valor da última rodada em que a sugestão ainda estava pendente:
`gps_*_estimado` (passo 5) e `tz_estimado` (passo 11, CR-01,
`engine.py:316-322,447-462`).

`_persistir_herancas` (`:350-372`): grava `gps_lat_estimado`,
`gps_lon_estimado`, `gps_estimado_de_id`, `gps_estimado_delta_s` (segundos,
inteiro). **Limpa os quatro** quando não há doador ou quando a foto passou a ter
coordenada própria. Reescreve a cada rodada porque a herança depende do
conjunto.

`_resolver_locations` (`:374-409`): memoiza por `cache_key` **dentro do loop**,
não só na tabela `locations` — sem isso, uma viagem de 500 fotos na mesma
coordenada arredondada vira 500 SELECTs. Grava `location_id` **inclusive
`None`**: coordenada que deixou de resolver não pode deixar a mídia presa a um
país que ela não tem mais (WR-01, `:401-407`).

`_atualizar_tz_estimado` (`:447-462`) usa `_pais_efetivo` (`:411-445`), que
repete a cascata geográfica **sem gravar evidência**: GPS próprio → GPS herdado
(só se `heranca.fator_de("pais")` não for `None`) → país da pasta → país
dominante da sessão. Duplicada de propósito para não arriscar mudar o texto das
justificativas existentes. Depois `media.tz_estimado = TZ_POR_PAIS.get(pais)`.

### 4.3 `_Draft` (`engine.py:203-217`)

```python
@dataclass(slots=True)
class _Draft:
    campo: str
    origem: str
    valor: str
    justificativa: str
    score_override: float | None = None   # herança modula pelo Δt; detector de tipo manda o próprio

    @property
    def score(self) -> float:
        return self.score_override if self.score_override is not None \
               else SCORES_REFERENCIA[self.origem]
```

É a evidência antes de virar linha no banco. `_persistir_sugestao` converte cada
`_Draft` em `Evidence` e indexa por campo num dict — **um draft por campo
vence**: `evidencias[draft.campo] = evidencia` (`engine.py:1196-1207`), o último
draft de um campo sobrescreve os anteriores no dict de destino (todos continuam
gravados como linhas em `evidence`).

### 4.4 `_Sessao` (`engine.py:219-243`)

Campos: `draft: ViagemDraft`, `tipo ∈ {viagem, evento, neutra}`, `rotulo`,
`origem`, `origem_do_rotulo`, `justificativa`, `categoria` (só do advisor),
`pais_dominante`, `lugares` (até 5), `trip_id`, `event_id`.
`periodo_curto()` (`:239-243`) → `"Viagem de 08-07 a 11-07"` ou
`"Viagem de 08-07"`.

`origem_do_rotulo` existe separada de `origem` porque as duas divergem: a sessão
pode ser viagem pelo GPS (`geocoding_offline`) e o nome vir do álbum
(`album_externo`). A categoria cita `origem`; a evidência de viagem/evento, cujo
valor **é** o rótulo, cita `origem_do_rotulo` (`grouping/classifier.py:78-86`).

### 4.5 Cascata por campo

#### `tipo` (`engine.py:793-819`)

`classificar_tipo(...)` (`classification/tipo_imagem.py:107-199`) roda **antes
de tudo** — o que não é foto não deve ser organizado por viagem. Entrada: nome,
pasta, extensão, largura, altura, make, model, lente, `tem_gps`.

**`tem_gps` usa `media.gps_lat` (LIDO do arquivo), nunca a coordenada efetiva**
(`engine.py:800-805`): a coordenada herdada é justamente o que uma captura de
tela feita no meio da viagem ganha das fotos vizinhas; usar a efetiva
transformaria a herança em atestado de origem de câmera.

Ordem interna do detector (`tipo_imagem.py:137-199`), do sinal mais específico
ao mais fraco — "na dúvida, é foto" (`tipo_imagem.py:12-16`):

| # | Sinal | Veredito | Score |
|---|---|---|---:|
| 0 | tem GPS gravado | `foto` | 0.95 |
| 1 | nome `^(IMG\|VID\|AUD\|PTT)-\d{8}-WA\d+` ou `^WhatsApp (Image\|Video)\b` | `recebida` | 0.95 |
| 1 | nome `^photo_\d{4}-\d{2}-\d{2}_` (Telegram) | `recebida` | 0.90 |
| 1 | nome `^(captura de (tela\|ecrã\|ecra)\|screenshot\|screen shot\|simulator screen shot)` | `captura` | 0.95 |
| 2 | pasta contém `whatsapp\|telegram\|signal\|messenger` | `recebida` | 0.85 |
| 2 | pasta contém `screenshots\|capturas de tela\|capturas` | `captura` | 0.85 |
| 3 | `(largura, altura)` em `_TELAS` **e** sem assinatura de câmera | `captura` | 0.85 |
| 4 | pasta `downloads\|transferências\|transferencias` sem câmera | `baixada` | 0.80 |
| 4 | nome `^(image\|imagem\|unnamed\|download\|untitled\|sem[-_ ]t[ií]tulo)[\s_-]*(\(\d+\))?$` sem câmera | `baixada` | 0.70 |
| 5 | extensão `png` sem câmera | `captura` | 0.55 |
| 6 | sem câmera e `largura*altura < _MP_MINIMO` | `recebida` | 0.55 |
| 7 | sem câmera, nada indica o contrário | `foto` | 0.50 |
| 8 | tem câmera | `foto` | 0.90 |

Constantes: `_MP_MINIMO = 480_000` (≈ 800×600, `tipo_imagem.py:99`) —
deliberadamente baixo, porque uma compacta de 1999 tirava 0,78 MP e marcar a
foto de infância de alguém como lixo custa a confiança no catálogo inteiro.
`_TELAS` (`:84-91`) tem 24 resoluções (Apple + monitores) **e suas transpostas**.
Vocabulário de pasta compartilhado com `grouping/origens.py:14-16`, um
vocabulário, dois usos.

Normalização de pasta por `_normalizar` (NFKD + ascii + lower,
`geolocation/folder_names.py:41-45`), não só `lower()`: o Finder/APFS grava
pasta acentuada em NFD (D-066, `tipo_imagem.py:130-134`).

No motor:
- `media.tipo_imagem = veredito.tipo` **sempre** (reescrito a cada geração — um
  arquivo reprocessado pode ganhar EXIF).
- `media.tipo_confirmado` **nunca** é tocado: é palavra do usuário
  (`engine.py:806-808`, gravada por `POST /api/midia/{id}/tipo`,
  `server/app.py:815-839`).
- Draft de `tipo` só nasce quando o veredito **não** é `foto`:
  origem `usuario` score 1.0 se confirmado, senão origem `arquivo` com
  `score_override = veredito.score` e justificativa `"<motivo> — a confirmar"`
  (`engine.py:809-819`).

#### `data` — exatamente UMA evidência por foto (`engine.py:821-845`)

```
1. media.data_capturada  → origem "exif"        0.95
     "data de captura lida do EXIF (DateTimeOriginal)"
2. data_no_nome(media.nome) → origem "nome_arquivo" 0.65
     "sem EXIF; '<texto>' no nome do arquivo (<padrão>)"
3. media.mtime → origem "fs"                     0.40
     "sem EXIF; data de modificação do arquivo (pouco confiável)"
```

"Uma evidência só de data por foto: é ela que vira o `{ano}` do destino, e duas
testemunhas do mesmo campo disputariam a vaga" (`engine.py:821-825`).

`data_no_nome` (`grouping/datas.py:243-270`) reconhece três convenções, nesta
ordem, e sempre valida a data (`_data_valida`, `:232-240`, com o mesmo teto de
"foto não nasce no futuro"):

| Padrão | Regex | `padrao` reportado |
|---|---|---|
| WhatsApp | `^(?:IMG\|VID\|AUD\|PTT)-(\d{8})-WA` | `convenção do WhatsApp` |
| ISO | `(?<!\d)((?:19\|20)\d{2})-(\d{2})-(\d{2})(?!\d)` | `data escrita no nome` |
| compacto | `(?<!\d)((?:19\|20)\d{2})(\d{2})(\d{2})(?!\d)` | `padrão de câmera de celular` |

Os lookarounds `(?<!\d)`/`(?!\d)` isolam o número: um serial de 13 dígitos que
contém "20240315" no meio é serial, não data (`datas.py:224-226`).

#### `ano` — segunda testemunha, nunca fonte (`engine.py:826-844`)

`data_no_caminho(media.pasta)` (`grouping/datas.py:179-193`) procura da **folha
para a raiz** a data mais específica; em empate de ano, a de maior precisão
(`_precisao` = tem mês + tem dia). Gera draft `("ano", "pasta", str(ano))` com
justificativa `"'<texto>' escrito no nome da pasta"`, mais:
- `" — confere com o EXIF"` quando `data_capturada.year == data_pasta.ano`;
- `" — DIVERGE do EXIF (<ano do exif>)"` quando não.

O EXIF continua mandando no destino: `campos["ano"]` é derivado de
`evidencias["data"]` (`engine.py:1213-1215`) e o draft de `ano` é **removido de
`usados`** (`engine.py:1266-1274`).

`separar_data(segmento)` (`datas.py:150-177`) é a função-base: normaliza para
NFC **uma vez, no início** (índices de fatiamento ficam presos à string
normalizada — NFC e NFD têm comprimentos diferentes, D-067, `datas.py:25-34`),
testa `_PADROES` (`:79-115`) em ordem do mais específico ao mais genérico:

1. `ano-mes-dia` (`2025-05-24`, `2025_05_24`, `2025.05.24`)
2. `dia-mes-ano` (`24-05-2025` — **convenção brasileira**, `datas.py:11-14`)
3. `dia de <mês> de ano` (`29 de outubro de 2016`) — D-073: sem ele, "29 de"
   sobrava como se fosse nome, e 303 fotos reais tinham destino
   `Eventos/2016/29 de`
4. `<mês> [de] ano` (`Abril 2015`, `Jul.2023`, `Julho de 2023`, `Abril/2015`)
5. `ano-mes` com separador `[-_.]` (não aceita espaço: "Rio 2016 04" é ano +
   número)
6. `ano` sozinho

`_ANO = r"(?:18|19|20)\d{2}"` (`:55`) — a âncora que impede "15 Anos" de virar
data e "Serena 15 Anos" de perder o nome. `_SEP = r"[-_./ ]"` (`:56`).
`_MESES` (`:35-50`) cobre PT e EN, com e sem acento, abreviado e por extenso;
`_MES_ALT` ordena por comprimento decrescente para "janeiro" casar antes de
"jan". Validação: mês 1..12, dia 1..31 (`_montar`, `:129-147`).

`_MES_DIA_SEM_ANO = ^<mês> <dia>$` (`:117-120`) — "novembro 30" não vira
`DataDaPasta` (falta o ano) mas também **não é nome**: sem isto virava nome de
álbum e podia ser promovido a evento falso pela regra 6 da cascata. Ancorado no
segmento inteiro: "Viagem novembro 30" é nome de verdade.

`rotulo_mes(ano, mes)` (`datas.py:203-206`) → `"jul.2023"` — o formato que o
dono já usa no próprio acervo, em minúsculas.

#### Geografia: `pais`, `regiao`, `cidade` (`_evidencias_geo`, `engine.py:902-1025`)

**Cada ramo que resolve faz `return` — não há acúmulo entre ramos.**

```
1.  GPS PRÓPRIO + resolver                                          :908-926
      → até 3 drafts, origem "geocoding_offline" (0.85)
      → justificativa: "geocodificação offline das coordenadas GPS do
        EXIF (<lat:.4f>, <lon:.4f>)"
      → grava media.location_id

1b. GPS HERDADO (Heranca) + resolver                                :928-983
      → um draft por campo em que heranca.fator_de(campo) is not None
      → score = round(SCORES_REFERENCIA["vizinhanca_temporal"] * fator, 3)
      → justificativa base: "GPS herdado de '<nome>' (<câmera>) — tirada
        a <Δt legível> de distância"
        + se granularidade != "cidade": "; a essa distância dá para afirmar
          <o país|a região>, não a cidade"
        + se heranca.hora_incerta: "; a hora de uma delas é a do arquivo,
          não a da captura — a proximidade pode ser coincidência"
        + se campo in heranca.concordancia: "; confirmada por outra foto do
          lado oposto no tempo, na mesma área plausível"

2.  NOME DA PASTA (extrair_hierarquia_da_pasta)                     :985-996
      → até 3 drafts, origem "pasta" (0.60)
      → justificativa: "reconhecido no caminho da pasta ('<segmento>')"

2c. PROPOSTA GenAI DE PASTA aprovada (cidade/país)                  :998-1017
      → origem "llm_pasta" (0.55), justificativa = a do modelo
      → fica ACIMA da vizinhança porque a proposta é sobre ESTA pasta

3.  VIZINHANÇA: país dominante da sessão                            :1019-1024
      → 1 draft ("pais", "vizinhanca", 0.55)
      → "outras fotos da mesma sessão têm GPS em <país>"

4.  return []  — não inventa localização                            :1025
```

`_delta_legivel` (`engine.py:82-86`): `<60s → "Ns"`, senão `"Nmin"`.
`_camera_legivel` (`:88-92`): `" (Canon EOS R6m2)"` via
`nome_da_camera(make, model)`.

`nome_da_camera` (`metadata/camera.py:23-38`): se o modelo já começa pelo
fabricante **em fronteira de palavra**, o modelo basta — `("Canon", "Canon EOS
5D Mark III")` → `"Canon EOS 5D Mark III"`, não "Canon Canon EOS…". A comparação
por prefixo exige que o caractere seguinte não seja alfanumérico, para
"Canonical" não casar com "Canon". Nunca remove pedaço do meio.

#### `viagem` e `evento` (`engine.py:876-900`)

Quando `sessao.tipo == "viagem"`:
`_Draft("viagem", sessao.origem_do_rotulo, sessao.rotulo, "<N> fotos entre
<período> — <justificativa da sessão>")`.
Quando `== "evento"`: idem com `"<N> fotos em <período>"`.
`periodo_legivel()` (`grouping/temporal.py:25-29`): `"dd/mm/aaaa"` ou
`"dd/mm/aaaa – dd/mm/aaaa"`.

Evento da proposta GenAI (`engine.py:886-900`) só entra **se nenhum draft de
`evento` existe** — a sessão determinística tem precedência absoluta; a proposta
só preenche o silêncio.

#### `categoria` (`_categoria`, `engine.py:1027-1083`)

```
1.  Segmento de pasta em _CATEGORIAS_PASTA, procurando da FOLHA para a raiz
        {"viagens","viagem"→"Viagens"; "familia","família"→"Família";
         "eventos","evento"→"Eventos"}                  engine.py:95-97,1032-1039
        origem "pasta" (0.60) — "pasta '<seg>' no caminho original"
2.  Tipo da sessão: viagem → "Viagens"; evento → "Eventos"
        origem = sessao.origem (0.60–0.85 conforme a regra que decidiu)
        justificativa = sessao.justificativa                     :1045-1052
2b. Palavra-chave humana (XMP/IPTC) com o MESMO vocabulário
        origem "curadoria" (0.55)                                :1053-1066
        "palavra-chave '<p>' (XMP/IPTC) na foto"
3.  sessao.categoria do advisor de cluster → origem "llm" (0.55) :1067-1071
3b. proposta_de_pasta.categoria → origem "llm_pasta" (0.55)      :1072-1081
4.  None
```

A ordem 2 antes de 2b é deliberada e está escrita no código
(`engine.py:1040-1044`): a sessão é o mesmo veredito para todas as fotos do
grupo, e uma palavra-chave de uma foto só não pode fragmentar esse veredito.
2b acima de 3 porque é determinístico e grátis. 3b é **irmão** de 3, nunca
fundido: a origem chega diferente ao banco (`llm_pasta` ≠ `llm`) porque são
afirmações de natureza distinta e a Revisão precisa distinguir as duas.

### 4.6 Templates de destino (`classification/templates.py`)

```python
TEMPLATE_PADRAO = "{categoria}/{ano} - {viagem}/{evento}/{pais}/{regiao}/{cidade}"
DESTINO_NAO_CLASSIFICADO = "Não classificadas"
DESTINO_NAO_FOTO = "Não são fotos"
_MAX_SEGMENTO = 80
_CHARS_INVALIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_RE_PARTES = re.compile(r"\s+[-–—]\s+")
```
(`templates.py:24-52`)

Placeholders reconhecidos são **quaisquer** `{palavra}` — o dict `campos` decide.
Os que o motor preenche: `categoria`, `ano`, `viagem`, `evento`, `pais`,
`regiao`, `cidade` (`engine.py:1213-1215`). `ano` é derivado da evidência `data`
(`datetime.fromisoformat(...).year`).

Regras de `render_destino` (`:99-107`) / `_render_segmento` (`:72-96`):
1. Segmento cujos placeholders ficaram **todos** vazios é descartado inteiro.
2. Valor que **já apareceu acima no caminho** não repete. A comparação é por
   parte inteira (`_partes` quebra em ` - `/` – `/` — `), normalizada sem acento
   e sem caixa (`_chave`, `:55-63`) — senão "York" sumiria sob "New York".
   Exemplo real: `2025 - Tailândia – Vietnã/Tailândia/Chiang Mai/Chiang Mai` →
   `2025 - Tailândia – Vietnã/Chiang Mai`.
3. Sobras de separador são aparadas: `"2024 - "` → `"2024"`; `" - - "` → `" - "`.
4. `normalizar_segmento` (`:38-49`): NFC, inválidos → `_`, espaços colapsados,
   `strip(". ")` nas bordas (problemáticas em vários filesystems), truncado em
   80 com `rstrip(". ")`.
5. Tudo vazio → `"Não classificadas"`.

`resolver_colisao(destino, existentes)` (`:110-117`): sufixa `" (2)"`, `" (3)"`…
até 9.999; nunca sobrescreve nome usado.

### 4.7 Montagem do destino (`_persistir_sugestao`, `engine.py:1181-1274`)

```
campos = {campo: evidencia.valor}                              :1213
campos["ano"] = ano de evidencias["data"]                      :1214-1215
sem_nome = nenhum de _CAMPOS_QUE_NOMEIAM preenchido            :1216
           ("categoria","viagem","evento","pais","regiao","cidade")  :100-101

SE campos["viagem"] ou campos["evento"]:                       :1228-1229
    campos["pais"] = campos["regiao"] = campos["cidade"] = None
    # UMA VIAGEM É UMA PASTA. Motivo medido: das 2.405 fotos de uma
    # mesma viagem, 106 tinham coordenada — deixar a hierarquia descer
    # partia a viagem em três pastas conforme QUAL foto por acaso
    # gravou GPS, que é acidente de equipamento (:1218-1227)
    # O lugar continua gravado como evidência e visível no inspetor.

SE media.tipo_efetivo not in (None, "foto"):                   :1231-1239
    destino = "Não são fotos/<Rótulo capitalizado>[/<ano>]"    :1084-1096
    usados = {tipo, data}

SENÃO SE sem_nome:                                             :1241-1252
    destino = _destino_nao_classificado(...)                   :1097-1118
      "Não classificadas/<ano>/<jul.2023>"  (data da evidência)
      ou, sem evidência de data, data_no_caminho(pasta):
        sem mês → "Não classificadas/<ano>"
        sem data → "Não classificadas/sem data"
    usados = {data}, contexto = lugar não usado

SENÃO:                                                          :1254-1274
    destino = render_destino(template, campos)
    usados  = {campo: ev for campo in evidencias
               if "{campo}" está no template e campos[campo] tem valor}
    se "{ano}" no template e há "data": usados["data"] = …; usados.pop("ano")
```

`_salvar_sugestao` (`:1276-1290`) então calcula
`nivel, _score = elo_mais_fraco([ev.score for ev in usados.values()])`, cria a
`Suggestion(media_id, destino_sugerido, template, nivel, versao_logica)` e
vincula `usados + contexto`.

---

## 5. Agrupamento temporal

### 5.1 Base de tempo

**Em todo o motor a base é `media.data_capturada or media.mtime`**
(`engine.py:469, 501, 571-573, 585`, `_IndiceDeAlbuns` em `:167`). Fotos sem
nenhum dos dois ficam de fora (`engine.py:502-504`).

⚠️ **Divergência conhecida (M1 da auditoria de 2026-09-19)**: `data_capturada` é
hora de parede local (`models/catalog.py:195-202`) e `mtime` é UTC naive
(`scanner/scanner.py:117-119`). No acervo real, 33,3% de 53.967 registros têm
delta múltiplo exato de 1 h (+3h em 17.468). 1.129 fotos só-mtime (1.046 sem
GPS) perdem herança de cidade/região (`correlacao.py:424-425`); eventos
(`eventos_temporais.py:56-58`) podem cortar errado; viagens são imunes (gap de
3 dias).

⚠️ **Divergência conhecida (M5)**: a cascata de `data` prefere o nome do arquivo
ao mtime (`engine.py:827-844`), mas a linha do tempo **ignora** o nome
(`engine.py:469`). `IMG-20150420-WA0001.jpg` copiado em 2024 recebe ano 2015 e
viagem de 2024.

### 5.2 Sessões por lacuna temporal (`grouping/temporal.py`)

```python
GAP_NOVA_VIAGEM = timedelta(days=3)     # temporal.py:13
```

`agrupar_viagens(itens, gap=GAP_NOVA_VIAGEM)` (`:32-52`): ordena por data e
corta onde `(data - atual.fim) > gap`. **Não usa dia de calendário** — uma
viagem pode durar semanas; o que separa é a lacuna longa sem fotos
(`temporal.py:1-6`).

`ViagemDraft` (`:16-29`): `inicio`, `fim`, `media_ids`, `n_fotos`,
`periodo_legivel()`.

### 5.3 Transição casa↔fora (`temporal.py:55-113`)

Só roda quando a casa é conhecida (`engine.py:508-515`).

**Detecção da casa** (`geolocation/home.py:29-40`): célula GPS modal,
arredondando a `_PRECISAO_CELULA = 1` casa decimal (≈ 11 km), exigindo
`_MIN_FOTOS_GPS = 20` fotos com GPS e `_FRACAO_MINIMA = 0.30` delas na célula.
Abaixo disso, "casa desconhecida". **Só GPS real** entra
(`engine.py:505-508`): coordenadas herdadas repetem as dos doadores e
inflariam artificialmente a célula modal.

`dividir_por_transicao_casa(itens)` recebe `[(media_id, data, estado)]` com
`estado = distancia_km(coords, casa) <= config.raio_casa_km` (50 km,
`classifier.py:33`) ou `None` sem coordenada (herda o estado corrente).
**A transição só corta quando confirmada pela foto com GPS SEGUINTE no mesmo
estado novo** (`temporal.py:81-88, 100-102`): uma foto isolada (GPS errado,
escala rápida perto de casa) não divide uma viagem real.

Depois do corte, `drafts = [d for d in drafts if d.n_fotos >= _MIN_FOTOS_SESSAO]`
com `_MIN_FOTOS_SESSAO = 2` (`engine.py:98,518`).

### 5.4 Sessão 100% mtime é neutra (`engine.py:525-543`)

```python
if any(m.data_capturada for m in membros):
    sessao = self._classificar(...)
    if sessao.tipo == "neutra" and self._advisor is not None:
        self._consultar_advisor(sessao, membros)
else:
    sessao = _Sessao(draft=draft)   # neutra, sem classificar
```

Motivo escrito no código (`:534-542`): "o que sobrou é mtime, a data em que o
arquivo chegou ao disco. Agrupar por ela cria uma 'viagem' no dia do scan —
captura de tela e arquivo recuperado viram passeio." A foto continua catalogada
e cai no ramo de não classificadas.

### 5.5 Cascata determinística de sessão (`grouping/classifier.py`)

Função pura, testável cenário a cenário e comparável entre variantes
(`scripts/avaliar_agrupamento.py`).

**`ConfigClassificacao`** (`classifier.py:23-38`):

| Campo | Default | Papel |
|---|---:|---|
| `duracao_min_viagem` | `3 dias` | estadia mínima para GPS geocodificado virar viagem (regra 5) |
| `duracao_max_evento` | `2 dias` | duração máxima para nome de álbum virar evento (regra 6) |
| `dist_viagem_km` | `100.0` | distância mediana até casa que caracteriza deslocamento (regra 4) |
| `raio_casa_km` | `50.0` | raio de casa para o corte por transição |
| `estadia_exige_casa_desconhecida` | `True` | regra 5 só vale com casa desconhecida |

A última linha é o resultado do benchmark (`docs/AGRUPAMENTO.md` §2b): variante
D venceu 16/16 (eram 16 cenários à época; hoje o benchmark tem 19) porque, com casa conhecida, quem decide deslocamento é a regra 4;
senão férias EM CASA (6 dias de GPS a 2 km) viravam "viagem".

**`DadosSessao`** (`classifier.py:41-76`): `pastas`, `duracao`,
`pais_dominante`, `dist_mediana_casa_km`, `periodo_curto`, `paises_no_tempo`,
`albuns` (tupla `(nome, contagem)`), `fonte_dos_albuns`, `cameras`,
`tipos_de_nome` (o léxico).

**`_cascata`** (`classifier.py:162-262`), em ordem:

| # | Condição | Resultado | origem | `rotulo_de_pasta` |
|---|---|---|---|---|
| 1 | `_normalizar(segmento) in {"viagens","viagem"}` | VIAGEM | `pasta` | False |
| 2 | `extrair_evento` devolveu nome **de keyword** | EVENTO nomeado pela pasta | `pasta` | True |
| 3a | um segmento lista **≥ 2 países** (`identificar_paises`) | VIAGEM nomeada pelo segmento cru | `pasta` | True |
| 3b | `extrair_hierarquia_da_pasta(pasta).pais` | VIAGEM nomeada pelo país | `pasta` | True |
| 4 | `dist_mediana_casa_km > dist_viagem_km` (100 km) | VIAGEM | `gps` | False |
| 5 | `pais_dominante` **e** `duracao >= 3d` **e** (`dist_mediana_casa_km is None`) | VIAGEM | `geocoding_offline` | False |
| 6 | `extrair_evento` devolveu nome **e** `duracao <= 2d` | VIAGEM se o léxico disser "lugar"; EVENTO se "ocasiao"; senão EVENTO pela pasta | `lexico` ou `pasta` | True |
| 7 | nada | NEUTRA | `agrupamento` | — |

Nomeação de viagem (`viagem()`, `:167-181`): país explícito → `" – ".join(pernas
cronológicas)` se ≥ 2 → `pais_dominante` → `periodo_curto`. Nunca rótulo vazio.

Regra 3a antes de 3b porque a pasta pode listar a viagem inteira ("Dubai, Thai &
Viet") e essa lista vale mais que as pernas deduzidas do GPS: nessa viagem, 106
de 2.405 fotos tinham GPS e **nenhuma** nos Emirados (`classifier.py:188-200`).
Detecta com a tabela canônica mas **nomeia com as palavras do dono**; os países
reconhecidos vão para a justificativa.

Regra 6 com léxico (`classifier.py:244-262`): sem léxico, `tipo_do_nome` devolve
`None` e nada muda. Com léxico, "Pantanal" (1d23h) vira VIAGEM em vez de EVENTO.
Se o nome extraído não é conhecido, `_opiniao_no_caminho` (`:142-160`) procura
da folha à raiz o primeiro segmento (com a data já removida) que o léxico
conheça como `lugar` ou `ocasiao` — em "Pantanal/Dia 2" a folha nomeia a
subpasta e quem diz o que a sessão É mora um nível acima.

**Nomeação por álbum** (`_nomear_por_album`, `classifier.py:107-140`), aplicada
DEPOIS da cascata, com três limites (D-030/D-034):
1. Sessão **neutra** continua neutra — álbum nunca cria acontecimento.
2. Se `rotulo_de_pasta` é True, a pasta ganha — o álbum não entra.
3. Só substitui nome **derivado** (país geocodificado ou período).

Justificativa concatenada: `"<justificativa da cascata>; nome do álbum '<nome>'
(<fonte>), que cobre <N> fotos deste período"`, com
`origem_do_rotulo = ORIGEM_ALBUM = "album_externo"`.

**Escolha do álbum** (`grouping/albuns.py:138-182`), entre os que cobrem o
período, nesta ordem de desempate:
1. **Não-prateleira antes de prateleira** — `_PRATELEIRAS` (`:118-129`):
   `ferias, vacation, holiday, familia, family, viagens, trips, travel, eventos,
   events, momentos, moments, memories, lembrancas, melhores, best of, selecao,
   selection, geral, general, diversos, misc, casa, home, trabalho, work, album,
   albuns, albums, fotos, photos, pictures, imagens` (+ variantes). Sem isto o
   acervo escolheria "Férias" (4.352) em vez de "Portugal e Italia com as
   Meninas" (3.729).
2. **Mais fotos primeiro** — separa o álbum do acontecimento inteiro do álbum
   aninhado dentro dele ("Dubai, Thai & Viet" 2.019 × "Nosso Casamento" 107).
3. **Nome mais curto, depois alfabético** — puro determinismo ("Empolga 2025" e
   "Empolga as 9 - 2025", 159 cada): o rótulo não pode dançar entre regenerações.

Filtros antes do desempate: `MIN_FOTOS_ALBUM = 3` (`albuns.py:131`, mesmo número
e mesma razão de `_MIN_FOTOS_PERNA`) e `album_nomeia` (`:91-104`), que descarta
`_APPS` (`:50-62`: instagram, twitter, x, facebook, flickr, tiktok, snapchat,
linkedin, pinterest, dropbox, icloud, email, airdrop, drone, gopro, print,
recentes, favoritos, importados, sem titulo, untitled, novo album + os
vocabulários de `grouping/origens.py`), o serviço dentro de frase
(`_RE_SERVICO`, `:63-65`), e câmera por dois caminhos (`_e_camera`, `:81-89`):
o conjunto `cameras` aprendido do catálogo **e** `_MARCAS` (`:70-76`: canon,
nikon, sony, fujifilm, fuji, olympus, panasonic, lumix, leica, pentax, sigma,
hasselblad, phase one, iphone, ipad, ipod, pixel, galaxy, xiaomi, motorola, eos,
nikkor, alpha, dji, mavic, insta360). Os dois são necessários: o maior álbum de
um acervo real era "Canon EOS 5D Mark IV" e o catálogo alcançável só conhecia
quatro modelos, nenhum deles esse (`albuns.py:19-36`). `_MIN_CARACTERES = 3`
(`:78`); precisa conter ao menos uma letra (`:103`). A data sai do nome por
`separar_data` ("Peru - Julho de 2026" nomeia "Peru").

`cameras_do_catalogo(pares)` (`albuns.py:184-196`) normaliza `(make, model)` e
guarda o modelo sozinho **e** marca+modelo — o dono escreve tanto "EOS R6m2"
quanto "Canon EOS R6m2".

**`_IndiceDeAlbuns`** (`engine.py:136-201`): carrega TODAS as marcações
`MetadataEntry.chave == "album"` uma vez por geração (com
`quando = data_capturada or mtime`), ordena, e responde por **bisseção**
(`bisect_left`/`bisect_right`, `:190-199`) quais caem em `[inicio, fim]` —
**sem folga nas bordas**, porque a régua é o período que o agrupamento já
decidiu. Uma consulta por sessão seria N+1 sobre a maior tabela do catálogo.
`fonte_legivel` (`:183-189`) traduz o namespace: `{"apple": "Apple Fotos",
"lightroom": "Lightroom"}` (`engine.py:113`), senão `"catálogo externo"`.

**Reconhecimento de evento na pasta** (`grouping/eventos.py`):
- `_KEYWORDS_EVENTO` (`:19-24`): `aniversario, casamento, formatura, batizado,
  cha de bebe, festa, natal, reveillon, ano novo, pascoa, churrasco, show,
  festival, despedida, confraternizacao, bodas` + `_RE_ANOS = \b\d{1,3}\s*anos?\b`
  (`:25`).
- `pasta_tecnica` (`:68-81`): `_RE_TECNICO` (`:28-44`) cobre datas, contadores
  de câmera (`img\d*`, `dsc\d*`, `dcim`), etapas de workflow (`originals`,
  `exports`, `edits`, `raw`, `jpeg`, `selecao`, `developed`, `revelados`,
  `tratados`, `finalizados`, `culling`, `picks`, `rejects`, `descartes`, `lixo`,
  `previews`, `thumbs`, `cache`, `sidecars`), nomes genéricos (`fotos`,
  `photos`, `imagens`, `camera`, `backup`, `nova pasta`, `sem titulo`,
  `untitled`) e pastas de sistema (`pictures`, `users`, `home`, `volumes`,
  `desktop`, `documents`, `downloads`, `library`). Mais: sufixo de pacote
  (`SUFIXOS_DE_CODIGO` de `scanner/discovery.py`) — sem isto,
  "BoraChurrascoRio.imageset" batizou 1.314 fotos de um acervo real; e
  contêiner com extensão no nome ("Pictures.wrp2").
- `_PASTAS_CONTEINER` (`:53-59`): `portfolio, portifolio, fotos organizadas,
  organizadas, organizado, acervo, catalogo, biblioteca, galeria, colecao,
  colecoes, arquivo, arquivos, diversos, geral, varios, outros, misc, temp, tmp,
  novo, novas` — prateleiras que dizem o que o dono FEZ com as fotos.
- `extrair_evento(pastas)` (`:101-134`) → `(nome, veio_de_keyword)`. Prefere o
  segmento **mais fundo** com keyword; senão o nome de álbum mais fundo, com
  `_PROFUNDIDADE_ALBUM = 3` (`:46`) contado da folha (`nivel 0 = folha`). Filho
  direto de `Users`/`home` é nome de usuário, não álbum (`:118-120`).

### 5.6 Subdivisão em acontecimentos (`grouping/eventos_temporais.py`)

Roda **depois** da classificação (`engine.py:545-556` → `_subdividir`,
`:564-595`), e cada bloco é **reclassificado** — a ordem é contraintuitiva e
está justificada em `docs/EVENTOS.md`: sem a classificação não dá para saber se
subdividir é permitido (viagem é uma pasta só), e cada pedaço tem duração e
lugar próprios.

Constantes (`eventos_temporais.py:52-88`):

| Constante | Valor | Papel | Por quê |
|---|---:|---|---|
| `PISO` | `90 min` | nunca corta abaixo disso | num dia disparando a cada 10 min, 70 min é sete vezes o ritmo e ainda é almoço. 90 e não 45 — o erro barato é juntar demais |
| `TETO` | `8 h` | sempre corta acima disso | protege a fronteira seguinte num dia de fotos esparsas |
| `FATOR` | `6.0` | múltiplo do ritmo local que vira corte | |
| `JANELA` | `12` | quantos intervalos **anteriores** definem o ritmo | janela simétrica se contamina com o bloco seguinte — num cenário de fotos esparsas seguidas de rajada, cortava quatro vezes |
| `DESLOCAMENTO_KM` | `3.0` | corta independente do tempo | 3 km separa bairros sem separar salões do mesmo casamento |
| `DURACAO_MAX_ACONTECIMENTO` | `20 h` | acima disso é estadia, não se divide | segura o Pantanal (97 fotos, 1d23h) que a régua de ritmo partia em quatro |
| `MIN_FOTOS_EVENTO` | `10` | bloco menor é absorvido no vizinho | Serena 15 Anos tinha 5 fotos de teste às 17:25 e a festa das 19:28 — tecnicamente dois eventos, mas o dono não reconhece 5 fotos como evento da vida dele |

`Momento` (`:91-100`): `media_id`, `quando`, `lat`, `lon` — as coordenadas são
as **efetivas** (`engine.py:571-573` usa `self._coords`).

`dividir_sessao(momentos, e_viagem)` (`:123-144`):
```
atravessa_noites = (ultimo - primeiro) > DURACAO_MAX_ACONTECIMENTO
if e_viagem or atravessa_noites: return [um bloco só]
return dividir_em_eventos(ordenados)
```

`dividir_em_eventos` (`:146-181`), para cada intervalo consecutivo:
```
distancia = _km(anterior, atual)        # None sem coordenada dos dois lados
if distancia is not None and distancia >= DESLOCAMENTO_KM: corta
elif intervalo >= TETO:                                    corta
elif intervalo <  PISO:                                    não corta
else:
    ritmo = mediana dos até JANELA intervalos anteriores
    corta = ritmo is not None and intervalo > ritmo * FATOR
```

`_km` (`:103-110`) é uma aproximação equirretangular com correção de cosseno
(não haversine) — suficiente para a escala de quilômetros.

`_absorver_pequenos` (`:183-201`): funde bloco `< MIN_FOTOS_EVENTO` no vizinho
anterior; o primeiro bloco, que não tem anterior, é prependido ao segundo. Um
bloco só, por menor que seja, fica.

**Sinais cogitados e NÃO implementados** (`docs/EVENTOS.md`): câmera/lente (o
próprio código cita troca de lente como exemplo do que não deve cortar), álbum
(D-030 — os álbuns se aninham) e hora do dia (não existe regra "manhã ≠ noite").

**Não há flag de configuração para desligar a subdivisão** — é incondicional
(`docs/EVENTOS.md`, "Como reverter ou desligar"). Desligar exige remover a
chamada a `_subdividir` em `engine.py:553-556`.

### 5.7 Pernas multi-país e lugares (`_geo_da_sessao`, `engine.py:663-703`)

Percorre os membros **em ordem temporal** (a sessão já vem ordenada), resolve a
coordenada efetiva de cada um e acumula:
- `paises` (Counter) e `ordem_paises` (ordem cronológica de chegada);
- `lugares`: `"Cidade, País"` sem repetição, **até 5** (`:701`).

**Corte por granularidade**: para foto com coordenada herdada, um campo só conta
se `heranca.fator_de(campo) is not None` (`:684-690`). Sem esse corte, uma foto
correlata a 6 h de distância nomearia a viagem com a cidade errada (D-025).

`pernas` = países com `>= _MIN_FOTOS_PERNA` (3, `engine.py:109`) fotos
geocodificadas, em ordem de chegada; **menos de 2 pernas → `()`**
(`:697-700`). Uma escala de aeroporto com 1-2 fotos não nomeia a viagem.

`dist_mediana_casa_km` (`_classificar`, `engine.py:630-639`): mediana (elemento
central da lista ordenada, não a média de dois em lista par) das distâncias das
coordenadas **efetivas** até a casa.

---

## 6. Correlação entre fontes e herança de GPS (`grouping/correlacao.py`)

A premissa: **a câmera boa não grava GPS; o telefone grava**
(`correlacao.py:1-6`). Nada é escrito em EXIF — a herança existe apenas como
evidência (`docs/AGRUPAMENTO.md` §2a).

### 6.1 Entrada — `FotoRef` (`correlacao.py:88-115`)

Projeção mínima, independente do ORM:

```python
media_id, source_id, quando,
camera: tuple[make, model] = (None, None),
lat, lon, hash_rapido, hash_perceptual,
hora_do_arquivo: bool = False    # quando veio do mtime, não do EXIF
```

`outra_origem(outra)` (`:112-115`): `source_id != outra.source_id or camera !=
outra.camera`. Duas fotos da mesma câmera na mesma fonte já vivem na mesma linha
do tempo e não acrescentam nada.

Construído em `engine.py:465-494` a partir de **todas** as mídias com
`data_capturada or mtime`, com
`hora_do_arquivo = (m.data_capturada is None)`.

### 6.2 Deriva de relógio (`estimar_offsets`, `correlacao.py:167-220`)

1. Indexa todas as fotos por `hash_rapido` **e** por `hash_perceptual`
   (`:179-184`) — phash cobre o caso do export recomprimido.
2. Para cada grupo com ≥ 2 fotos, todo par `(a, b)` com `a.media_id <
   b.media_id` e `a.source_id != b.source_id` (`:188-196`).
3. Exige que **exatamente uma** das duas tenha GPS (`a.tem_gps == b.tem_gps` →
   pula, `:197-198`): a que tem GPS é a **referência de relógio** (Google/Apple
   normalizam a hora real); a outra é a câmera. Câmera `(None, None)` é
   descartada.
4. Acumula `referencia.quando - camera.quando` por câmera.
5. Por câmera: exige `len >= _MIN_ANCORAS` (2, `:52`); calcula mediana e **MAD**
   (mediana dos desvios absolutos em torno da mediana); descarta se
   `mad > _DISPERSAO_MAX` (3 min, `:51`) — dispersão grande indica pareamento
   ruim.
6. Devolve `{camera: timedelta}` tal que `quando + offset` aproxima a linha do
   tempo da referência. Câmeras de fora ficam com offset implícito zero.

### 6.3 Janelas por campo (D-025)

```python
JANELAS_POR_CAMPO = (          # correlacao.py:38-42
    ("cidade", timedelta(minutes=10)),
    ("regiao", timedelta(hours=2)),
    ("pais",   timedelta(hours=12)),
)
JANELA_HERANCA = max(...)      # = 12 h — usada na BUSCA; cada campo é filtrado depois
_JANELA_CURTA  = timedelta(minutes=2)          # :49
_PENALIDADE_HORA_DE_ARQUIVO = 0.6              # :57
```

`campos_confiaveis(delta, hora_incerta)` (`:414-436`), do campo mais grosso ao
mais fino:
```
para (campo, janela) em JANELAS_POR_CAMPO ordenado por janela DESC:
    se delta > janela: pula
    se delta <= 2 min: fator = 1.0
    senão: fator = 1.0 - 0.4 * ((delta - 2min) / (janela - 2min))
    se hora_incerta: fator *= 0.6
    → (campo, round(fator, 3))
```

Cada campo decai **dentro da própria janela**, de 1.0 a 0.6 na borda dele —
"país a 6 h" e "cidade a 6 min" não competem na mesma escala. A penalidade 0.6
foi escolhida para derrubar a herança de "alta" para "média" mesmo com Δt curto:
`0.75 × 1.0 × 0.6 = 0.45`, abaixo do piso de média (`correlacao.py:53-57`).
Score final na evidência: `round(0.75 * fator, 3)` (`engine.py:966-968`).

### 6.4 Busca da doadora (`herdar_gps`, `correlacao.py:222-344`)

```
doadores = fotos com GPS, ordenadas pela hora CORRIGIDA (quando + offset)
para cada foto SEM GPS:
    alvo = corrigida(foto)
    i = bisect_left(tempos, alvo)
    achados = [procurar(i-1, passo -1),   # para trás
               procurar(i,   passo +1)]   # para frente
    delta, doador = min(achados)          # o mais próximo vence
```

`procurar` (`:254-274`) **caminha** para um lado só até estourar a janela — não
olha só os vizinhos imediatos. A versão anterior desistia quando os dois
vizinhos eram da mesma origem e nunca alcançava o terceiro: num acervo real isso
barrou **27.117 candidatos** que tinham doador válido logo atrás deles.

### 6.5 Concordância de duas âncoras (D-074, `_confrontar_com_outro_lado`, `:346-394`)

O lado perdedor não é descartado — testemunha a favor ou contra, **campo a
campo**:

- Sem outro lado → `campos_base` inalterado, `concordancia = ()`.
- `incerta` (a foto ou o doador escolhido com hora de arquivo) **ou**
  `doador_outro.hora_do_arquivo` → nenhum teste, `concordancia = ()`
  (`:381-382`). Um raio calculado sobre Δt que pode estar arbitrariamente errado
  não prova nada — e assim a justificativa nunca diz "confirmada" na mesma frase
  em que avisa que a hora é incerta.
- `campo == "pais"` → **nunca testado** (`:387`): `raio_incerteza` é calibrado
  para deslocamento de pessoa em até 12 h (teto 50 km), não para o tamanho de um
  país; duas doadoras a 300 km, claramente no mesmo país, falhariam o teste.
- `delta_outro > _JANELA_DO_CAMPO[campo]` → o outro lado não opina; campo segue
  como âncora única.
- Senão: **concordam** se `_distancia_m(doador, doador_outro) <=
  raio_incerteza(delta) + raio_incerteza(delta_outro)` (`:388-393`).
  Concordar **não** aumenta o fator (seria bônus inventado) — só marca
  `concordancia` e adiciona a frase. **Discordam** → o campo é removido, e não é
  herdado nem pelo lado mais próximo: duas doadoras a horas uma da outra, uma de
  cada lado, significam que a foto do meio está **em trânsito**.

Medido (`docs/LOCAL_ESTIMADO.md`, 2026-08-17, 39.443 pares na janela de 12 h):
`unica 5.554 (14,1%)`, `concordante 33.071 (83,8%)`, `discordante 818 (2,1%)`;
cobertura geral 94,2% / 97,5% / **91,1%** (50,9% na banda 1–10 min) — era aí que
a versão anterior errava calada.

**Limitação declarada, não escondida** (`correlacao.py:294-300`): ida e volta no
mesmo dia entre duas âncoras concordantes (casa → cidade vizinha → casa, sem
foto com GPS na cidade vizinha) produz falso-negativo — a foto do meio herda
"casa" com a confiança de concordância.

`_distancia_m` (`:399-411`) é haversine com `_RAIO_TERRA_M = 6_371_008.8`,
duplicada de propósito em relação a `scripts/calibrar_raio_incerteza.py` (o
script é ferramenta offline e este módulo puro não deve depender dele).

### 6.6 `Heranca` (`correlacao.py:118-165`)

```python
media_id, doador_id, lat, lon, delta,
campos: tuple[(campo, fator), ...],   # do mais grosso ao mais fino; nunca vazia
hora_incerta: bool = False,
concordancia: tuple[str, ...] = (),   # subconjunto de {"cidade","regiao"}
doador_concordante_id: int | None = None
```

- `fator_de(campo)` → fator ou `None` quando o Δt não permite afirmá-lo.
- `granularidade` → `campos[-1][0]`, o campo mais fino que este Δt sustenta.
- `raio_m` → `raio_incerteza(self.delta)`.

### 6.7 Raio de incerteza (D-032, `correlacao.py:59-84, 439-458`)

```python
VELOCIDADE_PLAUSIVEL_MS = 6.0       # ≈ 22 km/h
RAIO_PISO_M             = 15.0      # imprecisão do próprio receptor GPS
RAIO_TETO_M             = 50_000.0  # platô medido
COBERTURA_MEDIDA        = 0.936

raio(Δt) = min(50_000, max(15, 6.0 * |Δt| em segundos))
```

**Todos os três números foram calibrados contra 2.083 pares reais** do acervo
em que as duas fotos têm GPS próprio e origens diferentes
(`scripts/calibrar_raio_incerteza.py`). O achado central que derrubou a hipótese
de partida: a distância real **satura** — o p90 da banda 6–12 h (25 km) é
*menor* que o da banda 30 min–2 h (39 km). Um teto derivado da janela de país
daria 259 km e não informaria nada. Grade de sensibilidade em
`docs/LOCAL_ESTIMADO.md`: 6 m/s com 50 km é o **menor** par que passa dos 90%.

`frase_do_raio(delta, doadora)` (`:489-521`) devolve o texto pronto para a tela,
em três formas (piso: erro do receptor; teto: parou de crescer; meio:
velocidade × tempo). **Nasce em Python, não em TypeScript** — a frase cita o raio
e a velocidade que o produziram, e constante duplicada é constante que diverge.
`NOTA_DO_RAIO` (`:482-486`) diz a cobertura uma vez, para a legenda.

`_metros_legiveis` (`:461-467`): metros até 1 km, depois km com vírgula decimal.
`_tempo_legivel` (`:470-477`): `Ns` / `Nmin` / `Nh` / `Nh Nmin`.

### 6.8 Miniaturas do Apple Fotos como testemunha (D-024)

Registro que não serve como acervo é **rebaixado a fonte de sinal**
(`MediaRole.SINAL`), nunca removido: sai da grade, da revisão e do plano,
**continua doando data, GPS e correlação**. `_correlacionar` recebe TODAS as
mídias (`engine.py:287`), não só as organizáveis (`engine.py:282-286`). Medido
em 2026-07-31: apagar as 45.822 miniaturas do Apple Fotos levaria as fotos reais
com lugar estimado de **2.117 para 162** (CLAUDE.md invariante 8).

A base bruta da testemunha **não** é gravada (`scanner/scanner.py:485-492`) —
ninguém abre o IPTC de uma miniatura de cache, e guardar custou 685 mil linhas e
134 MB. A curadoria é a exceção (`:489-492`): é afirmação de gente sobre a foto.

Números do catálogo real hoje: 102.251 mídias, **21.753 com GPS próprio**,
**13.375 com GPS estimado**, 2.203 `locations` distintas cobrindo 17 países.

---

## 7. Geolocalização

### 7.1 `GeocodingProvider` (Protocol, `geolocation/base.py:14-36`)

```python
@dataclass(frozen=True, slots=True)
class GeoResult:
    pais: str | None; regiao: str | None; cidade: str | None
    fonte: str          # ex.: "offline:reverse_geocode/2"

class GeocodingProvider(Protocol):
    @property
    def fonte(self) -> str: ...        # identidade E VERSÃO
    def resolve(self, lat, lon) -> GeoResult | None: ...   # None = não sei, nunca inventa
```

A **versão** dentro de `fonte` não é decoração: lugar resolvido fica em cache no
catálogo, e sem versão uma mudança de nomenclatura só valeria para coordenadas
novas — as fotos já resolvidas guardariam para sempre o nome antigo
(`base.py:22-33`).

### 7.2 `OfflineGeocoder` (`geolocation/offline.py`)

```python
FONTE = "offline:reverse_geocode/2"    # offline.py:20
```
`/2` = país canonizado por código ISO e região sem rótulo administrativo em
inglês. **Bump obrigatório a cada mudança de nomenclatura.**

`_carregar()` (`:31-37`): import **lazy** de `reverse_geocode` — o dataset
carrega e monta uma árvore na primeira consulta (alguns segundos), por isso o
resolver deve rodar fora da thread da UI (`offline.py:1-5`).

`resolve` (`:39-57`): `rg.search([(lat, lon)])[0]`; qualquer exceção → `warning`
+ `None` (nunca levanta). Mapeamento:
- `pais` ← `pais_por_codigo(country_code)`, com fallback para `country` original
  em inglês se o código for desconhecido — "melhor em inglês do que ausente";
- `regiao` ← `limpar_regiao(state)`;
- **`cidade` fica no idioma local**: "Hoi An" e "Chiang Mai" são os nomes certos
  dos lugares, não erros de tradução (`:49-51`).

### 7.3 `LocationResolver` (`geolocation/resolver.py`)

```python
_PRECISAO = 3
cache_key(lat, lon) = f"{round(lat,3):.3f},{round(lon,3):.3f}"     # ≈ 110 m
```

`resolve(session, lat, lon)` (`:36-66`):
1. `SELECT Location WHERE cache_key = chave` — devolve se existe e **não está
   desatualizado**.
2. `_desatualizado` (`:27-33`): `location.fonte != provider.fonte`. `getattr`
   porque fakes de teste não declaram versão — sem ela o cache nunca expira, que
   é o comportamento antigo.
3. Provider mudo (`None`) → **devolve o que já se sabia**, não apaga (`:43-45`).
4. Mesmo lugar com nomenclatura nova → **reescreve a linha no lugar**, para que
   as fotos já resolvidas (`media_files.location_id`) acompanhem (`:46-54`).
5. Senão cria `Location(pais, regiao, cidade, lat, lon, fonte, cache_key)`.

### 7.4 Canonização de país (`geolocation/paises.py`)

`PAISES_PT` (`:22-148`): ISO 3166-1 alfa-2 → nome em pt-BR, tabela estática
completa, **sem rede** (invariante 4). Existe porque o dataset offline devolve
"Thailand"/"France" (GeoNames, inglês) e o nome de pasta devolve o que estiver
escrito — duas grafias do mesmo país viram duas pastas no destino.

- `pais_por_codigo(codigo)` (`:151-155`) — chave preferida, não depende de grafia.
- `canonizar_pais(nome)` (`:158-162`) — `"France"|"França"|"FRANCE"` → `"França"`
  via `_CANONICO` (apelidos normalizados).
- `identificar_paises(texto)` (`:188-207`) — países listados num segmento só, em
  ordem. Separadores `_RE_LISTA = [,&+/ ou " e "]` (`:168`); **hífen fica de
  fora** porque "Guiné-Bissau" e "Timor-Leste" o usam dentro do nome. Aceita
  abreviação por prefixo (`_por_prefixo`, `:173-185`) a partir de
  `_MIN_PREFIXO = 4` caracteres **e só quando UM país responde**: "Viet"
  identifica, "Ma" não, e se duas nações começam igual nenhuma é escolhida.
  Devolve `()` quando **nem toda** parte é país — meia lista reconhecida é ruído.
- `limpar_regiao(nome)` (`:227-233`) — tira sufixo/prefixo administrativo em
  inglês (`province, state, region, prefecture, county, district, governorate,
  municipality, oblast, territory, department, canton, emirate, autonomous
  region, metropolitan city, federal district`; e `Province of X`). O nome
  próprio é o que interessa; **não se traduz o nome em si** — endônimo é o nome
  certo do lugar.

### 7.5 Inferência por nome de pasta (`geolocation/folder_names.py`)

`_PAISES_RAW` (`:18-40`): lista PT/EN de ~90 grafias usada para montar
`PAISES_NORMALIZADOS`; `identificar_pais` (`:51-59`) delega a `canonizar_pais` e
**sempre devolve a grafia canônica em português**.

`extrair_hierarquia_da_pasta(pasta)` (`:69-81`): percorre os segmentos de cima
para baixo; no **primeiro** que for país:
- sem resto → `(pais, None, None, segmento)`;
- 1 segmento de resto → `(pais, None, resto[0], segmento)` (cidade);
- ≥ 2 → `(pais, resto[-2], resto[-1], segmento)` (região = penúltimo, cidade =
  último).

Sem país reconhecido → hierarquia **vazia**. Diferente do protótipo v1, que
chutava a pasta mais funda como cidade — removido por violar "não invente
localização" (`folder_names.py:1-8`).

`segmento_pais` existe para a justificativa poder citar o que foi lido.

### 7.6 Escala do desenho (`geolocation/escala.py`)

`metros_por_grau(lat)` (`:21-39`) — série de Taylor da WGS84, devolve
`(metros por grau de latitude, metros por grau de longitude)` separados, para o
mapa desenhar um **círculo redondo** e não uma elipse achatada fora do equador
(111 km no equador × 79 km no Rio). Clampa a longitude em `max(por_lon, 1.0)`:
nos polos o grau tende a zero e a divisão explodiria o desenho.

### 7.7 "Lugar estimado" na API (`server/app.py:343-437, 928-1020`)

`GET /api/mapa?trip_id=N` ou `?event_id=N` — **um grupo por vez**, porque sem
cartografia real (D-031) o acervo inteiro numa tela só não tem escala em que
informe nada. Rota de leitura pura: não recalcula herança, não escreve.

Cada ponto (`_ponto_do_mapa`, `:343-402`): `media_id`, `nome`, `lat`, `lon`,
`data_capturada`, `camera`, `motivo_indisponivel`, `estimado`, `raio_m`,
`delta_s`, `doadora_id`, `doadora_nome`, `porque`.
- `estimado = False` → ponto cheio, `raio_m = None`.
- `estimado = True` sem `gps_estimado_delta_s` → `raio_m = RAIO_TETO_M` e uma
  frase própria: "Δt ausente não é Δt zero" (`:382-393`).
- Senão → `raio_incerteza(delta)` e `frase_do_raio(delta, doadora.nome)`.

`_enquadramento` (`:404-437`): os limites já vêm **esticados pelo raio de cada
círculo** — num grupo em que todas herdaram da mesma doadora (o caso comum), a
caixa dos pontos tem lado zero e os círculos, 50 km. `escala` traduz metros em
graus na latitude média do grupo.

Contagens (`app.py:1008-1016`): `no_mapa + sem_coordenada == total`;
`fora_de_alcance` é **subconjunto** de `no_mapa` (desenhadas, sem miniatura).
Estar fora de alcance **não** tira a foto do mapa (D-033): o evento "Pantanal"
tem 80 das 97 fotos em `/Volumes/Externo`.

### 7.8 Timezones (`geolocation/timezones.py`)

`TZ_POR_PAIS: dict[str, str]` (`:54-305`) — **nome em português** (a mesma grafia
que `PAISES_PT` produz) → identificador IANA. A chave é o nome e não o código
ISO porque `Evidence.valor` já chega como nome (`timezones.py:20-23`).

Granularidade grosseira **de propósito** (D-038/D-07): um fuso por país, não
geometria coordenada→fuso. Sem dependência nova (`timezonefinder`, `pytz`,
`geo-tz` descartados) e sem rede.

Regra de preenchimento (D-08, `timezones.py:25-52`):
- país de fuso único → IANA canônico da capital;
- multi-fuso → capital ou maior população (Brasil → `America/Sao_Paulo`, EUA →
  `America/New_York`, Rússia → `Europe/Moscow`, Canadá → `America/Toronto`,
  Austrália → `Australia/Sydney`);
- território sem população permanente → fuso fixo mais próximo pela longitude
  (Ilha Bouvet → `Etc/GMT`; Heard/McDonald → `Indian/Kerguelen`);
- território sem IANA próprio (Kosovo) → o do território com as mesmas regras
  (`Europe/Belgrade`);
- Antártida → `Antarctica/McMurdo`.

Validado em teste contra `zoneinfo.available_timezones()`
(`tests/test_timezones.py:18`) e contra cobertura total de `PAISES_PT`
(`:14`). Uso: `media.tz_estimado = TZ_POR_PAIS.get(pais)`
(`engine.py:461-462`). Distribuição real: `America/Sao_Paulo 11.467`,
`America/Santiago 2.322`, `Africa/Accra 1.901`, `Asia/Bangkok 1.293`,
`America/New_York 1.214`, `America/Argentina/Buenos_Aires 1.042`.

### 7.9 Provider externo opt-in

**Não existe implementação.** A chave `geocoding_externo: 0.75` está declarada
em `SCORES_REFERENCIA` (`confidence.py:17`) e na tabela de
`docs/CONFIANCA.md`, e o `Protocol` está pronto (`geolocation/base.py:26-36`),
mas nenhuma classe além de `OfflineGeocoder` o implementa e nenhuma evidência
com essa origem existe no catálogo real. O CLAUDE.md promete "serviço externo
somente opt-in, com cache local e rate limit" — isso é contrato a cumprir, não
código a portar.

---

## 8. Duplicatas nível 3 — similaridade visual

### 8.1 phash (`duplicates/phash.py`)

`calcular_phash(original, thumb=None)` (`:65-81`):
```
fontes = [p for p in (thumb, original) if p is not None]   # thumb primeiro
para cada fonte: tenta abrir e devolver str(imagehash.phash(img))
qualquer exceção → log.debug e tenta a próxima; nada abriu → None
```

`imagehash.phash` é o phash de 64 bits (DCT sobre 32×32), devolvido em hex.
`_abrir` (`:84-97`) espelha `_open_source` do gerador de miniatura: RAW pela
miniatura embutida do libraw, o resto pelo Pillow.

⚠️ **Divergência conhecida (M4 da auditoria)**: `phash.py:97` abre o arquivo
**sem `exif_transpose`**, enquanto `thumbnails/generator.py:51` aplica. Duas
cópias de uma foto retrato — uma com miniatura em cache, outra sem — produzem
phashes diferentes e **não agrupam**. A docstring `phash.py:66-67` ("o resultado
é o mesmo, a leitura é menor") é falsa nesse caso.

### 8.2 BK-tree (`phash.py:25-62`)

Nó = `[valor, [payloads], {distância: nó_filho}]`. `distancia_hamming(a,b) =
(a ^ b).bit_count()` (`:21-22`).

- `inserir(valor, payload)` (`:31-46`): distância 0 acumula no mesmo nó.
- `buscar(valor, max_dist)` (`:48-62`): percorre por pilha e só desce os ramos
  com `d - max_dist <= dist_filho <= d + max_dist` — desigualdade triangular.
  Devolve `[(distância, valor, payloads)]`.

Evita a comparação O(n²); suficiente para dezenas de milhares de fotos sem
dependência extra (`phash.py:1-6`).

### 8.3 Níveis (`duplicates/detector.py:1-24`)

```
1. EXATO     — mesmo SHA-256 (candidatos por (tamanho, hash_rápido))
2. CONTEUDO  — mesmo phash (distância 0), bytes diferentes
3. VISUAL    — phash a distância 1..LIMIAR_VISUAL
4. SEQUENCIA — rajada: mesma câmera, frames a ≤ GAP_RAJADA
5. VARIANTE  — RAW + JPEG do mesmo clique
```

```python
LIMIAR_VISUAL = 8                      # detector.py:50
GAP_RAJADA    = timedelta(seconds=10)  # detector.py:52
```

### 8.4 Rajada × duplicata (`_eh_rajada`, `detector.py:55-65`)

```python
se alguma data_capturada é None: False      # sem data não se afirma rajada
se {(make, model)} tem != 1 elemento ou == {(None,None)}: False
ordena datas; True se TODOS os consecutivos estão a <= 10 s
```

**Rajada não é duplicata** — apresentar como tal induziria a descartar o melhor
frame (`detector.py:15-17`). É escolha do melhor frame, não desperdício.
**Precedência**: rajada vence os dois níveis de phash — até phash idêntico
(cena estática em burst) não é cópia se veio da mesma câmera em segundos
(`detector.py:225-227`).

### 8.5 Variante de revelação (`_eh_variante_de_revelacao`, `detector.py:68-92`)

`{Path(nome).stem.lower()}` com 1 elemento, ≥ 2 extensões distintas, e ao menos
uma em `RAW_EXTENSIONS`. **Testada ANTES da rajada** (`detector.py:228-233`):
um par RAW+JPEG é sempre da mesma câmera no mesmo segundo e casaria como rajada
— e "rajada" convida a escolher o melhor frame, que aqui não é a pergunta. O RAW
é o negativo, o JPEG é a cópia de trabalho, e o dono quase sempre quer os dois.
Duas cópias do mesmo `.CR3` em pastas diferentes **não** são variante (exige
extensões diferentes) e continuam caindo em CONTEUDO.

### 8.6 Fluxo de `detectar()` (`detector.py:120-157`)

```
1. midias com tamanho > 0, com selectinload(source)     :125-129
2. _completar_phashes: só quem não tem, e sem erro_leitura;
   usa thumb_cache.get(hash_rapido) como fonte preferida :159-167
3. _completar_sha256: SÓ para candidatos agrupados por
   (tamanho, hash_rapido) com ≥ 2 membros                :169-186
4. _limpar_grupos_sem_decisao → preservados              :141,271-291
5. _grupos_exatos: por SHA-256; devolve os NÃO-representantes
   (o primeiro de cada grupo segue elegível ao phash)    :188-200
6. _grupos_por_phash: BKTree + LIMIAR_VISUAL             :202-246
7. commit; devolve stats por nível + preservados
```

`_grupos_por_phash` separa os vizinhos em `identicos` (dist 0) e `parecidos`
(1..8) e escolhe:
```
VARIANTE  se _eh_variante_de_revelacao
SEQUENCIA se _eh_rajada
CONTEUDO  se havia idênticos
VISUAL    caso contrário
```

### 8.7 Decisões do usuário

`_criar_grupo` (`detector.py:248-269`): **só grupos EXATO** recebem resolução
automática (`escolher_principal_automatico`) e `resolvido_automaticamente =
True`. Bytes idênticos não deixam ambiguidade sobre o conteúdo — só resta
decidir qual caminho é a referência. CONTEUDO, VISUAL, SEQUENCIA e VARIANTE
ficam `INDEFINIDO` até um clique humano.

`escolher_principal_automatico` (`duplicates/resolucao.py:59-68`) minimiza a
tupla (`_pontuacao`, `:36-56`):
1. fonte própria (`SourceType.PASTA`) antes de catálogo externo;
2. `-profundidade(pasta)` — caminho mais organizado antes de raiz solta;
3. nome genérico depois de descritivo (`_NOME_GENERICO =
   ^(img|dsc|dscn|dcim|pxl|mvimg|vid|mov|p|photo|foto)[_-]?\d+$` ou só dígitos,
   `:17-25`);
4. `-riqueza` = menos entradas de `metadata_entries` perde (ideia vinda do
   Immich, adaptada: o tamanho não serve porque num grupo EXATO os bytes são
   idênticos);
5. `media.id` menor — último desempate, para o resultado ser estável entre
   execuções.

`_limpar_grupos_sem_decisao` (`:271-291`): preserva só grupos com decisão
**HUMANA** (`papel != INDEFINIDO` **e** `not resolvido_automaticamente`). Se
`resolvido_automaticamente` contasse, um grupo EXATO travaria no tamanho de
quando foi criado e uma terceira cópia idêntica nunca se juntaria a ele.

Contagens reais no catálogo: `EXATO 200`, `CONTEUDO 61`, `VISUAL 619`,
`SEQUENCIA 304`, `VARIANTE 164`.

---

## 9. GenAI

Três recursos **distintos**, com contratos de privacidade distintos. Todos
opt-in, todos desligados por padrão, todos "só metadados, nunca a imagem".

### 9.1 Advisor de cluster (`classification/advisor.py`)

**Quando é chamado**: `engine.py:530-531` — **apenas** para sessão que a cascata
classificou como `neutra`, e só quando `self._advisor is not None`. O advisor é
`None` sem `settings.privacidade.servicos_externos` (`server/jobs.py:335-346`).
Requer também a lib `anthropic` instalada (`pip install -e ".[llm]"`) e
credencial no ambiente — qualquer falha de import vira `warning` e `None`.

**Payload EXATO** (`advisor.py:129-139`), serializado como
`json.dumps(payload, ensure_ascii=False)` no único `content` de user:

```json
{
  "pastas":                  ["<caminho de pasta>", ...],
  "exemplos_de_arquivos":    ["<nome de arquivo>", ...],   // até 8
  "periodo":                 {"inicio": "<ISO>", "fim": "<ISO>"},
  "quantidade_de_fotos":     <int>,
  "lugares_geocodificados":  ["<Cidade, País>", ...]       // até 5
}
```

Montado em `_consultar_advisor` (`engine.py:705-712`) a partir de
`ClusterInfo(pastas=sorted({m.pasta}), exemplos_arquivos=tuple(m.nome for m in
membros[:8]), inicio, fim, n_fotos, lugares)`.

⚠️ **Divergência M2**: `m.pasta` é o caminho **ABSOLUTO** (gravado em
`scanner/scanner.py:441` como `str(path.parent)`), enquanto
`docs/PRIVACIDADE.md`, `location_advisor.py:6,67` e a UI prometem "nome da
pasta". A UI exibe `pastaCurta()`; o que sai da máquina é o caminho inteiro.

**Chamada** (`advisor.py:136-152`):
```python
client.messages.create(
    model="claude-sonnet-5",        # MODELO_PADRAO, :29
    max_tokens=1024,
    thinking={"type": "disabled"},  # explícito — ver abaixo
    system=_SYSTEM,                 # :95-103
    output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
)
```

`thinking` explicitamente desabilitado (`:139-145`): no Opus 4.8 omitir já
significava não pensar; no Opus 5 o padrão passou a ser pensar, e `max_tokens`
cobre raciocínio MAIS resposta — 1024 truncaria o JSON no meio.

**Escolha do modelo** (D-048/D-049/D-060, `advisor.py:22-29`): em 104 clusters
reais, Haiku 4.5 afirmava categoria onde Opus recusava por falta de evidência em
**≥ 19 de 31 discordâncias** — violava a instrução "nunca invente" do próprio
system prompt. Sonnet 5, medido depois nos mesmos 104 clusters, cai nesse padrão
**7 vezes**. Daí a escolha.

**Schema de resposta** (`_SCHEMA`, `:71-93`), `additionalProperties: false`,
todos obrigatórios:
- `categoria`: `"Viagens" | "Eventos" | "Família" | null`
- `evento`: `string | null` (nome curto)
- `justificativa`: `string` (uma frase em português citando o indício)

**System prompt** (`:95-103`, literal):
> "Você classifica grupos de fotos de um acervo pessoal a partir de METADADOS
> (nomes de pastas e arquivos, datas, lugares). Você nunca vê as imagens.
> Responda apenas o que os metadados sustentam: nomes de pasta como 'Serena 15
> Anos' indicam aniversário (Eventos); estadias de dias em outro país indicam
> Viagens. Se os metadados não bastarem, devolva categoria e evento nulos —
> nunca invente."

**Aplicação do resultado** (`engine.py:713-742`):
- `sessao.categoria = resultado.categoria`;
- se `categoria == "Viagens"`: `tipo = "viagem"`, `rotulo = evento or
  pais_dominante or periodo_curto()` (**nunca rótulo vazio**), `origem =
  origem_do_rotulo = "llm"`, justificativa prefixada
  `"LLM (apenas metadados): "`. Sem essa promoção, um "Viagens" do LLM só
  preenchia `categoria` e **nunca criava um Trip** — a sessão nunca aparecia na
  aba Viagens (medido em `docs/AVALIACAO_UX.md` §C.4);
- senão, se `evento`: `tipo = "evento"`, mesma marcação.

**Degradação** (`advisor.py:153-171`): qualquer exceção (rede, auth, limite) →
`warning` + `None`. `stop_reason == "refusal"` → `info` + `None`. JSON inválido
→ `warning` + `None`. A sessão simplesmente fica sem rótulo; a geração nunca cai.

`NullAdvisor` (`:60-68`) é o padrão: `local = True`, sempre `None`.
`ClaudeAdvisor.local = False` — **a UI usa isso para indicar envio externo**
(`:118-120`).

**Uso real hoje**: zero evidências de origem `llm` no catálogo. O advisor é
resíduo por construção (`docs/PLANO_IA_E_PRODUTO.md` §2).

### 9.2 Classificação de pasta por GenAI (fase 7)

Três módulos + um orquestrador de sessão.

#### (a) Pré-filtro D-01 — `classification/candidatas_de_pasta.py`

`candidatas(session, ja_classificadas)` (`:37-120`) lista **toda pasta com ao
menos um dos dois campos-alvo vazio**. O dono nunca digita nada: o sistema lista
sozinho.

Duas consultas agregadas sobre o catálogo inteiro, **nunca uma por pasta**:
1. `GROUP BY pasta` com `count(id)`, `min(data_capturada)`,
   `max(data_capturada)`, filtrando `MediaFile.organizavel` (`:79-88`);
2. `Evidence.campo IN ("categoria","cidade","pais")` join `MediaFile`, **também**
   com `organizavel` (`:90-98`).

`MediaFile.organizavel` nos **dois** lados é deliberado (`:47-64`): uma
`Evidence` presa a uma mídia não-organizável não pode "resolver" um campo aos
olhos deste filtro — senão uma pasta cuja única mídia é uma miniatura com
`categoria` já inferida pareceria completa. Pasta só com não-acervo nem aparece
na primeira consulta.

`"cidade_pais"` é **UM campo lógico**: basta um dos dois resolvido para o par
contar como preenchido (`:22-24,103-104`).

Saída `CandidataDePasta` (`:27-35`): `pasta`, `n_fotos`, `campos_ausentes`
(`("categoria",)` | `("cidade_pais",)` | ambos, nessa ordem), `periodo`
(`"2024-03-12 a 2024-03-19"` ou `None`). Ordenada por `pasta` — determinismo.

`ja_classificadas` chega de fora (`ClassificacaoPastaRepository.conhecidas()` —
pastas com linha em **qualquer** status) para não acoplar o pré-filtro à
persistência.

#### (b) Estimativa de custo — `classification/custo_genai.py`

```python
PRECO_ENTRADA_USD_POR_MTOK = 2.0        # :26
PRECO_SAIDA_USD_POR_MTOK   = 10.0       # :27
CAMBIO_USD_BRL_PADRAO      = 5.0        # :34
_CARACTERES_POR_TOKEN_CONSERVADOR = 3.0 # :50
```

`estimar(corpo, cambio)` (`:74-117`) — **sem rede**:
```
tokens_entrada    = ceil(len(json.dumps(corpo, ensure_ascii=False)) / 3.0)
teto_tokens_saida = corpo["max_tokens"]     # o MESMO que o payload real leva
custo_entrada_usd = tokens_entrada / 1e6 * 2.0
teto_custo_saida  = teto_tokens_saida / 1e6 * 10.0
teto_total_usd    = soma;  teto_total_brl = teto_total_usd * cambio
entrada_exata     = False
```
`corpo` vazio → tudo zero, sem calcular nada.

O fator 3,0 caracteres/token é **deliberadamente conservador** (`:41-49`): a
Anthropic desaconselha tokenizador genérico, que subconta 15-20% em texto típico
e mais em PT-BR (acentuação) e JSON (aspas, escapes). Um custo mostrado **abaixo**
do real é a falha que importa aqui.

`CAMBIO_FONTE_PADRAO` (`:35-38`): "taxa de referência fixa, capturada em 2026-08
— conversão de exibição, não cotação ao vivo". O módulo **não busca cotação
online**: abrir uma segunda saída de rede não consentida está fora do escopo do
que o dono aprovou.

`contar_exato(client, corpo)` (`:120-146`): **a única função do módulo que
transmite** (`client.messages.count_tokens`). Remove `max_tokens` do corpo (é
parâmetro de geração, não de contagem). Qualquer exceção → `warning` + `0`.
D-079: a prévia usa contagem local, e `contar_exato` só roda **depois** de
"Confirmar e classificar", aproveitando a mesma transmissão consentida; o número
exato aparece no resumo pós-execução, não na prévia.

#### (c) Cliente — `classification/location_advisor.py`

```python
MODELO_PADRAO = "claude-sonnet-5"   # :41
MAX_TOKENS    = 16000               # :45
_CATEGORIAS_PASTA = ("Viagens", "Família", "Eventos")   # :51
```

Modelo: o precedente D-059/D-060 vale **a fortiori** (`:36-40`) — um nome de
pasta sozinho é entrada mais esparsa que o cluster inteiro que foi medido, logo
o risco de o modelo afirmar sem base é **maior** aqui, não menor. "Nunca descer
para haiku sem repetir a mesma medição contra o caso de pasta isolada."

**`PastaPayload` — a allowlist inteira** (`:54-71`):

```python
pasta: str                            # caminho relativo/nome da pasta
n_fotos: int
periodo: str | None                   # "2024-03-12 a 2024-03-19"
campos_a_preencher: tuple[str, ...]   # ("categoria",) | ("cidade","pais") | ambos
ja_conhecido: dict[str, str]          # campos que JÁ têm valor
```

`corpo_da_chamada(pastas)` (`:196-226`) monta **campo a campo, por atribuição
explícita** — nunca serialização genérica de dataclass ou objeto. É o controle
que garante que um campo novo em `PastaPayload` (ou em qualquer objeto de
domínio) jamais vaze por acidente. Corpo exato:

```python
{
  "model": "claude-sonnet-5",
  "max_tokens": 16000,
  "thinking": {"type": "disabled"},
  "system": _SYSTEM,                                       # :148-174
  "output_config": {"format": {"type": "json_schema", "schema": _SCHEMA}},
  "messages": [{"role": "user", "content": json.dumps({"pastas": [
      {"pasta": p.pasta, "n_fotos": p.n_fotos, "periodo": p.periodo,
       "campos_a_preencher": list(p.campos_a_preencher),
       "ja_conhecido": dict(p.ja_conhecido)}
      for p in pastas
  ]}, ensure_ascii=False)}],
}
```

Exatamente **cinco chaves por pasta**. O teste
`tests/test_classification_pasta_genai.py::test_payload_nunca_envia_imagem`
verifica por **igualdade de conjunto** que só essas cinco saem, e varre cada
valor contra termos proibidos (`caminho`, `thumb`, `miniatura`, `base64`,
`image`, `.jpg`, `.cr2`, `.heic`).

`_SCHEMA` (`:114-146`): array `pastas` de objetos com `pasta` (string),
`cidade`/`pais`/`evento` (string ou null), `categoria` (enum das três ou null),
`justificativa` (string). Todos `required`, `additionalProperties: false`.

`_SYSTEM` (`:148-174`, literal, resumido): "Você classifica PASTAS… recebe
apenas o nome da pasta e metadado já catalogado (contagem de fotos, período) —
nunca a imagem, nunca um caminho de arquivo, nunca uma miniatura." Regras: NUNCA
invente (`null` é a resposta válida e **preferida**); só proponha campos em
`campos_a_preencher`; nunca proponha campo que aparece em `ja_conhecido`;
justificativa de uma frase em português; responda TODAS as pastas com a grafia
exata.

**UMA chamada para a lista inteira** (D-03, `:228-235`) — sem laço de lote, sem
chamada por pasta.

**Filtros sobre a resposta** (`:246-289`) — a obediência do modelo ao prompt
nunca é pré-requisito de segurança:
- pasta que não estava no pedido → descartada em silêncio (D-06);
- resposta com os **quatro** campos de valor `null` → não vira proposta (D-06);
- **D-02 reaplicada**: campo presente em `ja_conhecido` é zerado, mesmo que o
  modelo o tenha respondido.

Degradação (`:231-244`): qualquer exceção → `warning` + `[]`;
`stop_reason == "refusal"` → `info` + `[]`; JSON inválido → `warning` + `[]`.
`ClassificacaoDePastaNula` (`:100-111`) é o padrão: `local = True`, `[]`, `{}`.

#### (d) Sessão e gate — `server/genai_pasta.py`

**Gate de DOIS consentimentos** (`liberado()`, `:129-135`):
```python
settings.privacidade.servicos_externos          # chave MESTRA, TOML-only
AND settings_repo.genai_pasta_habilitado()      # opt-in PRÓPRIO, application_settings
```
Copiar o gate de UM flag só, como `jobs.py::_advisor` faz para o advisor de
cluster, é a regressão nomeada em `07-RESEARCH.md` Pitfall 4: este recurso **não
pega carona** no consentimento já dado ao Advisor (D-080).

`habilitar(True)` com o mestre desligado levanta `ValueError` com a mensagem
literal `MENSAGEM_MESTRE_DESLIGADO` (`:42-49`), que o endpoint converte em 409.
`MENSAGEM_GATE_FECHADO` (`:51-56`) é defesa em profundidade contra cliente HTTP
direto.

Ciclo (rotas em `server/app.py:1547-1596`):

| Passo | Método | Rota | Sessão |
|---|---|---|---|
| 0 | GET/PUT | `/api/genai-pasta/config` | `config()` / `habilitar()` |
| 1 | GET | `/api/genai-pasta/candidatas` | `candidatas()` |
| 2 | POST | `/api/genai-pasta/estimar-custo` | `estimar_custo(pastas)` — **sem rede** |
| 3 | POST | `/api/genai-pasta/rodar` | `rodar(pastas)` — a única que transmite |
| 4 | GET | `/api/genai-pasta/propostas` | `propostas_pendentes()` — **sem gate** |
| 5 | POST | `/api/genai-pasta/aprovar` | `aprovar(pastas)` |

`_payloads(pastas)` (`:182-232`): **reconcilia contra as candidatas reais** —
uma pasta pedida que já saiu da lista (o catálogo mudou entre o passo 1 e o 2)
é ignorada, não vira erro. Depois uma consulta agregada única para todas as
pastas confirmadas monta `ja_conhecido` a partir de `Evidence` de mídia
organizável nos campos `categoria`/`cidade`/`pais`.

`rodar` (`:287-352`): monta o corpo, chama `classificar` (envolto em try/except
que vira `ClassificacaoIndisponivel` → HTTP 502 com cópia amigável), grava as
propostas com `sessao = datetime.now(timezone.utc).isoformat()`, calcula
`pastas_sem_resposta` e devolve as propostas **achatadas por CAMPO**
(`_achatar_proposta`, `:101-113`: uma entrada por campo, com `valor_antes`
sempre `None` porque o pré-filtro garante que só campo vazio chega aqui).

`propostas_pendentes` (`:354-372`) **não exige o gate**: o dono pode ter
desligado o recurso e ainda assim precisar rever o que já foi pago.

`aprovar(pastas)` (`:373-381`): aprova as listadas, **descarta** as demais que
estavam em `proposta`. **Nenhuma linha é apagada em nenhum caminho**
(invariante 8).

#### (e) Persistência — `repositories/pasta_classificacao.py`

Tabela `pasta_classificacoes_genai`, chave primária `pasta`. Eixo
origem (`llm` | `manual`) × status (`proposta` | `aprovada` | `descartada`).

`salvar_propostas` (`:70-114`) — **guarda por CAMPO**, disciplina mais estrita
que a guarda por linha: campo já preenchido nunca é sobrescrito, mesmo por
proposta nova e mesmo quando o valor discorda. Linha com `origem == "manual"` é
**inteiramente intocável**, inclusive nos campos vazios — a máquina não completa
o que o dono já assumiu a autoria de decidir.

`aprovadas()` (`:53-56`) — **é isto, e só isto, que a cascata lê**.
`aprovar`/`descartar` (`:126-141`) só mudam `status`, nunca apagam.

#### (f) Entrada na cascata

`server/jobs.py:222-224` lê `ClassificacaoPastaRepository(...).aprovadas()` **do
cache local** e passa ao motor; `engine.py:336` busca
`self._pastas_classificadas.get(media.pasta)`. Três pontos de entrada, todos
como **último degrau**:
- `pais`/`cidade` em `_evidencias_geo` passo 2c (`engine.py:998-1017`), acima da
  vizinhança e abaixo da hierarquia determinística;
- `evento` (`engine.py:886-900`), só quando não há evento de sessão;
- `categoria` (`engine.py:1072-1081`), só quando o advisor não decidiu.

Score `llm_pasta = 0.55`, **medido** (D-081, `confidence.py:60-83`): 4 pastas de
amostra contra verdade determinística do próprio catálogo; categoria acertou
2/2, cidade/país recusou 2/2 (`null` — comportamento seguro de D-06, não falha);
**zero erros observados**. Preliminar — a base de medição da Fase 7 tem só ~1.400
arquivos e 2 fontes cadastradas.

Estado real do catálogo: 3 linhas em `pasta_classificacoes_genai`, todas
`status='proposta'`, `origem='llm'`. Nenhuma aprovada → nenhuma evidência
`llm_pasta` existe hoje.

### 9.3 Léxico de nomes (`classification/lexico.py` + `scripts/classificar_nomes.py`)

**O que classifica**: o NOME, não a sessão — e essa diferença é o que o torna
barato. São 100 nomes distintos no acervo inteiro; uma consulta resolve todos e
o resultado fica gravado (`lexico.py:9-14`).

```python
MODELO_PADRAO   = "claude-opus-5"   # :39
TAMANHO_DO_LOTE = 200               # :50
CATEGORIAS = ("lugar", "ocasiao", "pessoa", "ruido")   # :41-45
```

Opus e não Haiku (`:36-38`): `docs/PLANO_IA_E_PRODUTO.md` §3 recomenda Haiku para
rotulagem barata, e a recomendação vale quando a chamada é por sessão; **aqui ela
é uma só para o acervo inteiro**, então o custo não é o critério — a qualidade da
distinção lugar × ocasião é.

Chamada (`_lote`, `:155-197`): `max_tokens=16000`, `thinking={"type":
"disabled"}`, `output_config` com `_SCHEMA` (`:52-77`: array de
`{nome, categoria (enum das 4), justificativa}`), `content = json.dumps({"nomes":
[...]}, ensure_ascii=False)`.

`_SYSTEM` (`:79-108`) define as quatro categorias com exemplos reais do acervo
("Pantanal", "Chapada dos Veadeiros", "Visconde de Mauá" = lugar; "Serena 15
Anos", "Quizomba", "Teatro" = ocasião; "Vovó", "Meninas" = pessoa; "Canon EOS 5D
Mark IV", "DerivedData-access004", "node_modules" = ruído) e três regras: na
dúvida entre lugar e ocasião, prefira "lugar" **apenas** quando for
reconhecidamente topônimo; nome não reconhecido → classifique pela forma e diga
isso; responda TODOS na mesma grafia.

**Filtro sobre a resposta** (`:189-197`): só nomes que vieram na pergunta e com
categoria conhecida — a resposta não pode introduzir nome que o acervo não tem.

**Privacidade** (`lexico.py:16-22`): sai da máquina apenas a **LISTA DE
PALAVRAS** — nunca imagem, caminho completo, data, coordenada ou contagem.
Requer `servicos_externos = true`. `LexicoNulo` (`:119-127`) é o padrão.

**Acionamento**: **não** roda dentro de `gerar()`. É ação separada e explícita
via `scripts/classificar_nomes.py`, com quatro modos: `--listar` (mostra
exatamente o que sairia, **sem enviar**), `--enviar`, `--mostrar`, `--corrigir
"Pantanal=lugar"`. O que já foi classificado nunca é reenviado
(`LexicoRepository.faltantes`, `repositories/lexico.py:28-31`), e correção manual
(`origem='manual'`) nunca é sobrescrita pela máquina (`:33-60`).

**Uso na cascata**: `server/jobs.py:217` lê `LexicoRepository.conhecidos()` do
cache; vira `DadosSessao.tipos_de_nome` e só age na **regra 6**
(`classifier.py:244-262`). Com o léxico desligado, `tipo_do_nome` devolve `None`
e a cascata decide exatamente como decidia antes.

Estado real: tabela `nomes_classificados` **vazia** — o léxico nunca foi rodado
neste catálogo.

### 9.4 Privacidade — resumo operacional

| Recurso | Gate | O que sai | Quando sai | Revogar |
|---|---|---|---|---|
| Advisor de cluster | `[privacidade] servicos_externos` (TOML) | pastas (⚠️ caminho absoluto, M2), até 8 nomes de arquivo, período, contagem, lugares geocodificados | dentro de `gerar()`, por sessão neutra | desligar o TOML + reiniciar |
| GenAI de pasta | `servicos_externos` **E** `classificacao_pasta_genai` (`application_settings`) | 5 chaves por pasta: `pasta` (⚠️ caminho absoluto, M2), `n_fotos`, `periodo`, `campos_a_preencher`, `ja_conhecido` | só no POST `/rodar`, após confirmação explícita | link "Desligar" na própria tela (imediato) ou o TOML (derruba tudo) |
| Léxico | `servicos_externos` + `--enviar` explícito no script | **só a lista de palavras** | nunca automaticamente | não rodar o script |

Nenhum dos três envia imagem, byte de imagem ou miniatura. Nenhum roda por
padrão. `local: bool` em cada Protocol é o que a UI usa para indicar envio
externo (`advisor.py:118-120`, `lexico.py:146-148`,
`location_advisor.py:192-194`).

**Propostas já persistidas não são apagadas ao revogar** — revogar impede sessões
NOVAS, não desfaz classificações já aprovadas (`docs/PRIVACIDADE.md`).

---

## 10. Stubs: `vision/` e `faces/`

Os dois existem como `Protocol` + implementação nula. **Nenhum modelo é baixado,
nenhuma análise acontece, nenhum dado sai da máquina.**

### 10.1 `VisionProvider` (`vision/base.py`)

```python
@dataclass(frozen=True, slots=True)
class VisionResult:                     # base.py:17-31
    rotulos: dict[str, float]           # {"praia": 0.9, "externo": 0.8}
    tem_pessoas: bool | None = None
    qualidade_baixa: bool | None = None
    tipo: str | None = None             # captura_de_tela | documento | fotografia
    fonte: str = ""                     # identificação do provedor (auditoria)

class VisionProvider(Protocol):         # base.py:34-44
    @property
    def local(self) -> bool: ...        # True quando nenhum dado sai da máquina
    def analisar(self, path: Path) -> VisionResult | None: ...
```

Restrição de produto escrita no contrato (`base.py:1-8`): **rótulos visuais nunca
afirmam cidade/vila específica** — só cena (praia, montanha, urbano…).

`NullVisionProvider` (`vision/stub.py:12-20`): `local = True`, `analisar → None`.

**O que existe além disso**: nada. Zero consumidores — `grep` por
`VisionProvider` fora de `fotoorganizer/vision/` não encontra chamador. A
origem `visao: 0.30` está declarada em `SCORES_REFERENCIA`
(`confidence.py:58`) e nunca é produzida.

**O que o MVP promete** (`docs/AUDITORIA_IA.md`): visão, quando entrar, entra
**local** — o `[visao]` extra (~150–400 MB) é decisão em aberto do dono. A
auditoria identificou exatamente três casos em que só o conteúdo responde (dois
acontecimentos no mesmo dia/lugar/câmera; 2001–2018 sem GPS nem doador; metadado
corrompido) e recomendou consertar a régua antes de chamar modelo.

### 10.2 `FaceRecognitionProvider` (`faces/base.py`)

```python
@dataclass(frozen=True, slots=True)
class FaceDetection:                    # base.py:17-24
    bbox: tuple[float, float, float, float]   # normalizada 0-1: (x, y, w, h)
    embedding: list[float] | None              # será criptografado
    modelo: str

class FaceRecognitionProvider(Protocol):  # base.py:27-39
    @property
    def local(self) -> bool: ...
    def detectar(self, path: Path) -> list[FaceDetection]: ...
    def similaridade(self, a, b) -> float: ...   # 0-1; o LIMIAR é do chamador
```

Regras invioláveis no contrato (`base.py:1-9`, CLAUDE.md invariante 6): local,
nenhuma busca de identidade na internet, embeddings criptografados, limiar
conservador, resultado é **sempre SUGESTÃO**. Estados previstos:
`detectado → possível → confirmado/incorreto` (`models.FaceState`).

`NullFaceProvider` (`faces/stub.py:13-29`): `detectar → []`; **`similaridade`
está implementada de verdade** (cosseno, `:22-29`) — "pronto para quando houver
embeddings reais".

**A criptografia está pronta sem embedding** (`security/crypto.py`):
- `KeyStore` Protocol (`:26-27`);
- `KeychainKeyStore` (`:45-78`) — chave Fernet no Keychain do macOS via
  `subprocess.run` com **argumentos em lista, nunca `shell=True`**, timeout 10 s;
- `FileKeyStore` (`:30-42`) — fallback em arquivo `0600` no diretório de dados
  (CI, testes);
- serviço `FotoOrganizer`, conta `embeddings-key` (`:23-24`).

Tabelas `face_embeddings`, `face_occurrences`, `people` existem no catálogo e
estão vazias. `PeopleRepository` permite associação manual sem detector
(`faces/stub.py:3-5`). Provas: `tests/test_faces_privacy.py` —
`test_cifra_e_decifra_embedding`, `test_chave_persiste_com_permissao_restrita`,
`test_cadastro_e_embedding_cifrado_em_repouso`,
`test_apagar_pessoa_remove_todos_os_vestigios`, `test_stubs_sao_locais_e_inertes`,
`test_recursos_sensiveis_desligados_por_padrao`.

Configuração: `PrivacySettings.reconhecimento_facial: bool = False`
(`config/settings.py:63`) — **e essa flag nunca é lida por nenhum código**
(B5 da auditoria: `security/crypto.py:47-78` sem teste, faces stub, sem
consumidor).

**Limitação honesta declarada** (`docs/PRIVACIDADE.md`): num app desktop a chave
precisa estar acessível ao próprio app — quem tem a sessão desbloqueada tem
acesso. A criptografia protege contra leitura do arquivo do banco **fora da
sessão** (backup copiado, disco acessado por outra conta), não contra malware
rodando como o usuário.

---

## Lacunas e incertezas

1. **Base de tempo mista (M1)**. `data_capturada` (parede local) e `mtime` (UTC
   naive) são usados intercambiavelmente em `engine.py:469,501,571,585`. Medido:
   33,3% de 53.967 registros com delta múltiplo exato de 1 h. **Não sei** se a
   reconstrução deve (a) normalizar o mtime pelo `tz_estimado`, (b) excluir
   só-mtime da linha do tempo, ou (c) manter o comportamento atual. As três
   mudam resultado de agrupamento e exigem cenário novo em
   `scripts/avaliar_agrupamento.py` antes do ajuste.

2. **`phash` sem `exif_transpose` (M4)**. `duplicates/phash.py:97` diverge de
   `thumbnails/generator.py:51`. Corrigir muda **todos** os phashes já gravados
   em `media_files.hash_perceptual` — a reconstrução precisa decidir se
   normaliza (e invalida o cache de phash) ou se preserva o comportamento. Não
   há medição de quantos grupos mudariam.

3. **Caminho absoluto sai para a Anthropic (M2)**. `engine.py:707` e
   `candidatas_de_pasta.py:72 → genai_pasta.py:224-230 →
   location_advisor.py:203` enviam `MediaFile.pasta`, que é
   `str(path.parent)` absoluto (`scanner/scanner.py:441`). `docs/PRIVACIDADE.md`,
   `location_advisor.py:6,67`, D-075..D-081 e `ClassificacaoPasta.tsx:107-108`
   prometem "nome da pasta"; a UI mostra `pastaCurta()`. **Não sei** se a
   promessa deve ser cumprida (enviar só o basename, perdendo o contexto
   hierárquico que ajuda o modelo) ou se a documentação deve ser corrigida. O
   teste-prova `test_payload_nunca_envia_imagem` não pega isso.

4. **Origens declaradas sem produtor**. `gps: 0.95`, `geocoding_externo: 0.75` e
   `visao: 0.30` estão em `SCORES_REFERENCIA` (`confidence.py:15,17,58`) e na
   tabela de `docs/CONFIANCA.md`, mas **nenhum código as emite** e nenhuma linha
   de `evidence` no catálogo real as usa. `agrupamento: 0.70`
   (`confidence.py:39`) também não aparece no catálogo, embora
   `classifier.py:92` use `"agrupamento"` como origem da `Decisao NEUTRA` — que
   por construção nunca vira evidência. **Não sei** se são contrato futuro a
   preservar ou dívida a remover.

5. **Reabertura de sugestão aprovada**. O código **preserva**: mídia com
   `status != PENDENTE` é pulada inteira (`engine.py:1120-1124,330`). A memória
   do projeto registra a decisão do dono de "reabrir, não congelar" quando o
   reprocessamento muda o destino — e um documento de worktree
   (`.claude/worktrees/interesting-solomon-1c4c4b/plano-refactor.md:288-292`)
   diz explicitamente que "A1+A2 saíram sem flag e sem mecanismo de reabertura
   de sugestões" e que a decisão "fica registrada para a próxima mudança que de
   fato desloque a hora". **Não existe mecanismo de reabertura no código lido.**
   A reconstrução precisa saber se deve construí-lo.

6. **`ConfigClassificacao` não é configurável em runtime**. `engine.py:252`
   aceita o parâmetro, mas `server/jobs.py:225-233` nunca o passa — sempre o
   default. Os cinco limiares (`duracao_min_viagem`, `duracao_max_evento`,
   `dist_viagem_km`, `raio_casa_km`, `estadia_exige_casa_desconhecida`) só mudam
   por código ou por `scripts/avaliar_agrupamento.py`. Não sei se isso é
   intencional ou lacuna de UI.

7. **`VERSAO_LOGICA = "4.1"` é escrito e nunca lido** (D-043 registra o achado).
   Grep não encontra consumidor de `Evidence.versao_logica` nem de
   `Suggestion.versao_logica` fora da escrita. `docs/CONFIANCA.md` promete
   "permite re-gerar sugestões quando a metodologia evoluir e auditar com qual
   regra cada sugestão foi produzida" — a leitura não existe.

8. **Subdivisão de acontecimento sem benchmark próprio**. `docs/EVENTOS.md`
   declara: os 19 cenários de `avaliar_agrupamento.py` (contagem real 2026-09-20; `docs/EVENTOS.md` diz 17) cobrem sessão
   (viagem×evento×neutra), **não** subdivisão; não há script equivalente para o
   nível de acontecimento; e **não existe medição no acervo real** de um dia com
   dois acontecimentos genuinamente distintos sendo corretamente separado — só
   timestamps sintéticos. Mudar `PISO`/`TETO`/`FATOR`/`MIN_FOTOS_EVENTO` hoje não
   tem rede de proteção equivalente.

9. **Versão do dataset de geocodificação não é rastreada**. `reverse-geocode
   1.6.6` embarca `geocode.gz` (3.458.676 bytes) derivado de GeoNames
   `cities1000`, mas **nem o pacote nem o app registram a data do snapshot**. O
   `FONTE = "offline:reverse_geocode/2"` versiona a *nomenclatura do app*, não o
   dataset: atualizar a lib mudaria respostas sem invalidar o cache. Não sei se
   isso já mordeu alguém.

10. **`_Draft` duplicado por campo**. `_persistir_sugestao` indexa
    `evidencias[draft.campo] = evidencia` (`engine.py:1206`) — o último draft de
    um campo vence no destino, embora todos virem linha em `evidence`. Hoje
    nenhum caminho produz dois drafts do mesmo campo (cada ramo de
    `_evidencias_geo` faz `return`; a data é exclusiva por construção; o evento
    da proposta GenAI só entra se não houver outro). Mas **não há guarda** — um
    ramo novo que esqueça o `return` sobrescreveria em silêncio.

11. **Live Photo: o dado é capturado e não é usado**. `identidade_de_captura` é
    extraída (`exiftool.py:487-506`) e gravada
    (`scanner/scanner.py:503-509`), com a justificativa de que a correlação
    precisa saber que os dois arquivos são a MESMA captura para não tratar um
    como doador do outro a Δt zero. **`correlacao.py` não lê esse campo** —
    `FotoRef` não o tem. O par `.heic`/`.mov` com fontes ou câmeras diferentes
    ainda pode herdar um do outro a Δt zero.

12. **`_MIN_FOTOS_SESSAO = 2` descarta sessões de 1 foto silenciosamente**
    (`engine.py:518`). A foto continua catalogada e sem sessão, caindo em
    "Não classificadas". Não há log nem métrica dizendo quantas foram. Não
    encontrei decisão registrada para esse número.
