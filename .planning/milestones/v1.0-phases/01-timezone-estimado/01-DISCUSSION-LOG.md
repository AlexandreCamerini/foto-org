# Phase 1: Timezone estimado - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-16
**Phase:** 01-timezone-estimado
**Areas discussed:** Confiança/critério de país fraco, classificação
determinística vs. LLM (adiado), fuso com país multi-timezone, fonte de
verdade do spec (ROADMAP.md vs. fase-11-timezone-estimado.md), medição
contra catálogo zerado, revisão da tabela país→fuso, pesquisa de
referência (Immich/PhotoPrism)

---

## Rodada 1 — áreas iniciais propostas

| Option | Description | Selected |
|--------|-------------|----------|
| Fuso quando o país tem mais de um horário oficial | Brasil, EUA, Rússia etc. — como resolver | ✓ |
| Alcance do tz_estimado — só evidência ou também corrige exibição | Inspetor apenas vs. também Loupe/Revisão/ordenação | (superada pela D-03) |
| Confiança quando o país de origem já é média/baixa | Elo mais fraco padrão vs. teto adicional | ✓ |
| Nenhuma — seguir padrão razoável | — | |

**User's choice:** "Fuso com múltiplos horários" e "Confiança quando país já é média/baixa", mais texto livre.
**Notes:** O usuário respondeu com "Other", combinando as duas seleções com uma crítica mais ampla: falta de critério nas análises em geral (informação às vezes já está no nome do diretório/arquivo/EXIF antes de cair pra herança), e que a classificação determinística de viagem/evento/não-fotos/vídeo é um problema — às vezes precisa de LLM. A segunda parte foi identificada como fora do escopo desta fase (ver Deferred Ideas).

---

## Critério de análise (país fraco) — resolvido por código existente

**User's choice:** N/A — resolvido por investigação de código, não por pergunta nova.
**Notes:** `classification/engine.py:693-781` (`_evidencias_geo`) já faz cascata GPS próprio → herança temporal → pasta antes de aceitar um elo fraco. O ponto do usuário já é o padrão estabelecido; não havia decisão nova a tomar aqui para esta fase.

---

## Descoberta do spec autoritativo

| Option | Description | Selected |
|--------|-------------|----------|
| Seguir `docs/prompts/fase-11-timezone-estimado.md` | Spec detalhado, sem Evidence, tabela estática, escopo restrito | ✓ |
| Seguir `ROADMAP.md`/`REQUIREMENTS.md` (texto minerado do ingest) | Exige evidência de origem/confiança visível no Inspetor | |

**User's choice:** Seguir `fase-11-timezone-estimado.md` — "é o spec mais detalhado".
**Notes:** Doc não entrou no ingest original (ficou fora de `docs/prompts/`, excluído do escopo pra caber no cap de 50 docs). Contradiz `ROADMAP.md` no ponto de Evidence/confiança visível. `ROADMAP.md`/`REQUIREMENTS.md` foram corrigidos nesta sessão para refletir a decisão (ver diffs).

---

## Rodada 2 — áreas novas

| Option | Description | Selected |
|--------|-------------|----------|
| Medição do Aceite contra catálogo vazio | Bloqueia a fase, ou código-completo agora + medição depois | (respondida via "não decidir agora" → padrão razoável) |
| Revisão da tabela país→fuso (98 entradas) | Revisão linha a linha vs. confiar no critério documentado | (idem) |
| Nenhuma — seguir padrão razoável pras duas | — | ✓ (implícito) |

**User's choice:** Pediu pesquisa nas referências Immich/PhotoPrism em vez de responder diretamente — as duas áreas ficaram resolvidas pelo padrão razoável (medição adiada, tabela sem revisão linha a linha), registrado em D-08 e D-13.
**Notes:** —

---

## Pesquisa de referência (Immich/PhotoPrism)

**User's choice:** N/A — pedido de pesquisa, não escolha entre opções.
**Notes:** Lidos `docs/referencia-immich/02-metadados-e-midia.md`, `03-modelo-de-dados.md`, `docs/referencia-photoprism/02-metadados-imagem-e-visao.md` (não tinham entrado no ingest original). Confirmação: modelo de dois instantes do Immich bate com D-038; tabela estática evita a dependência `geo-tz`/`timezonefinder` que o Immich paga. Achado novo, não aplicável a esta fase: checagem de plausibilidade de offset (limite 27h) do PhotoPrism — relevante só quando a fase futura de `OffsetTimeOriginal` existir (registrado em Deferred Ideas).

---

## Claude's Discretion

- Ordem de implementação das 4 partes do fase-11 (tabela, cálculo, API, testes).
- Nomes de funções/variáveis auxiliares em `timezones.py`.
- Preenchimento linha a linha dos 98 países da tabela (capital/maior população), sem revisão humana entrada por entrada.

## Deferred Ideas

- Determinismo da classificação de viagem/evento/não-fotos/vídeo usar LLM quando regra determinística não alcança — fora do escopo desta fase, candidato a fase própria.
- Ler `OffsetTimeOriginal`/`Z` do QuickTime nos extratores — já adiado pelo próprio fase-11; revisitar checagem de 27h do PhotoPrism quando essa fase for planejada.
- Corrigir `sources/google_takeout.py:_data()` (fuso da máquina do importador) — mesmo adiamento.
- Converter `data_capturada` pra hora local exibida em UI usando `tz_estimado` — decisão de UI separada.
