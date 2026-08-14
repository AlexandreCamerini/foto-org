# Auditoria pós-gate da fase 5 — 18 achados medidos, priorizados, cruzados com PhotoPrism/Immich

Disparada pelo dono testando a UI depois do merge de PR #4/#5/#6 e reportando
"caos": fotos que não carregam, filtros confusos, classificações erradas.
Nada aqui foi implementado — é registro de achado medido, candidato a
decisão. Ver D-069.

## 0. Gate — nada disso é regressão desta sessão

Antes de investigar qualquer coisa, a pergunta obrigatória: os achados abaixo
já existiam antes da fase 5 (D-051 a D-065, PRs #4/#5/#6), ou foram
introduzidos por ela?

Resolvido por diff de código, não por impressão: `git diff 48c4378 HEAD`
(commit anterior à sessão inteira → HEAD atual) em
`fotoorganizer/grouping/classifier.py`, `fotoorganizer/grouping/eventos.py` e
`fotoorganizer/classification/lexico.py` — **zero diferenças**. É exatamente
o código que decide sessão-viagem/evento (regras 2/5/6 da cascata) e produz
os achados "Teatro" e "Bezerros" abaixo.

`fotoorganizer/classification/engine.py` mudou (98 inserções/10 remoções),
mas só em dois pontos:
- Nova regra 2b em `_categoria()` (palavra-chave XMP/IPTC, D-057) — inserida
  **abaixo** da checagem de `sessao.tipo`, que já existia antes e é o que
  decide Teatro/Bezerros. Não altera esses casos.
- `_resolver_locations()`, geolocalização adiantada para toda foto com
  coordenada (D-051/052/058, "geo-first") — não muda a REGRA que decide
  destino sem prefixo (achado 3 abaixo), mas pode ter mudado a CONTAGEM
  (mais fotos chegam a `_evidencias_geo` cedo do que antes).

**Veredito:** achados 1 e 2 (badge "Alta" enganoso, categorização por
heurística fraca) são 100% pré-existentes — não têm relação com esta sessão.

A comparação empírica (rodar `SuggestionEngine.gerar()` com o código de
48c4378 contra cópia do catálogo real) terminou depois de ~1h22 de CPU e
**confirma o diff sem nenhuma divergência**: media_id 233091 (achado "badge
Alta em nov.2008") produziu, com o código pré-sessão, exatamente
`Não classificadas/2008/nov.2008`, nível `alta`, única evidência `data`
(score 0.95) — idêntico ao comportamento atual. media_id 454553 (achado
"Gana sem prefixo") produziu `2013/Gana`, nível `media`, `pais: Gana —
origem=vizinhanca score=0.55` — também idêntico, inclusive no volume da
evidência mais fraca da cascata. **Os 4 achados originais e, por extensão,
os 18 desta auditoria não são regressão desta sessão em nenhum grau.**

## 1. Frente B — o que PhotoPrism/Immich têm para oferecer aqui: quase nada, e isso é o achado

`docs/referencia-photoprism/` e `docs/referencia-immich/` já existem — uma
auditoria de 453 capabilities lida do código-fonte real de ambos (não de
demo), sintetizada em `docs/prompts/fase-14-photoprism-e-sintese.md` com
decisões já fechadas (D-041 a D-045). Antes de propor scrape novo do demo
público, chequei se esse material (ou uma busca externa complementar) já
cobre os dois problemas de UX mais graves encontrados nesta auditoria:

- **Badge de confiança por campo/inferência**: nem PhotoPrism nem Immich têm
  isso. Os dois só rastreiam a *origem* do dado (exif/manual/IA, enum fixo),
  nunca o grau de certeza de uma leitura específica —
  `docs/referencia-photoprism/02-metadados-imagem-e-visao.md:109-114`. O
  modelo de evidência do foto-organizer (`Evidence.origem/.nivel/.score/
  .justificativa`) já é mais rico que o dos dois concorrentes lidos em
  profundidade.
- **Categorização automática por nome de pasta**: nenhum dos dois faz
  inferência de álbum/categoria a partir do nome da pasta original — é
  gerenciamento manual de álbum nos dois.

Checagem externa (WebSearch/WebFetch, 2026-08-14) não achou nenhum produto
de mercado com os dois mecanismos — nem Lightroom, nem Mylio (o único hit
promissor, "Auto Organize Folders", reorganiza por METADADO DE DATA, não
por nome de pasta, e não tem indicador de confiança), nem Synology Photos.

**Conclusão prática: não gastei o scrape completo do demo do PhotoPrism.**
Teria sido uma leitura de caixa-preta, sem código-fonte, refazendo com
qualidade inferior um trabalho que a fase 14 já fez em profundidade e que já
mostra que a resposta é "não existe". Os achados 2 e 5 abaixo (badge
enganoso, categoria ambígua) não têm mecanismo de terceiro para inspirar — a
solução tem que ser desenhada para o foto-organizer, do zero. Onde um
mecanismo de terceiro *é* relevante (achado 9, lote assimétrico), está
citado com âncora `arquivo:linha` na seção 3.

## 2. Achados priorizados (impacto medido × quão enganoso)

Prioridade: quantas fotos/sugestões afeta (medido, nunca estimado) × quão
enganoso é para o usuário — badge que mente pesa mais que nome de pasta
ambíguo, seguindo o critério do prompt original desta auditoria.

### TIER 1 — risco de dado ou bloqueio de uso básico

**1. Duplicata VARIANTE (RAW+JPEG do mesmo clique) pode ser resolvida como duplicata comum — risco de excluir o RAW ou o JPEG do plano de cópia sem aviso**
- Evidência: `webapp/src/components/Duplicates.tsx:8-14` não lista `variante`
  como filtro; o texto de orientação (linhas 136-142) cai no `else`
  genérico ("marque a cópia a manter como principal") — o oposto do que
  `fotoorganizer/duplicates/detector.py:68-84` documenta ("o dono quase
  sempre quer os dois"). Se o usuário marca uma "principal", a outra vira
  `VERSAO` e `fotoorganizer/operations/planner.py:78-86` a exclui
  automaticamente de qualquer plano de cópia futuro.
- Medido: **2.514 conjuntos** RAW+outra-extensão mesmo nome-base/pasta no
  ACERVO real; **1 par confirmado** (`IMG_3588.CR2`+`IMG_3588.jpg`, ids
  200199/366220/286623/292107, phash idêntico) já classificado hoje como
  `CONTEUDO` (grupo 4880) — o cenário exato que convida a descartar um dos
  dois. Causa raiz: a última detecção rodou 19 minutos antes do nível
  VARIANTE entrar no código (commit `b87fdcb`).
- Por que Tier 1: toca diretamente o invariante de segurança #8 do
  `CLAUDE.md` do projeto ("nada que possa ser a referência real de uma foto
  é apagado"). Um RAW é a referência real; hoje o app pode levar o usuário
  a descartá-lo sem avisar que está fazendo isso.
- Severidade: **Alta**.

**2. Badge "Alta" reflete confiança da DATA, não de classificação — a maioria absoluta do badge "Alta" no app não vem de categoria nenhuma**
- Evidência: `fotoorganizer/classification/engine.py:1094-1105`
  (`_persistir_sugestao`, ramo `sem_nome`) monta evidência só com `data`
  (EXIF, score 0.95 → sempre ALTA) quando não há categoria/viagem/evento.
- Medido: **28.635 fotos** (29,6% do acervo de 96.692) têm sugestão nível
  ALTA com exatamente 1 evidência, campo `data`, destino
  `Não classificadas/...`. É **63,8%** de todas as 44.914 sugestões nível
  ALTA do catálogo. Dentro do bucket "Não classificadas" isoladamente (o
  MAIOR grupo de destino do sistema, 29.119 fotos = 29% de toda a fila de
  revisão): **97,8%** tem badge Alta (28.492/29.119).
- Reproduzido na UI: linha "20140719-144517 e mais 2 → **Não
  classificadas**/2014/jul.2014 · 1.784 fotos · **Alta**" — contradição
  textual lado a lado, visualmente gritante.
- Severidade: **Alta**. Maior achado em extensão numérica de toda a
  auditoria — quase 1 em cada 3 fotos do acervo carrega esse badge.

**3. Aba Viagens fica falsamente vazia por 50–120+ segundos — provável causa direta do "caos" relatado**
- Evidência: `time curl /api/viagens` → 50,5s numa medição, timeout de 120s
  estourado noutra. Causa provável: `fotoorganizer/server/app.py:839-861`
  (`_agrupamentos`) faz 2 queries extras por grupo (contagem +
  `_capa_disponivel`, que busca até 24 candidatos com lookup em disco no
  `thumb_cache` cada) — N+1 sobre 60 viagens + 130 eventos = até ~4.560
  lookups de disco, piorado por contenção de lock com o job de geração
  rodando concorrente. `webapp/src/components/Trips.tsx:23-32` não trata
  loading: `vazio = (viagens ?? []).length === 0` trata "carregando" e
  "vazio de verdade" como a mesma coisa.
- Medido: catálogo real tem 60 viagens e 130 eventos — não é vazio. Por até
  2 minutos, a tela mostra "Nenhuma viagem ou evento ainda — gere as
  sugestões na aba Revisão", instruindo o usuário a refazer um trabalho já
  feito.
- Severidade: **Alta** — sintoma mais visível e mais fácil de reproduzir de
  toda a auditoria; provavelmente a origem direta do "caos" relatado.

**4. Confiança agregada (categoria/viagem) contradiz a confiança das evidências de que depende**
- Reproduzido na UI: grupo "Teatro → Viagens/2026 - Brasil" (2.126 fotos,
  badge **Alta**). No popover "por quê?": `país: Brasil — Confiança
  Média`, `região: Rio de Janeiro — Confiança Média`, mas `viagem: Brasil —
  Confiança Alta` e `categoria: Viagens — Confiança Alta` — duas linhas
  abaixo, no mesmo popover desenhado para justificar confiança ao usuário.
- Viola `docs/CONFIANCA.md` (não inflar confiança agregada além do que as
  evidências individuais sustentam) de forma visível no próprio mecanismo
  de transparência do app.
- Severidade: **Alta** — mina a credibilidade estrutural do modelo de
  evidências, o diferencial real do produto (seção 1).

### TIER 2 — misclassificação e falhas reais, escala moderada/grande

**5. Categorização "Eventos" por heurística fraca — 0% vem do vocabulário literal, 100% é inferência**
- Evidência: `SELECT origem, valor, COUNT(*) FROM evidence WHERE
  campo='categoria' GROUP BY origem, valor` — nenhuma foto no acervo tem
  pasta literalmente chamada "eventos" que virou "Eventos" pelo caminho 1
  (`_CATEGORIAS_PASTA`, `engine.py:900-906`). Toda ocorrência passa por
  `grouping/classifier.py:186-191` (regra 2, keyword fraca tipo "Festa" —
  caso Bezerros) ou `:244-283` (regra 6, álbum+duração ≤2 dias, sem
  keyword nenhuma).
- Medido: 3.300 fotos (38 pastas) por keyword fraca; 8.192 fotos (169
  pastas) por álbum+duração — das quais **3.220 fotos (48 rótulos)** são
  pasta cronológica ("2009/novembro 30") virando falso nome de evento
  porque `_RE_TECNICO` (`grouping/eventos.py:28-42`) não reconhece mês por
  extenso.
- Severidade: **Alta** — 11.492 fotos, 11,9% do acervo.

**6. Ações de duplicata (principal/ignorar/desfazer) falham em silêncio**
- Evidência: `Duplicates.tsx:28-37` usa `fetch()` bruto, nunca checa
  `resposta.ok`, sem `onError`, sem estado `erro` no arquivo inteiro —
  diferente do padrão que `Operations.tsx` já segue (`api.ts:400-408`). Um
  404/422/500 do servidor invalida a query do mesmo jeito; o clique parece
  não fazer nada.
- Severidade: **Alta** — usuário não sabe se a ação funcionou.

**7. Inventário por pasta é O(n²) por desenho — vai travar visualmente na maior pasta real do acervo**
- Evidência: `fotoorganizer/operations/inventario.py::registrar`, chamado
  a cada foto copiada (`executor.py:236`), relê + reescreve
  `inventario.json` inteiro e regera `INVENTARIO.md` inteiro por item.
- Medido: 283 pastas de destino, média 341,7 fotos/pasta, **máximo 7.618
  fotos** (`Viagens/2013 - Viagem de 22-09 a 12-10`). D-064 só testou com
  fixtures pequenas. Nenhum teste em escala.
- Severidade: **Alta** — vai parecer travamento no momento mais crítico
  (execução real de cópia), sem diferenciar "copiando" de "atualizando
  manifesto" no progresso.

**8. Panorama mostra dois números diferentes com o mesmo rótulo "organizáveis"**
- Evidência: `/api/panorama` → 96.692; `/api/funil` → 92.792 (diferença de
  3.900, 4,2%), lado a lado na mesma tela/scroll
  (`Panorama.tsx:167` vs `Funil.tsx`). É o mesmo padrão de bug que o
  próprio código documenta ter corrigido antes (`Funil.tsx:40`) — voltou,
  agora entre dois backends em vez de entre telas.
- Severidade: **Alta** — mina a credibilidade do trabalho de honestidade
  numérica que motivou D-065/Funil, na aba mais visitada do app.

**9. "Rejeitar em lote" não existe — só "Aprovar em lote"**
- Evidência: `Review.tsx:222-231` só renderiza `<Botao>Aprovar
  {grupo.total}</Botao>` no cabeçalho do grupo; rejeitar em lote só existe
  foto a foto, dentro do grupo expandido. O comentário do próprio arquivo
  (`Review.tsx:31-36`) declara "a unidade de decisão é o GRUPO" — só vale
  para aprovar.
- Consequência direta dos achados 4/5: para descartar o grupo
  "Teatro → Viagens/2026 - Brasil" (2.126 fotos, claramente questionável),
  o único caminho é rejeitar foto a foto, até 2.126 cliques.
- **Mecanismo de inspiração (não cópia de tela)**: PhotoPrism resolve o
  mesmo problema de ação em lote reativa em
  `frontend/src/component/photo/clipboard.vue:3-17,29-139` — a barra de
  ação só existe no DOM quando há seleção (`v-if`), cada ação (approve/
  edit/archive/delete) é `:disabled="selection.length===0 || busy"` com um
  único flag `busy` travando a barra inteira durante chamada em voo,
  evitando duplo-submit em lote. O que muda para o foto-organizer: não é
  sobre ter barra de seleção (o app já tem lista origem→destino com
  badges, mais rico que o clipboard genérico do PhotoPrism) — é sobre
  simetria: o mesmo padrão de "ação em lote com guarda de estado em voo"
  que hoje só existe para Aprovar precisa existir para Rejeitar também.
- Severidade: **Média/Alta**.

### TIER 3 — inconsistência visual e de nomenclatura, sem risco de dado

**10. Destino sem prefixo Viagens/Eventos quando só há evidência fraca de país**
- Evidência: 668 sugestões (`2013/Gana` = 462, `2012/Brasil` = 187, juntas
  97%) vêm de `vizinhanca` (score 0,55 — a origem mais fraca da tabela).
  `TEMPLATE_PADRAO` (`templates.py:24`) descarta o primeiro segmento
  quando não há categoria. Nível: 650 MÉDIA, coerente com o modelo (não
  há inflação de confiança aqui, ao contrário do achado 2).
- Severidade: **Média** — correto pelo modelo, mas 668 pastas soltas na
  árvore de destino, sem prefixo, ao lado de linhas com prefixo.

**11. Mesma viagem fragmentada em grafias/categorias diferentes na fila de Revisão**
- Evidência: "Peru-Bolivia-Chile" (sem acento) e "Peru-Bolívia-Chile" (com
  acento) são grupos separados; a mesma viagem de 2011 se espalha por 5
  linhas: `Viagens/2011 - Viagem de 01-10 a 21-10` (3.525),
  `Viagens/2011 - Peru-Bolívia-Chile` (2.655),
  `Viagens/2011 - Peru-Bolivia-Chile` (926),
  `Eventos/2011/Peru-Bolivia-Chile` (138),
  `Não são fotos/Captura de tela/2011` (41). Um usuário que quer "aprovar
  a viagem ao Peru inteira" precisa achar e decidir 5 linhas espalhadas
  numa lista de 285 grupos ordenada por tamanho, não por assunto.
- Severidade: **Média**.

**12. Nomes de card de viagem colidem em massa — 23 de 60 viagens chamam-se "Brasil"**
- Evidência: `SELECT nome, COUNT(*) FROM trips GROUP BY nome` — "Brasil"
  38% de todas as viagens. `Trips.tsx` ordena por data, então os 23 cards
  ficam espalhados na galeria, distinguíveis só pela legenda pequena de
  data.
- Severidade: **Média**.

**13. Biblioteca: rótulo da sidebar não bate com o total do filtro correspondente**
- Evidência: sidebar mostra "Todas as fotos (96.692)"; clicar cai em
  `alcance=tudo`, que mostra "477.222 no filtro" — divergência de 5x sem
  explicação visível. A matemática interna está certa (96.692 organizáveis
  + 380.530 faltantes = 477.222); o problema é só o rótulo da sidebar
  reaproveitar o número de `organizaveis` sob o nome "Todas".
- Severidade: **Média**.

**14. Painel "O acervo" do Panorama demora 13–20s sem nenhum loading state**
- Evidência: `/api/inventario` → 13,57s medido; `Panorama.tsx:135-138,164`
  não tem skeleton — o bloco aparece de repente, empurrando o resto da
  tela (layout shift). Viola `docs/METODO_DE_TRABALHO.md` §3 (skeletons,
  nunca silêncio).
- Severidade: **Média**.

**15. Plano preso em "executando" depois de crash do servidor nunca reconcilia**
- Evidência: `_reconciliar_scans` (`app.py:1383-1394`) existe para sessões
  de scan órfãs no boot; não há equivalente para
  `OperationPlan.status == EXECUTANDO`. `Operations.tsx:109` depende de
  `job.rodando` em memória, que zera a cada reinício — depois de um crash
  mid-cópia, o plano mostra "executando" para sempre, sem botão Cancelar e
  sem aviso de que está órfão (é retomável clicando "Copiar" de novo, mas
  nada na tela diz isso). Não observado no catálogo real hoje — gap de
  código, não incidente.
- Severidade: **Média**.

**16. Sem timestamp de última detecção de duplicata**
- Evidência: `DuplicateGroup.criado_em` existe no banco, nunca é
  serializado por `GET /api/duplicatas` nem exibido na UI — sem isso, o
  achado 1 (VARIANTE) fica invisível: nada sugere que os grupos estão
  desatualizados frente ao código atual.
- Severidade: **Média** (mas amplifica a severidade do achado 1).

### TIER 4 — polimento

**17. Grupos de duplicata (CONTEUDO/VISUAL/SEQUENCIA) não explicam "por quê" foram agrupados**
- Diferente das sugestões (evidência + justificativa), só mostram o rótulo
  do nível — sem distância de phash nem explicação por membro. Não quebra
  regra escrita (`DIRECAO_DE_ARTE` só promete "por quê" para sugestões),
  mas é inconsistência de padrão dentro do próprio app.
- Severidade: **Baixa/Média**.

**18. `classification/lexico.py` (Opus 5) é caminho separado, sem correlação com os achados acima**
- Confirmado: nenhum dos achados 1/2/5/10 passa pelo léxico. Ele só é
  consultado na regra 6 de `classifier.py`, depois de pasta/keyword
  falharem, e hoje só tem efeito positivo (694 fotos corrigidas de
  "Eventos" para "Viagens" por reconhecer "Pantanal"/"TERG" como lugar).
  Não é candidato a explicação nem a correção — registrado aqui para não
  ser redescoberto.
- Severidade: informativo, não é achado de bug.

## 2.1 Achado 19 (encontrado durante a fatia #1) — `/api/duplicatas` devolve o catálogo inteiro sem paginação: 58 MB por carregamento, alguns segundos de tela preta

- Evidência: `curl http://localhost:8405/api/duplicatas | wc -c` → **57.927.930
  bytes** (58 MB) numa única resposta, servindo os 41.996 grupos de
  duplicata do catálogo real de uma vez (`GET /api/duplicatas`,
  `fotoorganizer/server/app.py`, sem `limit`/`offset`). Reproduzido na UI:
  abrir a aba Duplicatas mostra a lista vazia por alguns segundos (parse do
  JSON + render de 41.996 itens) antes de aparecer, sem loading state —
  mesma classe de problema do achado 3 (Viagens falsamente vazia) e do
  achado 14 (painel sem skeleton).
- Não corrigido nesta fatia — fora do escopo do achado 1 (VARIANTE), achado
  novo e não medido pela auditoria original porque nenhum agente testou o
  carregamento fim-a-fim da tela de Duplicatas contra o volume real.
- Severidade: **Média/Alta** — mesma classe do achado 3, mas ainda não
  quantificada por número de decisões afetadas (a maioria dos 41.996 grupos
  já está `decidido`, então o impacto prático pode ser menor do que o de
  Viagens; não medi quantos estão `INDEFINIDO` de fato).

## 3. O que isso não é

Nenhuma mudança foi feita em `fotoorganizer/**`, `webapp/src/**`,
migrações ou `pyproject.toml`. Cada item acima é candidato a decisão — a
lista de 18 achados prioriza por impacto medido, não decide o que corrigir
primeiro. Essa escolha é do dono; ver D-069.
