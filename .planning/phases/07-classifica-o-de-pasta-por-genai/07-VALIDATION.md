---
phase: 7
slug: classifica-o-de-pasta-por-genai
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-18
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Extracted from `07-RESEARCH.md` § Validation Architecture per plan-checker
> finding (Dimension 8 blocker, 2026-08-18) — content unchanged, moved to
> the dedicated gate artifact (same pattern as `06-VALIDATION.md`).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.x, `pyproject.toml [tool.pytest.ini_options]`, `testpaths = ["tests"]` |
| **Framework (frontend)** | vitest, `webapp/package.json`, config in `webapp/vite.config.ts` |
| **Config file** | `pyproject.toml` (backend), `webapp/vite.config.ts` (frontend) |
| **Quick run command** | `pytest tests/test_classification_pasta_genai.py -x` (backend); `npx vitest run ClassificacaoPasta` (frontend, once component exists) |
| **Full suite command** | `scripts/verificar.sh` |
| **Estimated runtime** | quick commands scoped to new file/component only, <10s |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_classification_pasta_genai.py -x` (backend); `npx vitest run ClassificacaoPasta` (frontend).
- **After every plan wave:** `scripts/verificar.sh`.
- **Before `/gsd:verify-work`:** full suite must be green.

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|---------------------|-------------|
| GENAI-01 | Classificação desligada por padrão; nenhuma chamada externa; motor idêntico ao de hoje | unit | `pytest tests/test_classification_pasta_genai.py::test_desligado_por_padrao -x` | ❌ Wave 0 |
| GENAI-01 | Custo estimado mostrado antes de qualquer chamada; nada enviado antes de confirmar | unit (client mockado) | `pytest tests/test_classification_pasta_genai.py::test_custo_antes_de_confirmar -x` | ❌ Wave 0 |
| GENAI-02 | Payload enviado contém só nome de pasta + metadado já catalogado, nunca bytes/caminho de imagem | unit (payload, espelha `test_lexico.py`) | `pytest tests/test_classification_pasta_genai.py::test_payload_nunca_envia_imagem -x` | ❌ Wave 0 |
| GENAI-02 | Sonnet 5 é o modelo usado, `thinking` desligado | unit | `pytest tests/test_classification_pasta_genai.py::test_modelo_e_thinking -x` | ❌ Wave 0 |
| GENAI-03 | Resultado vira `Evidence` com origem distinta (`llm_pasta`), nunca sobrecarrega `"llm"`/Advisor de cluster | unit + integration (`SuggestionEngine.gerar()`) | `pytest tests/test_classification_pasta_genai.py::test_evidence_origem_propria -x` | ❌ Wave 0 |
| GENAI-03 | Falha de API/timeout/429 nunca derruba a geração; mídia segue sem a evidência de LLM | unit (mock que levanta exceção, espelha `advisor.py`) | `pytest tests/test_classification_pasta_genai.py::test_falha_api_nunca_derruba -x` | ❌ Wave 0 |
| D-02 | Campo já preenchido (categoria OU cidade/país) nunca é sobrescrito pelo resultado do LLM | unit | `pytest tests/test_classification_pasta_genai.py::test_nunca_sobrescreve_campo_preenchido -x` | ❌ Wave 0 |
| D-06 | Resposta ambígua/"não sei" do LLM não gera evidência nenhuma | unit | `pytest tests/test_classification_pasta_genai.py::test_resposta_incerta_nao_gera_evidencia -x` | ❌ Wave 0 |
| Pitfall 1 (durabilidade) | Evidência sobrevive a uma segunda rodada de `gerar()` sem reexecutar a sessão | integration | `pytest tests/test_classification_pasta_genai.py::test_sobrevive_a_segunda_geracao -x` | ❌ Wave 0 |

*Status: todos ⬜ pending até a Wave 1 aterrissar — este é o contrato pré-execução, não um log de execução ao vivo.*

---

## Wave 0 Requirements

- [ ] `tests/test_classification_pasta_genai.py` — cobre GENAI-01/02/03 + D-02/D-06 + durabilidade, espelha a estrutura de `tests/test_lexico.py` (mock `client` injetado em `ClassificacaoDePastaClaude`, mesmo padrão de `LexicoClaude(client=...)`)
- [ ] `webapp/src/components/ClassificacaoPasta.test.tsx` — espelha o padrão de teste checkbox-por-linha de `webapp/src/components/EscritaExif.test.tsx`
- Nenhum framework novo — pytest e vitest já configurados, usados por testes diretamente análogos existentes

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sessão real de classificação contra pastas reais do catálogo | GENAI-01/02/03 fim-a-fim | Precisa da chave real do dono e custo real, não simulável em teste unitário | `07-10-PLAN.md` Task 2/3 — checkpoint humano, dono roda sessão real de ~10 itens |
| Medição do score `llm_pasta` | GENAI-03 (D-074/D-059/D-060 discipline) | Precisa de amostra real do acervo, mesma barra empírica que D-059/D-060 | `07-09-PLAN.md` — dono roda script de medição com a própria chave, decide o número |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (confirmado pelo plan-checker, 2026-08-18)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (2 itens acima, ambos rastreados a um plano específico)
- [x] No watch-mode flags (`-x` e `vitest run`, não `--watch`)
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-18 (plan-checker verificado; conteúdo extraído verbatim de `07-RESEARCH.md` § Validation Architecture, nenhuma alegação nova introduzida)
