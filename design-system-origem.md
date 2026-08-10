# Design system do APP_ORIGEM — extração portável

Extraído em 2026-08-10 do fork local `~/dev/fot` (**Immich v3.1.0**, commit
`5ad1e4e0f`, remoto `AlexandreCamerini/Fot`).

Este documento é **descritivo e agnóstico de stack**: descreve valores, papéis
semânticos, estados e mecanismos. A origem é SvelteKit + Tailwind 4 +
`@immich/ui`; o destino é React + Tailwind 4. A camada de tokens é portável
diretamente; a camada de componentes não é — ver §8.

## Aviso de licença — leia antes de usar isto

O Immich é **AGPLv3**. Copiar folha de estilo, markup ou implementação de
componente para o Foto Organizer contamina o projeto inteiro com a AGPL.

Valores numéricos isolados (um hex, um raio, uma duração) não são obra
protegível, mas **a folha de estilo e a árvore de componentes são**. Este
documento foi escrito para permitir **reimplementação a partir da
especificação**, não transcrição. A mesma regra já vale no repositório —
`docs/referencia-immich/README.md`.

## Como cada valor foi obtido

| Fonte | O que saiu dela | Confiança |
|---|---|---|
| `web/src/app.css` | fontes, breakpoints, utilitários de app, altura de navbar | verificado |
| `@immich/ui@0.83.0` → `theme/default.css` | paleta completa, aliases semânticos | verificado |
| `@immich/ui@0.83.0` → `styles.js` + 40 componentes | variantes, estados, escala de tamanho | verificado |
| `web/src/**/*.svelte` (411 arquivos) | frequência real de radii, sombra, gap, tipografia, motion | verificado |
| `i18n/en.json` | tom de voz | verificado |

`web/node_modules` está vazio no fork local. O pacote `@immich/ui` foi lido
extraindo os blobs do `.pnpm-store/v11` por conteúdo — leitura pura, nada foi
instalado. Os valores OKLCH foram convertidos para hex sRGB por conversão
própria (OKLab → linear sRGB → gamma), arredondada ao inteiro; divergências de
±1 por canal contra o navegador são esperadas e irrelevantes.

---

## 1. Cor

### 1.1 Arquitetura da paleta

Três camadas, nesta ordem — é a decisão estrutural mais importante e vale mais
que qualquer valor individual:

1. **Rampa bruta** — `--immich-ui-<família>-<50..950>`, definida em OKLCH,
   11 degraus por família, gerada com trava no degrau 500 (a origem cita
   tints.dev como gerador).
2. **Alias semântico** — `--color-primary`, `--color-danger`, `--color-subtle`
   etc. apontam para um degrau da rampa. **Nenhum componente lê a rampa
   direto**; todos leem o alias.
3. **Escopo de tema** — a rampa inteira é redefinida sob o seletor `.dark`.
   Aliases e componentes não mudam uma linha entre temas.

Consequência prática: trocar tema, trocar marca ou trocar acento é editar a
camada 1. É a mesma arquitetura de duas camadas que o Foto Organizer já usa em
`webapp/src/index.css`, com uma diferença — lá os aliases apontam para valores
literais, aqui apontam para uma rampa nomeada.

### 1.2 Papéis semânticos

| Alias | Aponta para | Papel |
|---|---|---|
| `primary` | `primary-500` | ação principal, foco, link, estado ativo |
| `success` | `success-500` | confirmação, resultado positivo |
| `danger` | `danger-500` | destruição, erro, validação inválida |
| `warning` | `warning-500` | atenção reversível |
| `info` | `info-500` | informação neutra |
| `light` | `--immich-ui-light` | **cor de fundo do tema** (branco no claro, preto no escuro) |
| `dark` | `--immich-ui-dark` | **cor de texto do tema** (cinza-escuro no claro, cinza-claro no escuro) |
| `muted` | `--immich-ui-muted` | texto secundário |
| `subtle` | `--immich-ui-gray` | superfície elevada discreta (card, popover, hover) |
| `default-border` | `light-300` / `light-200` | borda padrão, aplicada globalmente |

