# Phase 7: Classificação de pasta por GenAI - Context

**Gathered:** 2026-08-18
**Status:** Ready for planning

<domain>
## Phase Boundary

O nome da pasta (e metadado já catalogado) vira evidência de
cidade/evento via Claude Sonnet 5, em sessão interativa opt-in com custo
estimado confirmado antes de rodar, entrando no motor como `Evidence`
própria — nunca reaproveitando o tipo de resultado do Advisor de
cluster existente.

</domain>

<decisions>
## Implementation Decisions

### Seleção de pastas para a sessão
- **D-01:** Sistema pré-filtra automaticamente as pastas candidatas —
  qualquer pasta com AO MENOS UM campo vazio (categoria OU
  cidade/país) entra na lista, não só pasta 100% sem evidência. Dono
  confirma a lista antes da sessão rodar, podendo desmarcar item
  pontual (checkbox por linha, mesmo padrão de D-02 da Fase 6).
- **D-02:** Evidência parcial nunca é sobrescrita — GenAI só complementa
  o campo que falta (categoria OU cidade/país), nunca substitui um
  campo já preenchido por outra fonte. Mesma disciplina de EXIF-02/D-075.

### Forma da chamada (redução de custo)
- **D-03:** Uma sessão manda **uma única chamada** ao Claude cobrindo
  TODAS as pastas candidatas confirmadas, não uma chamada por pasta.
  Saída estruturada com uma proposta por pasta. Continua síncrono e
  interativo — não reabre a decisão "Batch API vs. síncrono" já fechada
  no roadmap (a fase segue interativa por sessão, só muda de N chamadas
  para 1 chamada por sessão).
- Tela de revisão mostra antes/depois por pasta (nome atual vs. proposta
  do LLM); dono escolhe quais aceitar — mesmo espírito de review de
  sugestão já existente em Revisão, não uma tela nova do zero.

### Custo estimado
- **D-04:** Custo mostrado em **valor estimado (R$/US$)**, calculado a
  partir de tokens estimados (nomes de pasta + metadado da chamada
  única) × preço do Sonnet 5 — mesmo padrão do Advisor existente, não
  "N tokens" cru.
- **D-05:** Sem teto automático que bloqueia a sessão. Dono vê o valor e
  decide, sem segunda confirmação forçada. Sessões tendem a ser pequenas
  (pastas sem evidência de uma importação), risco de custo disparado é
  baixo.

### Resposta incerta do GenAI
- **D-06:** Pasta cuja resposta do Claude for ambígua/"não sei" não gera
  evidência nenhuma — fica "sem categoria"/campo vazio como já estava.
  Mesma disciplina de D-074/D-077 (nunca inventar confiança sem base).
  Não polui a Revisão com sugestão vazia ou de confiança inventada.

### Persistência do resultado (pós-pesquisa de fase, 2026-08-18)
- **D-07:** `SuggestionEngine.gerar()` apaga e reconstrói `Evidence` a
  cada rodada para mídia ainda não decidida — gravar o resultado do
  GenAI direto em `Evidence` faria ele sumir na próxima regeneração,
  cobrando de novo pelo mesmo resultado. Dono confirmou (via
  `AskUserQuestion`, não assumido): tabela nova de persistência, mesmo
  padrão já usado por `NomeClassificado`/`LexicoRepository` — a resposta
  do Claude sobrevive à regeneração, `Evidence` é reconstruída a partir
  dela sem nova chamada à API.

### Claude's Discretion
- Estrutura exata do prompt/schema da chamada em lote (uma pasta por
  item da saída estruturada) fica a critério da pesquisa/planejamento —
  `LexicoClaude._lote()` (`fotoorganizer/classification/lexico.py`) já é
  o padrão a seguir, confirmado pela pesquisa de fase.
- Método exato de estimativa de tokens para a prévia de custo: pesquisa
  de fase recomenda `client.messages.count_tokens` (exato, grátis, já
  disponível no SDK pinado) para o lado de entrada; saída não é
  pré-contável, UI deve deixar isso explícito.
- Valor numérico exato de `SCORES_REFERENCIA["llm_pasta"]` fica pendente
  de medição própria (mesmo método de D-059/D-060), não decidido por
  analogia — planner deve encaixar isso como tarefa de medição, não
  como constante inventada.
- Layout exato da tela antes/depois (reuso de componente de Revisão vs.
  novo) fica a critério do UI-SPEC.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Precedente operacional (Advisor existente)
- `fotoorganizer/classification/advisor.py` — `ClaudeAdvisor`, opt-in
  gate, `ClusterInfo` payload, contrato never-crash. GENAI-02/03 seguem
  o mesmo modelo operacional, mas com tipo de resultado IRMÃO
  (`LocationAdvisorResult` ou equivalente), nunca overload de
  `AdvisorResult`.
- `docs/DECISOES.md` D-059/D-060 — Sonnet 5 escolhido sobre Haiku para
  o Advisor de cluster; GENAI-02 herda essa conclusão a fortiori (nome
  de pasta sozinho é evidência mais esparsa que o cluster completo).

### Requisitos e roadmap
- `.planning/REQUIREMENTS.md` § GENAI-01..03
- `.planning/ROADMAP.md` § Phase 7 — "Abordagem travada" (interativa
  por sessão, Sonnet 5, tipo de evidência próprio, opt-in próprio,
  never-crash).

### Pesquisa de milestone
- `.planning/research/STACK.md` — padrão de API Anthropic recomendado
  para chamada de classificação barata/opt-in, structured output,
  aplicabilidade de prompt caching.
- `.planning/research/ARCHITECTURE.md` — onde o classificador de pasta
  se encaixa relativo à integração existente do Advisor.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClaudeAdvisor` (advisor.py) — plumbing de chamada à API Anthropic,
  opt-in gate, contrato never-crash — reusar a mecânica, não o tipo de
  resultado.
- Padrão de review por linha (checkbox, aprovar/rejeitar) já usado em
  Revisão — reusar pra tela antes/depois desta fase.

### Established Patterns
- `SCORES_REFERENCIA` na cascata do `SuggestionEngine` — GENAI-03 precisa
  de entrada própria (ex. `llm_pasta`, distinta de `llm` do Advisor).

### Integration Points
- Novo tipo de resultado em `classification/` (nome exato a definir no
  planejamento — ex. `LocationAdvisorResult`).
- Flag de opt-in própria (não reusa o consentimento do Advisor de
  cluster).

</code_context>

<specifics>
## Specific Ideas

- Dono quer explicitamente reduzir o número de chamadas à API batendo
  todas as pastas candidatas de uma importação numa única chamada, com
  uma tela de revisão antes/depois por pasta — não é detalhe de
  implementação, é decisão de custo que ele trouxe diretamente.

</specifics>

<deferred>
## Deferred Ideas

None — discussão ficou dentro do escopo da fase.

</deferred>

---

*Phase: 7-Classificação de pasta por GenAI*
*Context gathered: 2026-08-18*
