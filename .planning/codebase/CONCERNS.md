# Codebase Concerns

**Analysis Date:** 2026-08-16

Fonte principal desta análise: auditoria pós-gate da fase 5 (`docs/auditoria-pos-gate-fase5.md`,
18 achados medidos contra o catálogo real de produção) e o log de decisões
(`docs/DECISOES.md`, D-069 a D-073). 4 dos 18 achados já foram corrigidos
(D-070, D-071, D-072, D-073 parcial); os demais seguem como `Status: aguardando`.
Achados abaixo marcados **[ABERTO]** ainda não têm código corrigindo-os —
confirmado por leitura direta do código nesta análise (2026-08-16).

## Tech Debt

**Inventário por pasta é O(n²) — sem teste em escala real:**
- Issue: `registrar()` relê e reescreve `inventario.json` inteiro (parse +
  serialize) e regera `INVENTARIO.md` inteiro a cada foto copiada, com um
  scan `any(f["arquivo"] == destino.name for f in dados["fotos"])` linear na
  lista acumulada.
- Files: `fotoorganizer/operations/inventario.py:142-173` (`registrar`),
  chamado por `fotoorganizer/operations/executor.py:236` a cada item copiado.
- Impact: maior pasta real do acervo tem 7.618 fotos (`Viagens/2013 - Viagem
  de 22-09 a 12-10`); D-064 só testou com fixtures pequenas, nenhum teste em
  escala. Vai parecer travamento durante a execução real de cópia — o
  momento mais crítico do fluxo — sem diferenciar "copiando" de "atualizando
  manifesto" no progresso da UI.
- Fix approach: acumular entradas em memória durante a execução do plano e
  persistir o manifesto uma vez ao final (ou a cada N itens), ou trocar o
  formato por append-only (JSONL) com leitura preguiçosa. **[ABERTO]** —
  achado 7 de D-069.

**`/api/duplicatas` sem paginação — 58 MB numa resposta só:**
- Issue: endpoint devolve todos os grupos de duplicata do catálogo de uma vez,
  sem `limit`/`offset`.
- Files: `fotoorganizer/server/app.py:1056-1057` (`GET /api/duplicatas`);
  consumido por `webapp/src/components/Duplicates.tsx`.
- Impact: 41.996 grupos no catálogo real = 57.927.930 bytes numa resposta.
  Aba Duplicatas fica em branco por alguns segundos (parse do JSON + render
  de 41.996 itens) sem loading state — mesma classe de problema do achado 3
  (Viagens) e achado 14 (Panorama sem skeleton).
- Fix approach: paginar o endpoint, ou filtrar por `nivel`/status no backend
  em vez de mandar tudo e filtrar no cliente. **[ABERTO]** — achado 19 de
  D-069, encontrado durante a fatia de D-070, ainda não corrigido.

**Ações de duplicata falham em silêncio:**
- Issue: `fetch()` bruto na mutation de ação (marcar principal/ignorar/
  desfazer), sem checar `resposta.ok`, sem `onError`, sem estado de erro no
  componente inteiro — diferente do padrão que `Operations.tsx` já segue.
- Files: `webapp/src/components/Duplicates.tsx:29-37` (`acao` mutation,
  `mutationFn: (...) => fetch(url, {...})` sem tratamento de status).
- Impact: um 404/422/500 do servidor invalida a query do mesmo jeito que um
  sucesso — o clique do usuário parece não fazer nada, sem indicação de que
  a ação falhou.
- Fix approach: seguir o padrão de `webapp/src/api.ts:400-408`
  (`Operations.tsx`) — checar `response.ok`, lançar erro tipado, expor
  estado `erro` na UI. **[ABERTO]** — achado 6 de D-069.

**Panorama e Funil mostram números "organizáveis" diferentes:**
- Issue: `/api/panorama` e `/api/funil` calculam "organizáveis" por caminhos
  de código distintos e retornam valores diferentes para o mesmo rótulo.
- Files: `fotoorganizer/server/app.py:458-472` (`/api/funil`),
  `fotoorganizer/server/app.py:650+` (`/api/panorama`);
  `webapp/src/components/Panorama.tsx:167` vs `webapp/src/components/Funil.tsx`.
