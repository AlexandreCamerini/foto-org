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

## Tokens (tema QSS dark-first)

- Superfícies: fundo janela `#1E1E1E`, painéis `#252526`, cartões `#2D2D30`,
  bordas `#3E3E42` (1px, sem sombras pesadas).
- Texto: primário `#E8E8E8`, secundário `#9DA0A6`, desabilitado `#6B6E76`.
- Acento único (seleção, foco, progresso): azul `#3B82F6`. Não usar o acento
  para decoração.
- Semântica de confiança (badges discretos, nunca % cru na grade):
  alta `#34D399`, média `#FBBF24`, baixa `#F87171` — sempre com rótulo
  textual ("Alta/Média/Baixa") para acessibilidade.
- Tipografia: fonte do sistema (SF Pro via `-apple-system`); corpo 13px,
  secundário 11px, títulos de painel 11px uppercase tracking largo.
- Espaçamento em grade de 8pt (4/8/12/16/24). Cantos 6px. Miniaturas com
  gap de 8px e seleção por contorno de 2px no acento, não por overlay.

## Comportamentos que definem a classe

- Grade sempre fluida: placeholders cinza enquanto thumbs carregam; nunca
  travar a UI por I/O.
- Progresso persistente e honesto na barra de status (nada de spinners
  modais durante o scan).
- Ações destrutivas nem existem no MVP; ações físicas passam por tela de
  plano com diff origem→destino.
- Toda sugestão tem um "por quê?" a um clique (popover com evidências).
- Estado vazio bonito: primeira execução guia direto para "Adicionar pasta".
