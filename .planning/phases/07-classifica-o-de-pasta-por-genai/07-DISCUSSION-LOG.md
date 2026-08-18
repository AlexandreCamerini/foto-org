# Phase 7: Classificação de pasta por GenAI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-18
**Phase:** 7-Classificação de pasta por GenAI
**Areas discussed:** Seleção de pastas pra sessão, Custo estimado — formato, Resposta incerta do GenAI, Conflito com evidência já existente

---

## Seleção de pastas pra sessão

| Option | Description | Selected |
|--------|-------------|----------|
| Sistema sugere, dono confirma a lista | Pré-filtro automático + checkbox por linha | ✓ |
| Dono escolhe pasta por pasta manualmente | Sem pré-filtro, mais trabalho manual | |

**User's choice:** Sistema sugere, dono confirma a lista (Recomendado)
**Notes:** Usuário trouxe uma decisão adicional não coberta pelas opções originais: reduzir custo mandando **uma única chamada por sessão** cobrindo todas as pastas candidatas (não uma chamada por pasta), com tela de antes/depois por pasta para o dono escolher o que aceitar. Confirmado explicitamente numa pergunta dedicada — não reabre a decisão Batch API vs. síncrono do roadmap.

---

## Custo estimado — formato

| Option | Description | Selected |
|--------|-------------|----------|
| Valor estimado em R$/US$ | Baseado em tokens estimados × preço Sonnet 5 | ✓ |
| Contagem de pastas + tokens, sem converter | Mais técnico, menos direto | |

**User's choice:** Valor estimado em R$/US$ (Recomendado)

| Option | Description | Selected |
|--------|-------------|----------|
| Sem teto automático | Dono vê o valor e decide, mesmo modelo do Advisor | ✓ |
| Teto que pede confirmação extra | Mais fricção, mais segurança | |

**User's choice:** Sem teto automático (Recomendado)

---

## Resposta incerta do GenAI

| Option | Description | Selected |
|--------|-------------|----------|
| Não gera evidência pra essa pasta | Fica sem categoria, sem poluir Revisão | ✓ |
| Gera evidência de confiança baixa mesmo assim | Sempre produz sugestão, mesmo chutada | |

**User's choice:** Não gera evidência pra essa pasta (Recomendado)

---

## Conflito com evidência já existente

| Option | Description | Selected |
|--------|-------------|----------|
| Entra, GenAI complementa o que falta | Pasta com QUALQUER campo vazio entra; nunca sobrescreve | ✓ |
| Só pasta 100% sem evidência nenhuma | Escopo mais estreito | |

**User's choice:** Entra, GenAI complementa o que falta (Recomendado)

## Claude's Discretion

- Estrutura exata do prompt/schema da chamada em lote.
- Método exato de estimativa de tokens para a prévia de custo.
- Layout exato da tela antes/depois (reuso de componente de Revisão vs. novo).

## Deferred Ideas

None — discussão ficou dentro do escopo da fase.
