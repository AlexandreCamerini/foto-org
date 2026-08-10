# Plano de refactor — porte do APP_ORIGEM para o Foto Organizer

Branch: `refactor/design-port`. **Nenhum código escrito.** Este documento é o
que se aprova antes da Fase 4.

## Premissas

Duas, assumidas do "pode seguir com sua proposta". Se alguma estiver errada, a
seção correspondente é reescrita — nada mais.

1. **Seleção funcional:** A1 A2 A3 A4 A7 A8 A9 + B2 B4.
2. **Design:** portar **só a arquitetura de tokens**, não a linguagem visual.
   D-017 e `docs/DIRECAO_DE_ARTE.md` permanecem em vigor: dark-only, fundo
   `#08090a`, superfícies translúcidas, sem acento cromático, 13px. Nenhum
   valor de cor do Immich entra.

## Correções ao inventário da Fase 2

A leitura do código do destino desmentiu quatro linhas do inventário. Ficam
registradas porque mudam esforço e valor do que foi escolhido.

| Item | O inventário dizia | O código diz | Efeito |
|---|---|---|---|
| **A6** modelo de tempo de dois instantes | "trazer" | **já implementado** — `data_capturada` + `data_capturada_utc` em `models/catalog.py:169-200`, com comentário citando `03-modelo-de-dados.md §3` | **sai da lista.** Não estava na seleção; a nota existe para o registro |
| **A1** precedência de data | "trazer" (introdução) | **já existe com 6 tags** — `metadata/exiftool.py:266-270`, incluindo `IPTC:DateCreated` com justificativa própria | vira **ampliação de 6 → 10**. Esforço menor, ganho menor |
| **A3/A4** XMP e IPTC | "hoje 100% ignorados" | **XMP e IPTC embutidos já são capturados** em `MediaMetadata.extras` → `MetadataEntry` (namespaces `xmp`/`iptc`, `models/catalog.py:309`). O que falta é (i) o **arquivo `.xmp` irmão**, que o scanner não enxerga, e (ii) o **uso na decisão** | escopo muda de "extrair" para "descobrir o sidecar + consumir" |
| **A3/A4** natureza do sinal | "curadoria humana, confiança alta" | **é Aftershoot** — culling automático (`docs/INVENTARIO_DE_SINAIS.md §2`). `Selected`/`Blurred`/`Duplicates` são julgamento de máquina | **confiança média, não alta.** Erro meu. Entra como evidência de origem `xmp_sidecar`, nível médio |
| **B4** stacks | "trazer" | `DuplicateLevel.SEQUENCIA` e `DuplicateRole.VERSAO` (`models/duplicates.py:17,25`) já cobrem rajada e variante | escopo reduz a **RAW+JPEG do mesmo clique**, que hoje não é agrupado |

---

# Parte 1 — Design

## 1.1 Gap analysis, medido

Contagens sobre `webapp/src` (17 componentes, 64 `<button>`):

| Dimensão | Destino hoje | Origem | Diagnóstico |
|---|---|---|---|
| **Primitivos** | **zero.** 64 `<button>` crus | Button, IconButton, Field, Text, Icon | **o gap principal** |
| Duplicação de estilo | `rounded-md border border-borda bg-cartao px-3 py-1 hover:border-acento disabled:opacity-50` repetido **6×** com divergências (`px-2`/`px-3`/`px-2.5`, `w-full`, `shrink-0`) | uma tabela de variantes | idem |
| Escala de tamanho | **não existe** | `tiny→giant` ortogonal a cor e forma | falta |
| Tipografia | `text-[11px]` 12×, `text-[15px]` 4×, `text-lg` 2×, `text-2xl` 2× + `13px`/`11px` no CSS | 5 degraus nomeados | **valores arbitrários, sem escala** |
| Raio | `rounded-md` 61× · `rounded` 21× · `rounded-full` 2× · `rounded-sm` 1× + 6px/5px/4px soltos no CSS | mapeado por componente | **4 valores, nenhuma regra** |
| Espaçamento | `gap-2` 29× · `gap-1.5` 9× · `gap-1` 7× · `gap-3` 4× | 4/8/16 dominante | **saudável**, só não é nomeado |
| Cor | 18 aliases, **27 pares em uso**, 1 hardcoded (`rgba(255,255,255,.04)`) | rampa → alias → tema | **aliases sem rampa**; um degrau por papel |
| Estado | `disabled` 32× · `aria-disabled` **0** · `cursor-not-allowed` **0** | contrato completo | **estado visual sem estado semântico** |
| Foco | regra global em `index.css` | por componente | **destino está melhor** — cobre tudo por padrão |
| Motion | **3 transições no app inteiro**, nenhum token | 5 durações, 4 easings | falta |
| Sombra | 1 uso | 61 usos, raros por escolha | **destino está melhor** — coerente com superfície translúcida |
| Tema | dark-only por decisão | light+dark | **não é gap.** É D-017 |

