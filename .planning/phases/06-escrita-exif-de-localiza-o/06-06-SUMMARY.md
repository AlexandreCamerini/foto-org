---
phase: 06-escrita-exif-de-localiza-o
plan: 06
subsystem: exif_write
tags: [fastapi, sqlalchemy, jobmanager, exif, dry-run, audit-log]

# Dependency graph
requires:
  - phase: 06-01
    provides: "ExifWritePlan/ExifWriteItem com status por campo, AuditLog reusado com plan_id=None"
  - phase: 06-03
    provides: "ExifWritePlanner.criar_plano_exif() — candidatos, valor e status por campo"
  - phase: 06-05
    provides: "ExifWriteExecutor.dry_run()/aplicar_selecao()/executar(), DryRunObrigatorioExif"
provides:
  - "ExifWriteRepository (repositories/exif_write.py) — PlanRowExif/ItemRowExif, veredito do último dry-run lido do audit log, auditoria filtrada por detalhe['exif_plan_id']"
  - "JobManager.iniciar_escrita_exif()/_rodar_escrita_exif() — execução do plano EXIF em background, tipo de job 'escrita_exif'"
  - "Grupo de rotas /api/exif/* (6 endpoints): listar, criar plano, detalhe com itens por campo, dry-run, executar (com seleção D-02), auditoria"
affects: [06-07, exif_write UI React]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Camada de exposição HTTP espelhando 1:1 o grupo /api/operacoes* já existente (mesmos nomes de helper, mesma ordem de injeção de dependências, mesmo padrão de HTTPException 404/409) — mas com filtro de auditoria por JSON (detalhe['exif_plan_id']) em vez da coluna plan_id, porque essa FK aponta para operation_plans.id neste domínio."
    - "Job de background cujo dict de retorno do executor não tem a mesma forma do analog (\"gravados\"+\"sidecars\" em vez de \"copiados\") — o callback final de _atualizar() precisa somar os campos certos, não copiar o padrão literal do analog."

key-files:
  created:
    - fotoorganizer/repositories/exif_write.py
    - tests/test_exif_write_api.py
  modified:
    - fotoorganizer/repositories/__init__.py
    - fotoorganizer/server/jobs.py
    - fotoorganizer/server/app.py

key-decisions:
  - "`ExifWriteRepository` exportado em `repositories/__init__.py` (não listado no `files_modified` do plano, mas mesma convenção que todo outro repositório do pacote já segue — `OperationRepository`, `DuplicateRepository` etc. — e usado por `server/app.py` via `from fotoorganizer.repositories import ExifWriteRepository`)."
  - "`PlanRowExif.gravados` conta item cujos TRÊS campos (gps/cidade/pais) terminaram em GRAVADO ou PULADO e sem `erro` — os três status entram como filtros SEPARADOS no `contar(*filtros)` (AND implícito do `.where()`), não uma condição OR combinada; um item com 2/3 campos resolvidos e 1/3 pendente não conta."
  - "`_rodar_escrita_exif` mapeia `processados = stats['gravados'] + stats['sidecars']` no callback final de `_atualizar()` — o dict que `ExifWriteExecutor.executar()` devolve não tem a chave `'copiados'` que o analog de cópia física usa; `resultado=stats` completo (incluindo `falhas_parciais`) viaja junto para a UI não perder o detalhe por campo."
  - "`POST /api/exif/{plan_id}/executar` sempre recebe corpo (`ExecutarExifBody`, `itens: list[int] | None = None`) — `aplicar_selecao(plan_id, body.itens)` chamado ANTES de checar se algo foi selecionado, para D-02 persistir mesmo quando o resultado é 409 (auditoria de seleção registrada de qualquer forma)."
  - "**REQUIREMENTS.md NÃO foi marcado como completo para EXIF-01/02/03/05**, mesma disciplina de 06-01/06-02/06-03/06-04b/06-05: este plano entrega a camada HTTP completa (os 6 endpoints que a UI React precisa), mas nenhum frontend consome isso ainda — a aprovação do dono via UI (06-07+) é parte do texto de cada requisito e continua fora. `requirements.mark-complete` não foi executado."

