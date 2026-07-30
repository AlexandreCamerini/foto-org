# Plano de metadados — fase 3

Executada em 2026-07-30. Método em `docs/prompts/00-protocolo.md`. Medição de
partida: `docs/COBERTURA_METADADOS.md` (300 arquivos reais) e a seção 2 de
`docs/AUDITORIA_FUNCIONALIDADES.md`. Decisões: D-019 a D-021.

**Resumo em uma frase:** o `exiftool` não está instalado nesta máquina e
instalá-lo é decisão do dono, mas isso acabou revelando um caminho melhor
para agora — **IPTC e XMP são legíveis em Python puro**, e os dois namespaces
que a auditoria encontrou sempre vazios já não estão mais.

---

## 1. Requisitos

| Requisito | Estado |
|---|---|
| Ler EXIF, incluindo sub-IFD e MakerNotes | parcial — EXIF sim, MakerNotes não |
| Ler XMP | **implementado** (requer `defusedxml`) |
| Ler IPTC/IIM | **implementado**, sem dependência nova |
| Ler ICC | não implementado |
| Cobrir JPEG, HEIC, TIFF, PNG, WebP, CR3, DNG, RAW | EXIF sim; XMP/IPTC nos formatos que o Pillow abre |
| Somente leitura | mantido — nada escreve em arquivo original |
| Funcionar sem dependência de sistema | **sim** — é o ponto desta fase |
| Custo de scan medido | ver §5 |

---

## 2. Estado antes desta fase

A auditoria mediu, num catálogo de 59 arquivos sintéticos:

| namespace | linhas | chaves distintas |
|---|---:|---:|
| `exif` | 252 | 5 |
| `gps` | 144 | 4 |
| `iptc` | **0** | 0 |
| `xmp` | **0** | 0 |
| `fs` | **0** | 0 |

`iptc` e `xmp` estão declarados em `models/catalog.py:133` e em
`docs/ARQUITETURA.md:42` desde o M1, e nunca receberam uma linha: o extrator
puro-Python simplesmente não olhava para eles.

---

## 3. O que foi implementado

**IPTC/IIM, sem dependência nova.** `PIL.IptcImagePlugin.getiptcinfo()` lê o
bloco IIM dentro do APP13 Photoshop IRB. Foi mapeado o subconjunto que um DAM
usa — o padrão tem dezenas de campos e despejar todos enche
`metadata_entries` de ruído:

`ObjectName` (título), `Keywords`, `DateCreated`, `TimeCreated`, `By-line`
(autor), `By-lineTitle`, `City`, `Sub-location`, `Province-State`,
`Country-PrimaryLocationName`, `Headline`, `Credit`, `Source`,
`CopyrightNotice`, `Caption-Abstract`.

Campo repetível (`Keywords` aparece uma vez por palavra) vira **uma linha com
os valores separados por ponto e vírgula**, não uma chave indexada: índice em
chave não sobrevive a reprocessamento — reordenar as palavras mudaria a chave.

**XMP, atrás de `defusedxml`.** O Pillow só analisa o pacote XMP com um parser
de XML endurecido, e com razão: é XML de origem não confiável dentro do
arquivo do usuário. A árvore XMP é achatada em chaves pontuadas
(`dc.creator`, `photoshop.City`), que é como o resto do mundo escreve caminho
de XMP.

**Sem `defusedxml`, o extrator degrada em silêncio** — EXIF e IPTC seguem
normais, XMP não é lido, e o aviso sai **uma vez** no log em vez de uma vez
por arquivo (em 500 mil fotos, o comportamento padrão do Pillow seria meio
milhão de linhas idênticas).

Para ligar: `pip install -e '.[xmp]'`. Foi declarado como extra em
`pyproject.toml`, **não instalado** — o venv é compartilhado com o checkout
principal e mexer nele estava fora da minha alçada (D-019).

---

## 4. exiftool: por que não entrou agora

`exiftool` não está instalado nesta máquina, e instalá-lo é alteração no
ambiente do dono — classe C do protocolo. Registrado em D-020.

O que ele acrescentaria sobre o que já temos:

| Capacidade | Python puro hoje | exiftool |
|---|---|---|
| EXIF básico | sim | sim |
| GPS | sim | sim |
| IPTC/IIM | **sim** | sim |
| XMP | sim, com `defusedxml` | sim |
| **MakerNotes** | não | **sim** — é o diferencial real |
| ICC | não | sim |
| Metadado em CR3/HEIC além do que libraw dá | não | sim |
| Vídeo | não | sim |

**A lacuna que sobra é MakerNotes.** É onde vive o dado mais rico (modo de
foco, lente exata, contagem do obturador, série de rajada) e o menos
padronizado. Para um DAM comercial isso importa; para o núcleo atual, não é
bloqueio.