Duas linhas onde o destino já está à frente e que **não podem regredir**: foco
global e ausência de sombra. A superfície translúcida a 2/5/8% já é uma rampa
neutra — mais adequada a esta direção de arte que a rampa sólida do Immich.

**Onde a Fase 1 exagerou:** propus levar a rampa de 11 degraus. Errado aqui. A
rampa do Immich existe porque ele tem dois temas e cores saturadas. O destino
é dark-only com estados dessaturados, e o Tailwind 4 já resolve `bg-erro/10`
sobre qualquer cor. **A fórmula é o ativo; a rampa seria over-engineering.**

## 1.2 Mapeamento token-a-token

Nenhum valor de cor muda. O que entra é estrutura.

| Camada | Origem | Destino hoje | Proposta | Novo? |
|---|---|---|---|---|
| Superfície | `light` → `light-100` → `light-200` | `painel` 2% → `cartao` 5% → `realce` 8% | **manter**; documentar como escala de 3 degraus | não |
| Borda | `default-border` global | `borda` 10% / `borda-forte` 18% | **manter** | não |
| Texto | `dark` / `muted` | `texto` / `texto-2` / `texto-3` | **manter** (3 degraus > 2) | não |
| Estado | 5 famílias × 11 degraus × 2 temas | `atencao` `herdado` `ok` `erro` — 1 degrau | **manter os 4 valores**; adicionar a **fórmula de opacidade** | fórmula |
| Ação | `primary` | `acento` + `texto-invertido` | **manter** | não |
| Tamanho | `tiny…giant` | — | `sm` `md` `lg` (3, não 5 — o app tem 3 densidades reais) | **sim** |
| Tipografia | `text-xs…text-xl` | `[11px]` `13px` `[15px]` avulsos | `--text-micro:11px` `--text-base:13px` `--text-realce:15px` | **sim** |
| Raio | por componente | 4 valores soltos | `--radius-controle:6px` `--radius-painel:8px` + `full` | **sim** |
| Motion | 5 durações + 4 easings | nenhum | `--dur-micro:100ms` `--dur-padrao:150ms` `--dur-entrada:250ms`, easing `ease-out` | **sim** |
| Elevação | 6 níveis | 1 uso | **não criar token.** Superfície translúcida já resolve | — |

### A fórmula, adaptada à direção de arte do destino

```
solido   → bg: acento          texto: texto-invertido    hover: opacity 90%
contorno → bg: cartao          texto: texto   borda: borda   hover: borda-forte
fantasma → bg: transparente    texto: texto-2            hover: bg cartao
estado   → bg: <estado>/10     texto: <estado>   borda: <estado>/40
```

As três primeiras **já são o que os 64 botões fazem à mão** — a proposta é
nomear o que já existe, não introduzir aparência nova. A quarta é a única
novidade, e é o que hoje falta para um erro parecer erro sem virar caixa
vermelha.

## 1.3 Onde "porte" vira reescrita

| Camada | Veredito |
|---|---|
| Valores de token | **nada a portar** — o destino fica com os dele |
| Estrutura `@theme` | **porte direto** — mesmo Tailwind 4 |
| Fórmula variante | **reimplementação** — 4 linhas de spec, sem lib |
| Contrato de estados | **porte de contrato** |
| Componentes Svelte | **reescrita integral** — mas só 3 primitivos, não 41 |
| `tailwind-variants` / `tailwind-merge` | **não adotar.** Dependência nova para 3 componentes não se paga; `clsx` manual resolve |
| `bits-ui` | **não adotar** — headless de Svelte |
| Motion | **reimplementação** — durações portam, mecanismo não |
| `@mdi/js` | **não adotar** — o destino não usa ícone de biblioteca hoje |
| z-index | **não portar** — é dívida do origem |

---

