# Codebase Concerns

**Analysis Date:** 2026-08-16

Reanálise feita lendo o código atual (scanner, motor de sugestões,
duplicatas, operações, servidor FastAPI, repositórios e componentes React)
sem usar a auditoria pós-gate-fase-5 como fonte. Os invariantes de
segurança do `CLAUDE.md` (não mover/excluir original, dry-run obrigatório,
sem `shell=True`, nada sai da máquina por padrão) estão respeitados em todo
código lido — não há achado que os viole. Os pontos abaixo são dívida
técnica, fragilidade e lacunas de teste observadas na leitura direta.

## Tech Debt

**Motor de sugestões processa o catálogo inteiro em memória, de uma vez:**
- Issue: `SuggestionEngine.gerar()` carrega `list(session.scalars(select(MediaFile)))` — todas as linhas da tabela — e monta vários dicionários por id (`por_id`, `curadoria`, `herancas`) para o catálogo inteiro antes de processar qualquer sugestão. Não há streaming, chunking nem limite.
- Files: `fotoorganizer/classification/engine.py:266-326`
- Impact: tempo e memória do job "gerar sugestões" crescem linearmente (e nas etapas de correlação/agrupamento, potencialmente pior que linear) com o tamanho do acervo. Não existe modo incremental — toda geração reprocessa 100% das fotos, mesmo quando só um punhado mudou desde a última rodada.
- Fix approach: paginar a carga por lotes de mídia (mantendo os índices auxiliares — câmeras, álbuns — carregados uma vez), ou introduzir um caminho incremental que só reprocessa fotos novas/alteradas desde a última geração.

**Detector de duplicatas tem a mesma forma de full-scan em memória:**
- Issue: `DuplicateDetector.detectar()` carrega `select(MediaFile).where(MediaFile.tamanho > 0)` inteiro (com `selectinload(source)`) antes de calcular phash/sha256 e montar a BK-tree.
- Files: `fotoorganizer/duplicates/detector.py:120-156`
- Impact: mesma característica de crescimento O(n) em memória e tempo de wall-clock por rodada completa; sem exclusão de mídia já resolvida/decidida da fase de carregamento.
- Fix approach: mesmo tratamento do item acima — carregar em lotes ou restringir a fase de carregamento por fonte/lote quando o catálogo crescer.

**`_completar_sha256` não usa o pool de workers que o resto do código já usa:**
- Issue: enquanto `scanner/scanner.py` e `sources/importer.py` paralelizam extração via `ThreadPoolExecutor`, `DuplicateDetector._completar_sha256` lê e hasheia cada candidato a duplicata exata num loop `for` síncrono, thread única.
- Files: `fotoorganizer/duplicates/detector.py:168-183`
- Impact: em um acervo com muitos candidatos de mesmo tamanho+hash-rápido (comum em bibliotecas com exports repetidos), a etapa vira um gargalo serial de I/O que o restante do pipeline já sabe evitar.
- Fix approach: reaproveitar o mesmo padrão de `ThreadPoolExecutor` + janela limitada usado no scanner.

**Infra de download HTTP sem consumidor e com SSRF/DNS-rebinding conscientemente adiado:**
- Issue: `fotoorganizer/security/http_seguro.py` (445 linhas, bem testado) existe pronto para um futuro provider de geocodificação externo opt-in, mas hoje não tem nenhum chamador. A própria docstring do módulo declara que proteção contra SSRF e DNS rebinding foi deixada de fora "enquanto não houver caso de uso com URL de origem não confiável".
- Files: `fotoorganizer/security/http_seguro.py:30-39`
- Impact: nada quebra hoje (nenhum código chama a função), mas é uma armadilha de ativação silenciosa — o primeiro consumidor real que passar uma URL vinda de dado de terceiro (não escolhida pelo usuário) herda essa lacuna sem qualquer gate automático que force a revisão.
- Fix approach: quando o primeiro consumidor for escrito, tratar a adição de proteção SSRF/DNS-rebinding como parte obrigatória do mesmo PR, não como débito futuro solto.

**Job de execução de plano não tem reconciliação de órfão como o scanner tem:**
- Issue: `reconciliar_orfas` (chamado no startup do servidor) resolve sessões de scan travadas em `RODANDO` depois de um crash. Não existe equivalente para `OperationPlan.status == EXECUTANDO`: se o processo morrer no meio de uma execução física, o plano fica marcado como "executando" para sempre no banco, sem rotina de boot que o normalize.
- Files: `fotoorganizer/server/app.py:1391-1402` (só reconcilia scan), `fotoorganizer/operations/executor.py:162-194` (seta `EXECUTANDO` sem contrapartida de reconciliação)
- Impact: a UI mostra um plano "executando" que na verdade está parado; nada indica ao usuário que precisa reenviar o POST de execução. A reexecução manual funciona corretamente (itens `CONCLUIDA` são pulados), mas isso depende do usuário descobrir sozinho que precisa tentar de novo.
- Fix approach: no mesmo `startup` hook que reconcilia scans órfãos, normalizar planos em `EXECUTANDO` sem job ativo para um estado que deixe claro que a execução parou e pode ser retomada.

