---
phase: 01-timezone-estimado
reviewed: 2026-08-16T12:34:53Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - fotoorganizer/geolocation/timezones.py
  - tests/test_timezones.py
  - fotoorganizer/classification/engine.py
  - tests/test_suggestion_engine.py
  - fotoorganizer/server/app.py
  - tests/test_server_api.py
findings:
  critical: 1
  warning: 1
  info: 0
  total: 2
status: issues_found
---

# Fase 01: Relatório de Code Review

**Revisado em:** 2026-08-16T12:34:53Z
**Profundidade:** standard
**Arquivos revisados:** 6
**Status:** issues_found

## Resumo

A fatia adiciona `TZ_POR_PAIS` (tabela estática país→IANA, 250 entradas,
cobertura e validade IANA confirmadas por execução — `set(TZ_POR_PAIS) ==
set(PAISES_PT.values())` e todo valor em `zoneinfo.available_timezones()`),
o cálculo de `media.tz_estimado` em `_persistir_sugestao`
(`classification/engine.py`) e o passthrough do campo em `_media_json`
(`server/app.py`). A tabela em si e sua validação estão corretas e bem
testadas.

O problema real está na integração: o próprio `docs/prompts/fase-11-timezone-
estimado.md` (linha 144) exige que "regenerar sugestões atualiza
`tz_estimado` (mesmo padrão de recálculo dos campos `gps_*_estimado`)" — e os
campos `gps_*_estimado` são recalculados incondicionalmente, para TODA mídia,
a cada `gerar()` (`_persistir_herancas`, chamado sobre `midias` completo).
`tz_estimado`, por outro lado, só é (re)calculado dentro de
`_persistir_sugestao`, que é pulado para qualquer mídia cuja sugestão já
tenha decisão (`aprovada`/`rejeitada`/`editada` — ver `decididas` em
`gerar()`). Na prática, depois que o usuário aprova ou edita uma sugestão,
`tz_estimado` congela para sempre naquele valor, mesmo que o país efetivo da
foto mude numa rodada seguinte (nova doadora de GPS, pasta renomeada,
reclassificação). Reproduzi isso empiricamente (script de verificação, não
commitado) e confirmei que `gps_lat_estimado` muda corretamente na segunda
rodada enquanto `tz_estimado` permanece com o valor da primeira.

Durante a leitura completa de `engine.py` também apareceu um bug pré-
existente (não introduzido por esta fatia, mas no caminho direto do dado que
alimenta `tz_estimado`): `_resolver_locations` nunca limpa
`media.location_id` quando a nova coordenada deixa de resolver — só
sobrescreve quando a resolução dá um id novo. Registrado como aviso porque
está fora do escopo desta fase, mas é adjacente o bastante ao mesmo defeito
de "dado derivado que não se autocorrige" para merecer nota.

## Critical Issues

### CR-01: `tz_estimado` não é recalculado para mídia com sugestão já decidida — viola o próprio critério de aceite da fase

**Arquivo:** `fotoorganizer/classification/engine.py:306-315` (gating) e
`fotoorganizer/classification/engine.py:1064-1073` (cálculo)

**Issue:**
`gerar()` só chama `_evidencias_para`/`_persistir_sugestao` para mídia cujo
`media.id` NÃO está em `decididas` (status `PENDENTE`):

```python
for media in organizaveis:
    if media.id in decididas:
        continue
    drafts = self._evidencias_para(...)
    self._persistir_sugestao(session, media, drafts)
```

E é só dentro de `_persistir_sugestao` que `media.tz_estimado` é
(re)calculado:

```python
media.tz_estimado = TZ_POR_PAIS.get(
    evidencias["pais"].valor
) if "pais" in evidencias else None
```

Ou seja: assim que o usuário aprova, rejeita ou edita a sugestão de uma
foto, `tz_estimado` para de ser recalculado nas rodadas seguintes de
`gerar()` — fica congelado no valor da última rodada em que a sugestão
ainda estava pendente. Isso contradiz diretamente o critério de aceite
escrito em `docs/prompts/fase-11-timezone-estimado.md:144`: "regenerar
sugestões atualiza `tz_estimado` (**mesmo padrão de recálculo dos campos
`gps_*_estimado`**)". Os campos `gps_*_estimado` são recalculados
incondicionalmente para toda mídia em `_persistir_herancas`
(`engine.py:329-352`), que roda sobre `midias` (a lista completa, não
filtrada por `decididas`) — `tz_estimado` não segue o mesmo padrão, apesar
do comentário no código (linhas 1064-1070) alegar explicitamente que o
`else None` existe "para uma rodada futura de `gerar()` que não resolve mais
'pais' para esta mídia não deixar sobreviver um `tz_estimado` obsoleto da
rodada anterior" — essa garantia simplesmente não se aplica a nenhuma mídia
com sugestão decidida.

Reproduzido: câmera sem GPS herda país da França de um telefone próximo →
`tz_estimado = "Europe/Paris"`. Aprovo a sugestão da câmera. Na rodada
seguinte, o telefone doador perde a coordenada (deixa de geocodificar para
qualquer país conhecido) — `gps_lat_estimado` da câmera muda corretamente
para o novo valor (0.0), mas `tz_estimado` continua `"Europe/Paris"`.