# Parte 2 — Funcional

## 2.1 Onde cada item selecionado aterrissa

| # | Toca | Migração? | Esforço |
|---|---|---|---|
| A1 | `metadata/exiftool.py:266`, `metadata/purepython.py` | não | baixo |
| A2 | `metadata/exiftool.py`, `metadata/base.py` | não — colunas existem | baixo |
| A3 | `scanner/scanner.py` (descobrir irmão), `metadata/exiftool.py` (ler par + fundir), `metadata/base.py` | não | **médio-alto** |
| A4 | `metadata/exiftool.py`, `models/tagging.py` (existe), `classification/engine.py` | talvez (origem da tag) | médio |
| A7 | `metadata/exiftool.py` (`ContentIdentifier`), `duplicates/`, `grouping/` | provável (par foto↔vídeo) | médio |
| A8 | `duplicates/resolucao.py`, `models/duplicates.py` | não | baixo |
| A9 | `duplicates/resolucao.py` | não | baixo |
| B2 | `server/jobs.py`, `models/catalog.py`, nova migração | **sim** | médio |
| B4 | `duplicates/`, `models/duplicates.py` | provável | baixo (escopo reduzido) |

## 2.2 Efeito composto sobre a localização compartilhada

A1+A2+A7 não são três melhorias soltas — atacam a mesma cadeia:

```
data mais exata (A1: +SubSec, +GPSDateTime)
  → Δt mais exato até a doadora
    → raio_incerteza(Δt) menor  [correlacao.py:295]
      → círculo menor no mapa, mesma honestidade

fuso declarado (A2: OffsetTimeOriginal, 1.527 fotos)
  → estimar_offsets ganha âncora real  [correlacao.py:142]
    → menos fotos caem no fallback de mtime
      → menos herança penalizada pelo 0.6  [correlacao.py:44-47]

vídeo da Live Photo (A7)
  → doadora nova onde a foto não tem GPS
    → mais fotos com lugar estimado
```

O terceiro é o único que aumenta **cobertura**; os dois primeiros aumentam
**precisão**. Convém medir os três separadamente — ver §2.4.

## 2.3 Ordem de execução

Sete blocos. Cada um é uma fatia vertical fechada, com `pytest` verde e
screenshot quando toca UI, no método de `docs/METODO_DE_TRABALHO.md`.

| Bloco | Conteúdo | Por que aqui |
|---|---|---|
| **1** | Tokens: tipografia, tamanho, raio, motion no `@theme`. **Sem tocar componente.** | Reversível, isolado, e nada quebra se parar aqui |
| **2** | 3 primitivos (`Botao`, `Campo`, `Texto`) + fórmula de variante. Migrar **2 componentes** como prova. | Prova de conceito antes de 17 arquivos |
| **3** | Migrar os 15 restantes; eliminar `rgba` hardcoded; `aria-disabled` + `cursor-not-allowed`. | Mecânico depois que o bloco 2 fixa o padrão |
| **4** | A1 + A2 (data e fuso) **atrás de flag**, com script de medição do delta. | Muda dado gravado — precisa de número antes de virar padrão |
| **5** | A8 + A9 (duplicatas). | Baratos, isolados, sem migração |
| **6** | A3 + A4 (sidecar `.xmp` + keywords). | O mais caro; depende do bloco 4 para não misturar mudança de data |
| **7** | A7, B2, B4. | Cada um pede migração; ficam por último |

Blocos 1–3 são design e não tocam Python. Blocos 4–7 são funcionais e não
tocam token. **Podem ser aprovados e executados independentemente** — se você
quiser só o design, pare no 3.

## 2.4 Critérios de aceite verificáveis

| Bloco | Aceite |
|---|---|
| 1 | `pnpm build` verde; `vitest` verde; screenshot idêntico ao atual — token novo sem consumidor **não pode** mudar pixel |
| 2 | 2 componentes migrados, `<button>` cru cai de 64 para ≤58, testes verdes |
| 3 | `<button>` cru = 0; `grep rgba(` em `.tsx` = 0; `aria-disabled` presente em todo controle desabilitado; screenshot sem regressão |
| 4 | Script mede **quantas fotos mudam de data** e **de quanto**; herança recalculada com raio médio **antes vs depois**; nenhuma foto perde data |
| 5 | Grupo de duplicata com metadado divergente preserva o do descartado; principal escolhida por contagem de EXIF quando o tamanho empata |
| 6 | Os 605 sidecars descobertos; 599 viram evidência nível **médio**, origem `xmp_sidecar`; **zero** duplicação com o que `sources/lightroom.py` já importou |
| 7 | Par Live Photo unificado sem perder o vídeo do catálogo (invariante 8); estado de pipeline sobrevive a reinício |

