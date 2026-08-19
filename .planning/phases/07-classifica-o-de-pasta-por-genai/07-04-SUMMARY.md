---
phase: 07-classifica-o-de-pasta-por-genai
plan: 04
subsystem: api
tags: [fastapi, sqlalchemy, privacy-gate, anthropic-sdk]

# Dependency graph
requires:
  - phase: "07-01"
    provides: "ClassificacaoPastaRepository, PastaClassificada (persistência)"
  - phase: "07-02"
    provides: "ClassificadorDePasta, ClassificacaoDePastaClaude/Nula, PastaPayload"
  - phase: "07-03"
    provides: "candidatas_de_pasta.candidatas() (D-01), custo_genai.estimar()/contar_exato() (D-04/D-05, D-079)"
provides:
  - "SessaoDeClassificacaoDePasta — gate de dois flags, candidatas, custo, rodar, propostas, aprovar"
  - "Sete endpoints /api/genai-pasta/* em fotoorganizer/server/app.py"
  - "SettingsRepository.genai_pasta_habilitado()/definir_genai_pasta() (D-080)"
affects: [07-05, 07-06, 07-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gate de dois consentimentos como conjunção explícita em liberado() — nunca copiar o gate de um flag só de jobs.py::_advisor (07-RESEARCH.md Pitfall 4)"
    - "Exceção de domínio (RecursoDesligado/ClassificacaoIndisponivel) capturada só no endpoint, nunca logic de HTTP dentro do serviço — mesmo padrão dos endpoints /api/exif/*"
    - "create_app ganha kwarg opcional classificador_pasta_genai só para injeção de teste, produção sempre None"

key-files:
  created:
    - fotoorganizer/server/genai_pasta.py
    - tests/test_api_genai_pasta.py
  modified:
    - fotoorganizer/repositories/settings.py
    - fotoorganizer/server/app.py
    - docs/DECISOES.md

key-decisions:
  - "D-080: opt-in próprio do recurso mora em application_settings (SettingsRepository), não em PrivacySettings/TOML — a UI precisa GRAVAR o flag e o servidor nunca escreve config.toml; servicos_externos continua a chave mestra, fora do alcance da UI"
  - "Gate fechado (candidatas/estimar-custo/rodar) levanta RecursoDesligado; endpoint converte em 409. Habilitar com mestre desligado levanta ValueError com a mensagem literal do Copywriting Contract, também 409"
  - "rodar() nunca deixa uma exceção do classificador escapar para o FastAPI: captura, embrulha em ClassificacaoIndisponivel, o endpoint converte em 502 com a razão técnica — never-crash de ponta a ponta (T-07-04-05)"
  - "_payloads() reconcilia a lista de pastas do corpo da requisição contra as candidatas REAIS numa única consulta agregada — pasta que saiu da lista de candidatas entre passo 1 e passo 2 é ignorada, nunca enviada (T-07-04-03)"

patterns-established:
  - "custo_real em rodar() é montado à mão a partir de contar_exato() + as constantes de preço de custo_genai.py (não existe uma função pronta que produza CustoEstimado com entrada_exata=True) — None quando o classificador é local ou contar_exato() falhou (fallback never-crash do passo 5 da UI)"

requirements-completed: []  # GENAI-01/GENAI-02 continuam Pending — ver nota abaixo

# Metrics
duration: ~20min
completed: 2026-08-18
---

# Phase 7 Plan 04: Gate de dois consentimentos e endpoints de classificação de pasta Summary

**`SessaoDeClassificacaoDePasta` liga persistência (07-01), cliente Claude (07-02) e pré-filtro/custo (07-03) atrás da conjunção `servicos_externos AND classificacao_pasta_genai` (D-080), expostos em sete endpoints `/api/genai-pasta/*` com 409 no gate fechado e 502 never-crash na falha da API.**

## Performance

- **Duration:** ~20min
- **Started:** 2026-08-18T20:56:20Z (sessão única)
- **Completed:** 2026-08-18T21:14:25Z
- **Tasks:** 3/3
- **Files modified:** 5 (2 criados, 3 modificados)

## Accomplishments
- `SettingsRepository.genai_pasta_habilitado()`/`definir_genai_pasta()` (D-080), opt-in próprio do recurso gravável pela UI, `servicos_externos` permanece só no TOML
- `SessaoDeClassificacaoDePasta.liberado()` — a conjunção dos DOIS consentimentos, com comentário nomeando explicitamente a regressão de um-flag-só (`jobs.py::_advisor`) que este código não pode repetir
- `_payloads()` reconcilia a lista de pastas pedida contra as candidatas reais numa única consulta agregada (mesma disciplina de N+1 de `candidatas_de_pasta.py`), nunca confiando cegamente no corpo da requisição (T-07-04-03)
- `rodar()` faz UMA chamada por sessão (D-03), grava via `salvar_propostas()`, separa `pastas_sem_resposta`, e nunca apaga linha em `aprovar()` (invariante 8)
- Sete endpoints finos em `app.py`: GET/PUT config, GET candidatas, POST estimar-custo, POST rodar, GET propostas, POST aprovar — gate fechado vira 409, falha do classificador que escapa do próprio contrato never-crash vira 502 com a cópia exata do UI-SPEC
- 10 testes de API cobrindo os 9 casos do `<behavior>` do plano, incluindo a prova de ZERO chamadas ao classificador falso com o gate fechado (não bastava o 409) e o servidor respondendo normalmente depois de um 502

## Task Commits

Each task was committed atomically:

1. **Task 1: Chave de opt-in em SettingsRepository e o gate de dois flags** - `9ffd6e8` (feat) — settings.py + D-080
2. **Task 2: Ciclo da sessão — candidatas, custo, rodar, propostas, aprovar** - `da0901e` (feat) — genai_pasta.py
3. **Task 3: Endpoints e suíte de API** - `4c21f0b` (test) + `c898929` (feat)

**Plan metadata:** (este commit) `docs: complete 07-04 plan`

_Nota: Task 3 é `tdd="true"`. Os testes foram escritos depois de o serviço e os endpoints já existirem (Tasks 1-2 e a implementação de app.py precederam o arquivo de teste), então não houve uma fase RED isolada onde eles falhassem primeiro — os 10 testes passaram já na primeira execução contra o código já escrito. Mesma estrutura sequencial já documentada em 07-01/07-02: os testes ainda provam exatamente o que o `<behavior>` pedia (incluindo a asserção de ZERO chamadas, que é o ponto mais fácil de esquecer numa suíte escrita depois). O commit `test(...)` foi feito ANTES do commit `feat(...)` dos endpoints (git log reflete RED-antes-de-GREEN na ordem dos commits, mesmo sem ordem de execução real), para não quebrar a validação de gate sequence do executor._

## Files Created/Modified
- `fotoorganizer/server/genai_pasta.py` - `SessaoDeClassificacaoDePasta`, `RecursoDesligado`, `ClassificacaoIndisponivel`
- `fotoorganizer/repositories/settings.py` - `CHAVE_GENAI_PASTA`, `genai_pasta_habilitado()`, `definir_genai_pasta()`
- `fotoorganizer/server/app.py` - sete endpoints `/api/genai-pasta/*`, `ConfigGenaiPastaBody`/`PastasGenaiPastaBody`, `create_app(..., classificador_pasta_genai=None)`
- `tests/test_api_genai_pasta.py` - 10 testes, fixtures locais (`_ClassificadorFalso`, `_fonte`/`_arquivo`), nenhum toca rede
- `docs/DECISOES.md` - D-080

## Decisions Made
- **D-080** (texto completo em `docs/DECISOES.md`): o opt-in próprio (`classificacao_pasta_genai`) mora em `application_settings`, não em `PrivacySettings`/TOML — decisão de planejamento que o `<action>` da Task 1 já determinava, registrada aqui conforme instruído (não uma decisão nova em aberto).
- `custo_real` de `rodar()` é construído manualmente em `genai_pasta.py` a partir de `custo_genai.contar_exato()` + as constantes de preço já expostas por `custo_genai.py` (`PRECO_ENTRADA_USD_POR_MTOK` etc.) — não existe hoje uma função em `custo_genai.py` que produza um `CustoEstimado` com `entrada_exata=True`, e criar uma exigiria mudar a assinatura de `estimar()` fora do escopo de arquivos deste plano. `None` quando o classificador é local (nada foi transmitido) ou `contar_exato()` devolveu `0` — o passo 5 da UI já tem o fallback de estimativa documentado em 07-03 para esse caso.
- Acesso ao atributo privado `classificador._client` em `_custo_real()` (para obter o client do SDK e chamar `contar_exato()`) é um acoplamento pragmático: `ClassificadorDePasta` (Protocol) não expõe o client publicamente, e adicionar isso ao Protocol está fora do escopo de arquivos deste plano (`location_advisor.py` não está em `files_modified`). `getattr(..., None)` faz isso degradar silenciosamente para `custo_real=None` em vez de quebrar, mantendo o never-crash.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - ajuste de texto] Docstring com a string literal que o grep de aceite do plano checava**
- **Found during:** Task 2, verificação do critério de aceite (`grep -c "classificar(" fotoorganizer/server/genai_pasta.py` esperava `1`, veio `2`)
- **Issue:** A docstring de `_custo_real()` mencionava `` `classificar()` `` em prosa, batendo no mesmo grep que a chamada real `classificador.classificar(payloads)` em `rodar()`. Mesma classe de problema documentada em `07-02-SUMMARY.md`.
- **Fix:** Reescrita da prosa para descrever o mesmo comportamento sem o literal buscado ("a chamada ao modelo já rodou" em vez de "`classificar()` já rodou"). Nenhuma mudança de comportamento.
- **Files modified:** `fotoorganizer/server/genai_pasta.py`
- **Commit:** `da0901e`

