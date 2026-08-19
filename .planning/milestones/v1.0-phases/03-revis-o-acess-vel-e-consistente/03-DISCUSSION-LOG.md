# Phase 3: Revisão acessível e consistente - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-16
**Phase:** 03-revisão-acessível-e-consistente
**Areas discussed:** Estado real dos 7 achados REV (verificação de código antes de discutir), critério de classificação texto-3 vs texto-2 (REV-02)

---

## Verificação de estado real antes da discussão

**User's choice:** N/A — investigação de código + `git log`, não pergunta.
**Notes:** Confirmei, com evidência de commit, que REV-01 (já no código, sem commit específico rastreado), REV-04 (zero `rounded-lg`), REV-05 (`formatarData()` já usado), REV-06 (commit `ae60319`) e REV-07 (commit `a7d6e5e`) já estavam corrigidos antes desta sessão. Apresentei a tabela completa ao dono, que escolheu encolher a Fase 3 só pros 2 itens reais (opção "Recommended").

---

## Critério de classificação REV-02

| Option | Description | Selected |
|--------|-------------|----------|
| Só texto que o usuário precisa LER pra decidir algo | Conteúdo real vira texto-2; auxílio secundário/decorativo/transiente fica texto-3 | ✓ |
| Tudo que não for genuinamente desabilitado vira texto-2 | Mais agressivo, mais contraste em tudo | |

**User's choice:** "Só texto que o usuário precisa LER pra decidir algo".
**Notes:** Justificativa citada: mais contraste em tudo competiria mais com a foto, contra o princípio "a foto é a cor da interface" de `docs/DIRECAO_DE_ARTE.md`. Depois da escolha, investiguei os 19 usos restantes de `texto-3` (pós-commit `ae60319`) e apliquei o critério linha a linha — 9 viram texto-2, 10 ficam texto-3 — apresentado como auditoria completa, confirmado como "pronto pra escrever o CONTEXT.md" sem mais perguntas.

---

## Claude's Discretion

- Formatação exata do diff em cada uma das 19 linhas classificadas.
- Se o botão de troca de aba deve sempre limpar a busca, ou só quando muda de aba de fato.

## Deferred Ideas

Nenhuma — discussão ficou dentro do escopo restrito.
