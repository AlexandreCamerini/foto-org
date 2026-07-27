# Inventário de sinais — o que o acervo oferece

Medido em 2026-07-26 sobre o acervo real: **4.496 fotos com arquivo** e
**43.309 referências** do Apple Fotos (originais só no iCloud).

Três colunas que não devem ser confundidas: o que o dado **oferece**, o que
o catálogo **captura** hoje, e o que a cascata de classificação **usa** para
decidir. Sinal capturado e não usado é trabalho pronto parado.

## Resumo

| Fonte | Oferece | Capturado | Usado na decisão |
|---|---|---|---|
| EXIF do arquivo | 57 chaves | ✅ todas | 6 campos |
| XMP sidecar | 605 arquivos, 599 com curadoria | ❌ | ❌ |
| XMP embutido | ~100% dos JPG | ❌ | ❌ |
| IPTC embutido | ~29% dos JPG | ❌ | ❌ |
| Nome de arquivo | 1 padrão único | ✅ | ❌ (nada a extrair) |
| Nome de pasta | 19 segmentos | ✅ | ✅ principal sinal hoje |
| Apple Fotos | 6 tipos, 99.678 registros | ✅ | só GPS |
| Derivados | hash, phash, rajada | ✅ | só em duplicatas |

## 1. EXIF — capturado por inteiro, usado em parte

57 chaves distintas. Duas populações: JPG/DNG lidos por Pillow/exifread
(1.528 fotos, 34%) e RAW lidos por libraw (2.852, 63%).

**Usados hoje:** data, make, model, lente, orientação, dimensões, GPS.

**Capturados e ociosos, em ordem de valor:**

| Chave | Fotos | Para que serve |
|---|---|---|
| `OffsetTimeOriginal` | 1.527 | **Fuso horário da captura.** Elimina a ambiguidade que hoje a deriva de relógio estima por inferência |
| `BodySerialNumber` | 1.528 | Identifica o corpo específico, não o modelo. Separa duas câmeras iguais |
| `DateTimeDigitized` vs `DateTimeOriginal` | 1.528 | Divergência é o arquivo declarando que o relógio foi mexido |
| `SubsecTimeOriginal` | 1.524 | Sub-segundo: ordena rajada e desempata simultâneos |
| `LensSerialNumber` | 1.528 | Distingue duas lentes do mesmo modelo |
| `Artist` | 1.528 | Autoria — separa o que é seu do que veio de terceiros |
| `ISO`, `FNumber`, `ExposureTime`, `FocalLength` | 1.528 / 2.852 | Perfil de disparo: interno vs externo, teleobjetiva vs grande-angular |
| `Flash`, `WhiteBalance`, `SceneCaptureType` | 1.528 | Pistas de ambiente |

## 2. XMP — não capturado, e é curadoria humana

**605 sidecars `.xmp`**, dos quais **599 carregam curadoria**. Concentrados
em `2026` (450) e `EMPOLGA 2026 LEME` (149).

| Sinal | Distribuição |
|---|---|
| `xmp:Rating` | 5★ em 457 · 2★ em 97 · 4★ em 43 · 3★ em 2 |
| `xmp:Label` | Verde 457 · Vermelho 97 · Azul 43 · Amarelo 2 |
| `lr:hierarchicalSubject` | Selected 374 · Blurred 106 · Highlights 62 · Duplicates 52 |

A origem é o **Aftershoot** (culling automático), não seleção manual — o que
muda a confiança, não a utilidade. `Blurred` e `Duplicates` são julgamento
de qualidade; `Selected` e `Highlights` são candidatas a portfólio.

Além dos sidecars, **XMP embutido aparece em praticamente todo JPG**
(~3.000 caracteres por arquivo, com `Rating`).

Este é um eixo que o produto não tem hoje: **qualidade e seleção**, ortogonal
a onde e quando a foto foi tirada.

### XMP embutido — medido em todo o acervo

**1.528 de 1.528 JPG (100%)** carregam XMP embutido. Campos por frequência:

| Campo | Ocorrências | O que é |
|---|---|---|
| `xmp:Rating` | 2.727 | estrelas |
| `dc:creator` | 658 | autoria |
| `dc:subject` / `lr:hierarchicalSubject` | 638 | palavras-chave |
| `crs:Exposure`, `Shadows`, `Highlights`, `Blacks`, `Whites`, `WhiteBalance`, `ToneCurvePV`, `ProcessVersion` | 366–2.928 | ajustes de revelação do Lightroom |

Os campos `crs:` são um sinal indireto valioso: a foto **foi trabalhada no
Lightroom**. Foto revelada é foto que alguém escolheu — separa o material
tratado do bruto sem depender de estrela ou rótulo.

## 3. IPTC — não capturado, medido em todo o acervo

**322 de 1.528 JPG (21%)**, 8 campos distintos:

| Tag | Fotos | Conteúdo real |
|---|---|---|
| `(2,80)` By-line | 322 | `Alexandre Camerini` |
| `(2,55)` Date Created | 322 | `20260509` |
| `(2,60)` Time Created | 322 | `172545-0300` — **com fuso horário** |
| `(2,25)` Keywords | 319 | `Blurred` |
| `(2,62)` Digital Creation Date | 3 | `20250524` |
| `(2,63)` Digital Creation Time | 3 | `154958` |

