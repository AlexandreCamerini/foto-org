# 01 — Produto: o que é, o que vale, o que nunca pode quebrar

> Parte do mapa de reconstrução (`docs/reconstrucao/`). Leia depois de `00-INDICE.md`.
> Fontes: `CLAUDE.md` (raiz), `.planning/PROJECT.md`, `docs/DECISOES.md` (D-001..D-081),
> `docs/ROADMAP.md`, `docs/CONFIANCA.md`, `docs/PRIVACIDADE.md`. Números do acervo lidos do
> catálogo real em 2026-09-19 (somente `SELECT`).

## 1. O que é

App desktop macOS, **local-first**, para catalogar, analisar e organizar de forma assistida e
**não destrutiva** uma coleção pessoal grande de fotos (ordem de 100 mil registros, 25 anos,
dezenas de câmeras). Um único usuário: o dono, na própria máquina. O núcleo (scan, catálogo,
evidências, agrupamento, geolocalização offline, duplicatas, plano de cópia, escrita EXIF de
localização) funciona **inteiramente offline**. Recursos de nuvem (advisor LLM de cluster e
classificação de pasta por GenAI, ambos via API Anthropic) são **opt-in, desligados por padrão
e nunca pré-requisito**.

Forma de entrega: servidor FastAPI só em `127.0.0.1` servindo um webapp React (única UI), com
shell nativo Tauri 2 que embarca o runtime Python e abre a webview na porta anunciada. CLI para
operação sem UI.

## 2. Valor central (o que diferencia de um DAM comum)

> Toda sugestão de onde uma foto pertence é **auditável até a evidência que a gerou** —
> origem, confiança, justificativa — e **nenhuma operação física acontece sem revisão humana
> e dry-run**. Se isso quebrar, o produto perdeu a única coisa que o diferencia.
> (`.planning/PROJECT.md` § Core Value)

Corolários que a reconstrução precisa manter visíveis na UI, não só no banco:
- Cada campo de uma sugestão responde "por quê?" com origem + confiança + frase legível.
- Confiança é **quantidade** (segmentos), não semáforo de 3 cores (D-017): cor sozinha compete
  com a foto e falha para daltônicos.
- Confiança de uma sugestão é a do **elo mais fraco** entre os campos do destino — nunca média
  nem soma (`docs/CONFIANCA.md` § Regra de agregação).
- A unidade de decisão na Revisão é o **grupo** de sugestões idênticas, não a linha (D-018).

## 3. Princípio operacional

**Primeiro catalogar, depois sugerir, então revisar, e somente por último executar operações
físicas.** Cada etapa é um estado persistido e reversível até a última; a última (cópia,
escrita EXIF) é a única que toca o mundo fora do catálogo e exige plano → dry-run → aprovação
explícita → execução verificada → audit log.

## 4. Invariantes de segurança (nunca violar — `CLAUDE.md` raiz)

| # | Invariante | Onde a reconstrução prova |
|---|---|---|
| 1 | Catalogação é somente leitura: scan/análise nunca move, renomeia, exclui nem altera metadado. | Teste de scanner com hash do diretório antes/depois; ver `04-PIPELINES.arquivos.md`. |
| 2 | Operação física só existe como **plano dry-run** até aprovação explícita; execução é **copiar**, nunca mover. | `operations/` — `DryRunObrigatorio`; `10-VERIFICACAO.md`. |
| 3 | Nunca sobrescrever destino existente; hash antes e depois de cada cópia; tudo em audit log. | `_copiar_exclusivo` com `open("xb")`; ver `08-ERROS_CONHECIDOS.md` A3 (ramo de hash divergente hoje sem teste). |
| 4 | Nenhum dado sai da máquina por padrão. Serviço externo e sync são opt-in explícito, desligados inicialmente, com indicação prévia de **quais dados, finalidade, destino e revogação**. Nunca sincronizar fotos/RAW ou embeddings faciais sem consentimento específico e separado. Minimização de dados. | `settings.privacidade.servicos_externos=False`; opt-in de GenAI de pasta em `application_settings` (D-080); `docs/PRIVACIDADE.md`. **Divergência aberta:** caminho absoluto no payload (A: `08` M2). |
| 5 | Subprocesso sempre sem `shell=True`, argumentos em lista, caminhos validados (anti path traversal). Não atravessar symlinks por padrão. | `security/paths.py`; `metadata/exiftool.py`; `exif_write/writer.py`; `scanner/discovery.py`. |
| 6 | Reconhecimento facial desativado por padrão, processamento local, embeddings criptografados, resultado sempre sugestão a confirmar. | `faces/` é **stub**; `security/crypto.py` (Fernet + Keychain) pronto sem consumidor. |
| 7 | Exclusão de fotos **nunca é implementada**. Escrita EXIF em original só para **localização** (GPS lat/long, cidade, país) e só em **campo vazio** — nunca sobrescreve valor existente. Mesmo rigor de `operations/`: dry-run revisado, hash antes/depois, audit log. Qualquer outro campo EXIF fica fora de escopo (D-075). | `exif_write/` — reconferência ao vivo (TOCTOU); `08` A2/A4. |
| 8 | Nada que possa ser referência real de uma foto é apagado — nem do disco, nem do catálogo. Registro sem valor de acervo é **rebaixado a fonte de sinal** (`papel`), continua doando data/GPS/correlação (D-024). Medido: apagar 45.822 miniaturas do Apple Fotos levaria fotos com lugar estimado de 2.117 para 162. | Coluna `media_files.papel`; filtro `_ACERVO_OU_REFERENCIA`; nenhum `DELETE` de mídia no código. |

