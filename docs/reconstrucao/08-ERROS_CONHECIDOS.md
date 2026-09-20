# 08 — Erros conhecidos, dívida e o que a reconstrução deve fazer diferente

> Parte do mapa de reconstrução. Consolida: auditoria completa de 2026-09-19 (feita para este
> mapa, com verificação adversarial), `.planning/codebase/CONCERNS.md` (2026-08-16), auditoria
> pós-gate da fase 5 (D-069, 2026-08-14, `docs/auditoria-pos-gate-fase5.md`) e as avaliações de
> arquitetura/UX (`docs/AVALIACAO_ARQUITETURA.md`, `docs/AVALIACAO_UX.md`).
>
> Status: **aberto** (existe no código de `524903d`), **corrigido** (com a decisão/commit),
> **aceito** (limitação por desenho, documentada), **verificar** (sem registro de correção; quem
> reconstrói confirma antes de assumir).

## A. Auditoria de 2026-09-19 — todos ABERTOS em `524903d`

Base: main, working tree limpo. Suítes reais: pytest 966 passed / 3 failed / 23 errors (os 26
são sandbox — bind de socket e CA bundle bloqueados: `test_http_seguro` ×23, `test_web_launch`,
`test_apple_photos` ×2; não são defeitos); vitest 186/186; `npm run build` ok. Achados alto
foram submetidos a verificador independente que tentou refutá-los; severidades abaixo são as
que sobreviveram.

### ALTO

**A1 — Corrida em `JobManager` permite dois jobs no mesmo plano (e dois exiftool no mesmo
original).** `fotoorganizer/server/jobs.py:58` (`ocupado()` sem lock), `:127`/`:140` (checagens
sem lock), `:150-162` (`_iniciar`: check em `:150` e `self._thread=` em `:159` fora do
`with self._lock`, que só protege `_estado`). Rotas `executar_plano` (`app.py:1315`) e
`executar_plano_exif` (`app.py:1412`) são `def` síncronas → threadpool do Starlette. Nenhuma
guarda no nível do plano (`exif_write/executor.py:309` seta EXECUTANDO sem testar).
Reproduzido: 55/200 rodadas com 2+ threads de escrita sem tuning de GIL. Impacto: `writer.py:87`
não usa `-overwrite_original`, então o 2º exiftool renomeia a versão já modificada por cima do
`.jpg_original` — destrói o backup pristino que sustenta a restauração (invariante 8).
`_exec_control` sobrescrito (`:143`) → `cancelar()` para só uma thread. Gatilho realista: duplo
clique em `EscritaExif.tsx:395` (`disabled` vem de estado *polled*, sem `isPending`).
**Na reconstrução:** check-then-act e atribuição de thread dentro de um único lock; estado
EXECUTANDO do plano como segunda guarda (transição atômica); botão de executar com `isPending`;
teste de concorrência com `threading.Barrier` exigindo 0 duplas em 200 rodadas.

**A2 — Sidecar XMP grava GPS com hemisfério errado e a verificação aprova.**
`exif_write/writer.py:103-110` monta `-GPSLatitude={abs(lat)}` + `-GPSLatitudeRef=S` sem ramo
para sidecar; `XMP:GPSLatitudeRef` é `writable='false'` (exiftool 13.55) e o Ref é descartado
sem aviso. Reprodução pelo caminho real com (-22.95, -43.18): sidecar contém
`<exif:GPSLatitude>22,57.0N</exif:GPSLatitude>` — hemisfério **afirmado** errado (Rio → Mar
Vermelho). `verificacao.py:47` (`TAGS_POR_CAMPO_SIDECAR`) não lista Ref; `diferenca()` (`:470`)
só exige `valor_depois is not None`; `campo_gravado()` (`:486-490`) só exige presença → item vira
GRAVADO e o audit log mente. Sticky: `executor.py:78` nunca sobrescreve sidecar existente e
`_campo_ja_preenchido` lê o valor errado como válido. `executor.py:122-126` assume "sidecar
grava valor já assinado" — falso. Alcance: `.dng/.tif/.tiff/.cr3/.heic` (`formatos.py:48`);
3/1.399 no acervo medido; vira crítico com `.heic`. Teste existente
(`tests/test_exif_write_writer.py:297-314`) só assere presença da tag.
**Na reconstrução:** no ramo sidecar gravar `-XMP:GPSLatitude=<decimal assinado>` sem Ref;
verificação compara **valor** esperado × lido (tolerância numérica), nunca presença; teste com
coordenada sul/oeste assertando sinal; e sidecar existente é comparado por valor antes de ser
tratado como "já preenchido".