Note a inversão deliberada: `light` **não** significa "cor clara", significa
"o fundo"; `dark` significa "o texto". No tema escuro `light` = `#000000` e
`dark` = `#DBDBDB`. Um componente escrito como `bg-light text-dark` funciona
nos dois temas sem condicional. É um truque barato e eficaz — e é o oposto da
convenção usual, então documente ou vai gerar bug de leitura.

### 1.3 Valores — tema claro

Fundo `#FFFFFF` · texto `#3D3D3D` · secundário `#A1A1A1` · superfície sutil `#F5F5F5` · borda `#D4D4D4`

| Família | 50 | 100 | 200 | 300 | 400 | **500** | 600 | 700 | 800 | 900 | 950 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| primary | `#EEF2FE` | `#D9DBF3` | `#B1B5E6` | `#8C93DB` | `#646FCC` | **`#4250AF`** | `#343F8D` | `#273170` | `#1A2151` | `#0F1437` | `#060820` |
| success | `#F3FCF7` | `#B7FFC2` | `#19FB66` | `#17E85E` | `#15D556` | **`#10C14D`** | `#0B983B` | `#07702A` | `#024B19` | `#012B0B` | `#001B05` |
| danger | `#FEF4F3` | `#FDDEDE` | `#FCBCBB` | `#FB9492` | `#FA6967` | **`#FA2921`** | `#C81C15` | `#97120D` | `#6D0A07` | `#430402` | `#2B0201` |
| warning | `#FFF8F3` | `#FFEEDF` | `#FFE0C4` | `#FFCE9B` | `#FFC072` | **`#FFB003`** | `#C98A02` | `#936400` | `#644200` | `#362200` | `#231500` |
| info | `#F4F9FF` | `#DBE5FE` | `#B5CCFD` | `#8BB4FD` | `#569CFC` | **`#1984E9`** | `#1469BB` | `#0A4E8E` | `#053564` | `#021E3C` | `#011127` |

`primary-500` é o único valor da paleta inteira escrito em hex literal
(`#4250af`) e não em OKLCH — é a cor de marca, travada, com a rampa gerada em
volta dela.

Rampas neutras (`light-*` e `dark-*`) reutilizam a escala `neutral` do
Tailwind 4:
`#FAFAFA #F5F5F5 #E5E5E5 #D4D4D4 #A1A1A1 #737373 #525252 #404040 #262626 #171717 #0A0A0A`
(50→950). No tema claro `light-*` sobe 50→950 e `dark-*` desce 950→50; no
escuro as duas invertem. Ou seja: `light-100` é sempre "um passo acima do
fundo" e `dark-900` é sempre "quase a cor do texto", nos dois temas.

### 1.4 Valores — tema escuro

Fundo `#000000` · texto `#DBDBDB` · secundário `#D4D4D4` · superfície sutil `#101116` · borda `#262626`

| Família | 50 | 100 | 200 | 300 | 400 | **500** | 600 | 700 | 800 | 900 | 950 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| primary | `#0F1620` | `#1A2433` | `#314158` | `#425673` | `#536C8F` | **`#ACCBFA`** | `#BFD6FB` | `#D1E1FC` | `#DEE9FD` | `#EEF4FE` | `#F7F9FE` |
| success | `#02170A` | `#09311B` | `#165B38` | `#258755` | `#36B975` | **`#48ED98`** | `#4BF69E` | `#71FCAE` | `#B8FDD2` | `#DFFEE9` | `#EAFEF1` |
| danger | `#330303` | `#490606` | `#801212` | `#B81E1E` | `#F32B2B` | **`#F67D7D`** | `#F79A9A` | `#F9B5B5` | `#FBD0D0` | `#FDE6E6` | `#FEF4F4` |
| warning | `#1F1301` | `#3A2600` | `#6E4C00` | `#A37301` | `#DC9D00` | **`#FFD198`** | `#FFD9AE` | `#FFE4C7` | `#FFEEDD` | `#FFF5EB` | `#FFFCF9` |
| info | `#001427` | `#002745` | `#014776` | `#006CB0` | `#0091E9` | **`#7AB7FF`** | `#98C4FF` | `#B7D3FF` | `#CEE1FF` | `#E9F1FF` | `#F2F7FF` |

