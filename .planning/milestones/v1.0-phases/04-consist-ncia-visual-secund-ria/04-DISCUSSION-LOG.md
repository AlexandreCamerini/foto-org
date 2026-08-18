# Phase 4: Consistência visual secundária - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-16
**Phase:** 04-consistência-visual-secundária
**Areas discussed:** Verificação de estado real dos 8 achados CONS, Selos de identidade (CONS-01/02), Hierarquia de botão (CONS-03/07), Recuperação de estado ruim (CONS-04/05), Responsividade (CONS-06), Token de peso de ênfase (CONS-08)

---

## Verificação de estado real antes da discussão

**User's choice:** N/A — investigação de código via Explore agent, não pergunta.
**Notes:** Diferente das 3 fases anteriores (onde a maioria dos achados "pendentes" já estava corrigida), aqui os 8 achados CONS-01..08 confirmaram-se todos genuinamente abertos — nenhum commit desde 2026-08-06 (data da AVALIACAO_UX.md) tocou nesses arquivos com essa intenção. Escopo da fase permanece integral, nada reduzido.

---

## Selos de identidade (CONS-01/02)

| Option | Description | Selected |
|--------|-------------|----------|
| Nome da fonte de origem | Mostra de onde cada cópia veio (ex. "Apple Fotos") | ✓ |
| Rótulo genérico "Também em outro catálogo" | Mais simples, menos informativo | |

**User's choice:** Nome da fonte de origem.
**Notes:** N/A

| Option | Description | Selected |
|--------|-------------|----------|
| Selo em cada sugestão colidida | Marca linha por linha | ✓ |
| Indicação única no grupo | Um aviso só no cabeçalho | |

**User's choice:** Selo em cada sugestão colidida.

| Option | Description | Selected |
|--------|-------------|----------|
| `metodo=="album_externo"` → "Álbum"; resto → "Evento detectado" | Critério determinístico, zero mudança de backend | |
| Quero ver outros valores de metodo antes | Investigar mais | |
| (livre) LLM decide viagem-vs-evento lendo dados disponíveis | Nova capacidade, fora do escopo desta fase | (redirecionado) |

**User's choice:** Respondeu com uma proposta de escopo maior — usar LLM pra decidir se é viagem ou evento lendo os dados disponíveis, em vez de reaproveitar o campo `metodo` existente.
**Notes:** Identificado como a mesma ideia já levantada e adiada na discussão da Fase 1 (`01-CONTEXT.md` `<deferred>`). Redirecionado: anotado como deferred idea reforçada (2ª aparição), e perguntado de novo especificamente para o critério de CONS-02 nesta fase — usuário então confirmou `metodo=="album_externo"` como critério válido pra fechar o achado agora, sem esperar a fase de LLM.

---

## Hierarquia de botão (CONS-03/07)

| Option | Description | Selected |
|--------|-------------|----------|
| Só operação física (copiar arquivo) fica solid | Alinhado ao invariante "catalogar→sugerir→revisar→executar" | ✓ |
| Qualquer reescrita de dado do catálogo fica solid | Mais amplo | |

**User's choice:** Só operação física.

| Option | Description | Selected |
|--------|-------------|----------|
| Job em andamento = vermelho; edição/modal = neutro | Alinhado ao que já existe na maioria das telas | ✓ |
| Tudo neutro, sem exceção | Simplifica mas perde sinal de irreversibilidade | |

**User's choice:** Job em andamento = vermelho; edição/modal = neutro.

---

## Recuperação de estado ruim (CONS-04/05)

| Option | Description | Selected |
|--------|-------------|----------|
| Replicar padrão de Trips.tsx | Consistência, zero design novo | |
| Desenhar estado próprio pro Loupe/Duplicatas | Contextos diferentes (tela cheia vs. lado a lado) | ✓ |

**User's choice:** Desenhar estado próprio.
**Notes:** Follow-up perguntado sobre quem desenha o visual exato — usuário escolheu delegar ao UI researcher da fase (`/gsd:ui-phase 4`), travando só que precisa ser explícito (nunca ícone quebrado cru) e que Loupe/Duplicatas podem divergir entre si.

| Option | Description | Selected |
|--------|-------------|----------|
| Mesma ação nos 3 — "Adicionar pasta" | Reaproveita fluxo existente | ✓ |
| Ação própria por tela | Mais específico, mais trabalho | |

**User's choice:** Mesma ação nos 3.

---

## Responsividade (CONS-06)

| Option | Description | Selected |
|--------|-------------|----------|
| Inspetor colapsa automaticamente | Ganha altura, perde contexto | |
| Barra empilha em 2 linhas, Inspetor visível | Nada some, consome mais altura | ✓ |

**User's choice:** Barra empilha em 2 linhas.

| Option | Description | Selected |
|--------|-------------|----------|
| Tailwind `lg` (1024px) | Token padrão, sem precedente de custom breakpoint | ✓ |
| Breakpoint customizado 900px | Mais preciso ao sintoma medido | |

**User's choice:** Tailwind `lg` (1024px).

---

## Token de peso de ênfase (CONS-08)

| Option | Description | Selected |
|--------|-------------|----------|
| Sim, migrar tudo pro token único (`--font-weight-titulo: 500`) | Consistente com o que a Fase 3 já travou | ✓ |
| Quero discutir isso também | Adicionar como 5ª área | |

**User's choice:** Sim, migrar tudo pro token único.
**Notes:** Confirmado antes das 4 áreas de discussão principal, como pergunta de fechamento rápido (a Fase 3 já tinha travado o valor 500 e anunciado a reconciliação full-codebase como trabalho desta fase).

---

## Claude's Discretion

- Nome exato da classe/prop CSS para o token de peso (CONS-08), desde que o valor computado final seja 500.
- Estrutura exata do empilhamento em 2 linhas da barra superior (CONS-06), desde que o Inspetor continue visível.
- Layout/ícone exato do estado 404 (CONS-04) — delegado ao UI researcher.

## Deferred Ideas

- **Classificação de viagem/evento (e não-fotos/vídeo) via LLM lendo os dados disponíveis** — levantado pelo dono durante CONS-02, 2ª vez que aparece (1ª foi na Fase 1). Candidato a fase própria ou revisão de arquitetura da classificação — não decidido aqui, só reforçado como sinal forte de prioridade futura.
