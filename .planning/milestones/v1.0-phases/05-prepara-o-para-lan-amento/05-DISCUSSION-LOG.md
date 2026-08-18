# Phase 5: Preparação para lançamento - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-17
**Phase:** 5-Preparação para lançamento
**Areas discussed:** Empacotamento (LANC-01), Onboarding (LANC-03), Baseline de performance (LANC-04)

---

## Empacotamento (LANC-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Só Marco 1 | Verificar/fechar o `.app` sem assinatura contra o critério de aceite do Marco 1. Assinatura/notarização adiada até o dono decidir pagar o Developer Program. | ✓ |
| Marco 1 + Marco 2 | Aprovar o custo de US$99/ano agora e sair da fase com o `.app` assinado e notarizado. | |
| Só verificar o que já existe | Rodar só a verificação do scaffold existente contra o critério de aceite, sem tocar em mais nada de empacotamento. | |

**User's choice:** Só Marco 1
**Notes:** PROJECT.md § Constraints já trava que custo recorrente (Apple Developer Program) exige aprovação explícita do dono antes de entrar em fase — não solicitado aqui.

### Follow-up: bug real encontrado na verificação

| Option | Description | Selected |
|--------|-------------|----------|
| Corrigir dentro da fase | Bug no caminho crítico do empacotamento bloqueia o critério de aceite — corrige na mesma fase. | ✓ |
| Só documentar e seguir | Reporta o achado, não corrige agora — LANC-01 fica parcial. | |

**User's choice:** Corrigir dentro da fase
**Notes:** —

---

## Onboarding (LANC-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Tela guiada mínima | Estado vazio ganha passo-a-passo curto (adicionar pasta → progresso → grade populada), sem wizard multi-etapa. | ✓ |
| Wizard multi-etapa | Fluxo dedicado com telas separadas antes de cair na Biblioteca. | |
| Detectar automaticamente | Oferecer escanear locais comuns (~/Pictures, Fotos do Apple) com um clique. | |

**User's choice:** Tela guiada mínima
**Notes:** Claude identificou durante a discussão que a Fase 4 (plano 04-06) já entregou boa parte desse caminho (botão "Adicionar pasta…" nos 3 estados vazios, modal compartilhado com progresso). Surfaced ao dono antes de perguntar o que falta.

### Follow-up: o que falta pra fechar de verdade

| Option | Description | Selected |
|--------|-------------|----------|
| Nada estrutural, só validar | O caminho já existe — só testar com usuário real sem instrução e corrigir fricções, sem desenhar fluxo novo. | ✓ |
| Mensagem de primeira vez | Texto/CTA reconhece que é a primeira execução do app, distinto do estado vazio genérico. | |
| Feedback de progresso melhor | Contagem de arquivos, tempo estimado durante o scan inicial. | |

**User's choice:** Nada estrutural, só validar
**Notes:** As duas outras opções ficaram como ideias adiadas — só entram se a validação revelar bloqueio real.

---

## Baseline de performance (LANC-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Acervo real de produção | Rodar a baseline na rescan real do `catalog.db` (zerado em 2026-08-16, ainda sem rescan). | ✓ |
| Fixture sintética | Gerar conjunto sintético de tamanho fixo para baseline reprodutível. | |
| As duas | Fixture sintética para CI/regressão + medição pontual contra o acervo real. | |

**User's choice:** Acervo real de produção
**Notes:** —

### Follow-up: onde registrar os números

| Option | Description | Selected |
|--------|-------------|----------|
| Novo docs/PERFORMANCE.md | Documento dedicado, mesmo padrão de docs/AVALIACAO_UX.md. | ✓ |
| Direto no REQUIREMENTS.md | Anexa os números como evidência junto do próprio LANC-04. | |

**User's choice:** Novo docs/PERFORMANCE.md
**Notes:** —

---

## Claude's Discretion

- Ordem de execução dos 4 LANC dentro da fase (paralelo vs sequencial) — nenhuma dependência estrutural levantada.
- Formato exato de `docs/PERFORMANCE.md` — seguir padrão de `docs/AVALIACAO_UX.md`.
- Se a rescan do acervo real travar o fluxo de trabalho, decidir paralelismo interno da fase.

## Deferred Ideas

- Marco 2 (assinatura + notarização) — depende de aprovação de custo do dono.
- Reconexão de volumes desmontados/iCloud (~90 mil registros) — candidato de maior alavancagem do backlog, mas fora de escopo desta fase.
- Mensagem específica de "primeira vez" e feedback de progresso mais rico no onboarding — não pré-aprovado, só entra se a validação revelar bloqueio real.