**A rampa escura inverte a direção.** No claro, 50 é o degrau mais claro e 950
o mais escuro; no escuro, 50 é o mais escuro e 950 o mais claro. Isso mantém a
semântica "500 é a cor de estado, 50 é o fundo tingido, 950 é o texto tingido"
válida nos dois temas — e é por isso que `bg-danger/10 text-danger` produz um
alerta legível sem nenhuma regra condicional.

O acento no escuro (`#ACCBFA`) é **dessaturado e claro**, não o mesmo índigo
com brilho: cor saturada sobre preto vibra. É a única correção manual de
percepção em toda a paleta.

### 1.5 Superfície e elevação

Não há escala de elevação por sombra. A hierarquia é feita por cor:

- **Fundo**: `light` (`#FFF` / `#000`).
- **Superfície elevada**: `subtle` (`#F5F5F5` / `#101116`) — card, popover,
  menu, hover de item de lista.
- **Um passo além**: `light-100`/`light-200` para topo de modal, barra de
  controle, cabeçalho de tabela.
- **Borda**: aplicada por regra global (`*, ::before, ::after, ::backdrop`
  recebem `border-color: default-border`), então declarar `border` já sai na
  cor certa sem escolher cor.

**Overlay de estado** é a técnica dominante: um estado colorido é `cor/10` de
fundo + `cor` de texto + `cor` de borda. Hover sobe para `/15` ou `/20`.
Botão preenchido escurece por `cor/80`. Não existe token separado para
"hover-primary" — é sempre opacidade sobre o mesmo alias.

---

## 2. Tipografia

**Famílias.** `GoogleSans` (sans, variável, peso 410–900) e `GoogleSansCode`
(mono, variável, peso 1–900), servidas como TTF variável do próprio app — sem
CDN. `ascent-override: 106.25%` e `size-adjust: 106.25%` corrigem a métrica
para casar com o fallback e evitar salto de layout no carregamento.

**Ajuste global.** `letter-spacing: 0.1px` no `:root` — tracking levemente
positivo no corpo, não negativo. Escolha oposta à de interfaces de app denso.

**Escala nomeada** (mapeada em `styleVariants.textSize`, o mesmo token
`tiny→giant` que dimensiona botão, input, ícone e espaçamento de tabela):

| Nome | Tamanho | Uso |
|---|---|---|
| `tiny` | 12px | metadado, legenda, contador |
| `small` | 14px | **padrão de interface** |
| `medium` | 16px | corpo de leitura |
| `large` | 18px | subtítulo |
| `giant` | 20px | título de seção |

**Frequência real medida** nos 411 componentes: `text-sm` 148 · `text-xs` 55 ·
`text-lg` 23 · `text-2xl` 17 · `text-base` 15 · `text-xl` 12 · `text-3xl` 7 ·
`text-4xl` 6 · `text-6xl` 5.

Leitura: **a interface é 14px, não 16px.** O `text-base` aparece 15 vezes em
411 arquivos — o padrão do navegador é praticamente inexistente. Tamanhos
acima de 20px só existem em telas de marketing/onboarding/erro.

**Pesos.** Nove degraus expostos (`thin`→`black`), mas o único que aparece nos
componentes do design system é `font-medium` (500) — em botão e em rótulo de
campo. Hierarquia é feita por **tamanho e cor**, não por peso. Não há uso de
peso intermediário customizado apesar de a fonte ser variável.

---

## 3. Espaçamento

Base Tailwind (`--spacing` = 4px), com dois acréscimos:

- `--spacing-18` = 4.5rem (72px) — altura de navbar.
- `--spacing-control-bar-container` = 72px e `--spacing-control-bar` = 64px —
  tokens dedicados à barra de controle flutuante.

**Frequência real de `gap`:** `gap-2` (8px) 146× · `gap-4` (16px) 137× ·
`gap-1` (4px) 59× · `gap-6` (24px) 14× · `gap-3` (12px) 10×.