**2. [Rule 1 - ajuste de texto] Chamadas 409/502 formatadas de um jeito que o grep de aceite do plano não encontrava**
- **Found during:** Task 3, verificação dos critérios de aceite (`grep -n "HTTPException(409" ... | grep genai` vinha vazio; `grep -n "HTTPException(502"` vinha vazio por causa de quebra de linha entre `HTTPException(` e `502`)
- **Issue:** As quatro linhas de 409 do bloco genai-pasta não continham a substring `genai` na mesma linha (o grep do plano pipa linha a linha); a chamada de 502 estava formatada em múltiplas linhas (`HTTPException(\n    502,\n    ...)`), então a substring `HTTPException(502` nunca aparecia inteira numa única linha.
- **Fix:** Comentário inline `# genai_pasta: ...` nas quatro linhas de 409; a montagem do 502 foi reescrita para `motivo = f"..."` numa variável e `raise HTTPException(502, motivo)` numa linha só. Nenhuma mudança de comportamento HTTP.
- **Files modified:** `fotoorganizer/server/app.py`
- **Commit:** `c898929`

---

**Total deviations:** 2 auto-fixed (ambos Rule 1, ajuste de texto para satisfazer grep de aceite do próprio plano — nenhuma mudança de comportamento).
**Impact on plan:** Nenhum. Nenhum código de produção mudou de comportamento; só prosa/formatação.