O horário IPTC vem **com deslocamento de fuso** (`-0300`), assim como o
`OffsetTimeOriginal` da EXIF. Dois caminhos independentes para a mesma
informação que hoje é estimada por inferência.

## 3b. O buraco de cobertura: CR3

**Os 2.852 CR3 (63% do acervo) são ilegíveis pelo Pillow** — nem XMP nem
IPTC saem por esse caminho. Hoje o único acesso a eles é o libraw, que dá
exposição e lente mas não metadado editorial.

Consequência prática: qualquer sinal de curadoria extraído via Pillow
alcança no máximo 34% do acervo. Para os CR3, a curadoria do Lightroom vive
nos **sidecars `.xmp`** — que é justamente onde os 605 arquivos estão.

*(116 arquivos do catálogo não estavam no disco durante a medição: são os
dois volumes externos desmontados.)*

## 4. Nome de arquivo — sinal morto neste acervo

**100% seguem `ACM_NNNN`** — prefixo único, numeração sequencial. **Zero
datas recuperáveis.** Vale registrar como negativo: construir extração de
data por nome não traria nada aqui.

O número sequencial ainda ordena disparos dentro de um mesmo cartão, e
`ACM` distingue seu material de importados de terceiros — mas hoje tudo é
seu, então não separa nada.

Ressalva: nas **referências do Apple** e em material de celular o padrão é
outro (`IMG-20240210`, `PXL_...`), aí com data no nome.

## 5. Nome de pasta — o sinal que carrega o acervo hoje

19 segmentos distintos, e são falantes:

| Segmento | Fotos | Tipo |
|---|---|---|
| Dubai, Thai & Viet | 2.405 | viagem multi-país |
| 2026 | 1.832 | ano (técnico) |
| Teatro | 1.063 | **assunto/evento recorrente** |
| Quizomba | 450 | evento nomeado |
| Serena 15 Anos | 319 | evento nomeado |
| Pantanal Jul.2023 | 194 | viagem + data |
| 2025_05_24 | 143 | data (técnico) |
| Visconde de Maua - Abril 2015 | 18 | viagem + data |
| `[Originals]`, `[Developed]`, `backup`, `Pictures.wrp2` | — | técnico, a ignorar |

A cascata já usa isto com peso 0,60. O que **não** usa: a hierarquia entre
segmentos (`2026/Teatro` é ano + assunto), nem data embutida no nome da
pasta (`Pantanal Jul.2023`, `Abril 2015`).

## 6. Apple Fotos — 99.678 registros, um único usado

| Sinal | Registros | Usado |
|---|---|---|
| `album` | 25.304 | ❌ |
| `pessoa` | 12.760 | ❌ |
| `gps` | 16.192 | ✅ (158 heranças) |
| `data` | 43.309 | ✅ |
| `titulo` | 1.793 | ❌ |
| `favorito` | 198 | ❌ |
| `descricao` | 122 | ❌ |

Álbum e pessoa são **intenção humana já declarada** — o sinal mais forte que
existe num acervo, porque não é inferência, é decisão registrada.

## 7. Derivados — existem e não classificam

`hash_rapido` (xxhash) em todas, `hash_perceptual` (phash) sob demanda,
detecção de duplicatas em 4 níveis (exato, conteúdo, visual, rajada). Hoje
alimentam só a tela de duplicatas. Rajada, em particular, é agrupamento
pronto que a classificação ignora.

## Cobertura cruzada — o que limita cada sinal

| Sinal | Alcance no acervo medido |
|---|---|
| Nome de pasta | 100% |
| EXIF data | 100% |
| XMP embutido | 34% (todo JPG; CR3 é ilegível pelo Pillow) |
| EXIF rico (serial, fuso, exposição) | 34% |
| libraw (ISO, exposição) | 63% (só RAW) |
| IPTC | 7% (322 de 4.496) |
| XMP sidecar | 13% (605 de 4.496) |
| GPS herdado ±10 min | 3,5% |
| GPS próprio | 0% *nesta fatia* |

Nenhum sinal isolado cobre o acervo. É por isso que a decisão tem de ser por
**acúmulo de evidências**, e não por eleger um mecanismo — que foi o erro de
condução corrigido aqui.

## Este inventário mede uma fatia, não o acervo

As 4.496 fotos com arquivo são o que está acessível hoje: cinco pastas, das
quais duas em volumes desmontados. **O acervo do dono é maior**, e as partes
ausentes têm perfil diferente — material de celular grava GPS por padrão, e
outras câmeras podem preencher campos que estas deixam vazios.

Regra que decorre disso, e que vale para toda extração daqui em diante:
**um sinal ausente na amostra não é um sinal ausente no acervo.** A
extração deve tratar cada fonte de metadado como primeira classe mesmo
quando os arquivos disponíveis hoje não a exercitam — e os testes cobrem
esse caso com fixtures sintéticas, que é justamente para isso que elas
existem.
