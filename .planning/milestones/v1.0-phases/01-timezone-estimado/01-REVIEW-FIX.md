---
phase: 01-timezone-estimado
fixed_at: 2026-08-16T12:46:03Z
review_path: .planning/phases/01-timezone-estimado/01-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Fase 01: Relatório de Fix de Code Review

**Fixed at:** 2026-08-16T12:46:03Z
**Source review:** .planning/phases/01-timezone-estimado/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

## Fixed Issues

### CR-01: `tz_estimado` não é recalculado para mídia com sugestão já decidida — viola o próprio critério de aceite da fase

**Status:** fixed: requires human verification
**Files modified:** `fotoorganizer/classification/engine.py`, `tests/test_suggestion_engine.py`
**Commit:** 93d1216
**Applied fix:** Não segui o snippet literal do REVIEW.md (basear `tz_estimado`
em `media.location_id` → `Location.pais`) — leitura completa do caminho de
dados mostrou que país também vem de heurística de nome de pasta
(`extrair_hierarquia_da_pasta`) e de vizinhança dominante de sessão
(`sessao.pais_dominante`), nenhum dos quais grava `location_id`. Um fix
baseado só em `location_id` teria zerado `tz_estimado` já na primeira
`gerar()` para o cenário de país-por-pasta (`test_tz_estimado_atualiza_ao_
regenerar_sugestoes`, que já passava antes desta fatia).

Em vez disso: extraí a cascata de resolução de país de `_evidencias_geo`
(GPS próprio > GPS herdado > pasta > vizinhança da sessão) para um método
novo e sem efeito colateral, `_pais_efetivo`, replicando o mesmo critério
de parada de cada ramo (GPS próprio decide sozinho assim que resolve,
mesmo com `location.pais is None`; GPS herdado só decide quando
`heranca.fator_de("pais")` sustenta o campo). Um segundo método novo,
`_atualizar_tz_estimado`, chama `_pais_efetivo` para TODA mídia
organizável (não só a pendente) logo após `_persistir_agrupamentos` em
`gerar()` — mesmo padrão incondicional de `_persistir_herancas` para
`gps_lat_estimado`. Removido o bloco de `tz_estimado` de dentro de
`_persistir_sugestao` (que continua pulada para mídia decidida).

Duplicar a cascata em vez de reaproveitar `_evidencias_geo` diretamente foi
deliberado: reaproveitar arriscaria mudar texto de justificativa/score da
evidência existente, fora do escopo deste finding. Como bônus, resolver via
`self._resolver.resolve(...)` direto em vez de ler `media.location_id`
evita a interação que o próprio REVIEW.md apontou com WR-01 (se
`location_id` tivesse ficado obsoleto, `tz_estimado` herdaria o mesmo
problema) — o fix de WR-01 (abaixo) elimina essa classe de bug de qualquer
forma, mas o desenho de CR-01 não depende dele.

Teste novo adicionado (`test_tz_estimado_atualiza_mesmo_com_sugestao_
decidida`): aprova a sugestão de uma foto com país por GPS (França), muda
o GPS para fora da cobertura do geocoder fake entre duas chamadas de
`gerar()`, confirma que `tz_estimado` acompanha (vira `None`) mesmo com a
sugestão já `APROVADA` — e que a decisão do usuário continua preservada.
Suíte completa (840 testes) passou após o fix.

**Nota de verificação:** este é um fix de lógica de estado/cascata, não
apenas sintático — os tiers 1/2 (releitura + `ast.parse`) não confirmam
paridade de comportamento com `_evidencias_geo` em todos os ramos. Marcar
como **"fixed: requires human verification"** — revisão humana da cascata
de `_pais_efetivo` (em especial os dois pontos de "parada antecipada": GPS
próprio retorna mesmo com país `None`; GPS herdado só retorna quando
`fator_de("pais")` existe) é recomendada antes de considerar este finding
fechado com confiança total.

### WR-01: `_resolver_locations` nunca limpa `media.location_id` quando a coordenada deixa de resolver

**Files modified:** `fotoorganizer/classification/engine.py`
**Commit:** 3352fd3
**Applied fix:** Aplicado o fix sugerido no REVIEW.md praticamente como
está: troquei `if location_id is not None: media.location_id = location_id`
por atribuição incondicional `media.location_id = resolvidos[chave]`, que
grava `None` explicitamente quando a coordenada da rodada não resolve para
nenhum lugar. Confirmado por grep que nenhum outro código do projeto
depende do comportamento antigo de "nunca regride" (os dois outros pontos
que gravam `location_id`, em `_evidencias_geo` linhas ~815/834, seguem o
mesmo padrão de só gravar quando resolve — não há leitura em nenhum lugar
que dependa do valor antigo sobreviver). Suíte de testes de
`location`/`tz_estimado` (5 testes) e suíte completa (840 testes) passaram
sem quebra.

## Skipped Issues

None — both in-scope findings (CR-01 critical, WR-01 warning) were fixed.

---

_Fixed: 2026-08-16T12:46:03Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