## Known Bugs

Nenhum bug funcional confirmado por leitura direta do código desta rodada
(os invariantes de cópia seguem hash-antes/hash-depois, criação exclusiva
`xb`, e limpeza de parcial em toda falha). O único comportamento
observável e não intuitivo é o do plano "preso em `EXECUTANDO`" listado
acima em Tech Debt — não corrompe dado, mas confunde o usuário.

## Security Considerations

**SSRF/DNS rebinding não coberto no downloader HTTP (ver Tech Debt acima):**
- Risk: quando um provider de geocodificação externo opt-in existir e receber URL não fixada pelo usuário, requisições poderiam ser direcionadas a endereços internos.
- Files: `fotoorganizer/security/http_seguro.py`
- Current mitigation: nenhum consumidor real hoje; todo uso previsto usa endpoint fixo escolhido pelo usuário.
- Recommendations: gate de revisão obrigatório no PR que introduzir o primeiro consumidor de URL não confiável.

**Middleware de origem local depende só de `Host`/`Origin`:**
- Risk: `_exigir_origem_local` (server/app.py) bloqueia requisições cujo `Host` não é loopback e cujo `Origin` (quando presente) não é loopback — mitiga DNS rebinding e chamadas de página de terceiros. Requisições sem `Origin` (curl, scripts locais) passam livremente, por design (é o próprio CLI/ferramentas locais). Isso é aceitável para um servidor 127.0.0.1 de uso único, mas significa que qualquer processo rodando como o mesmo usuário no Mac (não só o navegador) pode chamar a API sem restrição — inclusive iniciar scans, aprovar sugestões em massa e criar planos de cópia.
- Files: `fotoorganizer/server/app.py:411-431`
- Current mitigation: escuta só em loopback; checagem de `Host`/`Origin` cobre o vetor de navegador (o mais provável).
- Recommendations: nenhuma ação necessária para o modelo de ameaça atual (app local single-user); vale documentar explicitamente esse limite se o produto algum dia rodar em ambiente multiusuário.

**Chave de embeddings faciais cai para arquivo 0600 quando o Keychain falha, sem alertar o usuário na UI:**
- Risk: `keystore_padrao` registra um `log.warning` e segue silenciosamente com `FileKeyStore` (arquivo 0600 no diretório de dados) quando o Keychain do macOS não está disponível — o que pode acontecer em ambientes sandboxed ou headless.
- Files: `fotoorganizer/security/crypto.py:70-78`
- Current mitigation: a proteção 0600 ainda existe, e reconhecimento facial já é opt-in/desligado por padrão (invariante 6).
- Recommendations: expor esse fallback também na UI/config (não só no log), já que embeddings faciais são dado biométrico sensível e o usuário deveria saber quando a proteção caiu do Keychain para um arquivo simples.

## Performance Bottlenecks

**`arvore_de_pastas` e todo filtro por `pasta` fazem table scan — sem índice na coluna:**
- Problem: `_sob_a_pasta` monta um `LIKE 'prefixo%' ESCAPE '\'` sobre `MediaFile.pasta`, usado tanto no filtro de mídia quanto em `/api/pastas` (árvore de pastas, chamada a cada nível clicado na sidebar). Não existe `Index` em `pasta` no modelo.
- Files: `fotoorganizer/repositories/media.py:136-151,367-444`, `fotoorganizer/models/catalog.py:117-137` (índices existem para `trip_id`/`event_id`/`papel`/`arquivo_offline`, mas não para `pasta`)
- Cause: consulta por prefixo de string sem índice correspondente força varredura completa da tabela `media_files` a cada clique na árvore de pastas.
- Improvement path: adicionar índice em `pasta` (o próprio código já documenta o precedente de ter adicionado índice em `trip_id`/`event_id` quando o custo de escrita se justificou por um consumidor real e mensurável — `pasta` está no mesmo caso, já que a navegação por pastas é a forma primária de explorar um acervo com muitos registros sem GPS/data).