patterns-established:
  - "Endpoint de execução que precisa materializar seleção opt-out (D-02) ANTES do gate de 'nada selecionado' — ordem importa: persistir primeiro, avaliar o resultado depois, para o audit log refletir a tentativa mesmo quando ela é recusada."

requirements-completed: []

# Metrics
duration: ~25min
completed: 2026-08-18
---

# Phase 6 Plan 06: Repositório, job e rotas /api/exif/* Summary

**Seis endpoints HTTP (`/api/exif/*`) espelhando o grupo `/api/operacoes*` existente, com `ExifWriteRepository` lendo o veredito do dry-run e a trilha de auditoria pelo JSON `detalhe["exif_plan_id"]` (nunca pela coluna `AuditLog.plan_id`, que fica sempre `NULL` neste domínio) e `JobManager.iniciar_escrita_exif()` rodando `ExifWriteExecutor.executar()` em background.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-08-18
- **Tasks:** 3
- **Files modified:** 5 (2 criados, 3 modificados — `repositories/__init__.py` é uma deviation menor de exportação, ver Decisões)

## Accomplishments

- `ExifWriteRepository` (`repositories/exif_write.py`): `PlanRowExif`/`ItemRowExif` espelhando `PlanRow`/`ItemRow` de `repositories/operations.py`, com `_veredito()` lendo `prontos`/`problemas`/`campos_a_gravar`/`sidecars` do último `AuditLog.acao == "dry_run_exif"` filtrado por `detalhe["exif_plan_id"]`, e `listar_planos()`/`plano()`/`itens()`/`auditoria()` nas mesmas assinaturas do analog.
- `JobManager.iniciar_escrita_exif()`/`_rodar_escrita_exif()`: mesmo padrão de `iniciar_execucao`/`_rodar_execucao` (o `ExecutionControl` nasce na thread do pedido, o callback de progresso alimenta `_atualizar`), mas com o mapeamento de stats correto para a forma real que `ExifWriteExecutor.executar()` devolve (`gravados`/`sidecars`/`falhas_parciais`, não `copiados`).
- Seis rotas em `server/app.py`: `GET /api/exif`, `POST /api/exif/plano` (409 sem candidato), `GET /api/exif/{id}` (itens com `campos.{gps,cidade,pais}.{valor,status,motivo}`), `POST /api/exif/{id}/dry-run`, `POST /api/exif/{id}/executar` (persiste seleção D-02 antes do gate, 409 sem dry-run / seleção vazia / trabalho em andamento), `GET /api/exif/{id}/auditoria`.
- Nenhuma linha do grupo `/api/operacoes*` alterada ou removida — confirmado por `git diff` (0 linhas removidas contendo `/api/operacoes` em todo o histórico deste plano).
- 9 testes HTTP cobrindo o fluxo completo, com as três mensagens de 409 travadas por asserção literal e prova de hash intacto quando a execução é recusada.

## Task Commits

Each task was committed atomically:

1. **Task 1: ExifWriteRepository** - `412e248` (feat)
2. **Task 2: Job de escrita EXIF e grupo de rotas /api/exif/*** - `22c684c` (feat)
3. **Task 3: Suíte HTTP do fluxo de escrita EXIF** - `7bbef76` (test)

**Plan metadata:** (commit desta etapa, a seguir)

## Files Created/Modified

- `fotoorganizer/repositories/exif_write.py` - `ExifWriteRepository`, `PlanRowExif`, `ItemRowExif`
- `fotoorganizer/repositories/__init__.py` - exporta `ExifWriteRepository`/`PlanRowExif`/`ItemRowExif` (deviation)
- `fotoorganizer/server/jobs.py` - `JobManager.iniciar_escrita_exif`, `_rodar_escrita_exif`
- `fotoorganizer/server/app.py` - DI (`exif_repo`/`exif_planner`/`exif_executor`), `ExecutarExifBody`, grupo de rotas `/api/exif/*`
- `tests/test_exif_write_api.py` - 9 testes, fixtures `client_exif`/`client_sem_candidato`, helper `_aguardar_job`

## Decisions Made

Ver `key-decisions` no frontmatter para o raciocínio completo. Resumo: exportação de `ExifWriteRepository` em `repositories/__init__.py` por convenção (não estava no `files_modified` do plano, mas todo outro repositório do pacote é exportado assim); contagem de `gravados` no repositório exige os três status_* como filtros AND separados, não uma condição combinada; o mapeamento de stats no job usa `gravados+sidecars` porque a forma do dict do executor deste domínio é diferente da de `OperationExecutor`; seleção D-02 é persistida antes do gate de "nada selecionado" para a auditoria registrar a tentativa mesmo quando recusada; REQUIREMENTS.md permanece com EXIF-01/02/03/05 em aberto.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Consistência/cobertura] `ExifWriteRepository` exportado em `repositories/__init__.py`**
- **Found during:** Task 1, ao terminar `exif_write.py` e revisar como `server/app.py` importaria o repositório.
- **Issue:** O plano lista só `fotoorganizer/repositories/exif_write.py` em `files_modified` da Task 1, mas todo outro repositório do pacote (`OperationRepository`, `DuplicateRepository`, `SuggestionRepository`...) é reexportado em `repositories/__init__.py`. Sem isso, `server/app.py` teria que importar de um submódulo diferente dos demais (`fotoorganizer.repositories.exif_write` em vez de `fotoorganizer.repositories`), quebrando a convenção de import uniforme do arquivo.
- **Fix:** Adicionadas as três entradas (`ExifWriteRepository`, `ItemRowExif`, `PlanRowExif`) ao `from ... import` e ao `__all__` de `repositories/__init__.py`, mantendo ordem alfabética.
- **Files modified:** `fotoorganizer/repositories/__init__.py`
- **Verification:** `from fotoorganizer.repositories import ExifWriteRepository, PlanRowExif, ItemRowExif` funciona; suíte completa (928 testes, antes da Task 3) permanece verde.
- **Committed in:** `412e248` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — consistência de convenção de import, sem mudança de comportamento).
**Impact on plan:** Nenhuma mudança de escopo além da exportação; `server/app.py` importa `ExifWriteRepository` da mesma forma que importa todo outro repositório do pacote.

## Issues Encountered

None além do item documentado acima em Deviations. O ponto de atenção antecipado pelo advisor antes da implementação (forma do dict de `ExifWriteExecutor.executar()` divergente do analog de `OperationExecutor.executar()`) foi verificado por leitura direta do código-fonte antes de escrever `_rodar_escrita_exif` — nenhum `KeyError` ocorreu em tempo de execução.

## User Setup Required

None - nenhuma configuração de serviço externo necessária.

## Next Phase Readiness

- Os 6 endpoints de `/api/exif/*` estão prontos para o plano de UI (06-07+) consumir, exatamente na forma declarada no bloco `<interfaces>` do plano: `PlanoExif`, `ItemPlanoExif` (com `campos.{gps,cidade,pais}`), `LinhaAuditoria`.
- `JobManager.iniciar_escrita_exif(plan_id)` devolve `tipo == "escrita_exif"` no estado do job — a UI pode fazer polling em `/api/job` no mesmo padrão já usado para scan/importação/execução de operações.
- **Nenhum requisito EXIF-01/02/03/05 foi marcado como completo em REQUIREMENTS.md** — este plano entrega a API completa (backend), mas o texto de cada requisito inclui a aprovação do dono via UI, que só chega em 06-07+. `requirements.mark-complete` não foi executado.
- Suíte completa (`.venv/bin/python -m pytest -q`) verde: 937 passed (era 928 antes deste plano + 9 testes novos).
- Nenhum arquivo fora de `fotoorganizer/repositories/exif_write.py`, `fotoorganizer/repositories/__init__.py` (deviation), `fotoorganizer/server/jobs.py`, `fotoorganizer/server/app.py` e `tests/test_exif_write_api.py` foi modificado, confirmado por `git status --short`.

---
*Phase: 06-escrita-exif-de-localiza-o*
*Completed: 2026-08-18*

## Self-Check: PASSED

All 5 key files found on disk (exif_write.py, test_exif_write_api.py, repositories/__init__.py, jobs.py, app.py) plus this SUMMARY; all 3 task commits (412e248, 22c684c, 7bbef76) found in git log.
