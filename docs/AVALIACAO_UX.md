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
