# Item D — timezone estimado a partir do país herdado

Staging pronto para integrar quando a fase 5 abrir a fronteira. Item 5 do
backlog (`docs/ROADMAP.md`, "Próximas versões"), especificado em detalhe em
`docs/prompts/fase-11-timezone-estimado.md`. 100% foto-organizer — não vem
de PhotoPrism nem de Immich, sem restrição de licença aqui.

## O que existe hoje (evidência)

- **A coluna já existe e está virgem.**
  `fotoorganizer/models/catalog.py:201` — `tz_estimado: Mapped[str | None]`
  em `MediaFile`, sem índice de propósito (comentário `:196-199`: nenhuma
  consulta filtra por ela hoje). Confirmado por `grep -rn "tz_estimado"
  fotoorganizer/ webapp/` nesta sessão: só a declaração da coluna, nenhuma
  leitura nem escrita.
- **A janela de herança de país já está pronta.** D-025
  (`docs/DECISOES.md`) — `JANELAS_POR_CAMPO` em `grouping/correlacao.py`,
  com janela própria por campo (cidade 10 min, região 2 h, país 12 h).
  `fotoorganizer/classification/engine.py:736-781` (`_evidencias_geo`) já
  monta `Evidence(campo="pais", origem=..., valor=<nome PT-BR>)` a partir
  de três origens: `geocoding_offline` (GPS próprio), `vizinhanca_temporal`
  (herança, condicionada a `heranca.fator_de("pais") is not None`), `pasta`
  (nome de diretório). `engine.py:948` (`_persistir_sugestao`) é onde
  `evidencias["pais"]` já está resolvido antes de gravar `Suggestion` — o
  ponto mais barato para ler o país que "venceu", sem geocodificar de novo.
- **Precedente de escrita direta em `MediaFile`, sem passar por
  `Suggestion`/aprovação.** `_persistir_herancas` (`engine.py:294`, número
  de linha real nesta sessão — a doc de fase cita `:282-305` de uma versão
  anterior do arquivo) já grava `gps_lat_estimado`/`gps_lon_estimado`
  direto, recalculados a cada `gerar()`. `tz_estimado` segue o MESMO
  padrão de precedente: gravado direto, sem `Evidence` nova, sem entrada em
  `docs/CONFIANCA.md` — é dado técnico auxiliar, não decisão de organização
  a revisar, mesmo raciocínio de `media.location_id`.
- **Nenhuma tabela de timezone existe no projeto hoje.** `pyproject.toml`
  não lista `pytz`/`timezonefinder`/`babel`; o dataset offline de
  reverse-geocoding devolve só `country_code`/`city`/`state`, sem fuso.
  `fotoorganizer/geolocation/paises.py` é o precedente de tabela estática
  (país → nome canônico PT-BR) que este item segue no mesmo espírito.
- **A tabela real de países é maior do que o prompt de fase cita.** A doc
  de origem fala em "98 países de `PAISES_PT`" — nesta sessão, `len(
  fotoorganizer.geolocation.paises.PAISES_PT)` mede **250**. A tabela deste
  item cobre os 250, confirmados por teste
  (`test_tabela_cobre_o_vocabulario_real_de_paises_pt`), não os 98 da
  estimativa desatualizada.
- **O modelo de dois instantes (D-038) já está em produção** e não muda
  neste item: `data_capturada` continua hora de parede,
  `data_capturada_utc` continua o mesmo instante absoluto, sem coluna de
  offset. `tz_estimado IS NOT NULL` é o sinal de "fuso conhecido" que este
  item passa a fazer existir — não a diferença entre as duas datas
  (limitação inerente já documentada em `models/catalog.py:184-189`).

## O que este item entrega

`lib.py`:

- `TZ_POR_PAIS: dict[str, str]` — os 250 nomes de `PAISES_PT` (chave é o
  MESMO nome em português, não o código ISO — evita recodificar
  `Evidence.valor` de volta para ISO só para procurar aqui) mapeados para
  um identificador IANA válido. Validado em teste que TODO valor está em
  `zoneinfo.available_timezones()` E que `zoneinfo.ZoneInfo(...)`
  instancia sem erro para cada um.
