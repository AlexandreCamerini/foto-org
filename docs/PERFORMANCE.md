# Baseline de 2026-08-17 — pós-reset do catálogo (fase 5, LANC-04)

## Contexto

`catalog.db` de produção foi zerado em 2026-08-16 (backup preservado em
`catalog-antes-do-reset-20260816-013503.db`, íntegro após esta medição) e
nenhuma varredura completa havia rodado desde então. Esta rodada é a
primeira varredura pós-reset e, ao mesmo tempo, a medição formal de LANC-04
(D-07: medir contra acervo real, nunca fixture sintética).

O acervo medido é uma fração deliberada do total histórico: 1.382 arquivos
em `~/Pictures/2026` (8,1 GB), contra os ~99 mil registros conhecidos e os
~422.738 registros do histórico de auditoria citados em `PROJECT.md` §
Context. A fração é pequena de propósito — ver Task 2 / decisão do dono
abaixo — e a extrapolação de taxa (arq/s) para o acervo total é válida,
mas o tempo absoluto de sugestões/duplicatas em 422 mil registros não é
linear e não deve ser projetado deste número sem nova medição.

## Metodologia

Três decisões de execução tomadas no plano 05-04, registradas aqui para a
próxima rodada repetir:

- **P-1 (varredura in place):** a varredura roda no catálogo real de
  produção — é a própria rescan pós-reset, não um passo extra.
- **P-2 (sugestões/duplicatas em cópia descartável):** `SuggestionEngine.gerar()`
  e `DuplicateDetector.detectar()` escrevem como efeito colateral
  (`Suggestion`, `DuplicateGroup`, `DuplicateMember`); medir in place
  deixaria produção com um lote de sugestões auto-geradas que ninguém
  revisou. Por isso rodam sobre uma cópia (`shutil.copy2`) do catálogo
  recém-varrido, feita **depois** da varredura e **antes** de qualquer
  geração. A cópia foi mantida ao final (invariante 8 do CLAUDE.md — nada
  que possa ser referência real é descartado): `baseline-20260817-171223.db`,
  8,1 MB, em `~/Library/Application Support/FotoOrganizer/`.
- **P-3 (100% local):** `advisor=None` literal, sem flag que ligue o
  advisor LLM opt-in (`privacidade.servicos_externos`) — medida
  reprodutível, sem depender de rede ou custo por token.

Esta medida é posterior à migração 0018 (plano 05-01, 9 índices novos em
FK de `media_files`, `suggestions`, `operation_items`, `audit_log`,
`duplicate_members`, `face_occurrences`), portanto reflete o schema com os
índices de FK já presentes — não é comparável a uma medição pré-0018.

**Comando exato que reproduz esta medição:**

```
.venv/bin/python scripts/medir_baseline_producao.py --pasta "$HOME/Pictures/2026"
```

(sem `--data-dir`: aponta para o `data_dir` real de produção, decisão P-1.)

**Decisão do dono sobre as raízes (Task 2, checkpoint):** entre as 10
fontes do catálogo anterior ao reset (`--listar-fontes`), o dono escolheu
varrer **só `~/Pictures/2026`**, excluindo:

| Fonte | Motivo da exclusão |
|---|---|
| `~/Pictures/2025_05_24` | caminho ausente agora |
| pasta de viagem pessoal em `~/Pictures/` | caminho ausente agora |
| `/Volumes/Externo` | volume não montado |
| `/Volumes/photo/Portfolio/Fotos Organizadas` | volume não montado |
| `/Volumes/photo` | volume não montado |
| `Photos Library.photoslibrary` (APPLE_PHOTOS) | importador, fora da medida de varredura de pasta |
| `Lightroom Catalog.lrcat` (LIGHTROOM) | importador, fora da medida de varredura de pasta |
| `~` (home inteiro) | escolha do dono — não representativo do que o produto organiza |
| `~` (duplicata em minúsculas do caminho do home) | escolha do dono — mesmo motivo acima |

Antes do reset, `catalog.db` zerado e recriado sem backup adicional
(escolha explícita e informada do dono, oferecida a alternativa "com
backup"). O backup pré-reset (`catalog-antes-do-reset-20260816-013503.db`)
segue intacto e foi usado apenas em modo leitura (`--listar-fontes`) para
enumerar as fontes.

## Taxa de indexação (varredura)

| Pasta | Indexados | Pulados | Erros | MB | Segundos | arq/s |
|---|---:|---:|---:|---:|---:|---:|
| `~/Pictures/2026` | 1.382 | 0 | 0 | 8.713,3 | 23,58 | 59 |
| **total** | 1.382 | 0 | 0 | 8.713,3 | 23,58 | 59 |

Total de registros em `media_files` após a varredura: **1.382**.

## Tempo de geração de sugestões

Tempo total: **1,33s**.

Resultado de `gerar()` (sobre a cópia descartável, catálogo de 1.382
registros): `{'sugestoes': 1382, 'viagens': 0, 'eventos': 2, 'herancas_gps': 0, 'preservadas': 0, 'descartadas': 0}`

## Tempo de detecção de duplicatas

Tempo total: **4,54s**.

Resultado de `detectar()`: `{'exato': 0, 'conteudo': 0, 'visual': 13, 'sequencia': 242, 'variante': 0, 'preservados': 0}`

## Máquina

MacBook Pro (Mac14,7), chip Apple M2, 16 GB RAM, macOS 26.5.2 (build
25F84).

## O que observar na próxima rodada

- **Escala:** esta rodada mede 1.382 registros (~0,3% dos ~422.738 do
  histórico de auditoria). Tempo de sugestões/duplicatas não escala
  linearmente com o volume — a próxima rodada num acervo maior (ex.:
  reconexão dos volumes Apple Fotos/Lightroom, ~90 mil registros
  adicionais, candidato ainda sem decisão em `PROJECT.md`) é necessária
  para um número comparável ao volume de produção real.
- **Importadores não cronometrados:** `APPLE_PHOTOS` e `LIGHTROOM` usam
  caminho de import, não `scan_source` de pasta — não entram nesta taxa de
  indexação e precisam de medição própria se forem otimizados.
- **Volumes não montados:** `/Volumes/Externo` e `/Volumes/photo` (e o
  subcaminho `Portfolio/Fotos Organizadas`) não puderam ser medidos por
  estarem desmontados no momento da rodada.
- **Sem caminho incremental:** motor de sugestões e detector de duplicatas
  fazem full-scan em memória a cada rodada (dívida técnica registrada em
  `.planning/codebase/CONCERNS.md`) — os tempos acima são de recomputação
  total, não de reprocessamento incremental.