- Impact: 96.692 (panorama) vs 92.792 (funil) — 4,2% de diferença, lado a
  lado na mesma tela/scroll. É recorrência do mesmo padrão de bug que o
  próprio código já documenta ter corrigido antes (`Funil.tsx:40`, D-065),
  agora entre dois backends em vez de entre telas — mina a credibilidade do
  trabalho de honestidade numérica que motivou D-065/D-068.
- Fix approach: unificar a fonte de verdade de "organizáveis" num único
  cálculo/repositório consumido pelos dois endpoints. **[ABERTO]** — achado 8
  de D-069.

**"Rejeitar em lote" não existe, só "Aprovar em lote":**
- Issue: o cabeçalho de grupo em Revisão só renderiza um botão "Aprovar
  {total}"; rejeitar em lote só existe foto a foto, dentro do grupo
  expandido.
- Files: `webapp/src/components/Review.tsx:222-231` (só `<Botao>Aprovar
  {grupo.total}</Botao>` no cabeçalho); comentário do próprio arquivo em
  `Review.tsx:31-36` declara "a unidade de decisão é o GRUPO" — vale só para
  aprovar.
- Impact: para descartar um grupo questionável de 2.126 fotos (ex. achado 4
  abaixo, "Teatro → Viagens/2026 - Brasil"), o único caminho é rejeitar
  foto a foto, até 2.126 cliques.
- Fix approach: espelhar o botão de aprovar em lote com um de rejeitar em
  lote, com a mesma guarda de estado em voo (`busy`) para evitar duplo-submit
  — ver referência de mecanismo em `docs/auditoria-pos-gate-fase5.md`
  (`clipboard.vue` do PhotoPrism). **[ABERTO]** — achado 9 de D-069.

**Constante de string duplicada entre backend e frontend, sem teste de contrato:**
- Issue: `webapp/src/sugestoes.ts` (`DESTINO_NAO_CLASSIFICADO`) precisa
  bater byte a byte com a string equivalente em `classification/templates.py`
  para o badge "Sem categoria" funcionar. Nada no CI quebra se um dos dois
  lados mudar sozinho.
- Files: `webapp/src/sugestoes.ts`, `fotoorganizer/classification/templates.py`,
  `fotoorganizer/classification/engine.py`.
- Impact: risco identificado e aceito conscientemente em D-071 — se a
  constante do lado Python mudar, o sintoma é o mesmo bug do achado 2
  (badge "Alta" enganoso) voltando em silêncio, sem alarme.
- Fix approach: teste de contrato entre backend e frontend (ex.: exportar a
  constante do Python para um fixture consumido pelo teste TS, ou endpoint
  que expõe o valor canônico). Registrado como debt em D-071, não resolvido.

**Sem `mypy`/`ruff` configurado em `pyproject.toml`:**
- Issue: não há seção `[tool.mypy]` nem `[tool.ruff]` no `pyproject.toml` —
  tipagem estática e lint não são verificados automaticamente.
- Files: `pyproject.toml` (raiz do projeto).
- Impact: erros de tipo e inconsistências de estilo só aparecem em runtime
  ou revisão manual; o projeto depende inteiramente de `pytest` para pegar
  regressões.
- Fix approach: adicionar `ruff` (lint + format, rápido, já popular no
  ecossistema Python 3.12) e opcionalmente `mypy` ao `scripts/verificar.sh`.

## Known Bugs

**Duplicata VARIANTE (RAW+JPEG) já corrigida na UI, mas a última detecção no catálogo real está desatualizada:**
- Symptoms: um par confirmado (`IMG_3588.CR2`+`IMG_3588.jpg`, grupo 4880) já
  está classificado como `CONTEUDO` em vez de `VARIANTE` porque a última
  detecção rodou 19 minutos antes do nível VARIANTE entrar no código
  (commit `b87fdcb`).
- Files: `fotoorganizer/duplicates/detector.py`, catálogo de produção
  (grupo 4880 no banco real, não em fixture).
