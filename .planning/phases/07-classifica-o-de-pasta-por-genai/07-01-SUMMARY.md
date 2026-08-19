---
phase: 07-classifica-o-de-pasta-por-genai
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, sqlite, repository-pattern]

# Dependency graph
requires: []
provides:
  - "Modelo ORM PastaClassificada (tabela pasta_classificacoes_genai)"
  - "Migração Alembic 0020, encadeada em 0019 (head)"
  - "ClassificacaoPastaRepository: aprovadas/propostas/conhecidas/salvar_propostas/aprovar/descartar"
affects: [07-02, 07-03, 07-04, 07-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Guarda de escrita por CAMPO (não por linha) para dado de origem mista LLM/manual — mais estrita que LexicoRepository.salvar()"
    - "Tabela de persistência paralela a Evidence para sobreviver à regeneração destrutiva de SuggestionEngine.gerar()"

key-files:
  created:
    - fotoorganizer/models/pasta_classificacao.py
    - fotoorganizer/repositories/pasta_classificacao.py
    - fotoorganizer/database/migrations/versions/0020_pasta_classificacoes_genai.py
    - tests/test_pasta_classificacao_genai.py
  modified:
    - fotoorganizer/models/__init__.py

key-decisions:
  - "D-02 aplicada no nível de CAMPO em salvar_propostas — cidade/pais/categoria/evento preenchidos nunca são sobrescritos, mesmo por proposta discordante; linha origem='manual' é inteiramente intocável, incluindo campos vazios"
  - "status (proposta/aprovada/descartada) é eixo separado de origem (llm/manual) — só status='aprovada' é lido pela cascata; descartar() nunca apaga linha (invariante 8)"
  - "Sem FK e sem índice extra na tabela nova — PK (pasta) é o único caminho de acesso, escala de dezenas/centenas por design"

patterns-established:
  - "PropostaDePasta (dataclass frozen/slots) como DTO de saída do repositório — instância ORM nunca sai da sessão"

requirements-completed: []  # GENAI-03 span múltiplos planos (07-01..07-10); ver nota abaixo

# Metrics
duration: ~20min
completed: 2026-08-18
---

# Phase 7 Plan 01: Camada de persistência do GenAI de pasta Summary

**Modelo `PastaClassificada`, migração 0020 e `ClassificacaoPastaRepository` com guarda de escrita por campo (D-02), fazendo o resultado do Claude sobreviver à regeneração destrutiva de `Evidence`.**

## Performance

- **Duration:** ~20min
- **Started:** 2026-08-18 (sessão única)
- **Completed:** 2026-08-18T20:26:43Z
- **Tasks:** 3/3
- **Files modified:** 5 (4 criados, 1 modificado)

## Accomplishments
- Tabela `pasta_classificacoes_genai` criada pela migração 0020 (encadeada em 0019, head anterior), sem FK/índice extra
- `ClassificacaoPastaRepository` expõe as seis operações do contrato de `<interfaces>` do plano, com D-02 aplicada por campo (mais estrita que o precedente `LexicoRepository`, que é por linha)
- Nenhum caminho de deleção de linha no repositório — `descartar()` rebaixa `status`, nunca remove (invariante 8)
- Seis testes cobrindo campo já preenchido, campo completado, linha manual intocável, transição de status, durabilidade do descarte e `conhecidas()` por status

## Task Commits

Each task was committed atomically:

1. **Task 1: Modelo PastaClassificada + registro + migração 0020** - `20cd04b` (feat)
2. **Task 2: ClassificacaoPastaRepository com disciplina por campo (D-02)** - `85ff89f` (feat)
3. **Task 3: Testes de D-02 por campo, transição de status e durabilidade** - `fa350a4` (test)

_Nota: Task 3 é `tdd="true"` no plano, mas Task 1/2 já haviam implementado o modelo e o repositório em commits `auto` anteriores (build sequencial, não RED-antes-de-implementar) — os 6 testes passaram já na primeira execução contra o código de Task 2, não houve fase RED separada. Ver "Issues Encontrados" abaixo._

## Files Created/Modified
- `fotoorganizer/models/pasta_classificacao.py` - Modelo `PastaClassificada`, PK=pasta, docstring explicando chave/D-07/eixo status vs. origem
- `fotoorganizer/models/__init__.py` - import + `__all__` de `PastaClassificada`
- `fotoorganizer/repositories/pasta_classificacao.py` - `PropostaDePasta` (dataclass) + `ClassificacaoPastaRepository` com as 6 operações do contrato
- `fotoorganizer/database/migrations/versions/0020_pasta_classificacoes_genai.py` - migração, `down_revision='0019'`, cria/derruba `pasta_classificacoes_genai`
- `tests/test_pasta_classificacao_genai.py` - 6 testes, sem mock, contra SQLite real via fixture `migrated_engine`

## Decisions Made
- D-02 (nível de campo) confirmada como implementada exatamente como o plano especificou: guarda por campo é estritamente mais forte que a guarda por linha de `LexicoRepository`, e uma linha `origem='manual'` é pulada por inteiro (nenhum campo dela é tocado, mesmo vazio) — decisão consciente de não "completar o vazio" numa linha que o dono já assumiu.
- Verificação manual extra (fora dos 6 testes fixos pelo plano, para não violar `grep -c "def test_" == 6`): confirmado que `aprovar()`/`descartar()` chamados numa linha que já não está em `status='proposta'` é no-op — não regride uma linha já `aprovada` de volta, nem duplamente descarta.

## Deviations from Plan

None - plano executado exatamente como escrito. `sessao: Mapped[str]` foi implementado sem `default=""` (a interface do plano não especificava default e o repositório sempre passa `sessao` explicitamente) — não é desvio de comportamento, é aderência literal ao contrato de `<interfaces>`.

## Issues Encontrados

Task 3 tem `tdd="true"`, mas o plano sequenciou Task 1 (modelo) → Task 2 (repositório, `type="auto"` sem tdd) → Task 3 (testes, `tdd="true"`). Como a implementação já existia ao chegar em Task 3, os 6 testes passaram na primeira execução (`6 passed`), sem uma fase RED isolada onde eles falhassem primeiro. Isso é a estrutura do próprio plano, não um desvio da execução — os testes ainda provam exatamente o que o bloco `<behavior>` pedia, e a suíte inteira (945 testes) segue verde. Registrado aqui porque a seção `tdd_execution` do executor pede fail-fast se um teste passar "inesperadamente antes de qualquer implementação"; aqui a implementação era esperada e intencional (Task 2 anterior), não um bug mascarado.

## User Setup Required

None - nenhuma configuração de serviço externo neste plano (só SQLAlchemy/Alembic já instalados, threat T-07-01-SC aceito sem instalação nova).

## Next Phase Readiness

- Contrato de `<interfaces>` (`PastaClassificada`, `PropostaDePasta`, `ClassificacaoPastaRepository`) está pronto para consumo direto pelos planos 07-02 (chamada ao Claude), 07-03 (pré-filtro de candidatas via `conhecidas()`), 07-04/07-05 (cascata lendo `aprovadas()`).
- **GENAI-03 permanece Pending em REQUIREMENTS.md** — este plano entrega só a camada de persistência (fundação), não o comportamento fim-a-fim (falta a chamada ao Claude, a UI de revisão e a integração na cascata do `SuggestionEngine`, planos 07-02 a 07-10). Nenhum requisito foi marcado como completo, por instrução explícita do plano.
- `SCORES_REFERENCIA["llm_pasta"]` continua pendente de medição própria (Open Question 1 do PATTERNS.md) — não é bloqueio para este plano, mas os planos de cascata (07-04/07-05) precisam resolver isso antes de gravar `Evidence` com essa origem.

---
*Phase: 07-classifica-o-de-pasta-por-genai*
*Completed: 2026-08-18*

## Self-Check: PASSED

All created/modified files found on disk; all 3 task commits (`20cd04b`, `85ff89f`, `fa350a4`) confirmed in git log.
