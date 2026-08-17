---
phase: 04-consist-ncia-visual-secund-ria
plan: 07
subsystem: ui
tags: [react, tanstack-query, fastapi, sqlalchemy, tailwind]

requires:
  - phase: 04-01
    provides: "font-titulo token para o nome do arquivo (a linha do selo reusa, não reintroduz font-medium/font-semibold)"
  - phase: 04-02
    provides: "webapp/src/fontes.ts (rotuloDeFonte/rotulosDeFontes) — a resolução e desambiguação de nome de fonte já existiam, este plano só as consome"
provides:
  - "source_id em cada linha de GET /api/sugestoes (_sugestao_json), tipado em SugestaoRow (api.ts) e no type local Item (Review.tsx)"
  - "Colisão por adjacência (nome+data_capturada+camera, media_id diferente) computada no cliente sobre a lista já buscada de FotosDoGrupo, sem campo novo de API"
  - "Selo neutro com o nome da fonte em cada sugestão colidida na Revisão, com title explicativo, fallback quando source_id não está no cache, e zero requisição nova (cache ['fontes'] compartilhado com App.tsx/Sidebar.tsx)"
affects: [ui, revisao, sugestoes]

tech-stack:
  added: []
  patterns:
    - "Detecção de colisão por adjacência (vizinho anterior/seguinte) computada no cliente sobre uma lista já buscada, em vez de um campo novo de API — quando o sinal de desambiguação já existe no catálogo e só precisa de comparação local"

key-files:
  created: []
  modified:
    - fotoorganizer/server/app.py
    - tests/test_server_api.py
    - webapp/src/api.ts
    - webapp/src/components/Review.tsx
    - webapp/src/components/Review.test.tsx

key-decisions:
  - "Estrutura de commit por task (feat único combinando implementação+teste) em vez do RED/GREEN separado que tdd=\"true\" sugeria — as Tasks 1 e 2 já tinham sido commitadas assim antes da retomada; a Task 3 seguiu o mesmo padrão para manter o histórico do plano consistente."
  - "Critério de aceite 'grep -c text-acento|border-acento retorna 0' do plano é whole-file; o arquivo já tinha um `focus:border-acento` pré-existente (linha 268, input de edição de destino) que a expressão regular casa por substring dentro de `focus:border-acento`. Não é o acento do selo (que não usa nenhuma classe de acento) — é ruído do padrão de grep contra código não tocado por este plano. Não alterado: fora do escopo declarado da Task 3."
  - "Testes novos usam apelido explícito ('Disco A'/'Disco B') em vez de nomes que colidem com outros campos da linha (ex. 'iPhone', que também aparece em `camera`), para manter as asserções de texto inequívocas."

patterns-established:
  - "Selo informativo neutro (border-borda + bg-cartao + text-texto-2, nunca acento) ao lado de um campo truncável: par shrink-0 (selo) + min-w-0 (contêiner flex) é o que permite o texto truncar e o selo sobreviver sem ser espremido a nada."

requirements-completed: [CONS-01]

duration: ~1h10min (incluindo a interrupção de infraestrutura e retomada)
completed: 2026-08-17
---

# Phase 04-07: Selo de fonte por colisão de sugestão (CONS-01) Summary

**Duas sugestões vizinhas com mesmo nome+data+câmera mas media_id diferente agora mostram, cada uma, um selo neutro com o nome da fonte de origem — via um campo aditivo de 1 linha no backend (`source_id`), colisão por adjacência computada no cliente e o cache `["fontes"]` já existente, sem requisição nova.**

## Performance

- **Duration:** ~1h10min de ponta a ponta (11:24 → 12:40), incluindo uma parada de infraestrutura no meio da execução (stream stall, não defeito de plano) e retomada por um agente de continuação no mesmo worktree
- **Started:** 2026-08-17T11:24:43-03:00
- **Completed:** 2026-08-17T12:40:10-03:00
- **Tasks:** 3 (todas `auto`)
- **Files modified:** 5 (`fotoorganizer/server/app.py`, `tests/test_server_api.py`, `webapp/src/api.ts`, `webapp/src/components/Review.tsx`, `webapp/src/components/Review.test.tsx`)

## Accomplishments
- `_sugestao_json` devolve `source_id` (já lido internamente para `motivo_indisponivel`, nunca servido) — o único ponto de contato com o backend da fase inteira, e custou 1 linha de produção.
- `FotosDoGrupo` computa colisão por adjacência (vizinho imediato anterior OU seguinte com mesma chave nome+data_capturada+câmera e `media_id` diferente) sobre a lista já buscada — nenhum campo novo de API, nenhuma requisição nova.
- Linha do nome do arquivo em `Review.tsx` virou uma linha flex com selo condicional: neutro (`border-borda`/`bg-cartao`/`text-texto-2`, sem acento), com `title` explicando a colisão, resolvendo o nome via `rotuloDeFonte(fontes, s.source_id)` sobre o cache `["fontes"]` já compartilhado com `App.tsx`/`Sidebar.tsx`.
- Fallback coberto: `source_id` presente mas ausente do cache de fontes mostra o rótulo de fallback de `rotuloDeFonte` ("fonte") em vez de sumir ou quebrar.

