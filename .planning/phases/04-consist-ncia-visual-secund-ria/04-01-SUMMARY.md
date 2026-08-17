---
phase: 04-consist-ncia-visual-secund-ria
plan: 01
subsystem: ui
tags: [tailwind, css-tokens, react, vitest, design-system]

# Dependency graph
requires: []
provides:
  - Token `--font-weight-titulo: 500` no bloco `@theme` de `webapp/src/index.css`
  - Utilitário `font-titulo` (auto-gerado pelo namespace `--font-weight-*` do Tailwind 4)
  - Migração dos 17 call sites de `font-semibold`/`font-medium` para `font-titulo` em 10 arquivos
  - Teste de guarda `webapp/src/design-tokens.test.ts` que quebra a build se `font-semibold`/`font-medium` voltar
affects: [04-02, 04-03, 04-04, 04-05, 04-06, 04-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Peso de ênfase é sempre `font-titulo`, nunca `font-semibold`/`font-medium` — qualquer markup novo do webapp usa o token"

key-files:
  created:
    - webapp/src/design-tokens.test.ts
    - webapp/src/node-builtins.d.ts
  modified:
    - webapp/src/index.css
    - webapp/src/App.tsx
    - webapp/src/components/Loupe.tsx
    - webapp/src/components/Trips.tsx
    - webapp/src/components/Inspector.tsx
    - webapp/src/components/Sidebar.tsx
    - webapp/src/components/Duplicates.tsx
    - webapp/src/components/TemplateEditor.tsx
    - webapp/src/components/Review.tsx
    - webapp/src/components/Operations.tsx
    - webapp/src/components/Mapa.tsx

key-decisions:
  - "Inspector.tsx:38 migrado como todos os outros 16 call sites — D-10 revisado em 2026-08-16 confirma 'migrar tudo' sobre 'tornar a exceção regra'"
  - "Novo token `--font-weight-titulo` em vez de redefinir `--font-weight-medium` — mantém cada call site migrado greppável e um futuro `font-semibold` ad hoc visivelmente desviante"

patterns-established:
  - "Guarda de regressão de design token: teste puro (`node:fs` + `import.meta.url`, sem dependência nova) que remove comentários antes de casar regex, com trava inferior (`toBeGreaterThanOrEqual`) contra 'resolver' apagando em vez de migrar"

requirements-completed: [CONS-08]

# Metrics
duration: ~50min
completed: 2026-08-16
---

# Phase 4 Plan 01: Token de peso de ênfase (CONS-08) Summary

**Token `--font-weight-titulo: 500` criado no `@theme` do Tailwind 4, 17 call sites de `font-semibold`/`font-medium` migrados para o utilitário `font-titulo` gerado por ele, e teste de guarda que falha se o desvio voltar.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3 completed + 1 correção de build-config
- **Files modified:** 12 (2 criados, 10 modificados)

## Accomplishments
- Webapp fecha com exatamente 2 pesos de fonte reais: 400 (corpo, sem classe) e 500 (`font-titulo`)
- Zero `font-semibold`/`font-medium` sobrevivendo em código de produção `.tsx`
- Teste de guarda automatizado (`design-tokens.test.ts`) entra no `npm test`, citando arquivo:linha de qualquer violação futura e ignorando o texto quando aparece só em comentário

## Task Commits

Cada task foi commitada atomicamente:

1. **Task 1: Definir o token `--font-weight-titulo` no `@theme`** - `f4ab976` (feat)
2. **Task 2: Migrar os 17 call sites para `font-titulo`** - `03efcd5` (feat)
3. **Task 3: Teste de guarda do peso único de ênfase** - `5157659` (test)
4. **Deviation fix: tipos ambiente para node:fs/path/url no build** - `ba97a63` (fix)

## Files Created/Modified
- `webapp/src/index.css` - adiciona `--font-weight-titulo: 500` no `@theme`, logo após a escala tipográfica
- `webapp/src/App.tsx` - título de marca "Foto Organizer" (linha 206)
- `webapp/src/components/Loupe.tsx` - nome no cabeçalho (linha 38)
- `webapp/src/components/Trips.tsx` - título do card (linha 151)
- `webapp/src/components/Inspector.tsx` - cabeçalho de nome de arquivo (linha 38) e `ev.campo` (linha 114) — os dois call sites do arquivo, incluindo o que era exceção em D-10 revisado
- `webapp/src/components/Sidebar.tsx` - 4 sites: título "Fonte mudou de lugar" (218), prefixo de reapontamento (241), título "Importar do Apple Fotos" (294), título do `ModalCaminho` (329)
- `webapp/src/components/Duplicates.tsx` - `grupo.rotulo` (134) e nome do membro (186)
- `webapp/src/components/TemplateEditor.tsx` - `ex.destino` (139)
- `webapp/src/components/Review.tsx` - destino no cabeçalho do grupo (201) e nome do arquivo na linha (306)
- `webapp/src/components/Operations.tsx` - coluna destino (286)
- `webapp/src/components/Mapa.tsx` - 2 sites (249, 777)
- `webapp/src/design-tokens.test.ts` (novo) - 3 asserções: token presente no CSS, zero `font-semibold`/`font-medium` fora de comentário, ao menos 17 `font-titulo`
- `webapp/src/node-builtins.d.ts` (novo) - declarações ambiente mínimas para `node:fs`/`node:path`/`node:url`, só as funções usadas pelo teste de guarda

## Decisions Made
Nenhuma decisão de produto nova além das já travadas pelo `04-UI-SPEC.md`/D-10. Execução seguiu a lista fechada de 17 call sites linha por linha; a numeração de linha do arquivo bateu exatamente com a tabela do UI-SPEC em todos os 17 casos, sem deslocamento.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking build-config error] `tsc -b` não resolvia `node:fs`/`node:path`/`node:url`**
- **Found during:** Verificação de plano (`scripts/verificar.sh`, passo [4/4] Build da UI web), após a Task 3 já commitada
- **Issue:** `webapp/src/design-tokens.test.ts` usa `node:fs`/`node:path`/`node:url` conforme mandado pela Task 3 ("Nenhuma dependência nova: só node:fs, node:path, node:url e vitest"). `npx vitest run` (verify da própria Task 3) passa porque vitest transforma via esbuild sem checar tipo — mas `npm run build` roda `tsc -b`, que falhava com `error TS2307: Cannot find module 'node:fs'`, porque o webapp não tem `@types/node` (não depende de Node em runtime, só browser) e `moduleResolution: bundler` não reconhece módulos `node:*` sem tipos declarados em algum lugar do programa.
- **Fix:** Criado `webapp/src/node-builtins.d.ts` com declarações de módulo ambiente cobrindo só as 6 funções usadas (`readFileSync`/`readdirSync`/`statSync` de `node:fs`; `dirname`/`join`/`relative` de `node:path`; `fileURLToPath` de `node:url`) — não o `@types/node` inteiro. Instalar o pacote `@types/node` foi descartado deliberadamente: é excluído do auto-fix de Rule 3 (instalação de pacote exige checkpoint humano) e o próprio `<threat_model>` do plano manda escalar antes de qualquer dependência nova nesta fase.
- **Files modified:** `webapp/src/node-builtins.d.ts` (novo, único arquivo)
- **Verification:** `cd webapp && npm run build` volta a terminar com exit code 0; `npm test` continua 16/16 arquivos, 127/127 testes verdes (o shim não muda comportamento em runtime, só tipo em tempo de build)
- **Committed in:** `ba97a63` (commit dedicado, depois da Task 3)