**A3 — Invariante 3 sem prova: ramo de hash divergente após cópia não é testado.**
`operations/executor.py:211-213` (`hash_pos != hash_pre` → `unlink` + erro). `grep "hash_pos"
tests/test_operations.py` só devolve asserts de igualdade (`:178`, `:375`, `:464`).
**Na reconstrução:** teste que força `sha256_full(destino)` divergente e assere cópia removida,
item ERRO, audit sem `copia_verificada`.

**A4 — Invariante 7 sem prova: reconferência ao vivo (TOCTOU) no alvo direto não é testada.**
`exif_write/executor.py:374-392`. O único teste que a menciona
(`tests/test_exif_write_executor.py:330-357`) admite no comentário (`:338-340`) que o item já é
terminal e "nem entra em pendentes"; `test_sidecar_existente_nunca_e_sobrescrito` (`:426`) cobre
só sidecar; `test_dry_run_promove_campo_vazio_e_pula_preenchido` (`:164`) cobre dry-run, não
execução. **Na reconstrução:** teste que grava GPS no `.jpg` via exiftool entre `dry_run()` e
`executar()` num item PRONTO e assere PULADO + hash inalterado.

### MÉDIO

**M1 — Duas bases de tempo na linha do tempo.** `classification/engine.py:469, 501, 571, 585` —
`m.data_capturada or m.mtime`. `data_capturada` é hora de parede local (declarado em
`models/catalog.py:195-202`); `mtime` é UTC naive explícito (`scanner/scanner.py:117-119`,
`_ts`). Nenhuma normalização em `geolocation/timezones.py` (só escreve `tz_estimado` *depois*),
`grouping/`, `repositories/`. Prova no catálogo: de 53.967 registros com ambos, 17.982 (33,3%)
têm delta múltiplo **exato** de 1 h (+3 h: 17.468; +2 h: 8.857) — ex. `1W0B8799.CR2` 11:39:20 vs
13:39:20. Alcance: 1.129 só-mtime (1.046 sem GPS). Impacto: herança de GPS
(`correlacao.py:424-425`) corta no delta cru → +3 h joga fora de "cidade" (10 min) e "regiao"
(2 h) — **supressão**, não cidade errada; acontecimentos (`eventos_temporais.py:56-58`, piso
90 min / teto 8 h) podem cortar no lugar errado; viagens imunes (`GAP_NOVA_VIAGEM`=3 d).
**Na reconstrução:** um único `quando(media)` que converte mtime para parede local via tz da
fonte/`tz_estimado` antes de qualquer comparação (resolve M5 junto).

**M2 — Caminho absoluto enviado à API da Anthropic onde se promete "nome da pasta".**
Cadeia sem redução: `scanner/scanner.py:443` (`media.pasta = str(path.parent)`) →
`classification/candidatas_de_pasta.py:72` → `server/genai_pasta.py:224-230` →
`classification/location_advisor.py:203` (`"pasta": p.pasta`); e `engine.py:707` →
`advisor.py:125` (advisor de cluster, gate único sem prévia). Payload capturado com cliente
mockado: `{"pasta": "/Users/fulano/Pictures/Viagem Chile 2023", ...}`. Contradiz
`docs/PRIVACIDADE.md` ("nome da pasta"; "nenhum ... caminho de arquivo sai"),
`location_advisor.py:6` (docstring), `:67` (comentário `# caminho relativo/nome da pasta`),
`docs/DECISOES.md:3175` e a UI (`ClassificacaoPasta.tsx:107-108`). Agrava: a UI mostra
`pastaCurta()` (`:32-35`, dois últimos segmentos) enquanto o backend envia tudo. O teste-prova
(`tests/test_classification_pasta_genai.py:41`, `:82`) usa fixture relativa e lista de proibidos
sem `/`. Sob duplo opt-in, sem byte de imagem. `exemplos_arquivos` do advisor de cluster **não**
é vazamento — `docs/AGRUPAMENTO.md:179-180` anuncia.
**Na reconstrução:** `pasta` no payload = `Path(pasta).name` (ou relativo à raiz da fonte);
prévia mostra exatamente o que sai; teste com fixture absoluta e `"/Users"` nos proibidos.