O vocabulário efetivo é **4 / 8 / 16 px**, com 24px para separar blocos. Os
ímpares (12px, 20px) são residuais. Um sistema de três degraus disfarçado de
escala de doze.

**Padding de controle**, por degrau da escala de tamanho:

| Tamanho | Botão (texto) | Botão (só ícone) | Ícone interno |
|---|---|---|---|
| tiny | 12×4px | 24×24px | 16px |
| small | 16×8px | 32×32px | 16px |
| medium | 20×8px | 40×40px | 16px |
| large | 32×10px | 48×48px | 24px |
| giant | 40×12px | 56×56px | 32px |

Input: padding vertical fixo de 10px, horizontal 16px — e **cai a zero do lado
que tem ícone**, para o ícone encostar no ponto certo em vez de dobrar o
respiro.

**Dimensões de layout:**
- navbar: `calc(4.5rem + 4px)` = 76px; 62px em telas médias.
- sidebar: `min(100vw, 16rem)` — 256px no desktop, largura total no mobile.
- barra de controle: 64px de altura, contêiner de 72px.

---

## 4. Raio

Escala Tailwind padrão. **Frequência real:** `rounded-lg` (8px) 62× ·
`rounded-full` 54× · `rounded-xl` (12px) 46× · `rounded-2xl` (16px) 31× ·
`rounded-3xl` (24px) 20× · `rounded-sm` 13× · `rounded-md` 11× ·
`rounded-none` 3×.

Mapeamento por componente:

| Elemento | Raio |
|---|---|
| botão (base) | 6px, subindo para 8px (tiny/small), 12px (medium/large), 16px (giant) |
| input, textarea, select | 8px em todos os tamanhos — não escala |
| item de menu | 8px |
| card, popover, menu | 12px |
| toast | 12px (16px no tamanho giant) |
| avatar, switch, badge, chip | pill (`rounded-full`) |

Há um token de **forma** (`shape`) ortogonal ao tamanho, com três valores:
`rectangle` (0), `semi-round` (raio da escala) e `round` (pill). É o que
permite pedir "este botão é pill" sem mexer no tamanho.

Raio dominante: **8px**, com 12px para contêiner. Sensivelmente mais arredondado
que o padrão de app desktop.

---

## 5. Sombra

**Frequência real:** `shadow-lg` 16× · `shadow-none` 7× · `shadow-sm` 6× ·
`shadow-2xl` 6× · `shadow-md` 3× · `shadow-xl` 2× · `shadow-xs` 1×.

61 usos em 411 arquivos — sombra é exceção, não sistema. Onde aparece:

- popover / menu de contexto: `shadow-sm`
- toast: `shadow-xs`
- barra de controle na variante `outline`: `shadow-md` + borda
- modal e overlay: `shadow-lg` / `shadow-2xl`

Superfície comum (card, painel, item de lista) **não tem sombra** — separa por
cor de fundo e borda. Sombra significa "isto flutua acima do documento", não
"isto é um cartão".

---

## 6. Breakpoints

Declarados **em ordem decrescente**, o que na prática os converte de
mobile-first para desktop-first no consumo:

| Nome | Largura |
|---|---|
| `sm` | 639px |
| `md` | 767px |
| `lg` | 1023px |
| `xl` | 1279px |
| `2xl` | 1535px |
| `sidebar` | 850px — ponto em que a sidebar deixa de ser overlay |
| `tall` | 800px — **altura**, não largura |

Dois breakpoints semânticos e não-canônicos (`sidebar`, `tall`) valem mais que
os cinco genéricos: nomeiam a decisão de layout em vez do dispositivo. `tall`
é o único que responde a altura de viewport — usado onde a grade precisa de
espaço vertical mínimo para valer a pena.

---

## 7. Motion

**Durações medidas** (`svelte/transition` + classes utilitárias):
500ms 30× · 250ms 17× · 200ms 17× · 100ms 12× · 150ms 9× · 2000ms 5× ·
400ms 2× · 300ms 2×.