O script de medição está pronto e não foi rodado:
`scripts/medir_exiftool.py` compara tag a tag contra a mesma amostra
estratificada de `docs/COBERTURA_METADADOS.md`. Basta instalar o exiftool e
rodá-lo para a decisão deixar de ser estimativa.

Quando entrar, entra como **segundo `MetadataExtractor`** — que é o primeiro
teste real daquele `Protocol`, hoje com uma implementação só (avaliação de
arquitetura, §2.3). Com `-stay_open` num processo persistente, e sem
`shell=True`, argumentos em lista e caminhos validados, como o invariante 5
exige.

---

## 5. Custo

Não medido em acervo real — o catálogo real do dono é classe C. No catálogo
sintético de 59 arquivos o scan completo levou **0,5 s** antes e depois da
mudança; a diferença está dentro do ruído. IPTC e XMP são lidos do mesmo
arquivo já aberto para o EXIF, sem I/O adicional.

O que **cresce** é `metadata_entries`: um JPEG editado no Lightroom pode
trazer dezenas de chaves XMP. Isso alimenta direto a decisão da §6.

---

## 6. Modelo de dados: o que fazer a seguir

**Recomendação: híbrido, e ainda não agora.**

O chave-valor de `metadata_entries` acomoda qualquer padrão sem migração, o
que é a escolha certa enquanto a cobertura ainda está mudando. O custo é que
nada ali é filtrável nem indexável por campo: "todas as fotos de que eu sou o
autor" hoje é uma varredura da tabela.

Os campos que merecem coluna tipada, pelo critério "a UI filtra ou ordena por
isso", são os de **direitos e autoria** — autor, detentor, licença, crédito.
São os quatro que a avaliação de arquitetura apontou como ausência estrutural
para um DAM comercial (§3), e agora que o IPTC os traz, eles existem no banco
sem ter onde morar.

**Por que não migrar já:** a decisão certa depende de saber quantas chaves por
foto um acervo real produz, e isso só se mede com o exiftool instalado ou com
o acervo do dono. Migrar antes é adivinhar o formato. A migração é aditiva e
barata; adiar custa pouco, errar custa uma segunda migração com 500 mil linhas
já escritas.

Estimativa de volume, para quando a decisão vier: hoje são ~7 linhas por foto;
com XMP de arquivo editado, algo entre 30 e 80. Em 500 mil fotos isso é 15 a
40 milhões de linhas em `metadata_entries` — o que torna o índice
`ix_metadata_entries_media_id` (já existente) obrigatório e recomenda um
índice composto `(media_id, namespace)`.

---

## 7. Vocabulário canônico

O mesmo conceito aparece em três padrões, e agora os três chegam ao banco:

| Conceito | EXIF | IPTC | XMP |
|---|---|---|---|
| Autor | `Artist` | `By-line` | `dc.creator` |
| Direitos | `Copyright` | `CopyrightNotice` | `dc.rights` |
| Legenda | `ImageDescription` | `Caption-Abstract` | `dc.description` |
| Palavras-chave | — | `Keywords` | `dc.subject` |
| Cidade | — | `City` | `photoshop.City` |
| Data | `DateTimeOriginal` | `DateCreated` + `TimeCreated` | `xmp.CreateDate` |

**Precedência proposta** (D-021), do mais para o menos confiável:
`XMP → IPTC → EXIF`. O critério não é o padrão em si: é que XMP costuma ser o
mais recentemente escrito (o editor grava XMP ao salvar), IPTC vem em segundo
por ser o formato de quem cataloga profissionalmente, e o EXIF é o que a
câmera pôs no momento do disparo e ninguém revisou.

Isso alimenta `docs/CONFIANCA.md` sem inventar regra nova: cada leitura vira
uma evidência com origem própria, e a divergência entre elas fica visível em
vez de ser resolvida em silêncio. Uma foto cujo `dc.creator` diverge do
`Artist` do EXIF mostra as duas evidências, e o usuário decide.

**Não implementado nesta fase** — depende da decisão de colunas tipadas (§6).

---

## 8. O que eu revisitaria

- **Quando o exiftool entrar:** se a assinatura de `MetadataExtractor` aguenta
  um processo persistente. `-stay_open` tem ciclo de vida (abrir, alimentar,
  fechar) que um extrator sem estado não tem.
- **Quando o primeiro acervo real for catalogado:** o volume de
  `metadata_entries` e a decisão de colunas tipadas.
- **Se vídeo entrar no escopo:** nada aqui cobre vídeo, e o Pillow não ajuda.