**M3 — Falha pós-verificação deixa destino órfão e trava o item.** `operations/executor.py:210`
(`sha256_full(destino)`) e `:215` (`copystat`) vêm depois da cópia já correta; `OSError` aí cai
em `:247` sem `unlink` → item ERRO com destino íntegro no disco. Retomada: `pendentes = status
!= CONCLUIDA` (`:168`) → `_copiar_exclusivo` levanta `FileExistsError` (`:263`) → "destino já
existe — sobrescrita bloqueada" (`:244`) para sempre. **Na reconstrução:** no retry, destino
existente com `sha256 == origem` é marcado CONCLUIDA; `copystat` é best-effort (aviso).

**M4 — phash da miniatura ≠ phash do original para fotos rotacionadas.** `duplicates/phash.py:97`
(`Image.open` sem `exif_transpose`) vs `thumbnails/generator.py:51` (`ImageOps.exif_transpose`);
`calcular_phash` (`:65-81`) usa a miniatura quando existe e a docstring "o resultado é o mesmo"
é falsa para Orientation≠1. Duas cópias da mesma foto retrato, uma com thumb e outra sem, não
agrupam. **Na reconstrução:** `exif_transpose` também em `_abrir`.

**M5 — Duas regras divergentes para "quando a foto foi tirada".** `engine.py:827-844` prefere
`data_no_nome` sobre mtime (e vira `{ano}` do destino, `:1213`); `:469/:501/:571/:585` usam
`data_capturada or mtime` ignorando o nome. `IMG-20150420-WA0001.jpg` sem EXIF copiado em 2024
→ ano 2015 na sugestão, viagem/evento em 2024. **Na reconstrução:** ver M1.

**M6 — Testes de mutação de original pulam em silêncio sem exiftool.**
`tests/test_exif_write_executor.py:47-49` (`skipif(not ExifToolExtractor.disponivel())`; idem
`test_exif_write_writer.py:31`, `test_exiftool_extractor.py:17`). Sem CI (não há
`.github/workflows`), um ambiente sem o binário passa verde sem executar o caminho mais
perigoso. **Na reconstrução:** CI com exiftool instalado; variável que transforma skip em fail
no `verificar.sh`.

**M7 — Entitlement contradiz o próprio comentário.** `src-tauri/Entitlements.plist:10-13`:
comentário "comece sem esta chave; ative só se um dep quebrar"; valor
`allow-unsigned-executable-memory=true`. Com `disable-library-validation` (`:8`) derruba as duas
proteções do hardened runtime. **Na reconstrução:** começar sem; se um dep exigir, registrar
qual no comentário.

**M8 — Cancelamento de execução/EXIF sem teste ponta a ponta.** `server/jobs.py:61-65`
(`JobManager.cancelar()`) nunca exercitado sobre job de execução ou escrita EXIF (`grep
"\.cancelar(" tests/` só acha `ScanControl` direto); `exif_write/executor.py:332-334` sem
nenhum teste; o analog em `operations/` tem `test_cancelamento_e_retomada`.

### BAIXO

- **B1** `server/app.py:102` — `localhost` em `_HOSTS_LOCAIS` sem porta: Origin
  `http://localhost:3000` (dev server de outro projeto) passa o guard (`:463-465`) e dispara POST
  sem corpo. Mitigante: porta efêmera. Reconstrução: comparar Origin completo (host+porta).
- **B2** `src-tauri/tauri.conf.json:13` `csp: null` e nenhum header CSP no FastAPI; como a
  janela é `WebviewUrl::External` (`main.rs:55-58`), CSP do Tauri nem se aplicaria. Sem XSS
  encontrado. Reconstrução: CSP via middleware do servidor.
- **B3** `server/jobs.py:130/143` — `_exec_control` atribuído antes de `_iniciar` confirmar e
  nunca limpo (dobra em A1).
- **B4** `scanner/scanner.py:245/252` — `except Exception` no consumidor engole erro de flush do
  SQLAlchemy; sessão fica em `PendingRollbackError`, arquivos seguintes viram "erro" e
  `_checkpoint` (fora do try) estoura. Padrão confirmado; gatilho não reproduzido.
- **B5** `security/crypto.py:47-78` `KeychainKeyStore`/`keystore_padrao` sem teste; sem consumidor
  (faces é stub).
- **B6** `operations/executor.py:249` ramo ENOSPC sem teste.
- **B7** `tests/test_database.py:31` e `tests/test_exif_write_writer.py:249` — zero asserts (só
  "não levanta").