- Trigger: qualquer catálogo cuja última detecção de duplicata rodou antes
  do commit que introduziu `DuplicateLevel.VARIANTE`.
- Workaround: rodar "Detectar" novamente na UI reclassifica o grupo — D-070
  deixou essa ação de escrita fora de escopo, fica para quando o dono
  clicar. A UI (`Duplicates.tsx`) já avisa corretamente para grupos VARIANTE
  detectados a partir de agora.

**Badge de confiança agregada contradiz as evidências que o próprio popover mostra:**
- Symptoms: grupo "Teatro → Viagens/2026 - Brasil" (2.126 fotos) tem badge
  agregado "Alta", mas o popover "por quê?" do mesmo grupo mostra `país:
  Brasil — Confiança Média` e `região: Rio de Janeiro — Confiança Média` ao
  lado de `viagem: Brasil — Confiança Alta`.
- Files: `fotoorganizer/classification/engine.py` (cálculo de confiança
  agregada de viagem/categoria), `docs/CONFIANCA.md` (regra violada: "elo
  mais fraco entre os campos usados no destino" não está sendo aplicado
  aqui).
- Trigger: qualquer grupo cuja confiança de viagem/categoria seja calculada
  independentemente da confiança de país/região que a sustenta.
- Workaround: nenhum — D-071 resolveu explicitamente um caso relacionado
  (badge "Alta" em "Não classificadas") mas deixou este de fora por ser
  "questão DIFERENTE" (exclusão deliberada de país/região do cálculo quando
  há viagem/evento, decisão de produto já documentada em `engine.py`,
  comentário "UMA VIAGEM É UMA PASTA"). **[ABERTO]** — achado 4 de D-069,
  explicitamente não resolvido por nenhuma fatia até agora.

**Categorização "Eventos" 100% por heurística fraca — parcialmente corrigido:**
- Symptoms: nenhuma foto no acervo vira "Eventos" pelo caminho de vocabulário
  literal (pasta chamada "eventos"); toda ocorrência passa por keyword fraca
  (regra 2, ex. "Festa") ou por álbum+duração ≤2 dias sem keyword nenhuma
  (regra 6).
- Files: `fotoorganizer/grouping/classifier.py:186-191` (regra 2, keyword
  fraca), `fotoorganizer/grouping/classifier.py:244-283` (regra 6,
  álbum+duração), `fotoorganizer/grouping/eventos.py` (`_RE_TECNICO`).
- Trigger: 3.300 fotos (38 pastas) por keyword fraca; 8.192 fotos (169
  pastas) por álbum+duração no total medido.
- Workaround: D-073 fechou a fração de 3.220/8.192 fotos que era pasta
  cronológica por extenso ("2009/novembro 30") sem reconhecimento de data.
  A fração por keyword fraca (regra 2, 3.300 fotos) e o resto de
  "álbum+duração" continuam abertos. **[ABERTO, parcial]** — achado 5 de
  D-069.

**Plano de operações preso em "executando" após crash nunca reconcilia:**
- Symptoms: se o servidor cai durante uma cópia, o plano fica marcado
  `EXECUTANDO` para sempre — a UI depende de `job.rodando` em memória, que
  zera a cada reinício. Sem botão Cancelar visível e sem aviso de que o
  plano está órfão.
- Files: `fotoorganizer/server/app.py:1392-1394` (`_reconciliar_scans`
  existe só para sessões de scan órfãs, sem equivalente para
  `OperationPlan.status == EXECUTANDO`); `webapp/src/components/Operations.tsx:109`
  (depende de `job.rodando`).
- Trigger: crash ou kill do processo do servidor durante execução de um
  plano de cópia.
- Workaround: retomável clicando "Copiar" de novo (idempotente, hash
  verificado antes/depois), mas nada na tela informa isso — não observado
  no catálogo real até a data da auditoria (gap de código, não incidente
  registrado). **[ABERTO]** — achado 15 de D-069.

## Security Considerations