**Cópia física lê cada arquivo de origem duas vezes e o destino uma vez:**
- Problem: `_executar_item` calcula `sha256_full(origem)` (leitura completa) **antes** de copiar, depois `_copiar_exclusivo` lê a origem de novo em streaming para escrever o destino, e por fim `sha256_full(destino)` (outra leitura completa) para verificar. No total: 2 leituras integrais da origem + 1 leitura integral do destino + 1 escrita integral do destino, por item.
- Files: `fotoorganizer/operations/executor.py:196-220`
- Cause: hash pré-cópia e cópia são passes separados sobre o mesmo arquivo de origem, em vez de um único passe que hasheia enquanto copia.
- Improvement path: computar `hash_pre` durante o mesmo streaming que escreve `_copiar_exclusivo` (hash incremental do que já foi lido), eliminando uma leitura completa da origem por item — relevante sobretudo para vídeo e RAW grandes em volumes lentos (NAS/USB).

**`OperationExecutor.executar` faz um `session.commit()` por item copiado:**
- Problem: o laço de execução (`for n, item in enumerate(pendentes, ...)`) commita a sessão a cada item, não em lote.
- Files: `fotoorganizer/operations/executor.py:174-181`
- Cause: durabilidade item-a-item (correto para nunca perder o registro de uma cópia concluída em caso de crash), mas paga o custo de um fsync do SQLite por arquivo.
- Improvement path: aceitável para acervos pequenos/médios; se planos de dezenas de milhares de itens se tornarem comuns, considerar commit em lotes pequenos (ex. a cada N itens) mantendo o hash_pre/hash_pos e o `AuditLog` do item já persistidos antes do commit em lote, para não abrir mão da garantia de durabilidade por item concluído.

## Fragile Areas

**`classification/engine.py` é um motor monolítico de 1138 linhas com precedência de regras codificada só em ordem de `if/elif`:**
- Files: `fotoorganizer/classification/engine.py` (cascata completa: pasta de categoria → tipo de sessão → palavra-chave → advisor LLM, em `_categoria`; GPS próprio → GPS herdado → pasta → vizinhança, em `_evidencias_geo`)
- Why fragile: a ordem de precedência entre fontes de evidência é a regra de negócio central do produto (confiança do "elo mais fraco", docs/CONFIANCA.md) e está expressa apenas como sequência de `if`/`elif`/`return` dentro de métodos longos, documentada em comentários em português, sem uma tabela de casos testada exaustivamente para todas as combinações de fontes concorrentes.
- Safe modification: qualquer alteração de ordem ou adição de uma nova fonte de evidência precisa ser acompanhada de teste que fixe explicitamente a precedência esperada contra as outras fontes já existentes — não só o caso novo isolado.
- Test coverage: `tests/test_suggestion_engine.py` (1321 linhas) cobre muitos cenários individuais, mas não é organizado como matriz de precedência; é fácil adicionar um cenário novo sem perceber que ele quebra a ordem de outro já coberto em separado.

**`webapp/src/components/PhotoGrid.tsx` — a grade virtualizada central da UI — não tem teste:**
- Files: `webapp/src/components/PhotoGrid.tsx` (124 linhas; sem `PhotoGrid.test.tsx`)
- Why fragile: calcula colunas a partir de `ResizeObserver`, faz paginação implícita (`fetchNextPage` quando a última linha visível está a 3 linhas do fim) e mapeia índice linear para posição `linha.index * colunas + c` para navegação por teclado — exatamente o tipo de aritmética que costuma ter off-by-one e não dá sinal visível óbvio quando quebra (a foto errada fica selecionada, ou a paginação para de disparar).
- Safe modification: qualquer mudança em `colunas`, no cálculo de `linhas` ou no gatilho de paginação deveria vir com teste; hoje depende de teste manual.
- Test coverage: outros componentes de mesmo porte (`Review.tsx`, `Mapa.tsx`, `Sidebar.tsx`, `Operations.tsx`, `Duplicates.tsx`, `Trips.tsx`) têm `.test.tsx` equivalente; `PhotoGrid.tsx`, `Panorama.tsx`, `LinhaDoTempo.tsx`, `Loupe.tsx`, `Miniatura.tsx` e `Confianca.tsx` não têm.

**`ClaudeAdvisor` (integração real com a API Anthropic) só é exercitada indiretamente via dublê:**
- Files: `fotoorganizer/classification/advisor.py:105-177`
- Why fragile: é o único ponto do código que fala com um serviço de rede externo pago, com parsing de JSON estruturado, tratamento de `stop_reason == "refusal"` e captura ampla de exceção (`except Exception`) para nunca derrubar a geração de sugestões. Nenhum teste no repositório instancia `ClaudeAdvisor` com um cliente mockado para verificar esses três caminhos (resposta válida, recusa, JSON malformado, exceção de rede) — os testes existentes usam `FakeAdvisor`/`NullAdvisor`, que passam ao largo do código real de `ClaudeAdvisor.classificar`.
- Safe modification: qualquer mudança no schema estruturado (`_SCHEMA`), no tratamento de `stop_reason` ou na extração do bloco de texto da resposta fica sem rede de segurança automatizada.
- Test coverage: nenhuma, hoje.

