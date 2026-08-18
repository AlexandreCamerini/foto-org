# Rodada de 2026-08-17 — teste de primeira execução (fase 5, LANC-03)

**Não chegou a uma grade populada sem documentação.** O teste travou no
próprio campo de caminho do `ModalCaminho` — critério 3 da Fase 5 (D-06) não
foi atendido nesta rodada. O bloqueador tinha causa de renderização, foi
diagnosticado com evidência visual e corrigido dentro desta mesma sessão
(commit `f820d1a`); ver "Achados classificados" abaixo.

## Método

Testador: alguém que nunca usou o Foto Organizer e não participou da
construção do app (perfil, não nome — T-05-41). O app era o `.app`
empacotado do Marco 1 (`05-03`), aberto sobre catálogo genuinamente vazio
via `FOTOORG_DATA_DIR` descartável, com uma pasta de fotos neutra separada
para o teste (Task 1 desta rodada). A única frase dita ao testador: "este
app organiza fotos; use como quiser".

Ressalva honesta, no mesmo espírito das rodadas anteriores: a sessão em si
foi conduzida fora deste agente executor — o dono do produto operou o
lançamento e a observação diretamente e relatou o resultado de volta no
chat desta sessão de execução; este documento transcreve esse relato, não
uma observação de primeira mão do agente. A cobertura vai da primeira tela
em diante, não do duplo-clique no ícone.

## O que foi observado

