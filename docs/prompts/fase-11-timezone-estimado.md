# Fase 11 — timezone estimado a partir do país

Item 5 do backlog atual (`docs/ROADMAP.md`, renumerado depois de D-035 — era
"item 6" nas fases anteriores). Esforço S/M: a coluna já existe
(`fotoorganizer/models/catalog.py:143`, `tz_estimado: Mapped[str | None]`,
migrada desde `0001_schema_inicial.py:145`) e a janela de país (D-025) já
está pronta. Ninguém escreve nem lê essa coluna hoje — terreno virgem,
confirmado por `grep -rn "tz_estimado" fotoorganizer/ webapp/ tests/`.

## Nota de 2026-08-09 — o modelo de tempo mudou embaixo desta fase

A fase 12 (item C) entregou o par de instantes que esta fase pressupunha e
não tinha. Leia **D-038** em `docs/DECISOES.md` antes de começar; em resumo:

- `MediaFile.data_capturada` é a **hora de parede** (sempre foi, por
  desenho: os extratores descartam fuso) e continua sendo o que ordena a
  grade e agrupa evento e viagem. Não mexa nela.
- `MediaFile.data_capturada_utc` é o **mesmo instante, absoluto**. O offset
  é a diferença entre as duas e **nunca** vira coluna. As duas iguais quer
  dizer "fuso desconhecido", nunca "tirada em UTC" — quem derivar offset
  precisa ler zero assim.
- **`tz_estimado IS NOT NULL` é o sinal de "fuso conhecido", não a diferença
  entre as duas datas.** Fuso real de +00:00 (Londres e Lisboa no inverno,
  Islândia, Marrocos) deixa as duas colunas iguais, exatamente como
  "desconhecido" — limitação inerente ao padrão, que o Immich também tem, e
  aceita de propósito. Quem for perguntar "esta foto tem fuso?" tem de
  perguntar a `tz_estimado`, e é esta fase que faz esse campo passar a
  existir.
- Logo, `tz_estimado` já nasce enriquecendo um modelo coerente sozinho, em
  vez de ser metadado decorativo. E escrever `tz_estimado` **não** autoriza
  reescrever `data_capturada_utc`: fuso estimado por país é palpite, o
  instante absoluto é medição, e este projeto não mistura os dois na mesma
  coluna (o mesmo motivo de `gps_lat` vs `gps_lat_estimado`). Se a fase
  quiser um absoluto derivado do fuso estimado, ele é coluna nova, com nome
  que diga que é estimado.
- Duas oportunidades ficaram explicitamente para cá, porque já mexem em
  fuso: ler `OffsetTimeOriginal` (e o `Z` do QuickTime) nos extratores —
  `MediaMetadata.data_capturada_utc` já existe esperando, em `None` — e
  corrigir `sources/google_takeout.py:_data()`, que hoje monta a hora local
  no fuso da máquina que importou, não no da foto.

## Formulação (reescrita — não é a antiga)

A formulação antiga era GPS próprio + hora local (alcançaria só 4 dos 25
anos do acervo, porque GPS é raro antes de 2018 — D-029). A reescrita usa
**país**, não coordenada exata: `tz_estimado` = fuso representativo do país
já atribuído à foto — não importa se esse país veio do GPS da própria foto,
de herança temporal (D-025) ou do nome da pasta. Não é geometria
(coordenada → fuso preciso via polígono de timezone); é o mesmo nível de
granularidade grosseira que o resto do app já assume para país estimado.

## O que já existe (mapeado por agente de reconhecimento, confirmado)

- `fotoorganizer/classification/engine.py:693-781` (`_evidencias_geo`) já
  monta, por mídia, a evidência `Evidence(campo="pais", origem=..., valor=
  <nome do país em PT-BR>)` — três origens possíveis: `geocoding_offline`
  (GPS da própria foto), `vizinhanca_temporal` (herança, condicionada a
  `heranca.fator_de("pais") is not None`), `pasta` (nome de diretório via
  `extrair_hierarquia_da_pasta` + `canonizar_pais`). As três convergem para
  o MESMO vocabulário de string: nomes em português de
  `fotoorganizer/geolocation/paises.py::PAISES_PT` (dict ISO alfa-2 → nome
  PT-BR, 98 países).
- `engine.py:930-950` (dentro de `_persistir_sugestao`) monta
  `evidencias: dict[str, Evidence]` com a chave `"pais"` já resolvida, antes
  de gerar `Suggestion`. É o ponto mais barato para ler o país que "venceu"
  para aquela mídia — não precisa geocodificar de novo.
- Precedente de escrita direta em `MediaFile` pelo motor de classificação,
  **sem** passar por `Suggestion`/aprovação: `_persistir_herancas`
  (`engine.py:282-305`) já grava `gps_lat_estimado`, `gps_lon_estimado`,
  `gps_estimado_de_id`, `gps_estimado_delta_s` direto, recalculados a cada
  `gerar()`. `media.location_id` (`engine.py:701,720`) é outro precedente,
  gravado dentro do próprio `_evidencias_geo`. `docs/CONFIANCA.md` não
  menciona esse caminho porque ele é ortogonal ao modelo Evidence→Suggestion
  — é dado técnico auxiliar, não decisão de organização a revisar.
  `tz_estimado` segue o MESMO padrão: gravado direto, sem revisão humana,
  sem `Evidence` nova, sem entrada em `docs/CONFIANCA.md`.
