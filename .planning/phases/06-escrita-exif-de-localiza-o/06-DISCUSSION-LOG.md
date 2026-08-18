# Phase 6: Escrita EXIF de localização - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-18
**Phase:** 6-Escrita EXIF de localização
**Areas discussed:** Aprovação do plano, Formatos sem suporte, Escrita sob sincronização, Escopo por campo

---

## Aprovação do plano

| Option | Description | Selected |
|--------|-------------|----------|
| Lote inteiro, uma aprovação | Mesmo padrão de Operations.tsx hoje | ✓ |
| Arquivo por arquivo | Mais controle, mas novo padrão de interação e lento | |

**User's choice:** Lote inteiro, uma aprovação (Recomendado)

| Option | Description | Selected |
|--------|-------------|----------|
| Pode desmarcar itens | Checkbox por linha, igual review de sugestões | ✓ |
| Tudo ou nada | Mais simples, sem controle fino | |

**User's choice:** Pode desmarcar itens (Recomendado)
**Notes:** Aprovação em lote com checkbox por linha para exceção pontual.

---

## Formatos sem suporte

| Option | Description | Selected |
|--------|-------------|----------|
| Testar antes, decidir por formato | Teste empírico contra cópia descartável, mesmo padrão D-026/D-074 | ✓ |
| Excluir CR3/HEIC do escopo já | Mais rápido, mas deixa fatia grande do acervo de fora | |

**User's choice:** Testar antes, decidir por formato (Recomendado)

| Option | Description | Selected |
|--------|-------------|----------|
| Aparece como "formato não suportado" | Linha visível com motivo explícito | ✓ |
| Simplesmente não aparece no plano | Mais limpo, mas invisível | |

**User's choice:** Aparece como "formato não suportado" (Recomendado)

| Option | Description | Selected |
|--------|-------------|----------|
| Todo formato RAW/proprietário do acervo | Evita descobrir formato quebrado depois de a fase fechar | ✓ |
| Só CR3 e HEIC | Escopo fechado, mais rápido | |

**User's choice:** Todo formato RAW/proprietário do acervo (Recomendado)

| Option | Description | Selected |
|--------|-------------|----------|
| Diff completo de tags + abre no visualizador padrão | Pega corrupção silenciosa que diff sozinho não pegaria | ✓ |
| Só o diff de tags | Mais rápido, mas corrupção estrutural passaria despercebida | |

**User's choice:** Diff completo de tags + abre no visualizador padrão (Recomendado)

| Option | Description | Selected |
|--------|-------------|----------|
| Oferece sidecar XMP como alternativa | Aproveita o que D-075 já deixou disponível | ✓ |
| Só marca como não suportado, sem alternativa | Sidecar XMP fica fora do escopo desta fase | |

**User's choice:** Oferece sidecar XMP como alternativa (Recomendado)
**Notes:** Esta escolha expande o escopo aprovado no roadmap (que listava sidecar XMP como "não é entrega desta fase"). Flagrado explicitamente e reconfirmado numa pergunta dedicada — ver seção "Confirmação de expansão de escopo" abaixo. ROADMAP.md e REQUIREMENTS.md (EXIF-05) atualizados.

---

## Escrita sob sincronização

| Option | Description | Selected |
|--------|-------------|----------|
| Detecta e avisa antes, dono decide | Plano marca com aviso, dono inclui/desmarca via checkbox de D-02 | ✓ |
| Bloqueia totalmente | Mais seguro, mas exclui fatia grande do acervo sem alternativa | |
| Não detecta, segue o risco | Mais simples, mas aceita risco sem avisar | |

**User's choice:** Detecta e avisa antes, dono decide (Recomendado)

---

## Escopo por campo

| Option | Description | Selected |
|--------|-------------|----------|
| Os 3 juntos sempre | Mais simples, sem seleção extra na UI | ✓ |
| Dono escolhe quais campos por sessão | Mais controle, mas UI mais complexa sem caso de uso concreto | |

**User's choice:** Os 3 juntos sempre (Recomendado)

---

## Confirmação de expansão de escopo (sidecar XMP)

| Option | Description | Selected |
|--------|-------------|----------|
| Confirma a expansão (atualiza roadmap+requisitos) | Fase 6 passa a incluir writer de sidecar XMP mínimo | ✓ |
| Mantém fora do escopo (Recomendado por escopo) | Formato reprovado fica só marcado, sem alternativa nesta fase | |

**User's choice:** Confirma a expansão (atualizo roadmap+requisitos)
**Notes:** ROADMAP.md § Phase 6 atualizado (Requirements, Explicitly out of scope, Success Criteria, Abordagem travada). REQUIREMENTS.md ganhou EXIF-05 e entrada na Traceability.

## Claude's Discretion

- Mecanismo exato de detecção de "pasta sincronizada" (atributos de arquivo, caminho conhecido, presença de marcador de app de sync).
- Formato exato do teste empírico de escrita por formato (script standalone vs. parte do plano da fase).

## Deferred Ideas

None — discussão ficou dentro do escopo da fase (com uma expansão de escopo explicitamente confirmada, não uma ideia deferida).
