---
name: orquestrar
description: >
  Orquestrador multi-agente do foto-organizer. Use quando a demanda cruzar
  mais de um domínio (arquivos, imagem, ux, arte), quando houver tarefas
  independentes que valha rodar em paralelo, ou quando o usuário pedir
  "orquestre", "use os agentes" ou "trabalhem em paralelo". Decompõe a
  demanda, escolhe o modelo por tarefa, despacha em paralelo, integra,
  verifica e commita. Para uma fatia de um só domínio, use `fatia-vertical`.
---

# Orquestrador do foto-organizer

Você (a sessão principal) é o **orquestrador**: decompõe a demanda, despacha
para os especialistas via a ferramenta Agent, centraliza decisões, reporta
status e integra o resultado. Subagentes não criam subagentes — a
coordenação é sempre sua. Você é o único que commita.

## Especialistas (`subagent_type`)

| Agente | Domínio | Território |
|---|---|---|
| `agente-arquivos` | Arquivos e filesystem | scanner, sources, operations, duplicates (hash), security, repositories, database, server/jobs |
| `agente-imagem` | Análise de imagem | metadata, thumbnails, phash/rajadas, classification, grouping (inclui correlação entre fontes), geolocation, vision, faces |
| `agente-ux` | Usabilidade e UX | `webapp/` (React/TS/Tailwind) e o contrato da API local |
| `agente-arte` | Direção de arte | tokens em `webapp/src/index.css`, consistência visual, revisão por screenshot |

## Processo

1. **Triagem.** Decomponha em tarefas independentes, cada uma no território
   de um especialista. Tarefa que cruza domínios se divide na fronteira
   natural: serviço novo = `agente-arquivos`; tela que o exibe =
   `agente-ux`; estilo do componente = `agente-arte`.
2. **Plano curto ao usuário** (3–6 linhas) antes de despachar: tarefas,
   agente e modelo de cada uma, o que roda em paralelo. Ambiguidade em ponto
   essencial → pergunte; no resto, decida e siga.
3. **Despacho.** Lance os agentes independentes **em uma única mensagem**.
   - Prompts autocontidos: contexto, arquivos relevantes, critério de aceite
     e o aviso de que o retorno é dado cru, não prosa.
   - Dois agentes editando código ao mesmo tempo → `isolation: "worktree"`
     nos dois, e você integra. Módulos disjuntos, risco nulo: dispensável.
   - Tarefas dependentes vão em sequência (arte revisa depois que ux entrega).
4. **Status.** A cada resultado, 1–2 linhas para o usuário (o que foi feito,
   verificação, pendências). Não despeje o relatório do agente.
5. **Integração e qualidade.** Antes de commitar:
   - `scripts/verificar.sh` verde (testes + benchmark de cenários + build da
     UI). Vermelho bloqueia o commit.
   - Confira os invariantes do `CLAUDE.md` no diff: catalogação somente
     leitura, operação física só como plano, sem `shell=True`, nada sai da
     máquina sem opt-in.
   - Mudança visual → captura da UI real como prova.
   - Revisão com olhos frescos: sub-agente de revisão com contexto isolado
     recebendo só o diff e a intenção.
   - Commits pequenos, convencionais, em português, explicando o porquê.
6. **Decisões.** Técnico e reversível: decida você. Produto, escopo ou
   difícil de reverter: escale ao usuário. Registre a decisão na resposta.

## Escolha de modelo (`model` do Agent)

| Situação | Modelo |
|---|---|
| Mecânico: renomear, mover código, docstrings, fixtures simples, varredura de leitura | `haiku` |
| Implementação padrão: feature especificada, testes, refactor local, tela seguindo padrão | `sonnet` |
| Julgamento alto: arquitetura, debugging difícil, algoritmo de agrupamento/confiança, direção de arte, código de operações físicas | `opus` |

Na dúvida, suba um nível para código que toca os invariantes de segurança
(`operations`, `security`, `server`) e desça para o resto.

## Encerramento

Feche com: tarefas concluídas (agente → resultado em 1 linha), estado da
verificação, commits (hash + mensagem), pendências e decisões em aberto.
