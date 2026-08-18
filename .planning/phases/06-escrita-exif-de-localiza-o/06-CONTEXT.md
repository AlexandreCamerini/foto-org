# Phase 6: Escrita EXIF de localização - Context

**Gathered:** 2026-08-18
**Status:** Ready for planning

<domain>
## Phase Boundary

O dono grava no EXIF do arquivo original a localização que o motor já
inferiu (GPS lat/long, cidade, país), exclusivamente em campo vazio, com
plano dry-run → aprovação → execução → verificação, num módulo próprio
(não estende `operations/executor.py`). Autorizado por D-075
(`docs/DECISOES.md`), que revoga parcialmente o invariante 7 do
`CLAUDE.md`.

</domain>

<decisions>
## Implementation Decisions

### Aprovação do plano
- **D-01:** Dono aprova o plano dry-run inteiro de uma vez (mesmo padrão
  de `Operations.tsx` para cópia), não arquivo por arquivo.
- **D-02:** Dentro do lote aprovado, o dono pode desmarcar itens
  pontuais antes de confirmar (checkbox por linha, mesmo padrão de
  review de sugestões) — não é tudo-ou-nada.

### Formatos sem suporte de escrita
- **D-03:** Antes de fechar o escopo de formato, roda um teste empírico
  de escrita contra cópia descartável real cobrindo **todo formato
  RAW/proprietário que aparecer no acervo** (não só CR3/HEIC citados na
  pesquisa) — formato que passa limpo entra no escopo da fase, formato
  que não passa fica de fora, registrado como decisão medida (mesmo
  padrão de D-026/D-074).
- **D-04:** Critério de "passou limpo": diff completo de tags
  antes/depois (só as tags de localização esperadas mudaram) **e**
  confirmação de que o arquivo ainda abre normalmente depois (ex.:
  `exiftool -validate` ou equivalente) — diff de tags sozinho não pega
  corrupção estrutural fora das tags.
- **D-05:** Arquivo com formato reprovado no teste (ou já sabidamente
  sem suporte) aparece no plano dry-run como linha explícita "formato
  não suportado" com o motivo — nunca desaparece silenciosamente da
  lista.
- **D-06:** Arquivo reprovado ganha oferta de sidecar XMP como
  alternativa no mesmo plano (D-075 mantém XMP disponível) — o dono
  decide se quer esse caminho para os casos que EXIF direto não cobre.
  Isto expande o entregável da Fase 6 para incluir escrita de sidecar
  XMP como fallback, não só EXIF direto.

### Escrita sob sincronização (iCloud Drive/Dropbox)
- **D-07:** Sistema detecta se o arquivo está dentro de uma pasta
  sincronizada (iCloud Drive, Dropbox, etc.) e marca isso explicitamente
  no plano dry-run com aviso do risco (dessincronização silenciosa —
  o app de sync pode sobrescrever com a versão antiga ou gerar
  conflito). Dono decide incluir ou desmarcar via o mesmo checkbox de
  D-02 — não é bloqueio automático nem escrita silenciosa sem aviso.

### Escopo por campo
- **D-08:** Cada arquivo tenta os 3 campos (GPS lat/long, cidade, país)
  juntos, no mesmo plano/execução — sem seleção de campo por sessão.

### Claude's Discretion
- Mecanismo exato de detecção de "pasta sincronizada" (checar
  `.icloud`/atributos de arquivo, caminho conhecido do iCloud Drive,
  presença de `.dropbox` etc.) fica a critério da pesquisa/planejamento
  da fase — o dono definiu o comportamento (avisar + deixar escolher),
  não o mecanismo de detecção.
- Formato exato do teste empírico de escrita por formato (script
  standalone vs. parte do plano da fase) fica a critério do
  planejamento.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Decisão que autoriza a fase
- `docs/DECISOES.md` D-075 — autoriza escrita EXIF de localização em
  campo vazio, revoga parte do invariante 7. Ler o texto completo (não
  paraphrase) — inclui a nota de refinamento de 2026-08-18 sobre
  hash-como-fato-de-auditoria vs. diff-de-tags-como-critério.
- `CLAUDE.md` invariante 7 (texto atualizado 2026-08-18) — escopo exato
  (lat/long, cidade, país; só campo vazio; nunca sobrescreve).

### Requisitos e roadmap
- `.planning/REQUIREMENTS.md` § EXIF-01..04
- `.planning/ROADMAP.md` § Phase 6 — inclui "Abordagem travada" com as
  restrições arquiteturais já assinadas (módulo próprio, não
  `operations/executor.py`).

### Pesquisa
- `.planning/research/STACK.md` — mecânica de escrita exiftool,
  `-if` não serve pra guarda de campo-vazio (precisa ser Python-side),
  GPSLatitudeRef/GPSLongitudeRef precisam ser escritos explicitamente.
- `.planning/research/ARCHITECTURE.md` — módulo novo recomendado
  (`fotoorganizer/exif_write/`), reusa `AuditLog` e `security/`
  (paths, hashing), não `OperationPlan`/`OperationItem`/
  `OperationExecutor`.
- `.planning/research/PITFALLS.md` — mental model de
  `operations/executor.py` não transfere pra mutação in-place; CR3/HEIC
  com histórico de corrupção documentado em escrita (leitura já validada
  por D-026, escrita não); concorrência com Lightroom/Photos.app é
  desync silencioso, não problema de lock.

### Precedente de rigor equivalente
- `fotoorganizer/operations/` (dry-run, hash antes/depois, nunca
  sobrescreve, audit log) — padrão de rigor a igualar, não módulo a
  estender.
- `webapp/src/components/Operations.tsx` — padrão de UI de
  plano→dry-run→aprovar→executar a reusar para a aprovação em lote
  (D-01).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `security/paths.py`, `security/hashing.py` — validação de caminho e
  hash, reusáveis pela nova fase sem herdar de `operations/`.
- `AuditLog` (genérico o bastante, per pesquisa de arquitetura) — reusa
  para registrar escrita EXIF, incluindo falha parcial.
- `Operations.tsx` — padrão de UI plano→dry-run→aprovar→executar,
  extensível para checkbox por linha (D-02) e badge "formato não
  suportado" (D-05).
- Padrão de checkbox por linha já usado em review de sugestões — reusar
  para D-02.

### Established Patterns
- `metadata/exiftool.py` — ponto de integração para escrita (extrator
  já usa exiftool via subprocesso `-stay_open`); escrita reusa a mesma
  invocação segura, não `shell=True`.
- D-074's padrão de decisão medida (script de calibração, decisão
  registrada em `docs/DECISOES.md`) é o molde para D-03 (teste empírico
  de formato).

### Integration Points
- Novo módulo `fotoorganizer/exif_write/` (ou nome equivalente) —
  paralelo a `operations/`, não filho dele.
- Sidecar XMP (D-06) precisa de um writer próprio — não existe ainda no
  código (fora de escopo do MVP original, ver invariante 7 anterior).

</code_context>

<specifics>
## Specific Ideas

- Dono quer o fallback de sidecar XMP disponível já nesta fase para
  formatos reprovados no teste de escrita — não deixar isso para uma
  fase futura separada, mesmo que o roadmap original não tivesse isso
  explícito.

</specifics>

<deferred>
## Deferred Ideas

None — discussão ficou dentro do escopo da fase.

</deferred>

---

*Phase: 6-Escrita EXIF de localização*
*Context gathered: 2026-08-18*
