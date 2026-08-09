# Referência: como o Immich resolve os mesmos problemas

Mapa de leitura do [Immich](https://immich.app) — gerenciador de fotos
self-hosted, o software livre com maior sobreposição de escopo com o Foto
Organizer. Levantado em 2026-08-08 a partir do fork local em
`~/dev/fot` (`AlexandreCamerini/Fot`), versão 3.1.0, commit `5ad1e4e0f`.

Cinco agentes de reconhecimento leram o repositório em paralelo, um por área.
Cada mapa descreve **o mecanismo** e aponta `arquivo:linha`; nenhum reproduz
blocos de código.

## Por que este material existe

O Immich resolveu, com anos de bug report em cima, um conjunto de problemas
que o Foto Organizer também tem: ordem de precedência de tags EXIF, arquivo
que some quando o volume desmonta, movimentação de arquivo que sobrevive a
crash, virtualização de grade com dezenas de milhares de fotos. Reler essas
decisões custa uma tarde; redescobri-las custa meses.

O que ele **não** resolve — e a diferença define o recorte útil deste
material — é o problema central deste projeto: um acervo em que o pixel é
raro. O Immich assume que toda foto tem arquivo legível; ~95% dos registros
deste catálogo não têm (D-028). Metade do que o Immich faz de mais
sofisticado (CLIP, faces, OCR, busca semântica) alcança 5% do acervo aqui.

## Licença — leia antes de copiar qualquer coisa

O Immich é **AGPLv3**, incluindo o diretório `machine-learning/`.

- Ler para entender arquitetura e **reimplementar**: livre.
- **Copiar código** para o Foto Organizer: contamina o projeto inteiro com a
  AGPL. Não fazer.
- Os **pesos de modelo** que eles baixam do Hugging Face (`immich-app/*`) são
  outra coisa: têm as licenças dos modelos originais (OpenCLIP, InsightFace),
  não a do Immich.

Os mapas foram escritos com essa restrição: descrevem mecanismo, não
transcrevem implementação.

## Os mapas

| Arquivo | Cobre |
|---|---|
| [01-ingestao-e-storage.md](01-ingestao-e-storage.md) | descoberta de arquivos, bibliotecas externas in-place, hash e dedup, storage template, journal de move, estados online/offline |
| [02-metadados-e-midia.md](02-metadados-e-midia.md) | precedência de tags EXIF, sidecar, RAW/HEIC, reverse geocoding offline, thumbnails, transcodificação, fila de jobs |
| [03-modelo-de-dados.md](03-modelo-de-dados.md) | tabelas centrais, modelo de tempo, proveniência, agrupamentos, soft delete, índices |
| [04-machine-learning.md](04-machine-learning.md) | contrato ML↔servidor, CLIP, detecção e clusterização facial, duplicata por embedding, OCR |
| [05-ui-web.md](05-ui-web.md) | contrato de timeline em duas chamadas, virtualização em dois níveis, teclado, visualizador, estados |

Cada mapa fecha com uma seção separando o que é específico do Immich
(multiusuário, Postgres, Redis, servidor) do que é portável para um app
desktop local-first single-user em Python com SQLite.

## O que saiu daqui

A leitura destes cinco mapas produziu
[`docs/prompts/fase-12-alcance-e-tempo.md`](../prompts/fase-12-alcance-e-tempo.md):
os três itens que mudariam substancialmente o projeto, dimensionados na régua
do `ROADMAP.md` (valor por unidade de custo **para este acervo**).

Resumo do julgamento, para quem não for ler os cinco:

**Vale importar** — a máquina de estados de alcance dos arquivos (ataca a
causa direta da queda de quatro itens do roadmap), o modelo de tempo de dois
instantes (pré-requisito coerente do timezone estimado), e o estado do
pipeline gravado no catálogo em vez de na fila.

**Não vale** — duplicata por embedding CLIP (o phash resolve sem depender de
pixel), payload colunar da grade com thumbhash (95% dos registros não têm
imagem para pré-visualizar), journal de move em duas fases (o executor daqui
copia, não move, e já cria com `'xb'`).

**Onde este projeto já está à frente** — a tabela `evidence` com origem,
confiança e justificativa é muito mais rica que o `lockedProperties` do
Immich (um array de nomes de coluna, sete campos, sem quem, quando ou valor
anterior). E `papel` ACERVO/SINAL resolve com mais precisão o que eles
espalham entre `visibility` e `isOffline`.