Vocabulário efetivo:

| Duração | Uso |
|---|---|
| 100ms | micro-estado: knob de switch, hover de item de navegação |
| 150–200ms | **padrão**: cor, opacidade, aparecimento de painel |
| 250ms | entrada de toast e de overlay |
| 500ms | transição de viewport / troca de asset no visualizador |
| 2000ms | indicador contínuo (spinner, progresso indeterminado) |

**Easings:** `quintOut` (10×) domina, `quartInOut` (4×) para movimento
bidirecional, `linear` (2×) para progresso, `cubicOut` (1×). Nas classes
utilitárias: `ease-out` 4× · `ease-in-out` 3× · `ease-in` 1×.

**Padrões de entrada/saída:**
- `fly` 20× — o padrão. Painel/menu entra deslocado no eixo relevante
  (menu: `y: 10px`; toast: `y: 200px`) e sai por fade.
- `fade` 10× — overlay, backdrop, saída rápida (100ms).
- `slide` 6× — acordeão e revelação de altura.

**Assimetria deliberada**: entra em 250ms com deslocamento, sai em 100ms com
fade. Aparecer é evento; desaparecer é sair do caminho.

**Só uma propriedade transiciona onde possível** — `transition-colors` no
botão, `transition-transform` no knob, `transition-[padding]` no item de
navegação. Não há `transition: all` nos componentes do design system.

---

## 8. Componentes

### 8.1 Inventário (por frequência de uso real no app)

Icon 79 · Text 74 · Button 73 · IconButton 59 · Field 36 · FormModal 34 ·
LoadingSpinner 30 · Input 23 · Stack 18 · Link 17 · Modal/ModalBody 16 ·
HStack 16 · Label 15 · ActionButton 15 · CommandPalette 14 · Switch 12 ·
Heading 12 · Textarea 10 · PasswordInput 9 · Container 8 · Alert 8 ·
HelperText 7 · Checkbox 7 · Card/CardBody 7 · Select 6 · ConfirmModal 6 ·
ListButton 5 · BasicModal 5 · Badge 5 · DatePicker 4 · ContextMenu 4 ·
Table\* 3 · VStack 3.

Leitura: **os cinco mais usados são primitivos de composição** (ícone, texto,
botão, botão-ícone, campo). Nenhum componente "de domínio" (galeria, card de
foto, linha do tempo) mora no design system — esses ficam no app. A fronteira
está desenhada no lugar certo.

### 8.2 O modelo de variação — a parte realmente portável

Todo componente é dimensionado pelo mesmo conjunto de eixos ortogonais:

| Eixo | Valores |
|---|---|
| `color` | `primary` `secondary` `success` `danger` `warning` `info` |
| `variant` | `filled` `outline` `ghost` |
| `size` | `tiny` `small` `medium` `large` `giant` |
| `shape` | `rectangle` `semi-round` `round` |
| `state` | `disabled` `loading` `invalid` `fullWidth` |

A combinação (`color` × `variant`) é resolvida por uma tabela de estilos
compartilhada, **uma vez**, e reutilizada por botão, alerta, badge, toast,
borda e ícone. O resultado é que um estado novo entra em toda a interface por
uma linha, e nenhum componente inventa a própria cor de perigo.

Fórmula de cada variante, em pseudo-CSS agnóstico:

```
filled   → fundo: cor        texto: fundo-do-tema   hover: cor/80
outline  → fundo: cor/10     texto: cor   borda: cor   hover: cor/20
ghost    → fundo: transp.    texto: cor              hover: cor/15
```

Essa fórmula é a peça mais valiosa do sistema inteiro e não depende de
framework, de Tailwind nem da paleta — funciona com qualquer conjunto de
aliases.

### 8.3 Estados obrigatórios

Cada controle interativo trata, sem exceção:

- **disabled** — `opacity-50` + `cursor-not-allowed` + `aria-disabled`; e
  todo hover é qualificado com `not-disabled:` para não acender item morto.
- **loading** — estado próprio, não um `disabled` disfarçado: troca o conteúdo
  por spinner dimensionado um degrau abaixo do botão, preserva a largura, e
  desabilita junto (`disabled = disabled || loading`).