- **Não existe hoje nenhuma tabela nem dependência de timezone** no projeto
  (`pyproject.toml` não tem `pytz`/`timezonefinder`/`babel`; o dataset
  offline `reverse-geocode` não devolve timezone, só `country_code`,
  `city`, `state`). Precisa ser tabela estática nova — coerente com o
  invariante 4 (nenhuma rede) e com o precedente de `paises.py`, que já é
  exatamente esse tipo de tabela.

## O que fazer

### 1. Tabela estática país → fuso

Novo arquivo `fotoorganizer/geolocation/timezones.py`, mesmo espírito de
`paises.py` (docstring explicando o porquê, tabela estática, sem rede).

- `TZ_POR_PAIS: dict[str, str]` — chave é o MESMO nome em português que
  `PAISES_PT` produz (não o código ISO: o valor de `Evidence.valor` já
  chega como nome, e recodificar de volta para ISO só para procurar na
  tabela seria trabalho e uma fonte de bug a mais). Cubra os 98 países de
  `PAISES_PT` — é a tabela pequena o bastante para fazer por completo, e
  parcial deixaria um país aparecer sem fuso por acidente de cobertura, não
  por decisão.
- Cada valor é um identificador IANA válido (`"America/Sao_Paulo"`,
  `"Asia/Bangkok"`, `"Europe/Paris"`...). Valide em teste que **todo** valor
  da tabela está em `zoneinfo.available_timezones()` (stdlib, sem
  dependência nova, sem rede) — é a rede de segurança contra erro de
  digitação num identificador que só vai doer quando alguém tentar
  convertê-lo.
- Países com mais de um fuso (Brasil, EUA, Rússia, Canadá, Austrália...):
  escolha o fuso da capital ou o de maior população, e diga isso num
  comentário no topo do arquivo — é uma aproximação deliberada, coerente
  com o resto do campo ser "estimado", não um substituto de
  `timezonefinder`. Não é preciso resolver isso caso a caso no código, só
  documentar a regra usada uma vez.

### 2. Cálculo e persistência

Dentro de `_persistir_sugestao` (`engine.py`), onde `evidencias["pais"]` já
existe (se existir), gravar:

```python
if "pais" in evidencias:
    media.tz_estimado = TZ_POR_PAIS.get(evidencias["pais"].valor)
```

Sem país conhecido, `tz_estimado` fica `None` (nunca inventa). Um país
conhecido mas fora da tabela (não deveria acontecer, dado o item 1 acima,
mas por segurança) também cai em `None`, não erro — mesma filosofia de
"erro de leitura não derruba o resto" do resto do projeto.

Confirme se `_persistir_sugestao` já recebe `media` como o objeto ORM
gravável (deveria, já que grava `Suggestion.media_id=media.id` mais abaixo)
antes de assumir que dá para atribuir `media.tz_estimado=` direto ali.

### 3. Serialização na API

`fotoorganizer/server/app.py` — ache o serializador que monta o JSON de
`MediaFile` para `GET /api/midia/{id}` (o mesmo usado por `detalhe_plano`/
grade, procure por onde `gps_lat_efetivo`/`local` já são montados) e
acrescente `"tz_estimado": media.tz_estimado`.

### 4. Testes

- `tests/test_timezones.py` (ou nome equivalente): tabela cobre os 98
  países de `PAISES_PT`, todo valor é IANA válido (`zoneinfo`).
- `tests/test_suggestion_engine.py`: cenário com país vindo de GPS próprio
  grava `tz_estimado`; cenário com país só herdado (sem GPS próprio, D-025)
  também grava; cenário sem nenhum país conhecido deixa `tz_estimado=None`;
  regenerar sugestões atualiza `tz_estimado` (mesmo padrão de recálculo dos
  campos `gps_*_estimado`).
- `tests/test_server_api.py`: `GET /api/midia/{id}` devolve `tz_estimado`.

## Fora de escopo nesta fase

- Qualquer geometria coordenada→fuso (`timezonefinder` ou similar) — é
  exatamente o que esta reformulação evita, por não ter dependência nova.
- Converter `data_capturada` para hora local usando `tz_estimado` em
  qualquer tela — este item só produz o dado; consumo (mostrar hora local
  em vez de naive) é decisão de UI separada, não pedida aqui.
- Mexer em `Evidence`/`docs/CONFIANCA.md` — este campo não passa por
  aprovação, como os `gps_*_estimado` que já existem.

## Aceite

- `pytest` verde, incluindo a validação IANA de toda a tabela.
- Foto com país só por herança (sem GPS próprio) ganha `tz_estimado`
  correto depois de `gerar()`.
- `GET /api/midia/{id}` devolve o campo.
- Medir no catálogo real (só leitura, sem regenerar sugestões de verdade
  contra o catálogo do usuário — usar cópia via `sqlite3 .backup`, mesmo
  padrão de `scripts/medir_nome_de_album.py`): quantas fotos ganhariam
  `tz_estimado` hoje, e quantas delas só o ganham por herança (não por GPS
  próprio) — é o número que confirma ou não o "~2.235 fotos" citado no
  ROADMAP.