---

**Total deviations:** 1 auto-fixed (1 blocking build-config, Rule 3)
**Impact on plan:** Necessário para satisfazer o critério de verificação de nível de plano ("`npm run build` termina com exit code 0"), que a Task 3 isolada não cobria (seu próprio `<verify>` só roda `npx vitest run`). Nenhuma dependência nova instalada, threat model T-04-01-SC do plano permanece intacto (`package.json`/`package-lock.json` seguem sem alteração — conferido no diff antes do commit da Task 3).

## Issues Encountered
- Worktree foi provisionado inicialmente numa branch (`worktree-agent-adc1f0192521fc0bd`) apontando para um HEAD de uma tarefa anterior não relacionada (`75d46c1`, PR #14 de fusos/mês por extenso). Corrigido via `git reset --hard` para o commit-base exigido (`6df1bb0`, working tree já estava limpo) antes de qualquer edição, conforme protocolo de HEAD assertion do executor.
- `webapp/node_modules` e `.venv` não existiam neste worktree (isolado do checkout principal) — `npm install` e a criação de `.venv` + `pip install -e ".[dev]"` foram necessários antes de rodar testes/build.
- `scripts/verificar.sh` reporta `pytest falhou` — 1 falha (`tests/test_apple_photos.py::test_video_entra_junto_com_a_foto`), 841 passaram, 1 pulado. A falha é `ModuleNotFoundError: No module named 'osxphotos'`: o pacote vive no extra opcional `apple` de `pyproject.toml` (não em `dev`), que nem `scripts/instalar.sh` nem este plano instalam por padrão. Pré-existente e fora de escopo — este plano não toca nenhum arquivo Python; confirmado que qualquer instalação padrão (`scripts/instalar.sh` sem flag) reproduziria a mesma falha. Não corrigido (Rule 3 exclui instalação de pacote sem verificação humana, e está fora do escopo desta fatia). Benchmark de agrupamento (19/19) e testes/build do webapp (127/127, build ok) continuam 100% verdes.

## User Setup Required

None - nenhuma configuração de serviço externo. Se alguém quiser rodar a suíte Python completa (incluindo os testes que tocam osxphotos), precisa `pip install -e ".[apple]"` — fora do escopo desta fatia.

## Next Phase Readiness
Wave 1 completa: os outros 5 planos da Fase 4 (Wave 2/3) podem escrever markup novo já usando `font-titulo` diretamente, sem tocar nos 10 arquivos que este plano migrou. Nenhum bloqueio identificado. A falha pré-existente de `osxphotos` (ver "Issues Encountered") não bloqueia nenhum plano da Fase 4 — nenhum deles toca `fotoorganizer/sources/apple_photos.py` ou equivalente.

---
*Phase: 04-consist-ncia-visual-secund-ria*
*Completed: 2026-08-16*