## Task Commits

Cada task foi commitada atomicamente, combinando implementação e teste (não RED/GREEN separado — ver Decisões):

1. **Task 1: source_id na serialização e nos dois tipos do cliente** - `4578929` (feat)
2. **Task 2: Detecção de colisão por adjacência na lista do grupo** - `4c13d1d` (feat)
3. **Task 3: Selo de fonte na linha da sugestão** - `9212859` (feat)

**Plan metadata:** (este commit) - `docs(04-07): SUMMARY do plano 07, CONS-01 fechado`

## Files Created/Modified
- `fotoorganizer/server/app.py` - `"source_id": linha.source_id,` em `_sugestao_json` (1 linha de produção)
- `tests/test_server_api.py` - `test_sugestoes_trazem_source_id_da_fonte_que_catalogou`: trava a presença e o valor correto de `source_id` na resposta de `/api/sugestoes`
- `webapp/src/api.ts` - `source_id: number` em `SugestaoRow`
- `webapp/src/components/Review.tsx` - `source_id?: number` no type `Item`; colisão por adjacência em `FotosDoGrupo`; `useQuery(["fontes"])`; selo condicional na linha do nome
- `webapp/src/components/Review.test.tsx` - describe `"selo de fonte (CONS-01)"`: par colidido mostrando cada selo com o nome correto da própria fonte, item de controle sem colisão sem selo, e fallback quando a fonte não está no cache de `/api/fontes`

## Decisions Made
Ver `key-decisions` no frontmatter. Resumo: (1) commit único por task (feat combinando implementação+teste) em vez do RED/GREEN que `tdd="true"` sugeria, para manter consistência com as Tasks 1/2 já commitadas antes da retomada; (2) o critério de aceite de grep whole-file para `text-acento|border-acento` casa um `focus:border-acento` pré-existente e não relacionado (input de edição de destino) — aceito como ruído do padrão de busca, não como violação real (o selo em si não usa nenhuma classe de acento); (3) fontes de teste usam apelidos ("Disco A"/"Disco B") que não colidem textualmente com outros campos da linha renderizada.

## Deviations from Plan

Nenhuma no conteúdo da implementação — Task 3 seguiu a `<action>` do plano à risca (import de `rotuloDeFonte`, `useQuery(["fontes"])`, linha flex com selo `shrink-0`/`min-w-0`, guarda de `source_id != null`, cor neutra). A única variação foi de processo (estrutura de commit), documentada acima.

## Issues Encountered
- **Parada de infraestrutura na primeira execução:** o agente executor original travou no meio da Task 3 (stream stall de infraestrutura, não um problema de conteúdo ou de plano) com a Task 1 e a Task 2 já commitadas e a Task 3 com implementação (mas não testes) escrita e não commitada no working tree. Um agente de continuação retomou no mesmo worktree, verificou o estado (`git diff`/`git log`), confirmou que a JSX não commitada batia com os critérios de aceite do plano, completou os testes faltantes e seguiu o restante do checklist do plano (verify chain completo, greps de aceite, SUMMARY, `requirements.mark-complete`). Não houve perda de trabalho nem necessidade de descartar código.
- **`.venv` ausente no worktree:** o worktree não tinha `.venv/` próprio (consistente com a nota de memória "worktree precisa de `.venv` e `node_modules` próprios" — `node_modules` já existia, `.venv` não). Recriado com `python3.12 -m venv .venv && pip install -e ".[dev]"`.
- **`osxphotos` ausente após `pip install -e ".[dev]"`, derrubando `tests/test_apple_photos.py::test_video_entra_junto_com_a_foto`:** causa raiz confirmada (não é falha silenciosa do `--quiet`) — `osxphotos` está declarado só no extra opcional `apple` de `pyproject.toml`, não no `dev`, e `scripts/instalar.sh` instala por padrão só `.[dev]`. O teste faz `import osxphotos` bare com um comentário ("pulado abaixo se ausente") que promete um skip que não existe de fato — ao contrário de outro teste no mesmo arquivo (linha ~95), que usa corretamente `pytest.importorskip("osxphotos", ...)`. Ou seja: numa instalação padrão do zero, esse teste específico sempre falharia, independente deste plano. Resolvido localmente instalando `osxphotos` manualmente (extra `apple`, ~80 pacotes de dependência) para poder rodar `scripts/verificar.sh` de ponta a ponta. Bug pré-existente, fora do escopo declarado de `files_modified` desta plano — sinalizado como tarefa separada (`test_06d1b055`, "Corrigir skip ausente em test_video_entra_junto_com_a_foto"), não corrigido aqui.

## User Setup Required
None - nenhuma configuração de serviço externo.

## Next Phase Readiness
- CONS-01 fechado: `scripts/verificar.sh` verde de ponta a ponta (844 testes pytest, 19/19 cenários de benchmark, 145 testes vitest, build do webapp).
- `git diff --stat 383af2f -- fotoorganizer/` confirma exatamente 1 arquivo e 1 linha de produção alterados no backend — a prova de que CONS-01 custou uma linha.
- Sem bloqueios conhecidos para os planos seguintes da fase.

---
*Phase: 04-consist-ncia-visual-secund-ria*
*Completed: 2026-08-17*
