# Phase 2: Correção de dados medidos - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-16
**Phase:** 02-correção-de-dados-medidos
**Areas discussed:** Estado real dos 4 bugs medidos (verificação de código antes de discutir), definição de "Tudo" (SINAL vs. ACERVO)

---

## Verificação de estado real antes da discussão

**User's choice:** N/A — investigação de código, não pergunta.
**Notes:** Antes de abrir áreas cinzentas, verifiquei diretamente no código (não confiei no texto do REQUIREMENTS.md/ingest) se os 4 "BUG-*" ainda estavam abertos. Achado: BUG-01 (commit `5c7b36d`, 2026-08-06), BUG-02 (`VIDEO_EXTENSIONS` já existe) e BUG-04 (`engine.py:713-725`) já estavam corrigidos, com testes cobrindo cada um. Só BUG-03 seguia aberto. Apresentei a tabela de achados ao dono, que escolheu encolher a Fase 2 só pro BUG-03 (opção "Recommended") em vez de investigar mais fundo os 3 já corrigidos.

---

## Definição de "Tudo" — SINAL vs. ACERVO

| Option | Description | Selected |
|--------|-------------|----------|
| Só acervo, exclui testemunha | "Tudo" = papel=ACERVO; testemunha nunca aparece em nenhum filtro | ✓ |
| Mantém testemunha em "Tudo", com selo visual | Testemunha continua visível, mas marcada | |

**User's choice:** "Só acervo, exclui testemunha".
**Notes:** Achado de contradição interna no código apresentado antes da pergunta: `_query()` tem comentário dizendo que testemunha fica fora de "qualquer filtro", mas `ALCANCES["tudo"] = "tudo que o app conhece"` e `estatisticas()` tratam testemunha como algo "conhecido" — sugerindo inclusão intencional. O dono resolveu a contradição a favor do comentário original (testemunha sempre fora da grade visível).

---

## Claude's Discretion

- Redação exata do novo rótulo `ALCANCES["tudo"]`.
- Implementação exata (reusar `_ACERVO` direto ou função nomeada nova).

## Deferred Ideas

Nenhuma — discussão ficou dentro do escopo restrito desta fase.
