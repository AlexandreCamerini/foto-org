# Direção de arte

Referências: Adobe Lightroom Classic (layout e densidade), Apple Fotos
(clareza e navegação), Mylio Photos (organização por fontes/calendário),
Peakto (catálogo unificado), Photo Mechanic (velocidade/teclado no loupe),
Aftershoot/Narrative (survey de rajadas). Regra de ouro dos apps dessa
classe: **a foto é a cor da interface** — o chrome é neutro, escuro e
silencioso.

Este documento é a spec das DUAS UIs (webapp React, principal; PySide6,
fallback): mesmos tokens, mesmo layout de 3 painéis. No webapp os tokens
vivem em `webapp/src/index.css` (@theme) e devem espelhar os valores
abaixo.

## Layout (3 painéis, estilo Lightroom)

```
┌──────────┬──────────────────────────────┬───────────────┐
│ Sidebar  │  Grade de miniaturas          │  Inspetor     │
│ Fontes   │  (virtualizada, slider de     │  Preview      │
│ Filtros  │   tamanho no rodapé)          │  Metadados    │
│ Álbuns/  │                               │  Sugestão +   │
│ Sugestões│                               │  evidências   │
├──────────┴──────────────────────────────┴───────────────┤
│ Barra de status: scan, arquivos/s, erros, itens fila     │
└──────────────────────────────────────────────────────────┘
```

- Sidebar e inspetor recolhíveis. Atalhos: **`[` e `]`** no webapp, com
  ⌘1/⌘3 valendo em paralelo — o navegador reserva ⌘1–⌘8 para trocar de
  aba e nunca entrega essas teclas à página, então ⌘1/⌘3 só passam a
  funcionar no app empacotado (Tauri). Duplicatas usam vista lado a lado
  (compare) no lugar da grade.
- O inspetor descreve a foto selecionada: existe na Biblioteca, não nas
  telas que não têm grade.
- A barra de status atravessa a janela inteira, abaixo dos três painéis, e
  é a mesma em todas as abas — o trabalho em background continua rodando
  quando o usuário troca de tela, e o progresso precisa continuar visível.
- Revisão de sugestões é uma lista com origem → destino e badges, não um
  formulário.

## Tokens (webapp — fonte de verdade; ver nota sobre o QSS abaixo)

Esta seção substitui a paleta anterior (fundo `#1E1E1E`, painéis sólidos em
degradê de cinza, acento azul `#3B82F6`). Essa paleta era "site com tema
escuro": cinza sólido pinta superfície própria em vez de deixar a foto
comandar a cor, e um azul saturado decora a UI inteira em vez de significar
só estado. O webapp abandonou-a de propósito (D-017, `docs/DECISOES.md`;
levantamento em `docs/REFERENCIAS_DESIGN.md`) — este documento estava
desatualizado, não o código. Os valores abaixo são os reais de
`webapp/src/index.css` (bloco `@theme`).

- **Superfícies não têm cor própria.** Fundo da janela `#08090a`
  (quase-preto, não cinza). Painel, cartão e realce são branco em opacidade
  baixa *sobre* esse fundo — `rgba(255,255,255,.02)` (painel),
  `rgba(255,255,255,.05)` (cartão), `rgba(255,255,255,.08)` (realce),
  bordas `rgba(255,255,255,.1)` / `.18` na forte. Opacidade module o que
  está atrás em vez de competir com a foto; é o mecanismo que faz "a foto é
  a cor da interface" ser código, não intenção. 1px, sem sombras pesadas.
- **Texto**: primário `#f7f8f8`, secundário `#8a8f98`, terciário/desabilitado
  `#62666d`.
- **Acento único, dessaturado**: `#d6d9dd` (quase-branco, não azul) para
  seleção, foco e progresso. Continua reservado a estado — nunca decoração
  — mas agora o próprio "não ter cor" é o que garante isso: um acento
  cromático fixo compete com qualquer foto atrás dele.
  - Texto sobre um botão de acento (`bg-acento`) precisa do token
    `--color-texto-invertido` (= cor da janela, `#08090a`), não branco: o
    acento é claro, e texto quase-branco sobre um fundo quase-branco é
    ilegível. Contraste medido `#08090a` sobre `#d6d9dd` ≈ 14:1 (AAA).