- **focus** — `outline` de 2px na cor do componente, com `outline-offset: 2px`,
  só em `focus-visible`. Input remove o outline do navegador e move o foco para
  um `ring` de 1px no **contêiner**, não no campo — assim o anel envolve ícone
  e texto juntos.
- **invalid** — `ring-danger` no contêiner, herdado por contexto de campo.
- **hover** — sempre overlay de opacidade sobre a cor semântica.

### 8.4 Composição

- **Contexto de campo**: `Field` publica `id`, `required`, `invalid`,
  `disabled` por contexto; `Label`, `Input` e `HelperText` consomem. O
  consumidor não amarra `for`/`id` à mão e não pode dessincronizar o estado
  inválido do rótulo.
- **Layout por primitivo**: `Stack` / `HStack` / `VStack` com `gap` padrão de
  8px cobrem quase todo o arranjo. Praticamente não há CSS de layout ad-hoc
  nos componentes.
- **Ícone como dado**: ícones são *paths* SVG importados de `@mdi/js`
  (191 ocorrências) e passados como prop — não são componentes nem fonte de
  ícone. Cada componente aceita `leadingIcon` / `trailingIcon` e resolve
  tamanho e cor sozinho. Trocar biblioteca de ícone é trocar o import.
- **`cleanClass`**: todo componente funde as classes da variante com a
  `class` do consumidor via `tailwind-merge`, então uma classe passada de fora
  **vence** a do componente em vez de duplicar. Sem isso, a API `class` de
  escape não funciona de verdade.

### 8.5 Camadas

Não há escala de z-index nomeada. Uso real: `z-1` 18× · `z-2` 16× · `z-10` 4× ·
`z-60` 2× · `z-70` 1× · `z-9999` 1×. Empilhamento resolvido ad-hoc — é a
fraqueza mais visível do sistema e **não deve ser portada**.

---

## 9. Direção de arte

### 9.1 Princípios legíveis no código

1. **A foto é o conteúdo, o chrome é branco ou preto.** Fundo é `#FFFFFF` ou
   `#000000` puro — não cinza-escuro, não quase-preto. Preto puro no tema
   escuro é decisão de app de foto: a miniatura recorta contra o fundo sem
   halo. (O corpo ganha `background: black` explícito quando o visualizador
   está aberto.)
2. **Cor significa estado, nunca decoração de superfície.** As cinco famílias
   semânticas só aparecem em elemento que comunica estado ou ação. Painel,
   card e barra são neutros.
3. **Um único acento cromático** (índigo `#4250AF`), e ele é a marca. Não há
   segunda cor de destaque.
4. **Contraste por cor, profundidade por sombra — e sombra é rara.** 61 usos
   em 411 arquivos.
5. **Paridade real entre temas.** Não é um tema escuro por cima de um claro: é
   uma rampa por tema, com dessaturação corrigida à mão no escuro.
6. **Acessibilidade estrutural, não retrofit.** `focus-visible` em todos os
   controles, `aria-disabled` junto de `disabled`, `aria-hidden` em ícone
   decorativo, contexto de campo amarrando rótulo e controle.

### 9.2 Densidade

**Média para confortável.** Corpo de 14px, gap padrão de 8px, botão médio com
40px de alvo, raio de 8–12px, input com 10px de padding vertical. Alvo de
toque respeitado até no tamanho `tiny` (24px).

Não é densidade de app profissional de foto (Lightroom, Capture One: 11–13px,
gap de 4px, raio de 4px, alvo de 20px). É densidade de **aplicação web
multiplataforma que também roda no telefone** — coerente com a origem ter um
app Flutter irmão e 55 rotas de navegador.

### 9.3 Iconografia

Material Design Icons via `@mdi/js`, **como dados** (path SVG), não como
fonte nem componente. Traço uniforme, cheio, sem variação de peso, ~24px de
grid nominal renderizado a 16px na maioria dos controles. Ícone decorativo
sempre `aria-hidden`. Ícone semântico tem mapa fixo por cor — no toast:
sino=primary, octógono=danger, informação=info, alerta=warning, check=success.