## 5. O acervo real (por que o produto é assim)

Estado do catálogo em 2026-09-19 (`SELECT` no `catalog.db`; foi zerado em 2026-08-16/17 para
baseline e re-varrido em 2026-08-19):

| Métrica | Valor |
|---|---|
| `media_files` | 102.251 |
| Fontes | 4: `/Volumes/photo` (rede, DiskStation), `/Volumes/Externo` (USB), Apple Fotos (`Photos Library`), `/Volumes/photo/Portfolio` |
| Com GPS próprio (`gps_lat`) | 21.753 (21%) |
| Sem `data_capturada` (só `mtime`) | 1.129 (1,1%) |
| `evidence` | 175.569 |
| `suggestions` | 55.096 (+143.044 `suggestion_evidence`) |
| `metadata_entries` (tags brutas) | 3.598.491 |
| `locations` | 2.203 |
| `trips` / `events` | 13 / 70 |
| `duplicate_groups` / `duplicate_members` | 1.348 / 3.158 |
| `exif_write_plans` / itens | 2 / 2.416 |
| `pasta_classificacoes_genai` | 3 |
| `people`, `face_*`, `tags`, `media_tags`, `nomes_classificados`, `operation_*` | 0 (stubs, ou nunca usados neste catálogo) |

Fatos medidos que **definem a ordem de prioridade** do roadmap (`docs/ROADMAP.md`, D-024..D-030):
- **Pixel local é raro.** Historicamente ~99 mil registros conhecidos, 44.661 do Apple Fotos só
  no iCloud e 45.397 do Lightroom em volume desmontado — só ~5% com arquivo legível. Tudo que
  precisa abrir a imagem (rosto, visão) alcança pouco.
- **GPS é raro e recente.** 58 câmeras de 2001 a 2026; só a EOS 5D Mark IV tem receptor
  próprio; 4 de 25 anos com GPS. Por isso existe **herança de GPS entre fontes** e **lugar
  estimado com raio de incerteza** — não é enfeite, é a única resposta a "onde" para a maior
  parte do acervo.
- **Intenção declarada é abundante.** 27.226 nomeações de álbum, notas, palavras-chave XMP/IPTC
  já no banco. Por isso "álbum nomeia, não divide" (D-030/D-034) e palavra-chave vira evidência
  de categoria (D-057).
- Escala já medida: 422.738 registros numa rodada de auditoria. Grade virtualizada, sem N+1, sem
  imagem em resolução completa são **requisitos**, não otimizações.

Baseline de performance (M2, 16 GB, 1.382 arquivos, `docs/PERFORMANCE.md`): varredura 59
arq/s; geração de sugestões 1,33 s; duplicatas 4,54 s. Motor e detector são full-scan em memória
(sem caminho incremental) — ver `09-MELHORIAS.md`.

## 6. Stack fixa (decidida; trocar exige justificativa de ganho concreto)