- **Confiança é quantidade, não semáforo** (D-017): alta e média não têm
  cor própria — são segmentos preenchidos (ver componente `Confianca`).
  Só a confiança baixa/atenção usa cor, âmbar `#c2833a`, porque é o único
  caso que pede "olhe aqui". Outros estados semânticos, todos dessaturados
  na régua de "cor só quando significa algo": herdado `#6e8fa8`,
  ok `#6e9a78`, erro `#a8615a`. Sempre com rótulo textual junto ("Alta" /
  "Média" / "Baixa"), nunca só cor — regra de acessibilidade, não estética.
- **Tipografia**: fonte do sistema (`-apple-system, BlinkMacSystemFont,
  "SF Pro Text"`); corpo 13px, secundário 11px, títulos de painel 11px
  uppercase com tracking largo (`.titulo-painel`). Confirmado batendo com
  `index.css` — nenhuma mudança aqui.
- **Espaçamento em grade de 8pt** (4/8/12/16/24). Cantos 6px (`rounded-md`
  no Tailwind do webapp — não `rounded-lg`, que é um raio maior e destoa
  do resto). Miniaturas com gap de 8px e seleção por contorno de 2px no
  acento (`outline-acento`), não por overlay nem sombra.

### Nota sobre o QSS (PySide6, em remoção)

`fotoorganizer/ui/theme.py` ainda usa a paleta antiga (cinza sólido, azul
`#3B82F6`) porque pertence à UI legada que está a caminho de sair inteira,
não em pedaços — ver CLAUDE.md. Não portar os tokens novos para lá: seria
esforço em código que vai ser removido, e as duas UIs divergindo já é o
estado esperado até a remoção.

## O mapa do lugar (webapp, `components/Mapa.tsx`)

A tela não tem cartografia (D-031): é geometria sobre uma malha, e a cor vem
da UI, não da foto. Por isso a régua aqui é contraste e hierarquia, e a
linguagem — decidida em `docs/prototipos/03-mapa-local-estimado.html` — é
"cheio × vazado". Ela só funciona se as duas formas forem distinguíveis num
relance:

- **Ponto cheio**, raio 5, `--color-texto`: coordenada lida do arquivo.
- **Anel tracejado**, `--color-herdado`, preenchimento a 7%: lugar herdado,
  e o raio é a dúvida. **Piso de 10** no raio, não 7: o anel precisa passar
  longe do ponto de 5, senão vira franja e a distinção morre. Medido em
  "Dubai, Thai & Viet", onde os 30 lugares caem todos no piso.
- **Seleção**: anel de `--color-acento`, 2px, afastado 8 do desenho — colado
  ele lê como traço duplo e some qual dos dois é a dúvida.
- **"×N" é um número por ponto visível**, 11px/500 em `--color-texto-2`
  (`--color-texto` quando selecionado), ancorado no PONTO (não na borda do
  círculo da dúvida) e nunca sobre outro ponto. Rótulo que fica mais perto do
  ponto do vizinho do que do seu é omitido: número no ponto errado é
  informação falsa, e o painel diz tudo a um clique. Quando um grupo tem
  lugares calados por isso, o painel diz quantos — silêncio explicado não é
  silêncio.
- **O quadro ocupa o painel inteiro** (`h-full` + `meet`, malha maior que o
  viewBox), canto 6px como todo o resto. Um mapa de altura fixa deixava faixa
  preta entre ele e o rodapé, que lê como tela inacabada.
- **Miniatura de 40×30 usa a variante densa** da `Miniatura` (só o glifo ⊘): a
  frase do motivo não cabe em 30px de altura e vazava para fora da caixa. O
  motivo continua no `title` e para leitor de tela; a linha ao lado já traz
  nome e hora.
- **O número não soma lugares vizinhos na tela.** Em "Dubai, Thai & Viet",
  vários lugares — coordenadas distintas, cada uma com sua própria doadora —
  caem perto o bastante na projeção para se tocarem visualmente; o "×N" mostra
  a contagem do lugar dono do ponto, não a soma de quem está perto. Somar
  misturaria a identidade de coordenadas diferentes num número só — é o
  mesmo problema que D-031 já rejeitou (agregação por proximidade de tela não
  é uma correlação real), agora do lado do desenho, não do dado. Quem quer o
  total de uma vizinhança clica cada ponto; o painel não esconde nada.

## Comportamentos que definem a classe

- Grade sempre fluida: placeholders cinza enquanto thumbs carregam; nunca
  travar a UI por I/O.
- Progresso persistente e honesto na barra de status (nada de spinners
  modais durante o scan).
- Ações destrutivas nem existem no MVP; ações físicas passam por tela de
  plano com diff origem→destino.
- Toda sugestão tem um "por quê?" a um clique (popover com evidências).
- Estado vazio bonito: primeira execução guia direto para "Adicionar pasta".
