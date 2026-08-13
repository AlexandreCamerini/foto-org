# Item A — filtro composto sobre proveniência

Staging pronto para integrar quando a fase 5 abrir a fronteira de
`fotoorganizer/**` e `webapp/src/**`. Nasce de
`docs/prompts/fase-14-photoprism-e-sintese.md` §3 e do schema real lido
nesta sessão — nenhuma linha vem dos repositórios de referência em si
(ambos AGPLv3), só da descrição de mecanismo já registrada em
`docs/referencia-photoprism/`.

## O que existe hoje (evidência)

- `fotoorganizer/repositories/media.py:54-66` — `LACUNAS`, 12 predicados de
  escolha única (`_condicao_lacuna`, `:69-110`), aplicados em `:240-241`
  dentro de `_query`. `MediaFilters` (`:131-166`) é um `dataclass` de 15
  parâmetros fixos — cada faceta nova exige um campo novo na classe, um
  parâmetro novo no endpoint e uma condição nova no `if`.
- `fotoorganizer/server/app.py:565-583` — os mesmos 15 parâmetros repetidos
  como argumentos de `GET /api/midia`.
- `webapp/src/App.tsx:83` (`useState<Recorte | null>`, comentado "Um só") —
  o recorte vindo de outra aba é um único `useState` no componente. Não há
  `searchParams`, `pushState` nem `localStorage` em `webapp/src/`
  (confirmado por grep nesta sessão: zero ocorrências). Um F5 apaga o
  recorte.
- `fotoorganizer/models/inference.py:39-58` — `Evidence.origem`, `.nivel`,
  `.score`, `.justificativa`, `.versao_logica`: dado que nenhum filtro atual
  alcança, porque os 15 parâmetros fixos filtram `MediaFile`, nunca
  `Evidence`.
- `fotoorganizer/models/catalog.py:45-61` — `MediaRole.ACERVO/SINAL`
  (D-024): também fora do vocabulário de filtro hoje.

## O que este item entrega

`lib.py`:

- `FiltroProveniencia` — dataclass imutável, única fonte de verdade
  (`confianca`, `origem`, `papel`, `lugar`, `busca`).
- `parse(texto) -> FiltroProveniencia` — tokeniza com `shlex` (aspas escapam
  espaço), reconhece `chave:valor` para o vocabulário fechado
  (`confianca`, `papel`, `lugar`) e livre para `origem`; qualquer outro
  token vira busca livre. Campo desconhecido, valor fora do vocabulário,
  campo repetido ou aspas não fechadas levantam `FiltroInvalido` com o
  token exato — nunca falha em silêncio.
- `serialize(filtro) -> texto` — inverso de `parse`, com ordem de campo
  fixa (`_ORDEM_CAMPOS`) para o mesmo recorte lógico sempre produzir a
  mesma string, não importa a ordem em que os controles de UI o
  construíram.
- `com_campo(filtro, campo, valor)` — o caminho que um chip/dropdown da UI
  usaria para escrever no mesmo objeto que a caixa de texto edita, sem
  criar um segundo estado.
- `para_condicoes(filtro) -> tuple[Condicao, ...]` — o recorte vira N
  predicados abstratos (campo, operador, valor, tabela-alvo), sempre em
  AND implícito. Não depende de SQLAlchemy nem do ORM do foto-organizer —
  é a prova, testável isoladamente, de que a composição funciona antes de
  tocar `repositories/media.py`.

## Decisões (Classe A, ver também `docs/DECISOES.md`)

1. **Sem `!` (negação) nem `|` (OU) nesta versão.** A seção 6 do prompt de
   origem recomenda cortar isso do escopo inicial e medir depois se algum
   recorte salvo pediu os dois. Conjunção pura de tokens + texto livre
   resolve o caso citado no prompt ("confiança baixa e sem câmera
   identificada").
2. **Tokenização via `shlex`, não parser caractere a caractere.** O prompt
   de origem pede explicitamente para não portar
   `internal/form/serialize.go:80-191` (mecanismo descrito em
   `docs/referencia-photoprism/`) — biblioteca padrão testada entrega o
   mesmo contrato com menos borda de manutenção.
3. **`origem` é vocabulário aberto.** No schema, `Evidence.origem` é
   `Mapped[str]` livre (`models/inference.py:50`), não um enum — o parser
   não trava a lista de origens possíveis (`exif`, `pasta`, `vizinhanca`,
   `usuario`, `geocoding`, ...), só a reconhece como token estruturado.
4. **`confianca`/`papel`/`lugar` normalizam para minúsculo; `origem`
   preserva a caixa digitada.** Os três primeiros são enum fechado
   (`ConfidenceLevel`, `MediaRole`, e o par estimado/medido); `origem` é
   texto livre do schema e comparação de caixa é decisão de quem compõe o
   predicado real, não deste parser.

## Onde plugar quando a fronteira abrir

- `fotoorganizer/repositories/media.py`: `MediaFilters` ganha um campo
  novo, por exemplo `proveniencia: str | None = None`. Dentro de `_query`
  (`:173-244`), decodificar com `parse(filters.proveniencia)` e traduzir
  cada `Condicao` de `para_condicoes` para SQLAlchemy real — `confianca` e
  `origem` viram subconsulta contra `Evidence` no mesmo padrão de
  `_condicao_lacuna` (`:69-110`, que já usa `MediaFile.id.in_(select(...))`
  para não inflar contagem quando a mídia tem mais de uma sugestão/
  evidência); `papel` e `lugar` são coluna direta de `MediaFile`
  (`papel`, `gps_lat_estimado`/`gps_lat`).
- `fotoorganizer/server/app.py`: `GET /api/midia` (`:565-583`) ganha um
  parâmetro `proveniencia: str | None`, validado com `parse()` antes de
  virar `MediaFilters` — erro de sintaxe vira HTTP 422 com a mensagem de
  `FiltroInvalido`, no mesmo padrão que `lacuna`/`alcance` já usam
  (`:585-588`).
- `webapp/src/App.tsx`: fora do escopo deste item (fronteira de
  `webapp/src/**` continua fechada), mas o ponto de entrada é o mesmo
  `useState<Recorte | null>` de `:83` — trocar por `searchParams` que
  serializa/desserializa com o par acima é o que resolve "recorte morre no
  F5", citado como motivação no prompt de origem.

## Limitações declaradas

- `para_condicoes` não força `confianca` e `origem` a mirarem a MESMA linha
  de `Evidence` quando os dois aparecem juntos — hoje cada um filtra
  independentemente, podendo casar com evidências diferentes da mesma
  mídia. Documentado como comportamento aceito neste MVP, não bug
  escondido; corrigir exigiria uma subconsulta conjunta em vez de duas.
- Sem OU/negação (decisão 1 acima) — void de propósito, não esquecimento.