**Invariante de segurança #8 do projeto (nada que é referência real é apagado) já foi tocado por um bug de UX — corrigido:**
- Risk: grupo de duplicata VARIANTE (RAW+JPEG do mesmo clique) sendo tratado
  como duplicata comum na UI podia levar o usuário a marcar uma "principal" e
  excluir a outra (o RAW ou o JPEG) do plano de cópia sem aviso — o RAW é a
  referência real do arquivo.
- Files: `webapp/src/components/Duplicates.tsx`,
  `fotoorganizer/repositories/duplicates.py:149-165` (`escolher_principal`,
  indiferente ao nível), `fotoorganizer/operations/planner.py:78-86` (exclui
  `VERSAO` do plano de cópia).
- Current mitigation: D-070 (commit `40d78ae`) adicionou filtro "RAW + JPEG",
  texto de aviso específico e label "Manter só esta" com `title` explicando a
  consequência. `_herdar_metadados` já protegia contra perda de metadado
  antes da fatia (nada é apagado do disco em nenhum caso — o invariante
  nunca foi tecnicamente violado, só a interface não avisava).
- Recommendations: reclassificar o catálogo de produção (rodar "Detectar"
  de novo) para corrigir grupos já detectados como CONTEUDO que deveriam ser
  VARIANTE (ver "Known Bugs" acima) — ação de escrita deixada para quando o
  dono acionar manualmente.

**Subprocessos seguem o invariante 5 (sem `shell=True`, argumentos em lista):**
- Confirmado por grep em todo `fotoorganizer/`: nenhuma ocorrência de
  `shell=True`. Usos de `subprocess.run`/`subprocess.Popen` em
  `fotoorganizer/security/volumes.py`, `fotoorganizer/security/crypto.py`,
  `fotoorganizer/sources/apple_photos.py`, `fotoorganizer/metadata/exiftool.py`
  todos com argumentos em lista. Não é uma dívida — registrado aqui como
  verificação positiva, útil para não redescobrir.

**Downloader HTTP (feature recente, commit `69477f5`) merece revisão dedicada:**
- Risk: `fotoorganizer/security/http_seguro.py` (445 linhas) é a peça mais
  nova e mais volumosa da camada de segurança — implementa "downloader HTTP
  seguro e precedência explícita de config". Nenhum achado específico da
  auditoria pós-gate cobre este arquivo (ele é posterior à auditoria).
- Files: `fotoorganizer/security/http_seguro.py`.
- Current mitigation: `tests/test_http_seguro.py` existe (435+ linhas,
  inclui um `skipif`).
- Recommendations: como é a superfície de rede mais nova do projeto (o
  invariante 4 exige opt-in explícito e indicação visual antes de qualquer
  dado sair da máquina), vale auditoria dedicada equivalente à de duplicatas/
  operações antes de expor a próxima feature de rede que dependa dela.

## Performance Bottlenecks

**Aba Viagens/Eventos — corrigido (era N+1 + falta de índice):**
- Problem: `/api/viagens`/`/api/eventos` levavam 50-120s+, fazendo a UI
  mostrar "Nenhuma viagem ou evento ainda" por até 2 minutos mesmo com 190
  grupos existentes.
- Files: `fotoorganizer/server/app.py` (`_agrupamentos`),
  `fotoorganizer/models/catalog.py` (índices `ix_media_files_trip_id`,
  `ix_media_files_event_id`, migração `0017`).
- Cause: `trip_id`/`event_id` sem índice (scan completo de 477 mil linhas por
  grupo) somado a 1 `SELECT COUNT` por grupo (N+1 clássico, ~190 consultas).
- Status: corrigido em D-072 (commit incluído em PR referenciado) — medido
  em ~0,1s pós-fix, ~500-1200× mais rápido. `_capa_disponivel` continua 1
  query por grupo (agora indexada, ganho colateral) — não é a causa
  dominante, deixado de fora conscientemente até medição mostrar que ainda é
  gargalo.

**Painel "O acervo" do Panorama sem loading state (13-20s de silêncio):**
- Problem: `/api/inventario` mede 13,57s no catálogo real; o bloco aparece
  de repente, empurrando o resto da tela (layout shift), violando o
  princípio de "skeletons, nunca silêncio" do método de trabalho do projeto.