- Python ≥ 3.12; SQLite em WAL como **única fonte local de verdade**; SQLAlchemy 2 + Alembic.
- FastAPI só em `127.0.0.1` (`fotoorganizer/server/`) + React 18 / Vite 6 / TypeScript 5.6 /
  Tailwind 4 / TanStack Query 5 / react-virtual (`webapp/`). **Única UI.** PySide6 e Streamlit
  já foram tentados e removidos (commit `2e0ef1a`) — não reabrir sem evidência nova.
- Tauri 2 + python-build-standalone para o `.app` (não PyInstaller — fragilidade de codesign de
  libraw/libheif; `docs/EMPACOTAMENTO.md`). Marco 1 (assinatura ad-hoc) entregue; Marco 2
  (notarizado, US$ 99/ano) não aprovado.
- Metadados: exiftool em batch (`-stay_open`) quando instalado (D-026), fallback puro-Python
  (Pillow + exifread + pillow-heif + rawpy). MakerNotes fora da base bruta (D-027).
- Hashing: xxhash sempre + SHA-256 sob demanda; duplicata visual por `imagehash.phash`.
- Geocodificação reversa offline (`reverse_geocode`); externo só opt-in (não existe hoje).
- Thumbnails em `~/Library/Caches/FotoOrganizer/thumbs`, geradas em background.
- Testes: pytest (fixtures sintéticas geradas em runtime — **nunca foto real no repo**) + vitest.
- Config TOML; logging estruturado sem conteúdo sensível.
- Railway/Postgres: só como adaptador **opcional** de sync/backup de metadados; binários e
  embeddings nunca vão para lá. Não existe hoje.

## 7. Fora de escopo (com o motivo, para não voltar)

- Visão/rosto via provedor externo — conflita com invariante 4; quando entrarem, entram locais
  (`docs/PLANO_IA_E_PRODUTO.md` §8).
- Exclusão de fotos — invariante 7.
- Escrita EXIF fora de localização, ou sobrescrita de campo preenchido — D-075.
- Outra UI que não o webapp — decidido e revertido.
- Quatro lacunas de esquema DAM (derivados/linhagem, tags hierárquicas, direitos, coleções
  autorais) — não-bloqueio (D-008); só com caso de uso real.
- Score único de "saúde do acervo" — viola elo mais fraco; usar distribuição por dimensão.
- Paginação da grade — medido: não é o problema; o problema é âncora temporal (`NAVEGACAO.md`).

## 8. Decisões que a reconstrução DEVE preservar

Linha = título da decisão (`docs/DECISOES.md`, linha indicada) + o que ela fixa. Quem
reconstrói lê a entrada completa antes de mudar qualquer regra abaixo.

**Modelo de confiança e evidência**
- D-017 (`:269`) confiança como quantidade, não semáforo.
- D-018 (`:288`) unidade de decisão da Revisão é o grupo.
- D-021 (`:335`) precedência XMP → IPTC → EXIF na leitura de metadados.
- D-043 (`:1117`) `versao_logica` precisa ser lido (era escrito e nunca lido) — regenerar quando a
  metodologia mudar.
- D-057 (`:1770`) palavra-chave XMP/IPTC vira evidência de categoria.
- D-074 (`:2637`) herança de GPS confronta doadora antes **e** depois (duas âncoras) em vez de
  descartar o perdedor; nenhum bônus de confiança sem medição.
- D-081 (`:3162`) score de `llm_pasta` = 0,55, preliminar (amostra de 4 pastas).

**Sinal nunca é apagado**
- D-024 (`:387`) rebaixar, nunca apagar (invariante 8). D-035 (`:730`) registra a remoção das
  miniaturas do Apple Fotos feita **antes** de D-024 e o custo medido (10 fotos de 4.938).
- D-036 (`:788`) reapontar fonte não reescreve referência de nuvem. D-037 (`:820`) "não visto
  no walk" ≠ "apagado" — vira `arquivo_ausente`/`arquivo_offline`, nunca remoção.
- D-068 (`:2204`) "organizável" exige a fonte respondendo agora.