- `tz_estimado_para_pais(pais) -> str | None` — a função de cálculo:
  país conhecido na tabela devolve o fuso; `None`, string vazia, ou país
  fora da tabela devolvem `None` (nunca inventa).
- `calcular_tz_estimado(pais, origem_pais) -> ResultadoTzEstimado` — junta
  a resolução de fuso com a proveniência, para a medição pedida no aceite
  da fase-11 ("quantas fotos ganhariam `tz_estimado` hoje, e quantas só por
  herança") sair de uma função só, sem duplicar a lista de origens em dois
  lugares do código de medição.

## Decisões (Classe A, ver também `docs/DECISOES.md`)

1. **Fuso da capital ou do local de maior população, documentado país a
   país no comentário ao lado da entrada** (não uma regra geral aplicada
   às cegas) — mesma exigência da fase-11 §1: "diga isso num comentário no
   topo do arquivo". Feito por entrada, não por bloco único, porque cada
   país multi-fuso tem uma razão diferente (Brasil: maior população;
   Austrália: maior população; China: fuso oficial único do país inteiro).
2. **Territórios não habitados sem zona IANA própria** (Ilha Bouvet, Ilha
   Heard e Ilhas McDonald) usam offset fixo `Etc/GMT[+-]N` pela longitude
   aproximada, e **Kosovo** (sem zona IANA própria, `XK` não tem entrada
   `tzdata`) usa `Europe/Belgrade`, mesmas regras de DST da região.
   Documentado inline — decisão que a fase-11 não previu porque a
   contagem de "98 países" da doc de origem provavelmente já excluía esses
   casos de fronteira.
3. **`calcular_tz_estimado` considera herança só `origem_pais ==
   "vizinhanca_temporal"`**, não `"pasta"`. A fase-11 cita "país herdado"
   como sinônimo de D-025 (janela temporal); nome de pasta é uma terceira
   fonte que também não é GPS próprio, mas não é a herança que o ROADMAP
   mede como "~2.235 fotos". Quem integrar e quiser contar as duas juntas
   ajusta o predicado — a função documenta a escolha, não esconde.

## Onde plugar quando a fronteira abrir

- `fotoorganizer/geolocation/timezones.py` (novo arquivo) — mover
  `TZ_POR_PAIS` para lá, mesmo padrão de `paises.py`.
- `fotoorganizer/classification/engine.py`, dentro de `_persistir_sugestao`
  (`:948`, onde `evidencias["pais"]` já existe se existir): gravar
  ```python
  if "pais" in evidencias:
      media.tz_estimado = TZ_POR_PAIS.get(evidencias["pais"].valor)
  ```
  exatamente como a fase-11 §2 especifica — este item já entrega
  `tz_estimado_para_pais` pronta para essa chamada virar
  `media.tz_estimado = tz_estimado_para_pais(evidencias["pais"].valor)`.
  Confirmar antes que `_persistir_sugestao` recebe `media` como o objeto
  ORM gravável (a fase-11 já assinala essa checagem como pendente).
- `fotoorganizer/server/app.py`, no serializador de `MediaFile` para JSON
  (`_media_json`, `:275-...`, onde `gps_lat_efetivo` já é montado, `:298`)
  — acrescentar `"tz_estimado": m.tz_estimado`.
- Medição no catálogo real (fora deste item, mas o aceite da fase-11
  pede): usar `calcular_tz_estimado` sobre uma cópia via `sqlite3 .backup`
  (mesmo padrão de `scripts/medir_nome_de_album.py`), contando
  `resultado.tz_estimado is not None` e `resultado.veio_de_heranca` para
  confirmar (ou não) o número "~2.235 fotos" citado no `ROADMAP.md`.

## Fora de escopo (herdado da fase-11, mantido aqui)

- Geometria coordenada→fuso (`timezonefinder` ou similar) — é exatamente o
  que a reformulação por país evita, sem dependência nova.
- Converter `data_capturada` para hora local usando `tz_estimado` em
  qualquer tela — este item só produz o dado.
- Mexer em `Evidence`/`docs/CONFIANCA.md` — este campo não passa por
  aprovação, como os `gps_*_estimado` que já existem (mesmo precedente).
