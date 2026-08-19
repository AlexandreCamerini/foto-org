---
status: partial
phase: 02-correção-de-dados-medidos
source: [02-VERIFICATION.md]
started: 2026-08-16T00:00:00Z
updated: 2026-08-16T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Confirmação visual do filtro "Tudo" num catálogo populado
expected: com a Biblioteca aberta em `alcance=tudo` (o padrão), a grade
mostra o acervo real mais referências externas sem arquivo local (fotos
só no iCloud, itens do Lightroom em volume desmontado) — e NÃO mostra
miniatura/derivado interno de outro app (arquivo real dentro de pacote
`.photoslibrary`/`.aplibrary`/`.lrdata`).
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps

Nenhum gap conhecido — bloqueado só pela ausência de catálogo populado
(`catalog.db` de produção foi zerado em 2026-08-16, nova varredura ainda
não rodou). Cobertura automatizada (843 testes, incluindo 3 novos que
travam os dois lados do predicado) está completa e verde.