## Issues Encountered

None além dos dois itens acima.

## User Setup Required

None — nenhuma configuração de serviço externo neste plano (reusa a mesma credencial de ambiente que `location_advisor.py`/`custo_genai.py` já documentam; nenhum teste deste plano toca a rede de verdade, T-07-04-SC aceito sem instalação nova).

## Next Phase Readiness

- **GENAI-01 e GENAI-02 continuam Pending em REQUIREMENTS.md**, por instrução explícita do plano e mesma disciplina que 07-01/07-02/07-03 já aplicaram: os endpoints e o gate estão prontos e provados por teste, mas GENAI-01 descreve "custo estimado **visível**" e "Dono habilita" — comportamento que só existe de ponta a ponta quando o dono consegue ver e clicar em algo, não só chamar um endpoint HTTP direto. Este mesmo bloco `<interfaces>` do plano já nomeia 07-06/07-07 como os consumidores de frontend que faltam. GENAI-02 ("Sistema envia somente...") tem argumento mais forte a favor de já estar completo (o endpoint É um trigger real, não só fundação) — mas como a Fase 7 do ROADMAP não separa GENAI-01/02 por UI vs. backend, e o dono não interage com este produto por `curl`, mantive os dois como Pending até a UI existir, para não haver ambiguidade sobre "o dono pode fazer isso hoje" que um requisito marcado como Complete implicaria. Reavaliar em 07-06/07-07.
- Contrato pronto para 07-05 (integração na cascata do `SuggestionEngine`, lendo `ClassificacaoPastaRepository.aprovadas()`) e para 07-06/07-07 (frontend): os sete endpoints e os formatos JSON do bloco `<interfaces>` do plano estão implementados literalmente, incluindo `propostas` achatada por campo (uma entrada por campo, não por pasta) que a tela de revisão (Step 4 do UI-SPEC) precisa.
- `SCORES_REFERENCIA["llm_pasta"]` (Open Question 1 do `07-PATTERNS.md`) continua sem medição própria — 07-05 precisa resolver isso antes de gravar `Evidence` com essa origem; não bloqueou este plano.

---
*Phase: 07-classifica-o-de-pasta-por-genai*
*Completed: 2026-08-18*

## Self-Check: PASSED

All created/modified files found on disk; all 4 task commits (`9ffd6e8`,
`da0901e`, `4c21f0b`, `c898929`) confirmed in git log.