- Files: `webapp/src/components/Panorama.tsx:135-138,164`.
- Improvement path: adicionar skeleton/loading state, mesmo padrão já usado
  em outras telas (`Trips.tsx` ganhou isso em D-072). **[ABERTO]** — achado
  14 de D-069.

**Inventário por pasta — ver Tech Debt acima (O(n²), sem teste em escala).**

## Fragile Areas

**`fotoorganizer/server/app.py` — arquivo de rotas monolítico (1.422 linhas):**
- Files: `fotoorganizer/server/app.py`.
- Why fragile: concentra praticamente todas as rotas FastAPI (panorama,
  funil, viagens, eventos, duplicatas, operações, reconciliação de scan) num
  único módulo. Mudanças em qualquer domínio tocam o mesmo arquivo, o que já
  se manifestou como causa raiz de achado 3 e achado 8 (dois cálculos de
  "organizáveis" divergentes vivendo no mesmo módulo sem serem notados como
  duplicados).
- Safe modification: ao adicionar rota nova, verificar se já existe cálculo
  equivalente em outro endpoint do mesmo arquivo antes de duplicar lógica de
  agregação.
- Test coverage: `tests/test_server_api.py` existe e cobre casos pontuais
  (contagem por grupo, adicionado em D-072), mas não há teste de
  consistência cruzada entre `/api/panorama` e `/api/funil`.

**`fotoorganizer/classification/engine.py` — motor de sugestões, 1.138 linhas:**
- Files: `fotoorganizer/classification/engine.py`.
- Why fragile: concentra toda a cascata de decisão de destino/confiança
  (categoria, viagem, evento, geolocalização, confiança agregada). É o
  arquivo por trás de 3 dos 4 achados Tier 1 da auditoria (badge enganoso,
  confiança agregada contraditória, parte da categorização por heurística
  fraca).
- Safe modification: qualquer mudança em `_resolver_locations`,
  `_categoria` ou no cálculo de confiança agregada precisa medir contra o
  catálogo real antes/depois (padrão já seguido em D-069/D-072) — mudanças
  puramente lidas por teste sintético já mostraram divergir do
  comportamento em escala real (28.635 fotos afetadas pelo achado 2, só
  visível com dados reais).
- Test coverage: cobertura de unidade existe, mas nenhum teste de
  regressão que compare confiança agregada vs. confiança das evidências
  individuais que a compõem (o bug do achado 4 passaria despercebido por
  qualquer suíte atual).

**`webapp/src/components/Mapa.tsx` — maior componente do frontend, 888 linhas:**
- Files: `webapp/src/components/Mapa.tsx`.
- Why fragile: lógica de clustering geográfico com comentários registrando
  casos-limite já corrigidos manualmente (ex. `Mapa.tsx:43,528` — lugares do
  "sudeste asiático" caindo todos no mesmo cluster por proximidade de ponto
  a ponto). Indica heurística geográfica sensível a dados reais, sem
  cobertura clara de todos os casos-limite.
- Safe modification: `webapp/src/components/Mapa.test.tsx` existe (301
  linhas) — rodar antes/depois de qualquer mudança de clustering.
- Test coverage: existe, mas os comentários no próprio código sugerem que
  casos-limite geográficos foram achados por observação ao vivo, não por
  teste anterior à mudança.

## Scaling Limits

**Catálogo de produção medido: 477.222 registros, 96.692 "organizáveis":**
- Current capacity: catálogo real usado como referência de medição em toda
  a auditoria pós-gate tem 477.222 registros de mídia, 41.996 grupos de
  duplicata, 60 viagens, 130 eventos.
- Limit: pontos que já mostraram degradação nesta escala — endpoint de
  duplicatas (58 MB por resposta), inventário por pasta (O(n²) na maior
  pasta, 7.618 fotos), painel de inventário do Panorama (13-20s).
- Scaling path: paginação em `/api/duplicatas` (ver Tech Debt), manifesto
  incremental no inventário por pasta (ver Tech Debt), e considerar cache/
  pré-cálculo para `/api/inventario` se o acervo crescer além da faixa atual.