---

# Parte 3 — Riscos e dívida

Sem suavizar.

## 3.1 Riscos que podem custar caro

**R1 — A1/A2 mudam datas já gravadas, e a data é a espinha do app.**
Data alimenta ordenação, agrupamento temporal, viagens, eventos, correlação de
GPS e sugestões **já revisadas e aprovadas** pelo dono. Mudar a precedência
reclassifica retroativamente. Uma sugestão aprovada com a data antiga pode
passar a apontar para outra pasta sem ninguém pedir.
*Mitigação:* flag, `versao_logica` nova na evidência preservando a anterior,
medição do delta antes de virar padrão, e **decisão explícita sua** sobre o que
fazer com sugestões aprovadas que mudarem. Não decido isso sozinho.

**R2 — A3 pode duplicar curadoria.**
`sources/lightroom.py` já importa catálogo Lightroom. Os 605 `.xmp` vieram do
mesmo fluxo. Ler os dois caminhos sem checar interseção soma confiança sobre a
mesma afirmação — exatamente o que `docs/CONFIANCA.md` proíbe.
*Mitigação:* medir a interseção **antes** de escrever o parser. Se for alta, A3
vira deduplicação, não ingestão.

**R3 — A confiança do sinal XMP é menor do que eu disse na Fase 2.**
É Aftershoot, não olho humano. `Blurred` e `Duplicates` são julgamento de
máquina sobre qualidade. Entrar como confiança alta contaminaria a badge, que é
o principal ativo de credibilidade da interface.
*Mitigação:* nível médio, origem `xmp_sidecar`, justificativa dizendo que a
origem é culling automático.

**R4 — Migrar 17 componentes de uma vez quebra a UI toda de uma vez.**
*Mitigação:* é a razão do bloco 2 existir separado do 3.

**R5 — O bloco 1 pode mudar pixel sem querer.**
Token novo com nome que colide com utilitário Tailwind existente muda render
silenciosamente.
*Mitigação:* o aceite do bloco 1 é screenshot **idêntico**. Se mudou, o nome
está errado.

**R6 — B2 troca a fonte de verdade do progresso.**
`JobManager` guarda estado em memória (`server/jobs.py:50`). Mover para o banco
muda o que a UI lê e como a retomada funciona. Feito errado, quebra
`RetomarScan.tsx`.
*Mitigação:* último bloco, migração própria, teste de reinício.

## 3.2 Dívida que este plano cria

- **Três primitivos não são um design system.** Modal, tabela, menu e toast
  continuam ad-hoc. Aceitável — o app tem 17 componentes, não 411 — mas é
  dívida, e vai reaparecer quando a UI crescer.
- **A fórmula de variante fica em código, não em teste.** Sem um teste que
  falhe quando alguém escrever `bg-erro` sem `/10`, a regra decai. Não vou
  propor um lint novo: é escopo além do pedido. Fica declarado como dívida.
- **A escala de tipografia legaliza `15px`**, que veio de Linear e não de app
  Mac (13px). Nomeá-la torna mais difícil questioná-la depois.
- **A2 não resolve fuso `+00:00` real** — indistinguível de desconhecido, como
  o próprio `models/catalog.py:180-186` já documenta. `tz_estimado` continua
  pendente, e este plano não o entrega.

## 3.3 Dívida que este plano NÃO paga (e não deveria)

Fora de escopo por decisão, não por esquecimento: fase 11 (fuso estimado),
D-038, empacotamento Tauri, os itens da faixa B não selecionados (B1, B3,
B5–B10), e toda a faixa C.

---

## O que acontece na Fase 4

Ao aprovar: bloco por bloco, diff impresso, checkpoint entre blocos, sem
commit sem seu ok. Se quiser só parte, diga quais blocos — eles são
independentes por construção.

**Uma pergunta que preciso responder antes do bloco 4** e que não posso
decidir por você: sugestões **já aprovadas** cujo destino mude por causa da
nova data — reabrir para revisão, ou congelar no que foi aprovado?