### 9.4 Uso de imagem

- Miniatura desenha **thumbhash** (hash visual de ~25 bytes) como placeholder
  antes do arquivo chegar — a grade nunca pisca branco nem salta.
- Grade justificada calculada em **WebAssembly**
  (`@immich/justified-layout-wasm`): linhas de altura constante e larguras
  variáveis que respeitam a proporção original. Nada de recorte quadrado.
- Fundo do visualizador é preto puro; o chrome vira overlay sobre a imagem,
  com sombra de texto (`text-shadow` duplo) e `drop-shadow` no ícone para
  legibilidade sobre foto arbitrária.
- Fundo xadrez dedicado (`AlphaBackground`) para imagem com transparência.

### 9.5 Tom de voz

Inglês, imperativo curto, sentence case, sem ponto final em rótulo. Chaves de
tradução por ação (`add_a_description`, `add_to_album`), reticências
tipográficas (`…`, não `...`) em ação que abre diálogo. Sem primeira pessoa,
sem exclamação, sem humor. Interpolação por ICU MessageFormat com plural
correto. **Nenhuma string literal em componente** — tudo passa por i18n, e o
design system carrega o próprio serviço de tradução.

---

## 10. O que é porte e o que é reescrita

| Camada | Origem | Destino | Veredito |
|---|---|---|---|
| Rampa + aliases de cor | custom properties CSS | custom properties CSS | **porte direto** — valores e estrutura atravessam sem tradução |
| Espaçamento, raio, breakpoint | `@theme` Tailwind 4 | `@theme` Tailwind 4 | **porte direto** — mesma versão do Tailwind |
| Escala de tamanho `tiny→giant` | tabela em JS | tabela em TS | **porte direto** — é dado, não código |
| Fórmula `color × variant` | `tailwind-variants` | precisa de equivalente | **reimplementação trivial** — a fórmula é a spec, a lib é detalhe |
| Estados (disabled/loading/focus/invalid) | contrato de props | contrato de props | **porte de contrato**, implementação nova |
| Componentes (41 arquivos) | Svelte 5 runes + `bits-ui` | React 18 | **reescrita integral** — `$props`, `$derived`, snippets e `bind:` não têm tradução mecânica; `bits-ui` é headless de Svelte |
| Contexto de campo | contexto do Svelte | contexto do React | **reimplementação** — mesmo padrão, API diferente |
| Motion | `svelte/transition` | precisa de equivalente | **reimplementação** — durações e easings portam, o mecanismo não |
| Ícones | `@mdi/js` | idem (dependência nova) | **porte direto**, mas é dependência a aprovar |
| Fontes GoogleSans | TTF variável no repo | — | **não portar sem checar licença do arquivo de fonte** |
| Escala de z-index | ad-hoc | — | **não portar** — é dívida, não sistema |
| Grade justificada em WASM | `@immich/justified-layout-wasm` | — | fora do escopo de design system; decidir no inventário funcional |

**Onde este documento contradiz o destino.** O Foto Organizer tem direção de
arte registrada em `docs/DIRECAO_DE_ARTE.md` e decisão D-017 em
`docs/DECISOES.md`: dark-only, fundo `#08090a`, painéis translúcidos em branco
a 2–8%, **sem acento cromático**, corpo a 13px, referência Linear — com
rejeição explícita da paleta anterior por "parecer site com tema escuro".

A origem é o oposto em cinco pontos: acento índigo presente em toda a
interface, light+dark com paridade, superfícies sólidas em rampa neutra, corpo
a 14px, raio de 8–12px. Adotar a linguagem visual inteira **reverte** aquela
decisão; adotar só a arquitetura (rampa → alias → tema, fórmula de variante,
contrato de estados, escala de tamanho ortogonal) a **reforça**, porque é
exatamente o que falta no `index.css` atual, que declara aliases sem rampa por
trás.

A escolha entre as duas é sua e vira a primeira seção do `plano-refactor.md`.