- **B8** `server/app.py:660` `GET /api/midia/alcances` e `:1206` `POST /api/reconciliacao` sem
  consumidor em webapp/CLI/scripts (a CLI chama `reconciliar()` direto, `cli.py:387-393`).
- **B9** `server/app.py` — 12 `select()`/`session.execute` diretos (ex. `:477`, `:893`, `:1484`)
  no mesmo arquivo que instancia `MediaRepository`/`SuggestionRepository`.
- **B10** Docs desatualizados: `docs/ROADMAP.md:252` (item 9 "escrita é caminho novo" — `exif_write/`
  existe, com fallback sidecar `formatos.py:100-108`); `:126` (`EVENTOS.md` existe, 165 linhas);
  `:300` (cita `cli.py:156-158`; a mensagem real está em `:288-289`); `docs/DECISOES.md:2788`
  (D-075 "aguardando implementação" — convenção do arquivo é "decidido (implementado e
  commitado)", cf. `:2440`); `.planning/REQUIREMENTS.md` marca GENAI-01..03 como Pending com
  a Fase 7 já mergeada; `AGENTS.md` (raiz) ainda traz o invariante 7 pré-D-075 ("MVP não
  implementa ... futuro: sidecar XMP apenas") — diverge de `CLAUDE.md` e não é symlink como
  D-009 previa; `.claude/agents/agente-arte.md` carrega tokens hex que o CSS já não usa.

- **B11** `webapp/src/api.ts:7` — `Fonte.tipo` é união de 3 valores; backend `SourceType` tem 4
  (`lightroom`, `models/catalog.py:39-42`); `Sidebar.tsx:11-15` `ICONE_TIPO` sem entrada para
  Lightroom. Fonte Lightroom importada pela CLI aparece sem ícone/fora do tipo.
- **B12** `server/app.py:1089` limita `limit` de `GET /api/sugestoes` a 500 por requisição;
  `06-UI.md` §3.17 descreve "mostrar mais" incrementando `limite` sem teto — se a UI não usar
  `offset`, um grupo com > 500 sugestões para em 500 enquanto o rótulo promete o resto.
  **Verificar** (achado do dry-run de reconstrução, não confirmado contra `Review.tsx`).
- **B13** `exif_write/writer.py:126` — `subprocess.run` do exiftool **sem `timeout`**
  (`verificacao.dump`/`dump_lote` têm 30 s). Exiftool travado em arquivo corrompido prende o job.
- **B14** Declarados sem produtor nem consumidor: `media_files.status_revisao` (enum
  `nao_revisado·pendente·revisado`), `media_files.volume`, `OperationStatus.APROVADA`,
  tabelas `tags`/`media_tags` (vazias); origens de confiança `gps` 0,95, `geocoding_externo`
  0,75, `visao` 0,30, `agrupamento` 0,70 sem nenhuma linha em `evidence`. **Verificar** se são
  ponto de extensão ou dívida (`00-INDICE` § Decisões em aberto, 7).
- **B15** `docs/EVENTOS.md` diz que o benchmark tem 17 cenários; `scripts/avaliar_agrupamento.py`
  tem 19 (gate roda 19/19). Doc desatualizado.

### Verificado e limpo em 2026-09-19 (não repetir como suspeita)
Segredos versionados (zero; `.gitignore:16-22`), injeção SQL/comando/XSS (zero `text(`,
`shell=True`, `dangerouslySetInnerHTML`), path traversal (`security/paths.py:37-44` valida
pós-`resolve()`; endpoints de imagem recebem `media_id: int`), CORS (nenhum middleware), bind
(`cli.py:652` em 127.0.0.1), DNS rebinding (guard de Host), invariante 7 (recheck ao vivo,
hash pré/pós, diff de tags, audit), CVEs (`requests` 2.32.3 é transitiva via osxphotos, não
importada).

## B. Dívida estrutural (`.planning/codebase/CONCERNS.md`, 2026-08-16)

| Item | Onde | Status |
|---|---|---|
| Motor de sugestões carrega o catálogo inteiro em memória; sem caminho incremental — toda geração reprocessa 100%. | `classification/engine.py:266-326` | aberto |
| Detector de duplicatas idem (full-scan + `selectinload`). | `duplicates/detector.py:120-156` | aberto |
| `_completar_sha256` serial, sem o `ThreadPoolExecutor` que scanner/importer usam. | `duplicates/detector.py:168-183` | aberto |
| `security/http_seguro.py` (445 linhas, testado) sem consumidor; SSRF/DNS rebinding conscientemente adiados na docstring. | `http_seguro.py:30-39` | aceito até o 1º consumidor — obrigatório fechar SSRF no mesmo PR |
| Plano `OperationPlan.EXECUTANDO` não é reconciliado no boot após crash (só scan tem `reconciliar_orfas`). | `server/app.py:1391-1402`, `operations/executor.py:162-194` | aberto (também Tier 3 de D-069) |
| Índice ausente em `pasta` (árvore O(n)). | — | corrigido (LANC-02, migração 0018, 9 índices de FK) |
| `PhotoGrid.tsx` e `ClaudeAdvisor` sem teste dedicado. | `webapp/src/components/PhotoGrid.tsx`, `classification/advisor.py` | verificar |

## C. Auditoria pós-gate da fase 5 (D-069, 18 achados, 2026-08-14)

Detalhe com SQL/linha em `docs/auditoria-pos-gate-fase5.md`. Nenhum era regressão (diff contra
`48c4378` vazio nos módulos decisórios; confirmado empiricamente).

| Tier | Achado | Status |
|---|---|---|
| 1 | Duplicata VARIANTE podia excluir RAW ou JPEG do plano sem aviso (2.514 conjuntos) — toca invariante 8 | corrigido D-070 (PR #7) |
| 1 | Badge "Alta" refletia só a confiança da data em 29,6% do acervo ("Não classificadas") | corrigido D-071 (vira "Sem categoria") |
| 1 | Aba Viagens falsamente vazia por 50–120 s (N+1) | corrigido D-072 (~0,1 s) |
| 1 | Confiança agregada contradiz as evidências no popover "por quê?" | verificar |
| 2 | Categoria "Eventos" 100% por heurística fraca (11.492 fotos), nunca por vocabulário literal | verificar (D-057 adicionou palavra-chave XMP/IPTC como evidência; não cobre pasta) |
| 2 | Ações de duplicata falham em silêncio | verificar |
| 2 | Inventário por pasta O(n²) (7.618 fotos na maior pasta) | verificar contra D-064 |
| 2 | Panorama mostra dois "organizáveis" (96.692 vs 92.792) | corrigido D-068 (funil exige fonte respondendo) |
| 2 | "Rejeitar em lote" não existe, só "Aprovar em lote" | verificar |
| 3 | Destino sem prefixo de categoria (668 fotos) | verificar |
| 3 | Mesma viagem fragmentada em 5 grafias/categorias na Revisão | verificar |
| 3 | 23 de 60 cards de viagem chamados "Brasil" | verificar |
| 3 | Rótulo da sidebar ≠ total do filtro (5×) | verificar |
| 3 | Painel "O acervo" sem loading state (13–20 s) | verificar |
| 3 | Plano preso em "executando" após crash | aberto (= B acima) |
| 3 | Sem timestamp da última detecção de duplicata | verificar |
| 4 | Grupos de duplicata não explicam por que foram agrupados | verificar |
| 5* | Mês por extenso sem reconhecimento em `grouping/datas.py` | corrigido D-073 |

## D. Avaliação de UX (2026-08-06 e fase 6)

Os 15 itens priorizados (`docs/AVALIACAO_UX.md` §D) foram todos endereçados nas Fases 3-4
(REV-01..07, CONS-01..08; `.planning/PROJECT.md` § Validated, 2026-08-16/17). As 5 propostas da
fase 6 (§4.1-4.5: confiança que leva à evidência, revisão em lote, mapa lido×estimado, linha do
tempo por fonte, plano antes-e-depois) são **melhorias**, não erros — ver `09-MELHORIAS.md`;
só o mapa lido×estimado foi implementado (D-031..D-033, D-050, D-065). BUG-01..04 da §C
(original em pacote rebaixado; vídeo não catalogado; filtro "Tudo"; advisor "Viagens" não cria
viagem) — todos corrigidos e validados em 2026-08-16.

## E. Ambiente e teste (não são bugs, mas custam reconstrução)

- 26 testes exigem `bind()` em 127.0.0.1 ou leitura do CA bundle do sistema — falham em
  sandbox sem rede. Documentar como pré-requisito de CI. Fora do sandbox passam (45/45 nos três
  arquivos, 2026-09-20).
- Sem linter/type-checker configurado (nenhum ruff/mypy/eslint). Qualquer reconstrução deve
  nascer com ambos e com CI rodando `scripts/verificar.sh`.
- `.planning/codebase/*` está 200 commits atrás de `524903d` (anterior às Fases 6-7).