## Missing Critical Features

**Sem "Rejeitar em lote" na fila de Revisão** — ver Tech Debt acima. Bloqueia
descarte rápido de grupos de sugestão questionáveis (ex. 2.126 fotos em um
clique só de "Aprovar", zero equivalente para "Rejeitar").

**Sem timestamp de última detecção de duplicata:**
- Problem: `DuplicateGroup.criado_em` existe no schema mas nunca é
  serializado por `GET /api/duplicatas` nem exibido na UI.
- Blocks: sem isso, o achado de grupos VARIANTE desatualizados (ver "Known
  Bugs") fica invisível — nada na tela sugere ao usuário que os grupos
  podem estar desatualizados frente ao código de detecção atual.
- Files: `fotoorganizer/server/app.py` (endpoint `/api/duplicatas`),
  `fotoorganizer/models/duplicates.py` (`DuplicateGroup.criado_em`).
- **[ABERTO]** — achado 16 de D-069.

## Test Coverage Gaps

**Componentes React sem arquivo de teste dedicado:**
- What's not tested: `webapp/src/components/Confianca.tsx`,
  `webapp/src/components/LinhaDoTempo.tsx`, `webapp/src/components/Loupe.tsx`,
  `webapp/src/components/Miniatura.tsx`, `webapp/src/components/Panorama.tsx`,
  `webapp/src/components/PhotoGrid.tsx` não têm `.test.tsx` correspondente
  (verificado por listagem direta contra os demais 17 componentes, todos com
  par de teste).
- Files: os 6 arquivos acima.
- Risk: `Confianca.tsx` é justamente o componente que renderiza os badges de
  confiança no centro de 3 dos 4 achados Tier 1 (badge enganoso, confiança
  agregada contraditória) — mudanças aqui têm cobertura indireta via
  `Review.test.tsx`/`Inspector.test.tsx`, não testes de unidade próprios.
  `Panorama.tsx` e `PhotoGrid.tsx` são telas centrais do fluxo de revisão.
- Priority: Alta para `Confianca.tsx` e `PhotoGrid.tsx` (caminho mais
  percorrido, achado real já passou batido por falta de teste dedicado — ver
  nota do Inspector em D-071); Média para os demais.

**Inventário por pasta sem teste em escala real:**
- What's not tested: comportamento de `registrar()`
  (`fotoorganizer/operations/inventario.py`) com centenas/milhares de
  entradas acumuladas na mesma pasta.
- Files: `fotoorganizer/operations/inventario.py`, testes existentes
  cobrem só fixtures pequenas (D-064).
- Risk: degradação O(n²) só se manifesta em escala — silenciosa em qualquer
  suíte de teste atual.
- Priority: Alta — toca o momento mais crítico do fluxo (execução real de
  cópia).

**Sem teste de consistência cruzada entre `/api/panorama` e `/api/funil`:**
- What's not tested: que os dois endpoints retornem o mesmo valor para
  "organizáveis" dado o mesmo estado de catálogo.
- Files: `tests/test_server_api.py` (ausência), `fotoorganizer/server/app.py`.
- Risk: é exatamente o tipo de bug (dois cálculos divergentes do mesmo
  conceito) que já se repetiu duas vezes no projeto (entre telas, D-065;
  entre backends, achado 8) — sem teste de contrato, uma terceira ocorrência
  passaria despercebida até o dono notar visualmente de novo.
- Priority: Alta.

**Sem teste de contrato entre `DESTINO_NAO_CLASSIFICADO` (TS) e a constante equivalente em `templates.py` (Python):**
- What's not tested: que as duas strings permaneçam idênticas ao longo do
  tempo.
- Files: `webapp/src/sugestoes.ts`, `fotoorganizer/classification/templates.py`.
- Risk: debt explicitamente registrado em D-071 (ver Tech Debt acima) — o
  bug do achado 2 (badge "Alta" enganoso) voltaria em silêncio se uma das
  strings mudar sozinha.
- Priority: Média.

---

*Concerns audit: 2026-08-16*