## Scaling Limits

**Geração de sugestões e detecção de duplicatas são sempre full-recompute, nunca incrementais.**
- Current capacity: qualquer chamada a `/api/sugestoes/gerar` ou `/api/duplicatas/detectar` reprocessa 100% do catálogo — não existe caminho para "só as fotos novas desde a última rodada".
- Limit: o tempo de wall-clock de cada rodada cresce linearmente (na melhor hipótese) com o total de fotos catalogadas — cresce junto do acervo, não junto do que mudou.
- Scaling path: introduzir processamento incremental (marca d'água por `indexado_em`/versão de lógica) para os casos comuns de "importei mais 500 fotos", mantendo o full-recompute como operação explícita separada para quando a lógica de classificação mudar de versão.

**Navegação por árvore de pastas (`/api/pastas`) é O(n) na tabela inteira por clique, sem índice de apoio (ver Performance Bottlenecks).**
- Current capacity: cada nível da árvore paga uma varredura completa de `media_files` filtrando por `LIKE`.
- Limit: cresce proporcional ao total de registros do catálogo (acervo + testemunhas), não ao tamanho da subárvore consultada — o oposto do que a UI promete ("um nível por vez" para evitar carregar tudo).
- Scaling path: índice em `pasta`, como descrito acima.

## Missing Critical Features

**Nenhuma rotina de boot reconcilia planos de operação travados em `EXECUTANDO` após um crash** (detalhado em Tech Debt) — falta o equivalente de `reconciliar_orfas` para `OperationPlan`.

**`arvore_de_pastas` trunca em 400 filhos diretos sem sinalizar que há mais:**
- Problem: `MediaRepository.arvore_de_pastas(prefixo, limite=400)` aplica `LIMIT 400` na lista de subpastas e devolve só isso — não há contagem total nem flag "há mais" na resposta.
- Files: `fotoorganizer/repositories/media.py:367-444`
- Blocks: uma pasta física com mais de 400 subpastas diretas (plausível em bibliotecas organizadas por data com granularidade de dia, por exemplo) tem subpastas escondidas da UI sem qualquer indicação de que a lista está incompleta.

## Test Coverage Gaps

**Componentes React sem arquivo de teste dedicado:**
- What's not tested: `webapp/src/components/PhotoGrid.tsx` (grade virtualizada central — ver Fragile Areas), `Panorama.tsx`, `LinhaDoTempo.tsx`, `Loupe.tsx`, `Miniatura.tsx`, `Confianca.tsx`.
- Files: `webapp/src/components/*.tsx` listados acima
- Risk: regressão silenciosa em navegação por teclado, paginação e no componente que traduz nível de confiança em badge visual — exatamente as três áreas que `docs/DIRECAO_DE_ARTE.md`/CLAUDE.md tratam como requisito de produto (teclado-first, badges de confiança).
- Priority: Alta para `PhotoGrid.tsx` (é a superfície mais usada do app); Média para os demais.

**`ClaudeAdvisor` sem teste unitário direto (ver Fragile Areas).**
- What's not tested: parsing de resposta estruturada, tratamento de `stop_reason == "refusal"`, JSON malformado e exceção de rede dentro de `ClaudeAdvisor.classificar`.
- Files: `fotoorganizer/classification/advisor.py`
- Risk: mudança de schema/SDK quebra em produção (com chamada real cobrando API) antes de quebrar em CI.
- Priority: Média — o caminho só roda com opt-in explícito (`servicos_externos = true`) e sempre com fallback (`except Exception` → `None`), o que limita o raio de dano, mas o comportamento observável (advisor "sempre indisponível" por um bug silencioso) não teria alarme de teste.

**Reconciliação de job travado só é testada para o scanner, não para os demais tipos de job.**
- What's not tested: comportamento do sistema quando o processo morre no meio de `gerar sugestões`, `detectar duplicatas` ou `executar plano` — `tests/test_reconciliacao.py` cobre exclusivamente o caso de arquivo que sumiu/voltou do disco (`arquivo_offline`), não o de sessão/job travado por crash fora do scanner.
- Files: `tests/test_reconciliacao.py`, `fotoorganizer/server/jobs.py`
- Risk: o gap de reconciliação de `OperationPlan.EXECUTANDO` (Tech Debt acima) poderia ter sido pego por um teste de boot que simulasse esse estado — não existe.
- Priority: Média — consequência é confusão de UI, não perda de dado (a reexecução manual funciona).

---

*Concerns audit: 2026-08-16*