- O testador chegou à tela inicial (estado vazio do Panorama, "Catálogo
  vazio — adicione uma pasta na barra lateral para começar.") e encontrou
  um dos pontos de entrada de "Adicionar pasta…" — isso funcionou.
- Ao abrir o `ModalCaminho`, os textos da tela de trás (a frase do estado
  vazio do Panorama e o próprio botão "Adicionar pasta…") apareciam
  sobrepostos ao título e ao campo de caminho do modal — relato literal do
  dono: "os textos estão se sobrepondo".
- O testador travou exatamente nesse ponto e não avançou sozinho — relato
  literal do dono, quando perguntado diretamente: **"travou ali, não
  passou desse ponto"**. O teste terminou em falha, não em sucesso com
  atrito.
- Um segundo comentário do dono, no mesmo relato: "não tem widget que abre
  uma árvore de diretório" — dito sobre o mesmo momento, mas é uma
  observação distinta (ausência de funcionalidade, não defeito visual; ver
  achado 2 abaixo).

## Achados classificados

**1. Bloqueador — textos sobrepostos no `ModalCaminho`, corrigido nesta
rodada.**

Causa raiz diagnosticada empiricamente (screenshot real do `.app`
empacotado antes de qualquer alteração de código, não inspeção de fonte
isolada — `webapp/src/components/ModalCaminho.tsx` lido primeiro e parecia
estruturalmente correto, sem overlap óbvio de z-index/espaçamento no JSX;
o defeito só ficou visível ao renderizar de fato): o backdrop do modal
(`bg-black/60`, 60% de opacidade) não é opaco o bastante para ocluir o
conteúdo da tela por trás — a frase do estado vazio do Panorama e o botão
"Adicionar pasta…" atravessavam visualmente o backdrop e o painel do modal
(`bg-painel`, translúcido por design — D-017/`docs/DIRECAO_DE_ARTE.md`) e
se sobrepunham ao título/input do próprio modal. `vitest`/`jsdom` não
renderiza pixel real, por isso o bug nunca apareceu na suíte automatizada
apesar do wiring estar coberto (`App.test.tsx:373-510`).

Fix mínimo aplicado: `bg-black/60` → `bg-black/95` em
`ModalCaminho.tsx`, reusando o mesmo valor de opacidade que
`Loupe.tsx` já usa para um backdrop que precisa ocluir por completo —
nenhum token novo, nenhuma mudança em `bg-painel` nem em qualquer outro
componente. Re-verificado visualmente (captura de tela antes/depois,
Safari/WebKit — mesmo motor de renderização do WKWebView do Tauri no
macOS — servindo `webapp/dist` reconstruído contra o backend Python
direto): o vazamento de texto deixou de ser legível/sobreposto. Regressão
travada em `App.test.tsx` (asserção de classe do backdrop, já que
`vitest` não pode travar o pixel em si). Commit `f820d1a`.

**2. Atrito / não-bloqueador — sem seletor de pasta navegável (árvore de
diretório).**

O `ModalCaminho` pede o caminho digitado à mão, sem widget de navegação de
diretórios. Isso já é um item de backlog rastreado separadamente (tarefa
de fundo iniciada pelo dono em outra sessão, sobre um componente de
seletor de pasta navegável + gauge de progresso de importação) — **não**
é trabalho novo desta rodada, e D-04/D-05 mantêm essa reconstrução de
fluxo fora do escopo de LANC-03. Registrado aqui só como confirmação de
que o próprio teste de usuário tocou nesse ponto, não como tarefa a
executar.

## Recomendação

| Ordem | Item | Classificação | Esforço |
|---|---|---|---|
| 1 | Backdrop translúcido demais no `ModalCaminho` | bloqueador — já corrigido nesta rodada | P (feito) |
| 2 | Seletor de pasta navegável (árvore de diretório) | atrito — já no backlog do dono, fora de escopo aqui | M/G (backlogged, não decidir aqui) |

Recomendação de reteste: repetir o teste de primeira execução (Task 2 desta
mesma rodada) com o fix aplicado, antes de fechar LANC-03 como atendido —
esta rodada corrige o bloqueador observado mas não reexecuta o teste de
usuário do zero.

---

# Rodada de 2026-08-06 — pós-correções de scan + feedback do dono

Contexto: nesta rodada primeiro foram corrigidos os defeitos de scan/SSE/log
que causavam o sintoma "app lendo o dia todo sem gerar informação" (commits
`3f85ca3`…`7d237f7` desta sessão), depois foram acrescentados sinais novos à
cascata de classificação (nome de arquivo, IPTC/XMP, léxico multi-nível).
Esta seção é a crítica de UX/arte pedida em seguida — dois agentes
independentes, um navegando o app vivo (cópia de 422.738 registros do
catálogo real, 65.367 organizáveis) e outro auditando tokens/consistência
pelo código — mais o feedback direto do dono do produto recebido durante a
espera. Nada foi implementado a partir daqui: é o relatório para aprovação.

## A. Crítica de fluxo (app vivo, `agente-ux`)

Resumo do agente: a base já resolveu boa parte do que a fase 6 (abaixo)
apontou — Revisão agrupada por destino, confiança como barra com rótulo,
"por quê" com evidências, plano com diff origem→destino existem e funcionam.
Os defeitos desta rodada são de **integração entre telas**, não de conceito.

| # | Defeito observado | Referência que resolve melhor | Proposta | Esforço |
|---|---|---|---|---|
| 1 | Cabeçalho de grupo em Revisão é `<header onClick>` sem `tabIndex`/`role`/`onKeyDown` — só abre com mouse, e é o único caminho até Aprovar/Rejeitar de cada foto | Photo Mechanic/Lightroom: qualquer nó expande com Enter/seta | `role="button"`, `tabIndex={0}`, `onKeyDown` (Enter/Espaço) no cabeçalho | P |
| 2 | Busca de texto sobrevive à troca de aba/grupo: abrir uma viagem com busca antiga no campo mostra "0 no filtro" para um grupo de 4.812 fotos, com a mensagem genérica de biblioteca vazia | Lightroom mostra filtros ativos como chips removíveis quando o resultado é zero | Limpar a busca ao abrir um grupo (ou mostrar os filtros ativos como chips com "limpar" quando zerado) | P |
| 3 | Em ~900px, com grupo aberto: dropdown de ordenação, busca e texto do Inspetor se sobrepõem (clique na busca seleciona texto do Inspetor) | Lightroom colapsa painéis antes de sobrepor conteúdo | Abaixo de ~1000px, colapsar o Inspetor automaticamente ou empilhar a barra em duas linhas | M |
| 4 | Imagem em alta resolução que retorna 404 (Loupe e comparação de Duplicatas) mostra só nome em texto ou retângulo preto — nenhum estado de erro | Lightroom/Photo Mechanic mostram "arquivo ausente/offline" com ícone e ação | Capturar erro de carregamento e renderizar estado explícito, no Loupe e na comparação de Duplicatas | M |
| 5 | Data no Inspetor em ISO cru (`2026-07-31T21:28:05`) enquanto Loupe e Revisão formatam em pt-BR com `formatarData()` | Qualquer app do mercado formata data igual em toda tela | Reusar `formatarData()` de `Review.tsx` no Inspetor | P |
| 6 | Linhas adjacentes em Revisão com nome+câmera+timestamp idênticos (`media_id` diferentes, confirmado pela rede) sem indicar pasta/fonte — não dá para saber se é a mesma foto em dois catálogos (D-028) ou arquivo diferente | Lightroom/Photo Mechanic sempre mostram a pasta de origem na miniatura por este motivo | Selo de fonte quando duas sugestões adjacentes colidem em nome+data+câmera, ou agrupar com "também em: X" | M |
| 7 | Dois cards de Eventos com o mesmo nome ("Serena 15 Anos", 10 fotos e 628 fotos) sem selo que diferencie álbum de evento detectado (D-030/D-034 preveem a distinção, não aparece no card) | Apple/Google Fotos diferenciam álbum de "momento" com selo | Selo "álbum" vs. "evento detectado" quando dois grupos colidem no nome | P/M |

**20 sugestões sem mouse: NÃO.** Abrir qualquer grupo de destino em Revisão
exige clique de mouse (achado #1); e os atalhos globais de teclado do app
são desligados fora da aba Biblioteca (`App.tsx`), então mesmo com o grupo
aberto, atravessar de um grupo para o próximo — o que revisar 20 sugestões
quase sempre exige, com 13 grupos no catálogo — volta a pedir mouse.

## B. Auditoria de consistência visual (`agente-arte`)

Resumo do agente: os tokens (`webapp/src/index.css`) são fiéis à direção de
arte nova, e o componente `Confianca` é exemplar. A implementação vaza em
pontos concretos e recorrentes.

| # | Inconsistência (arquivo:linha) | O que a direção de arte pede | Proposta | Esforço |
|---|---|---|---|---|
| 1 | `texto-3` (#62666D, contraste ≈3,46:1) usado como texto de CONTEÚDO, não decoração — `Review.tsx:294`, `Inspector.tsx:264`, `Operations.tsx:269,315` | `texto-3` é terciário/desabilitado; AA exige 4,5:1 para texto normal | Trocar para `text-texto-2` (≈6,1:1); reservar `texto-3` para o de fato desabilitado | M |
| 2 | `rounded-lg` nos modais — `Sidebar.tsx:159,198` | Regra explícita do doc: cantos 6px (`rounded-md`), nunca `rounded-lg` | Trocar para `rounded-md` | P |
| 3 | Três gramáticas de "botão importante" sem critério: preenchido, contorno estático colorido, contorno neutro+hover — `RetomarScan.tsx:55`, `StatusBar.tsx:127`, `Sidebar.tsx:76,84`, `Operations.tsx:126,189,207` | Acento reservado a seleção/foco/progresso, nunca decoração persistente | Definir escala (preenchido = ação mais comprometedora) e mover "Retomar"/"Gerar sugestões" para contorno neutro+hover | M |
| 4 | Mesmo par Aprovar/Rejeitar com dois pesos no mesmo arquivo: cabeçalho é neutro-até-hover, linha individual é colorida em repouso — `Review.tsx:213` vs. `:323,331` | Cor reservada a estado, não rótulo permanente | Uniformizar as duas para neutro-até-hover | P |
| 5 | `text-acento` como cor permanente em coluna inteira de lista — `Operations.tsx:288`, `TemplateEditor.tsx:139` — enquanto o mesmo conceito em `Review.tsx:185` usa `font-medium` neutro | Acento nunca decorativo | Trocar para `font-medium` | P |
| 6 | Estados vazios repetem a mesma frase estática sem ação — `Panorama.tsx:149`, `PhotoGrid.tsx:74-75`, `Trips.tsx:31` | Doc: "estado vazio bonito guia direto para Adicionar pasta" | Botão no próprio estado vazio que abre o modal | M |
| 7 | Hover de "cancelar" diverge por tela: `StatusBar.tsx:98` usa `hover:text-erro`; `Sidebar.tsx:170,213` e `Review.tsx:267` usam `hover:bg-cartao` neutro | Consistência entre botões da mesma família semântica | Alinhar todos ao mesmo padrão (decidir se cancelar job é irreversível o bastante para justificar `erro`) | P |
| 8 | Peso de texto sem token — `font-semibold` e `font-medium` convivem sem regra (vários arquivos) | `_tokens.md` previa peso único de ênfase (`--p-tit: 510`) | Adicionar `--font-weight-titulo` ao `@theme` e migrar, ou documentar a regra implícita | M |

## C. Feedback do dono (2026-08-06) — Fase 5, diagnosticado com evidência

Recebido durante a espera dos agentes da seção A/B. Os itens 2–4 abaixo
foram medidos (consulta na cópia do catálogo real de 422.738 registros, ou
citação de código) — deixaram de ser hipótese. Os itens 1, 5, 6 e 7
continuam como design a decidir (dependem do que sai daqui).

### C.2 Fotos presentes e não exibidas — MEDIDO, causa raiz encontrada

**21.378 arquivos são originais de verdade** dentro de
`Photos Library.photoslibrary/originals/` (Apple Fotos) ou
`.aplibrary/Masters/` (Aperture) — não miniaturas, não derivados — e estão
catalogados com `papel='SINAL'`, porque `dentro_de_pacote()`
([scanner/discovery.py:79-88](../fotoorganizer/scanner/discovery.py))
decide pelo SUFIXO da pasta (`.photoslibrary`, `.aplibrary`) sem olhar o
subcaminho: `originals/` (a testemunha real) e `resources/derivatives/` (a
miniatura interna) recebem o mesmo veredito.

De acordo com a política já documentada (D-024): SINAL não entra na
Revisão, não é agrupado em Viagem/Evento (`engine.py`: `organizaveis = [m
for m in midias if m.organizavel]`) e não entra em plano de cópia — mesmo
sendo o arquivo original.

**8.419 desses 21.378 SÓ EXISTEM dentro da biblioteca** (nenhuma cópia
catalogada em `papel='ACERVO'` com o mesmo hash) — ou seja, são fotos
reais, únicas, que o dono nunca vê em Revisão/Viagens/Operações. Os outros
12.959 têm uma cópia equivalente já classificada como ACERVO em outro
lugar (aí o rebaixamento é inofensivo — é exatamente para isso que D-024
existe).

Achado secundário, sem o mesmo peso: o filtro "Tudo" da Biblioteca
(`alcance=tudo`) não filtra NADA —
[repositories/media.py:143](../fotoorganizer/repositories/media.py) devolve
`select(MediaFile)` sem `WHERE` — então a grade em "Tudo" já mostra os
353.480 SINAL junto com o acervo. O sintoma do dono não é sobre essa tela;
é sobre Revisão/Viagens/Operações, que filtram por `organizavel`.

### C.3 Cobertura de formato — MEDIDO, um gap real e um não-gap

- **Vídeo não é lido pelo scanner de arquivo, em hipótese nenhuma.**
  `PILLOW_EXTENSIONS`/`HEIF_EXTENSIONS`/`RAW_EXTENSIONS`
  ([metadata/purepython.py:43-45](../fotoorganizer/metadata/purepython.py))
  não têm `.mov`/`.mp4`/`.mpg`/nenhuma extensão de vídeo — e é essa lista
  que `scanner/discovery.py` usa para decidir o que sequer enumerar. Um
  `.mov` numa pasta de fotos nunca vira linha no banco, nunca gera erro,
  nunca aparece em lugar nenhum — é invisível por completo. Os
  `.mov`/`.mp4`/`.mpg` que HOJE existem no catálogo (43+37+17 registros)
  vieram do catálogo do Apple Fotos importado, não do scanner de pasta.
- **Formato de imagem: sem gap medido.** A amostra de uma pasta real
  (`/Users/acamerini/Pictures/2026`, 1.382 arquivos) não trouxe nenhuma
  extensão de imagem fora da lista suportada — só `.jpg` e um `.DS_Store`
  (corretamente ignorado). A lista de RAW já cobre Canon/Nikon/Sony/
  Fujifilm/Olympus/Panasonic. Sem evidência de fotos perdidas por formato.

### C.4 "Confusão entre eventos e viagens" — MEDIDO, é uma assimetria no código, não desligamento

O advisor está ATIVO (`servicos_externos = true` no `config.toml` real) e
É chamado — mas só quando a cascata determinística já decidiu "neutra"
([engine.py:389-390](../fotoorganizer/classification/engine.py)). O
prompt do sistema pede exatamente a distinção que o dono lembra
([classification/advisor.py:89-96](../fotoorganizer/classification/advisor.py)):
"nomes de pasta... indicam aniversário (Eventos); estadias de dias em
outro país indicam Viagens."

O bug está no que o motor FAZ com a resposta
([engine.py:572-579](../fotoorganizer/classification/engine.py)): só
`resultado.evento` (nome de evento) promove a sessão para `tipo="evento"`.
**Não existe nenhum caminho de código em que `categoria="Viagens"` vindo
do LLM crie ou junte a sessão a uma Viagem.** Quando a cascata fica neutra
e o LLM responde "Viagens", o único efeito é `sessao.categoria = "Viagens"`
— usado três passos depois só como texto de fallback da pasta
`{categoria}` ([engine.py:826-830](../fotoorganizer/classification/engine.py)),
NUNCA cria um `Trip`, nunca aparece na aba Viagens. A suíte de testes
confirma a assimetria: `test_advisor_llm_apoia_sessao_neutra`
([tests/test_suggestion_engine.py:612](../tests/test_suggestion_engine.py))
só cobre o caminho Evento — não existe teste equivalente para Viagem,
porque não há comportamento a testar.

**Não é reativação — é completar o código que já existe** para tratar
`categoria="Viagens"` com o mesmo peso de `evento`: criar/juntar a sessão
a uma Viagem quando o LLM disser isso, com a mesma justificativa e nível
de confiança que o caminho de Evento já tem.

### Itens ainda de design (não medidos por natureza — são decisão, não fato)

1. **Painel único de decisão** (origem + dados + análise + destino):
   depende de A.5/A.6 (já corrigidos nesta rodada).
5. **Viagens só viagens; aba Eventos irmã** — soma-se a C.4: sem o fix de
   C.4, uma "viagem" mal-classificada continua aparecendo em lugar nenhum
   mesmo depois de separar as abas.
6. **Redesenho da Revisão** — já parcialmente endereçado (A.1, A.2, A.6,
   B.1, B.3, B.4 desta rodada).
7. **Rever rótulo/propósito da aba Operações** — sem medição própria ainda.

## D. Priorização consolidada (A + B, ordenada por valor/esforço)

| Ordem | Item | Fonte | Esforço |
|---|---|---|---|
| 1 | Cabeçalho de grupo em Revisão navegável por teclado | A.1 | P |
| 2 | `texto-3` fora do AA em conteúdo real | B.1 | M |
| 3 | Busca não limpa ao trocar de grupo (falso "vazio") | A.2 | P |
| 4 | `rounded-lg` nos modais | B.2 | P |
| 5 | Data crua no Inspetor | A.5 | P |
| 6 | Aprovar/Rejeitar com dois pesos no mesmo arquivo | B.4 | P |
| 7 | `text-acento` decorativo em lista | B.5 | P |
| 8 | Selo de fonte em sugestões adjacentes idênticas | A.6 | M |
| 9 | Selo álbum × evento detectado | A.7 / B.6 | P/M |
| 10 | Três gramáticas de botão importante | B.3 | M |
| 11 | Estado de erro de imagem (Loupe/Duplicatas) | A.4 | M |
| 12 | Estados vazios com ação | B.6 | M |
| 13 | Inspetor/busca se sobrepõem em ~900px | A.3 | M |
| 14 | Hover de "cancelar" inconsistente | B.7 | P |
| 15 | Peso de texto sem token | B.8 | M |

**Pare aqui.** Nada acima foi implementado. Itens 1–7 (todos esforço P) são
o lote natural de uma primeira fatia, se aprovado. Os 7 pontos da seção C
exigem uma rodada de diagnóstico à parte, com evidência, antes de virar
código — nenhum deve ser "consertado" a partir de suposição.

---

# Avaliação de UX — fase 6

Executada em 2026-07-30. Método em `docs/prompts/00-protocolo.md`. Insumos:
`docs/AUDITORIA_FUNCIONALIDADES.md` (fase 2) e `docs/REFERENCIAS_DESIGN.md`.
Protótipos em [`docs/prototipos/`](prototipos/index.html). Decisões desta fase:
D-017 e D-018.

**Resumo em uma frase:** o problema não é que a interface seja feia — é que
ela é uma **página web mostrando conclusões**, quando precisa ser um
**aplicativo mostrando decisões**; as duas coisas têm causas diferentes e se
resolvem em camadas diferentes.

---

## 1. Por que parece um site

O diagnóstico do dono ("parece que estou navegando numa tela web") tem causas
identificáveis, todas visíveis nas capturas da fase 2. Não é impressão vaga.

| Sintoma | Causa | Camada |
|---|---|---|
| Seletor "Mais antigas" com a setinha do Chrome | `<select>` nativo sem estilo | controle |
| Campo de busca genérico com placeholder | `<input>` nativo sem estilo | controle |
| Navegação como fileira de links de texto | padrão de menu de site; no Mac seria barra de ferramentas ou lateral | idioma |
| Acento azul | `blue-500`, o padrão do Tailwind | token |
| Botões de bloco no rodapé da lateral | layout de web; no Mac seria `+` discreto ou item de menu | idioma |
| Quatro miniaturas no canto de uma área imensa vazia | grade não preenche nem centraliza | layout |
| Superfícies em cinza sólido (#252526, #2d2d30) | painel com cor própria compete com a foto | token |

**Correção de 30/07.** A versão anterior deste documento listava "corpo em
16px" como causa. Está errado: `webapp/src/index.css` já definia 13px, e a
medição por `getComputedStyle` na página viva confirmou. A escala não era o
problema — as superfícies cinza-sólidas e o acento azul eram.

A causa raiz é uma só: **React + Vite + Tailwind num navegador herda o visual
do navegador em tudo que não for explicitamente desenhado.** O
`docs/DIRECAO_DE_ARTE.md` existe e não está sendo aplicado — o `<select>` cru
é a prova de que a folha de estilo nunca chegou aos controles.

Isso é corrigível com tokens e com uma camada de controles próprios. É a parte
**fácil** do problema.

---

## 2. O problema difícil: a interface mostra conclusão, não decisão

A fase 2 mediu o seguinte: o motor grava, para uma foto sem GPS,
`"GPS herdado de 'IMG_9100.jpg' (Apple iPhone 15 Pro) — tirada a 2min de
distância"`, com confiança média e score 0,75. Isso é uma frase que responde
"por que aqui?" melhor do que a maioria dos DAMs do mercado consegue.

E a interface mostrava um badge escrito **"Média"**, sem link, numa linha cuja
única outra informação era um caminho absoluto truncado antes do nome do
arquivo.

Depois das correções de 30/07 o Inspetor passou a mostrar o porquê — mas a
**Revisão**, que é onde as decisões em lote acontecem, continua cega. É o
problema central desta fase, e nenhuma quantidade de token resolve: é
arquitetura de informação.

### O que a Revisão não responde hoje

Olhando uma linha da tela de Revisão, o usuário não sabe: qual foto é, de que
câmera veio, quando foi tirada, por que aquele destino, o que o "Média"
significa, nem o que acontece se ele errar.

Ele tem dois botões — Aprovar e Rejeitar — e nenhuma base para escolher entre
eles. Com 63 linhas idênticas, a única ação racional é "Aprovar todas", que é
exatamente o que a tela oferece no topo.

**Uma tela de revisão que empurra o usuário para "aprovar tudo" não é uma tela
de revisão.**

**Correção de 30/07.** A versão anterior dizia "não há miniatura". Está
errado: `Review.tsx` sempre teve um `<img>` de 48px por linha, e o nome do
arquivo sempre foi renderizado. O defeito real é mais estreito e mais
interessante — `{s.pasta}/` vinha antes do nome na mesma linha, e o
`truncate` cortava antes de o nome aparecer. O elemento estava lá; a
informação, não. Foi por isso que as 63 linhas ficaram visualmente idênticas.

---

## 3. Estados que a interface trata bem

Registro para não desfazer o que funciona:

- **Panorama** é a melhor tela do app e um acerto de conceito: lacunas
  clicáveis que recortam a biblioteca ("5 sem data de captura", "25 sem
  coordenada"). É diagnóstico virando ação, e não vi equivalente nos produtos
  consultados.
- **Lacuna zerada fica desabilitada** em vez de sumir — decisão certa, com
  teste próprio (`App.test.tsx`).
- **Erro por arquivo é registrado e o scan continua**: 1 erro no catálogo de
  demonstração, visível no rodapé, sem interromper nada.
- **Barra de status com atalhos** — a intenção teclado-first está lá.
- **Operações exige dry-run antes de executar**, e o resumo carrega o veredito.

---

## 4. As cinco propostas

Cada uma é um arquivo autocontido em `docs/prototipos/`. Abrem com duplo
clique, sem servidor e sem rede.

### 4.1 [Confiança que leva à evidência](prototipos/01-confianca.html)

Confiança vira **quantidade** — três segmentos preenchidos 3/3, 2/3, 1/3 — e
não três cores. Neutro em alta e média; só a baixa recebe cor, porque é a
única que pede olho humano. Isso resolve dois problemas de uma vez: um
semáforo de três cores numa ferramenta de foto compete com a imagem, e cor
como único canal falha para daltônicos.

O indicador é um **botão** que abre o porquê. Badge que não leva à
justificativa é decoração.

O lugar herdado ganha marcação própria (pino azul dessaturado) e um chip com a
foto doadora — a origem fica alcançável, não implícita.

### 4.2 [Revisão em lote](prototipos/02-revisao-em-lote.html)

A mudança conceitual: **a unidade de decisão é o grupo, não a foto solta.**
"Aprovar as 22 de Viagens/2024 - França" é uma decisão que o usuário consegue
tomar com informação; "aprovar a linha 37 de 63" não é.

Cada linha ganha miniatura, nome, câmera e horário, destino, confiança e o
porquê inline expansível. Teclado: `↑↓` navega, `↵` aprova, `⌫` rejeita, `?`
abre o porquê, `⇧↵` aprova o grupo. O rodapé mantém o rastro do lote com
desfazer.

O grupo "Não classificadas" recebe uma marca de atenção na borda — é o único
que quase sempre precisa de olho.

### 4.3 [Mapa: lido x estimado](prototipos/03-mapa-local-estimado.html)

Ponto cheio é coordenada lida; ponto vazado e tracejado é local estimado; o
traço liga a estimativa à foto que doou. O painel lateral avisa que corrigir
uma estimativa desfaz também a viagem que ela ajudou a formar — o efeito em
cascata aparece **antes** da ação.

O desenho do mapa é esquemático de propósito. O protótipo decide a linguagem
(cheio × vazado, o traço, o aviso de cascata), não a cartografia: mapa real
exige antes decidir entre dados offline embarcados e serviço externo, o que é
matéria de `docs/PRIVACIDADE.md`.

### 4.4 [Linha do tempo por fonte](prototipos/04-linha-do-tempo.html)

Uma faixa por dispositivo. É isso que torna o cruzamento **visível**: dá para
ver a câmera fotografando entre duas fotos do telefone, que é literalmente o
motivo de ela ter herdado a coordenada. Numa faixa só, isso vira uma pilha
indistinta.

O segundo painel mostra a deriva de relógio: hora gravada em cinza, hora
corrigida em azul, com o deslocamento medido e quantas âncoras o sustentam.
Hoje essa correção acontece em silêncio; quando erra, o usuário vê fotos no
dia errado sem saber por quê.

### 4.5 [Plano: antes e depois](prototipos/05-plano-antes-depois.html)

Duas árvores lado a lado, origem intacta à esquerda, o que será criado
destacado à direita. A faixa de resumo traz arquivos, pastas novas, espaço,
conflitos — e **quantas fotos vão por lugar estimado**, com link para revê-las
antes de executar.

O botão de executar só existe porque o dry-run rodou: o invariante 2 vira
comportamento visível em vez de regra escrita no código. Quando não rodou, o
botão aparece desabilitado com o motivo ao lado, em vez de sumir — controle
que desaparece ensina menos que controle que explica.

---

## 5. Ordenado por quanto aumenta a confiança nas decisões

Não por esforço de implementação.

| # | Mudança | Por quê | Esforço |
|---|---|---|---|
| 1 | Revisão com miniatura, nome e porquê inline | hoje a tela empurra para "aprovar tudo" | médio |
| 2 | Agrupar a Revisão por destino | transforma 63 decisões cegas em 4 informadas | médio |
| 3 | Confiança como quantidade, clicável | badge vira porta de entrada da evidência | baixo |
| 4 | Camada de controles próprios (`select`, `input`, botões) | mata o "parece site" na raiz | médio |
| 5 | Tokens: fundo quase-preto, superfície translúcida, 13px | implementa "a foto é a cor da interface" | baixo |
| 6 | Marcar lugar estimado em toda superfície | o diferencial deixa de ser invisível | baixo |
| 7 | Antes/depois no plano | executar deixa de ser aposta | médio |
| 8 | Linha do tempo por fonte | o cruzamento entre câmeras fica demonstrável | alto |
| 9 | Mapa | depende da decisão de dados offline × serviço | alto |

Os itens 3, 5 e 6 somam pouco esforço e mudam bastante — mesma característica
dos itens que a fase 2 recomendou e que já foram feitos.

---

## 6. Trade-offs

| Escolha | Ganha | Perde |
|---|---|---|
| Confiança como quantidade, não cor | não compete com a foto; funciona para daltônicos | menos chamativo que semáforo — deliberado |
| Sem acento cromático fixo | a foto manda na interface | interface menos "marcada"; identidade vem da tipografia e do espaçamento |
| Superfície translúcida em vez de painel sólido | profundidade sem introduzir cor | exige cuidado com contraste sobre foto clara — **não verificado** neste protótipo |
| Revisão agrupada por destino | decisão informada em lote | grupo grande esconde a foto individual; o desdobramento resolve, com um clique a mais |
| Protótipo em HTML solto | rápido de iterar e discutir | não prova integração com a grade virtualizada nem desempenho em 500 mil fotos |

---

## 7. O que eu revisitaria

- **Contraste sobre foto clara.** A superfície translúcida foi verificada
  sobre fundo escuro apenas. Sobre uma foto de neve ou praia, `rgba(255,255,
  255,.05)` pode sumir. Precisa de teste com fotos reais antes de virar token.
- **A grade virtualizada.** Os protótipos usam listas curtas. A Revisão
  agrupada precisa virtualizar dentro de cada grupo, e isso muda a
  implementação.
- **Acessibilidade além da cor.** Foco visível, ordem de tabulação e leitor de
  tela foram considerados no desenho (o indicador é `<button>`, há
  `aria-expanded`), mas **não foram testados**.
- **Modo claro.** Toda a proposta é dark-first, conforme
  `docs/DIRECAO_DE_ARTE.md`. Se o produto comercial precisar de modo claro, a
  mecânica de superfície translúcida inverte e precisa ser redesenhada, não
  apenas invertida.

---

## Comparação com o mercado

Consultado em 2026-07-29 (detalhe e tokens em `docs/REFERENCIAS_DESIGN.md`).

**Navegação de acervo grande.** Lightroom e Peakto resolvem com barra lateral
hierárquica mais filtros persistentes. O Panorama daqui faz algo diferente e
melhor para acervo pessoal: parte das **lacunas** ("25 sem coordenada") em vez
da hierarquia, o que dá ao usuário um caminho de trabalho em vez de uma
árvore. Vale preservar e ampliar.

**Revisão em lote.** É o ponto fraco da categoria inteira: Lightroom resolve
com bandeiras e estrelas, que exigem que o usuário já saiba o que quer. Nenhum
dos consultados oferece "aprove esta inferência" com justificativa — porque
nenhum deles infere e explica.

**Transparência de decisão automática.** Aqui não há referência a copiar.
DAMs comerciais tratam metadado inferido como fato: a foto simplesmente
"está" em Avignon. O modelo de evidências deste projeto é a diferenciação
defensável, e a fase 6 existe para que ela deixe de ser invisível.

**Idioma visual.** A composição recomendada continua sendo mecânica da Linear
(superfície translúcida, densidade, peso 510, tracking negativo) mais idioma
de controle do macOS. Peakto foi rejeitada como referência visual em D-015 —
espelhar cyme.io deixaria o app mais parecido com site, não menos.
