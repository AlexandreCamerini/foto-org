---
phase: 07-classifica-o-de-pasta-por-genai
plan: 02
subsystem: classification
tags: [anthropic-sdk, claude-sonnet-5, json-schema, never-crash]

# Dependency graph
requires: ["07-01: ClassificacaoPastaRepository, PastaClassificada"]
provides:
  - "PastaPayload/PropostaDoModelo/ClassificadorDePasta (Protocol)"
  - "ClassificacaoDePastaNula (padrão) e ClassificacaoDePastaClaude"
  - "corpo_da_chamada() — kwargs exatos para messages.create, reusável para estimativa de custo sem chamar a API"
affects: [07-03, 07-04, 07-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Serialização por allowlist literal campo a campo (nunca asdict()/__dict__) — mesmo padrão que lexico.py já usa, agora com um teste que trava por igualdade de conjunto de chaves"
    - "D-02 reaplicada sobre a RESPOSTA do modelo (não só no prompt) — obediência do modelo nunca é pré-requisito de segurança"

key-files:
  created:
    - fotoorganizer/classification/location_advisor.py
    - tests/test_classification_pasta_genai.py

key-decisions:
  - "categoria do schema é enum restrito ao vocabulário canônico de engine.py::_CATEGORIAS_PASTA (Viagens/Família/Eventos) — não inventado, para convergir com a cascata determinística"
  - "Ordem de filtro na resposta: (1) descarta pasta não pedida, (2) descarta item cujos 4 campos de valor vêm todos null (D-06), (3) só então zera por campo os que já têm ja_conhecido (D-02) — ordem literal do <action> do plano"
  - "Tasks 1 e 2 foram para um único commit — o arquivo foi escrito numa passada só porque contrato e implementação do mesmo módulo pequeno são inseparáveis sem reescrita artificial"

patterns-established:
  - "corpo_da_chamada() como método público separado de classificar() — mesmo objeto de kwargs sai idêntico chamado direto ou via classificar(), verificado manualmente com ja_conhecido populado (07-03 depende deste contrato para estimar custo)"

requirements-completed: []  # GENAI-02 permanece Pending — ver nota abaixo

# Metrics
duration: ~25min
completed: 2026-08-18
---

# Phase 7 Plan 02: Cliente Claude de classificação de pasta Summary

**`ClassificacaoDePastaClaude`: uma chamada em lote por sessão a Sonnet 5, saída estruturada por JSON schema, filtro anti-alucinação + D-02/D-06 reaplicados sobre a resposta, e nenhum caminho que levante exceção.**

## Performance

- **Duration:** ~25min
- **Started:** 2026-08-18 (sessão única)
- **Completed:** 2026-08-18T20:36:35Z
- **Tasks:** 3/3
- **Files modified:** 2 (2 criados)

## Accomplishments
- `fotoorganizer/classification/location_advisor.py`: contratos (`PastaPayload`, `PropostaDoModelo`, `ClassificadorDePasta`), `ClassificacaoDePastaNula` como padrão, e `ClassificacaoDePastaClaude` com chamada única em lote (D-03), schema JSON estruturado (`categoria` restrita ao vocabulário canônico de `engine.py`), never-crash em todo caminho de falha (rede, `refusal`, JSON inválido, 429)
- Filtro sobre a resposta em três camadas: pasta não pedida é descartada (anti-alucinação), item totalmente ambíguo não vira proposta (D-06), e campo já `ja_conhecido` é zerado mesmo que o modelo o tenha devolvido (D-02 reaplicada no código, não só no prompt)
- Oito testes verdes provando GENAI-02 (payload por allowlist com comparação de conjunto de chaves por igualdade + assert negativo dos termos caminho/thumb/miniatura/base64/image/.jpg/.cr2/.heic), modelo Sonnet 5 + thinking desabilitado, D-03, never-crash parametrizado, filtro anti-alucinação, D-06 e D-02
- `MODELO_PADRAO = "claude-sonnet-5"` com o precedente D-059/D-060 citado a fortiori: nome de pasta sozinho é entrada mais esparsa que o cluster de 104 medido, então o risco de o modelo afirmar sem base é maior aqui, não menor

## Task Commits

Tasks 1 e 2 foram commitadas juntas — ver "Deviations from Plan":

1. **Task 1+2: Contratos + ClassificacaoDePastaClaude** - `a3776a1` (feat)
2. **Task 3: Testes** - `6d882f5` (test)

## Files Created/Modified
- `fotoorganizer/classification/location_advisor.py` - contratos, `ClassificacaoDePastaNula`, `ClassificacaoDePastaClaude`, `_SYSTEM`/`_SCHEMA`
- `tests/test_classification_pasta_genai.py` - 8 testes (`_RespostaFalsa`/`_ClienteFalso` locais, no molde de `tests/test_lexico.py`), nenhum toca rede real

## Decisions Made
- `categoria` do JSON schema é `enum` restrito a `("Viagens", "Família", "Eventos")` — lido de `engine.py::_CATEGORIAS_PASTA`, não inventado, para o resultado do GenAI convergir com o vocabulário que a cascata determinística já reconhece.
- Ordem de filtro na resposta segue literalmente o `<action>` do plano: (1) pasta não pedida descartada primeiro, (2) item com os 4 campos de valor (`cidade`/`pais`/`categoria`/`evento`) todos `null` descartado por D-06, (3) só então cada campo que aparece em `ja_conhecido` daquela pasta é zerado (D-02) — nessa ordem, um item que só ficou "vazio" por causa do zeramento de D-02 ainda pode ter sobrevivido ao filtro de D-06 se algum outro campo não-conhecido veio preenchido (comportamento coberto por `test_nao_propoe_campo_ja_conhecido`, que usa `cidade` preenchida ao lado de `categoria` zerada).
- Verificação manual extra (fora dos 8 testes fixos pelo plano): confirmado que `corpo_da_chamada()` produz o mesmo dict chamado diretamente ou via `classificar()`, com `ja_conhecido` populado serializando corretamente e `corpo_da_chamada([])` devolvendo um corpo válido com `"pastas": []` — contrato do qual 07-03 depende para estimar custo sem chamar a API.

## Deviations from Plan

### Processo (não é Regra 1-4, é registro de estrutura de commit)

**Tasks 1 e 2 foram para um único commit (`a3776a1`), não dois.** O plano lista Task 1 (contratos) e Task 2 (implementação) como itens separados do mesmo arquivo, mas o arquivo foi escrito numa única passada porque contrato e implementação de um módulo pequeno como este são inseparáveis sem reescrita artificial (declarar `ClassificacaoDePastaClaude` vazia, commitar, depois preenchê-la, não agrega nada). Ambas as tasks foram verificadas contra seus próprios critérios de aceite antes do commit único. Nenhum comportamento foi pulado.

### Auto-fixed Issues

**1. [Rule 1 - ajuste de texto] Docstrings continham as strings literais que os greps de aceite do plano checavam, inflando a contagem**
- **Found during:** Task 2, verificação dos critérios de aceite (`grep -n "messages.create"` esperava 1 linha; `grep -n "asdict\|__dict__"` esperava 0)
- **Issue:** A docstring de `corpo_da_chamada` mencionava "messages.create" em prosa, e o comentário/docstring de topo do módulo mencionava "asdict()"/"`__dict__`" ao explicar a regra de nunca usá-los — ambos batiam nos greps do plano e inflavam a contagem além do esperado.
- **Fix:** Reescrita da prosa para descrever o mesmo comportamento sem usar as strings literais buscadas pelo grep (ex.: "chamada de criação de mensagem do SDK" em vez de "messages.create"; "serialização genérica de dataclass/objeto" em vez de "asdict()/__dict__"). Nenhuma mudança de comportamento, só de texto.
- **Files modified:** `fotoorganizer/classification/location_advisor.py`
- **Commit:** `a3776a1`

## User Setup Required

None - nenhuma configuração de serviço externo neste plano (usa `anthropic>=0.116` já instalado e em uso por `advisor.py`/`lexico.py`; T-07-02-SC aceito sem instalação nova, conforme `07-RESEARCH.md`).

## Next Phase Readiness

- **GENAI-02 permanece Pending em REQUIREMENTS.md.** Este plano entrega o cliente que comprovadamente só envia nome de pasta e metadado catalogado — mas nada no repositório ainda CHAMA `ClassificacaoDePastaClaude.classificar()` a partir de um fluxo real do dono (endpoint, botão, sessão confirmada). O texto de GENAI-02 ("Sistema envia somente...") descreve um comportamento fim-a-fim que só existe quando 07-04 conectar este cliente a um trigger de UI/endpoint com confirmação de custo (D-04) e opt-in (`classificacao_pasta_genai`). Mesma disciplina que 07-01 aplicou a GENAI-03: fundação primeiro, requisito marcado só quando o comportamento observável pelo dono existir de ponta a ponta.
- Contrato de `<interfaces>` (`PastaPayload`, `PropostaDoModelo`, `ClassificadorDePasta`, `ClassificacaoDePastaNula`, `ClassificacaoDePastaClaude`, `corpo_da_chamada()`) está pronto para consumo direto por 07-03 (estimativa de custo via `count_tokens` sobre o mesmo dict de `corpo_da_chamada()`) e por 07-04/07-05 (endpoint que monta `PastaPayload` a partir de `ClassificacaoPastaRepository.conhecidas()`/`propostas()` de 07-01 e grava o resultado via `salvar_propostas()`).
- `SCORES_REFERENCIA["llm_pasta"]` (Open Question 1 do `07-PATTERNS.md`) continua sem medição própria — não bloqueia este plano, mas 07-04/07-05 precisam resolver isso antes de gravar `Evidence` com essa origem.

---
*Phase: 07-classifica-o-de-pasta-por-genai*
*Completed: 2026-08-18*

## Self-Check: PASSED

All created files found on disk (`fotoorganizer/classification/location_advisor.py`, `tests/test_classification_pasta_genai.py`); both task commits (`a3776a1`, `6d882f5`) confirmed in git log.