**Tempo e lugar**
- D-025 (`:409`) janela de herança depende do campo: cidade 10 min, região 2 h, país 12 h.
- D-029 (`:504`) GPS de câmera com receptor ≠ coordenada de celular (sinais diferentes).
- D-031 (`:542`) mapa do lugar estimado **sem tiles externos** (tile revela coordenada).
- D-032 (`:580`) raio de incerteza é **medido**: `raio(Δt)=min(50 km, max(15 m, 6 m/s×Δt))`.
- D-033 (`:626`) foto fora de alcance continua no mapa com o motivo.
- D-038 (`:863`) uma foto tem dois instantes (parede local e UTC); offset **não é coluna** —
  `data_capturada` é parede, `data_capturada_utc` existe, `tz_estimado` é IANA por país.
- D-051/D-052/D-058 (`:1501`, `:1570`, `:1799`) geo-resolução cedo (antes da cascata), como
  funções puras.
- D-066/D-067/D-073 (`:2101`, `:2156`, `:2585`) normalizar NFD em nome de pasta e mês por
  extenso antes de comparar.

**Agrupamento e nomes**
- D-030 (`:528`) + D-034 (`:653`) álbum **nomeia**, nunca divide; desempate em 3 camadas
  (`docs/AGRUPAMENTO.md` §2c). Os álbuns se aninham (mesma foto em 3 álbuns em 29 dias).
- D-042/D-046 (`:1087`, `:1245`) empilhamento de capturas irmãs (RAW+JPEG etc.) = 11,72% do
  acervo; um mapa só.
- D-053/D-054 (`:1624`, `:1677`) categoria travada em 3 valores; expansão é um **eixo novo**
  (tipo de mídia), não mais opções.

**Extração e fontes**
- D-026/D-027 (`:433`, `:455`) exiftool padrão quando instalado; MakerNotes fora.
- D-028 (`:477`) Lightroom é fonte externa e a principal do discovery.

**IA embarcada**
- D-004 (`:56`) IA é superfície de produto com três restrições (ler a entrada).
- D-022 → D-048/D-049 → D-059/D-060 (`:352`, `:1343`, `:1398`, `:1845`, `:1880`): advisor de
  cluster com `thinking` desligado; Haiku inventa onde Opus recusa; modelo final **Sonnet 5**,
  medido nos 104 clusters reais. Consultado só para sessões "neutra".
- D-047 (`:1288`) "resíduo" do advisor é 39% das sessões / 43% do acervo — não é zero.
- D-079 (`:3051`) prévia de custo do GenAI de pasta: estimativa local antes, contagem exata depois.
- D-080 (`:3113`) opt-in do GenAI de pasta mora em `application_settings`, não em TOML.

**Operações e escrita**
- D-061..D-064 (`:1933`..`:2012`) inventário por pasta (`inventario.json` + `INVENTARIO.md`),
  escrita aditiva, só após cópia verificada.
- D-075 (`:2741`) escrita EXIF de localização em campo vazio revoga parte do invariante 7.
- D-076/D-077 (`:2791`, `:2884`) allowlist de formatos com escrita direta medida **byte a byte**
  contra o acervo: só `.jpg/.jpeg/.cr2`; o resto vai para sidecar XMP.
- D-078 (`:2963`) `IPTC:EnvelopeRecordVersion` entra no andaime incondicional.

**Navegação e arte**
- `docs/NAVEGACAO.md` decisões 1-3: abas com esqueleto comum; esquerda é lugar, topo é recorte,
  um estado só (chips); rolagem contínua com âncora temporal — **não paginar**.
- Tokens de design: fonte de verdade é `webapp/src/index.css` `@theme`; `DIRECAO_DE_ARTE.md`
  espelha (`06-UI.arte.md`).

**Decisões de processo (histórico; não são requisitos do produto):** D-001..D-003, D-005..D-007,
D-009..D-016, D-019/D-020, D-023, D-039..D-041, D-044/D-045, D-050, D-055/D-056, D-069..D-072
(auditoria pós-gate e suas fatias). Úteis para entender *por que*, não *o quê*.

## 9. O que "pronto" significa para o produto inteiro

`scripts/verificar.sh` verde (pytest + benchmark de agrupamento 100% dos cenários + vitest +
build), nenhuma violação dos 8 invariantes, app abre e cada fatia é demonstrável ponta a ponta
com o catálogo real. Detalhe por funcionalidade em `10-VERIFICACAO.md`.