O teste adicionado nesta fatia (`test_tz_estimado_atualiza_ao_regenerar_
sugestoes`, `tests/test_suggestion_engine.py:1085-1112`) não cobre esse
caminho: ele nunca aprova/edita a sugestão entre as duas chamadas de
`gerar()`, então a mídia nunca entra em `decididas` e o bug não aparece —
dá falso verde para o critério de aceite que alega cobrir.

Impacto prático hoje é limitado porque nada no código ainda lê
`tz_estimado` para produzir comportamento visível ao usuário — o próprio
prompt da fase exclui explicitamente "converter `data_capturada` para hora
local usando `tz_estimado`" do escopo. Ou seja, o defeito é **latente**: não
quebra nenhuma tela hoje, mas quebra silenciosamente assim que um consumidor
futuro (a conversão de hora local citada no roadmap) passar a confiar nesse
campo — e, por ser gravado direto em `MediaFile` sem passar por
`Evidence`/revisão (por desenho, D-03), não há nenhuma superfície de UI ou
auditoria que exponha a inconsistência para o usuário notar e corrigir.
Classifico como Critical porque é um desvio comportamental documentado e
verificável do critério de aceite da própria fase, não uma preferência de
estilo.

**Fix:**
Separar o cálculo de `tz_estimado` do fluxo de `_persistir_sugestao` e
recalculá-lo para toda mídia organizável com país conhecido, no mesmo lugar
e com a mesma incondicionalidade de `_persistir_herancas`/`_resolver_
locations` — por exemplo, adicionar um passo próprio logo após
`_resolver_locations` que releia o país do `Location` resolvido (via
`media.location_id`) para cada mídia com coordenada efetiva, em vez de
depender de `evidencias["pais"]` (que só existe para mídia ainda não
decidida):

```python
def _atualizar_tz_estimado(self, session: Session, midias) -> None:
    """tz_estimado segue o mesmo padrão de recálculo incondicional dos
    campos gps_*_estimado — inclusive para mídia com sugestão já decidida."""
    for media in midias:
        if media.location_id is None:
            media.tz_estimado = None
            continue
        local = session.get(Location, media.location_id)
        media.tz_estimado = TZ_POR_PAIS.get(local.pais) if local else None
```
Chamar isso a partir de `gerar()` logo após `self._resolver_locations(...)`,
sobre a lista completa de `midias` (não só `organizaveis` sem decisão). Isso
também simplifica `_persistir_sugestao`, que pode perder o bloco de
`tz_estimado` (linhas 1064-1073) por completo. Adicionar um teste que
aprova/edita a sugestão entre duas chamadas de `gerar()` e muda o país
efetivo da foto, confirmando que `tz_estimado` acompanha a mudança mesmo
para mídia decidida.

## Warnings

### WR-01: `_resolver_locations` nunca limpa `media.location_id` quando a coordenada deixa de resolver

**Arquivo:** `fotoorganizer/classification/engine.py:373-386`

**Issue:**
```python
resolvidos: dict[str, int | None] = {}
for media in midias:
    coordenada = media.coordenada
    if coordenada is None:
        continue
    chave = _chave_de_coordenada(*coordenada)
    if chave not in resolvidos:
        location = self._resolver.resolve(session, *coordenada)
        resolvidos[chave] = location.id if location is not None else None
    location_id = resolvidos[chave]
    if location_id is not None:
        media.location_id = location_id
```
Quando `location` vem `None` (coordenada não geocodificável nesta rodada —
por exemplo porque a doadora de GPS mudou de coordenada, ou o provider
passou a rejeitar aquele ponto), `location_id` fica `None` no dicionário
`resolvidos`, mas o `if location_id is not None` faz o laço simplesmente não
tocar `media.location_id` — o valor antigo (de uma rodada anterior, para uma
coordenada diferente) sobrevive. Isso é diretamente adjacente ao bug de
CR-01: se a implementação de CR-01 usar `media.location_id` como fonte do
país (como sugerido no fix), essa falha de invalidação se propaga para
`tz_estimado` também.

Não foi introduzido por esta fatia (a função já existia antes, sem alteração
no diff), mas está no caminho direto do dado consumido pela feature nova e é
facilmente reproduzível: coordenada A resolve para França (grava
`location_id`), a mesma mídia troca para coordenada B que não resolve para
nada — `location_id` continua apontando para o registro de França de uma
coordenada que a mídia não tem mais.

**Fix:**
```python
location_id = resolvidos[chave]
media.location_id = location_id  # grava None explicitamente quando não resolve
```
(Confirmar que nenhum outro código depende de `location_id` "nunca
regredir" antes de aplicar — se depender, documentar a razão em vez de
deixar implícito num `if` que parece só uma otimização.)

---

_Revisado em: 2026-08-16T12:34:53Z_
_Revisor: Claude (gsd-code-reviewer)_
_Profundidade: standard_
