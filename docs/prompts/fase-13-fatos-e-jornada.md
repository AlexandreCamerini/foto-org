# Fase 13 — fatos determinísticos e jornada de trabalho

Leia `docs/prompts/00-protocolo.md` primeiro. Origem: pedido direto do dono em
2026-08-09 — sente falta de uma reformulação de UX/workflow e acha o sistema
"refém de gerar sugestões" quando parte das regras já é determinística (deu
como exemplo duplicata exata, que "pode ser eliminada" em vez de revisada uma
por uma). Auditoria feita por três agentes de domínio (ux, imagem, arquivos)
lendo o código real; este documento é a síntese e o plano, não a auditoria
bruta.

Continua a linha da fase 7: a pergunta que orienta continua sendo **quantas
decisões o usuário precisa tomar para organizar o acervo**. A fase 7 reduziu
isso agrupando por destino (D-018). Esta fase reduz de novo, tirando da fila
o que já não é decisão nenhuma — é fato.

Nenhum item deste documento apaga arquivo, pula dry-run ou move em vez de
copiar. Os invariantes 1, 2, 3 e 7 do `CLAUDE.md` não mudam.

---

## O que a auditoria confirmou

**A confiança já foi identificada como decorativa, e a correção não saiu do
papel.** `docs/DECISOES.md` D-017 (30/07/2026) registrou: *"hoje o nível é um
badge colorido que não leva a lugar nenhum. Precisa virar superfície de
entrada da evidência."* A decisão tomada ali foi só sobre o estilo visual do
badge (segmentos neutros em vez de semáforo); a parte "levar a algum lugar"
nunca foi implementada. Confirmado em código:

- `fotoorganizer/models/inference.py:72-74` — toda `Suggestion` nasce
  `PENDENTE`, sem exceção.
- `fotoorganizer/classification/engine.py:1037-1051` — o elo mais fraco
  (`docs/CONFIANCA.md`, regra de agregação) só calcula `nivel` (o badge),
  nunca `status`.
- Data EXIF (`score 0.95`) e GPS EXIF válido (`0.95`, os dois mais fortes da
  tabela depois de correção manual) esperam na mesma fila, com o mesmo botão
  "Aprovar", que um país estimado por herança temporal (`0.55–0.75×fator`).
- Até a correção manual do próprio usuário (`score 1.0`) gera uma sugestão
  nova que nasce pendente de novo (`engine.py:998-1004`) — ele confirma o
  fato e é obrigado a confirmar a consequência dele separadamente.

**Duplicata exata é o caso mais nítido, e os dois sistemas não se falam.**
`fotoorganizer/duplicates/detector.py:1-14` já documenta os quatro níveis
(EXATO = SHA-256 idêntico, sem ambiguidade nenhuma sobre conteúdo; CONTEUDO =
mesmo phash, bytes diferentes; VISUAL = edição leve; SEQUENCIA = rajada,
explicitamente **não** é duplicata). Mesmo assim `webapp/src/components/
Duplicates.tsx:174-179` exige o mesmo gesto manual — abrir grupo, comparar
lado a lado, marcar principal — para os quatro níveis, sem atalho de lote
para nenhum. E o rótulo resultante não vai a lugar algum: o próprio docstring
de `fotoorganizer/repositories/duplicates.py:1-2` admite *"apenas papéis
registrados para uma futura fase de operações"* — `fotoorganizer/operations/
planner.py` nunca lê `DuplicateMember.papel` (zero ocorrências, confirmado
por grep). Um membro marcado `IGNORADO` hoje é copiado do mesmo jeito se
tiver uma sugestão aprovada.

**O workflow é seis módulos técnicos colados, não uma jornada.** Panorama,
Biblioteca, Viagens, Revisão, Duplicatas, Operações são abas de peso igual em
`webapp/src/App.tsx:23-31`, sem sequência nem "o que fazer agora". Cada tela
sabe sua própria fila (sugestões pendentes, grupos de duplicata não
decididos, planos sem dry-run) mas nenhuma cruza as três — zerar a fila de
Revisão não diz "agora vá para Duplicatas". A única ponte automática hoje
(`StatusBar.tsx:118-131`, sugerir "Gerar sugestões" depois de um scan) cobre
só a primeira transição da jornada, não as demais.

---

## Item A — Resolução automática de grupos EXATO

**Classe B** (muda comportamento visível do produto: uma decisão que hoje é
sempre manual passa a ter um caminho automático).

Regra de desempate, aplicada como passo automático de pós-detecção, no mesmo
lugar que hoje espera o clique humano:

1. `source.tipo` de acervo próprio (`PASTA`) preferido sobre fonte externa
   (`APPLE_PHOTOS`/`GOOGLE_TAKEOUT`/`LIGHTROOM`) — o arquivo já dentro do
   fluxo de scan é mais provável de ser a referência de trabalho.
2. Caminho mais profundo/organizado preferido sobre raiz solta.
3. Nome descritivo (sem padrão `IMG_####`/hash) preferido sobre genérico.
4. Desempate final por `id` menor, para ser estável entre execuções.

