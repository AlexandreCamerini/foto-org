---
phase: 07-classifica-o-de-pasta-por-genai
plan: 03
subsystem: classification
tags: [sqlalchemy, cost-estimation, privacy, anthropic-sdk]

# Dependency graph
requires:
  - phase: "07-01"
    provides: "ClassificacaoPastaRepository.conhecidas() (fonte futura de ja_classificadas)"
  - phase: "07-02"
    provides: "ClassificadorDePasta.corpo_da_chamada() (o dict que custo_genai.py mede)"
provides:
  - "candidatas_de_pasta.py::candidatas() — pré-filtro D-01 em 2 consultas agregadas"
  - "custo_genai.py::estimar()/contar_exato() — D-04/D-05 conforme decisão híbrida D-079"
  - "D-079 em docs/DECISOES.md — dono decidiu: estimativa local antes de confirmar, contagem exata só depois, no resumo"
affects: [07-04, 07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Duas consultas agregadas + combinação em memória (mesma disciplina de engine.py::_carregar_curadoria) — nunca uma consulta por pasta"
    - "MediaFile.organizavel como filtro em AMBAS as consultas de um pré-filtro, não só na contagem — Evidence presa a mídia não-acervo não pode 'resolver' um campo"
    - "Estimativa local deliberadamente conservadora (fator de caracteres/token reduzido, não a razão nominal) para nunca mostrar custo abaixo do real"

key-files:
  created:
    - fotoorganizer/classification/candidatas_de_pasta.py
    - fotoorganizer/classification/custo_genai.py
    - tests/test_candidatas_e_custo_genai.py
  modified:
    - docs/DECISOES.md
    - .planning/phases/07-classifica-o-de-pasta-por-genai/07-UI-SPEC.md

key-decisions:
  - "D-079: dono escolheu a opção híbrida (c) sobre a colisão count_tokens × critério 2 do ROADMAP — estimativa local antes de confirmar, contagem exata só depois, mostrada no resumo pós-execução (passo 5), nunca na prévia (passo 2)"
  - "entrada_exata sempre False em estimar() — a decisão fecha a porta para a opção (a); contar_exato() existe separado, para ser chamado só depois da confirmação, fora do escopo deste plano (ponto de integração real é 07-04)"
  - "cambio_usd_brl entra como parâmetro obrigatório de estimar(), nunca buscado — CAMBIO_USD_BRL_PADRAO/CAMBIO_FONTE_PADRAO ficam como constantes datadas, repassadas pelo endpoint futuro"

patterns-established:
  - "07-UI-SPEC.md atualizado no mesmo commit da decisão de checkpoint, não depois — 'Entrada (exata)' vira 'Entrada (estimada)', passo 5 ganha linha de custo real com fallback documentado para quando contar_exato() falhar (never-crash)"

requirements-completed: []  # GENAI-01 permanece Pending — ver nota abaixo

# Metrics
duration: ~15min
completed: 2026-08-18
---

# Phase 7 Plan 03: Pré-filtro de pastas candidatas e estimativa de custo Summary

**`candidatas()` (D-01, duas consultas agregadas) e `estimar()`/`contar_exato()` (D-04/D-05) implementando a decisão híbrida do dono (D-079) sobre a colisão entre `count_tokens` e o critério "nada sai antes de confirmar" do ROADMAP.**

## Performance

- **Duration:** ~15min
- **Started:** 2026-08-18 (sessão única)
- **Completed:** 2026-08-18T20:54:52Z
- **Tasks:** 3/3 (Task 1 = decisão já respondida pelo dono via `AskUserQuestion` antes desta execução, registrada como D-079; Tasks 2-3 = implementação)
- **Files modified:** 5 (3 criados, 2 modificados)

## Accomplishments
- **Task 1 (decisão):** D-079 registrada em `docs/DECISOES.md` — o dono escolheu a opção híbrida sobre a colisão nomeada entre `client.messages.count_tokens` (transmite o payload) e o critério de sucesso 2 da Fase 7 ("nada é enviado antes de ele confirmar"). `07-UI-SPEC.md` atualizado no mesmo commit: rótulo "Entrada (exata)" → "Entrada (estimada)", nota de honestidade do passo 2 reescrita para declarar que nada foi enviado ainda, e o passo 5 (Concluído) ganhou uma linha nova de custo real com fallback documentado.
- **Task 2:** `candidatas_de_pasta.py::candidatas()` — pré-filtro D-01 em duas consultas agregadas sobre o catálogo inteiro (contagem/período por pasta + presença de `Evidence` por campo/pasta), combinadas em memória. `MediaFile.organizavel` filtra as duas: miniatura de cache e referência de catálogo externo (invariante 8) nunca entram no `n_fotos` nem "completam" um campo via `Evidence` presa a mídia não-acervo. Pasta já classificada nunca reaparece. Resultado ordenado por pasta.
- **Task 3:** `custo_genai.py::estimar()`/`contar_exato()` — implementa exatamente a decisão híbrida: `estimar()` conta a entrada LOCALMENTE (fator conservador documentado, nunca abaixo do real) sem tocar rede, sempre com `entrada_exata=False`; `contar_exato()` existe separada, never-crash (qualquer exceção devolve `0`), pronta para ser chamada só depois da confirmação do dono (ponto de integração real é o endpoint de 07-04). Preços Sonnet 5 (US$ 2/US$ 10 por MTok) como constantes nomeadas; teto de saída ancorado em `max_tokens` do payload real.
- 19 testes novos (11 do pré-filtro D-01 + 8 da estimativa de custo), todos verdes; suíte inteira (975 testes) sem regressão.

## Task Commits

Each task was committed atomically:

1. **Task 1: Decisão D-079 (dono já respondeu via AskUserQuestion) + atualização do UI-SPEC** - `af2eaf0` (docs)
2. **Task 2: Pré-filtro de pastas candidatas (D-01)** - `8af4e98` (feat)
3. **Task 3: Estimativa de custo da sessão (D-04/D-05)** - `2924d1a` (feat)

## Files Created/Modified
- `fotoorganizer/classification/candidatas_de_pasta.py` - `CandidataDePasta` (dataclass) + `candidatas(session, ja_classificadas)`, duas consultas agregadas, docstring explicando por que `organizavel` filtra ambas
- `fotoorganizer/classification/custo_genai.py` - `PRECO_ENTRADA_USD_POR_MTOK`/`PRECO_SAIDA_USD_POR_MTOK`, `CAMBIO_USD_BRL_PADRAO`/`CAMBIO_FONTE_PADRAO`, `CustoEstimado`, `estimar()`, `contar_exato()`
- `tests/test_candidatas_e_custo_genai.py` - 19 testes (11 candidatas + 8 custo), fixtures locais no molde de `tests/test_inventario.py` e `tests/test_lexico.py`
- `docs/DECISOES.md` - D-079 (nova entrada, próximo número livre depois de D-078)
- `.planning/phases/07-classifica-o-de-pasta-por-genai/07-UI-SPEC.md` - rótulos do passo 2 e linha nova do passo 5 do Copywriting Contract, coerentes com a opção híbrida

## Decisions Made
- **D-079** (a decisão em si — ver `docs/DECISOES.md` para o texto completo): o dono, perguntado diretamente pelo orquestrador com as mesmas três opções que a Task 1 do plano definia, escolheu a opção (c) híbrida. Isto não foi decidido pelo planejador nem pelo executor — é a razão de a Task 1 ter sido roteada como `checkpoint:decision gate="blocking"` em vez de ser resolvida no planejamento.
- `estimar()` mantém `cambio_usd_brl` como parâmetro obrigatório (sem default na assinatura), exatamente como o bloco `<interfaces>` do plano especificava — os defaults (`CAMBIO_USD_BRL_PADRAO`/`CAMBIO_FONTE_PADRAO`) ficam como constantes de módulo para o chamador futuro (07-04) repassar.
- `contar_exato()` remove `max_tokens` do corpo antes de chamar `count_tokens` — é parâmetro de geração, não de contagem de entrada, e a função não recebeu `pastas` vazio como caso especial (isso é responsabilidade de `estimar()`/do chamador, não de `contar_exato()`, que só sabe fazer uma coisa: contar o que recebeu).

## Deviations from Plan

None - plano executado exatamente como escrito, incluindo a Task 1 sendo tratada como decisão já respondida (a orientação de execução explicitou isto antes da tarefa começar, não é um desvio da execução em si).

## Issues Encontrados

None.

## User Setup Required

None - nenhuma configuração de serviço externo neste plano (`contar_exato()` reusa a mesma credencial de ambiente que `location_advisor.py` já documenta; nenhum caminho deste plano a exercita de fato — isso fica para 07-04).

## Next Phase Readiness

- **GENAI-01 permanece Pending em REQUIREMENTS.md.** Este plano entrega as duas peças que precedem qualquer gasto (pré-filtro de candidatas + estimativa de custo), mas o texto de GENAI-01 ("Dono habilita a classificação... com custo estimado visível antes de confirmar") descreve um comportamento fim-a-fim que só existe quando 07-04 (endpoint que orquestra a sessão, incluindo o gate de opt-in e a chamada real a `contar_exato()` pós-confirmação) e 07-06 (UI do assistente) existirem. Mesma disciplina que 07-01/07-02 já aplicaram.
- Contratos prontos para 07-04: `candidatas()` (só falta 07-04 passar `ClassificacaoPastaRepository.conhecidas()` como `ja_classificadas`), `estimar()` (só falta 07-04 chamar com o `corpo` de `ClassificadorDePasta.corpo_da_chamada()` e uma `cambio_usd_brl`), `contar_exato()` (só falta 07-04 chamá-la no ponto exato que D-079 define: imediatamente antes de `messages.create`, depois da confirmação do dono).
- `07-UI-SPEC.md` já está coerente com a decisão — 07-06 não corre risco de implementar cópia contraditória (rótulo "Entrada (estimada)", linha de custo real no passo 5, ambos já especificados).

---
*Phase: 07-classifica-o-de-pasta-por-genai*
*Completed: 2026-08-18*

## Self-Check: PASSED

All created/modified files found on disk; all 3 task commits (`af2eaf0`, `8af4e98`, `2924d1a`) confirmed in git log.