Grava exatamente como `escolher_principal` grava hoje
(`fotoorganizer/repositories/duplicates.py:104-121`) — mesma tabela, mesmo
campo `DuplicateMember.papel`, mesmo `desfazer_grupo` para reverter. Nenhum
arquivo é tocado; a diferença é só quem clica.

Fecha a lacuna real: `fotoorganizer/operations/planner.py` passa a **ler**
`DuplicateMember.papel` e excluir `VERSAO`/`IGNORADO` do plano — isso ainda
passa pelo dry-run normal (invariante 2) antes de qualquer cópia. Hoje esse
`JOIN` simplesmente não existe.

- *Muda o quê:* resolver duplicata exata deixa de ser N cliques (um por
  grupo) e passa a ser automático e revisável, com a garantia extra de que o
  plano de cópia para de incluir cópias redundantes por engano.
- *Esforço:* **M** — a regra em si é pequena; o trabalho real é o `JOIN`
  novo em `planner.py` (com teste de regressão: o plano nunca pode passar a
  copiar o que devia ficar de fora) e uma tela de confirmação em lote
  ("42 grupos resolvidos automaticamente — revisar ou confirmar todos").
- *Não se estende a CONTEUDO por padrão:* mesmo phash a distância 0 é forte
  mas não é prova bit-a-bit (recompressão pode ter perdido HDR, crop
  imperceptível ao phash de 64 bits). Automatizar aqui arrisca descartar do
  plano a versão editada que o usuário queria. Proposta: pré-selecionar a
  candidata (maior arquivo/mais recente) mas manter a confirmação manual
  antes de gravar `papel`. VISUAL e SEQUENCIA continuam manuais — o próprio
  código já diz por quê (`detector.py:7-11`: edição reconhecida e "induziria
  a descartar o melhor frame", respectivamente).

## Item B — Hub de trabalho pendente

**Classe A** (composição de dados que já existem; não muda modelo nem
comportamento de aprovação).

Painel único, extensão do Panorama (`webapp/src/components/Panorama.tsx`),
cruzando as três filas isoladas hoje: `api.gruposDeSugestoes` (Revisão),
`api.duplicatas` com `g.decidido` (Duplicatas), planos sem dry-run/execução
(`Operations.tsx:65-68`). Cada linha do painel diz "N grupos aguardando
revisão" / "M grupos de duplicata não decididos" / "P planos sem dry-run",
com atalho direto para a tela e o filtro certos.

Complementar: contagem por fila anexada ao rótulo de cada aba
(`App.tsx:193-203`), e generalizar o padrão que já existe em
`StatusBar.tsx:122-131` (hoje só recomenda "Gerar sugestões" após scan) para
cobrir as transições seguintes — fila de revisão e duplicatas zeradas e sem
plano → sugerir "Criar plano".

- *Muda o quê:* resolve o "o que eu faço agora?" sem mexer no motor de
  confiança nem em nenhum invariante. Independente do Item A e do Item C —
  pode entrar em paralelo com qualquer um dos dois.
- *Esforço:* **S/M**.

## Item C — Trilha de fato confirmado, separada de sugestão real

**Classe B** (muda a semântica de `Suggestion` — decisão de modelo de
dados/produto, registrar em `docs/DECISOES.md` como ADR antes de codar,
seguindo o protocolo).

Critério objetivo: campo com evidência ALTA (score ≥ 0.8, tabela de
`docs/CONFIANCA.md`), sem conflito registrado e sem ser herança/estimativa,
marca-se como confirmado automaticamente — ainda reversível, ainda auditável
por `versao_logica` (nada muda em como a evidência é produzida, só em quando
ela exige clique humano). Uma sugestão só permanece na fila de revisão se
tiver ao menos um campo MÉDIA/BAIXA usado no destino, ou evidências
conflitantes para o mesmo campo.

Isto reaproveita a regra de elo mais fraco já existente
(`docs/CONFIANCA.md:34-45`) como **gatilho de fluxo**, não só como cálculo de
badge — sem contradizer o documento: a regra de agregação continua a mesma,
só passa a ter uma consequência real além da cor.

**Onde o invariante aperta:** o invariante 2 do `CLAUDE.md` — "operações
físicas só existem como plano até aprovação explícita" — não muda. "Aplicar
direto" aqui quer dizer sair da fila de *revisão de sugestão*, nunca pular o
dry-run de *operação física*. O plano continua exigindo confirmação humana
antes de qualquer cópia, em lote ou não.

- *Muda o quê:* é a mudança estrutural de verdade desta fase — ataca o
  problema na raiz (`Suggestion.status` sempre `PENDENTE`, independente do
  `nivel`) em vez de só nos sintomas (duplicata, badge).
- *Esforço:* **M** — aditivo, não recria o motor de 1050 linhas nem o elo
  mais fraco. Precisa de: função que classifica "precisa revisão" por campo
  reaproveitando os scores existentes; possivelmente um status novo (ex.
  `CONFIRMADA_AUTO`) distinto de `APROVADA` (humana), via migração Alembic
  pequena, para preservar a auditoria de quem/o quê decidiu; e trabalho de
  UX para separar visualmente as duas filas.
- *Depende de:* nada tecnicamente, mas **faz mais sentido depois dos itens A
  e B** — validar o padrão "decisão automática, reversível, auditável" no
  caso mais simples (duplicata exata) antes de aplicá-lo ao motor de
  sugestão inteiro.

## Item D — Distribuição de confiança no cabeçalho do grupo

**Classe A.**

Hoje um grupo de sugestões com 49 fotos de alta confiança e 1 de baixa herda
o badge "Baixa" inteiro no cabeçalho (`webapp/src/components/Review.tsx:220`,
`fotoorganizer/repositories/suggestions.py`, `_nivel_do_grupo`) — o próprio
comentário da função nota que isso ainda não acontece na prática porque o
nível hoje é constante dentro de cada destino. Depois do Item C isso se
resolve quase sozinho (o campo fraco vira o único que permanece pendente),
mas vale como reforço visual preventivo mesmo antes: estender o contador do
grupo com uma distribuição por nível (`{alta: 49, baixa: 1}`) em vez de só o
nível agregado.

- *Esforço:* **S/M**.

## Item E — Unificar vocabulário de decisão entre Revisão e Duplicatas

**Classe A**, mas cruza com direção de arte — não é só código.

Revisão (grupo → "Aprovar N") e Duplicatas (card → "Manter esta"/"Ignorar")
respondem à mesma pergunta de fundo — "o que fazer com este conjunto de
fotos" — com duas linguagens visuais diferentes, refletindo a separação
interna `classification/` vs `duplicates/`, não um modelo mental único.
Aproximar o padrão (mesmo tipo de cabeçalho grupo→ação, mesmo lugar para "por
quê") é polimento, não redução de atrito funcional — por isso fica por
último.

- *Esforço:* **L**.

---

## Ordem recomendada

**A → B → C → D → E.**

A é o ganho mais concreto e mais barato — fecha o exemplo que o dono deu,
isolado, sem tocar no motor de sugestões. B é independente e barata, entra em
paralelo se sobrar fôlego. C é a mudança estrutural de verdade e se beneficia
de A já estar validado em produção (mesmo padrão "automático + reversível +
auditável", num domínio menor primeiro). D é refinamento de C. E é
polimento visual, cruza com `docs/DIRECAO_DE_ARTE.md`, fica para quando as
quatro primeiras estiverem estáveis.

## Arquivos relevantes

`webapp/src/App.tsx`, `webapp/src/components/{Panorama,StatusBar,Review,
Duplicates,Operations,Sidebar,Trips,Confianca,Funil,Inspector,PhotoGrid}.tsx`,
`fotoorganizer/classification/{engine,confidence,advisor}.py`,
`fotoorganizer/models/inference.py`, `fotoorganizer/models/duplicates.py`,
`fotoorganizer/duplicates/detector.py`, `fotoorganizer/repositories/
{suggestions,duplicates}.py`, `fotoorganizer/operations/{planner,executor}.py`,
`docs/CONFIANCA.md`, `docs/DECISOES.md` (D-017, D-018), `docs/prompts/
fase-7-jornada-da-decisao.md`.
