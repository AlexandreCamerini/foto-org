# Referência: como o PhotoPrism resolve os mesmos problemas

Mapa de leitura do [PhotoPrism](https://www.photoprism.app) — gerenciador de
fotos self-hosted, AGPLv3, escrito em Go (backend) e Vue 3 (frontend web).
Levantado em 2026-08-12 a partir de uma auditoria paralela de 453
capabilities feita em `~/dev/photoprism-develop` (branch `develop`), com
âncoras `arquivo:linha` verificadas contra o código real.

Três agentes de domínio deste projeto (`agente-arquivos`, `agente-imagem`,
`agente-ux`) leram os recortes relevantes da auditoria em paralelo, cada um
julgando fit para o foto-organizer com o próprio contexto de domínio — não
agentes leitores genéricos. Cada mapa descreve **o mecanismo** e aponta
`arquivo:linha`; nenhum reproduz blocos de código.

## Por que este material existe

Mesmo motivo do `../referencia-immich/`: o PhotoPrism resolveu, com anos de
uso em cima, parte do mesmo conjunto de problemas que o foto-organizer tem —
precedência de tags de metadado, conversão RAW/HEIC, cache de thumbnail,
backup, busca por sintaxe livre. Reler essas decisões custa uma tarde;
redescobri-las custa meses.

A diferença de recorte é a mesma do Immich: o PhotoPrism assume acervo com
pixel local; aqui ~5% dos registros têm (D-028). O corte aplicado nos três
mapas é o mesmo do `referencia-immich` — qualquer mecanismo que dependa de
abrir a imagem foi julgado contra essa fatia, não contra o acervo inteiro.

## Licença — leia antes de copiar qualquer coisa

O PhotoPrism é **AGPLv3**, mesma licença do Immich.

- Ler para entender arquitetura e **reimplementar**: livre.
- **Copiar código** para o foto-organizer: contamina o projeto inteiro com a
  AGPL. Não fazer.

Os mapas foram escritos com essa restrição: descrevem mecanismo, não
transcrevem implementação.

## Os mapas

| Arquivo | Cobre | Agente |
|---|---|---|
| [01-ingestao-e-arquivos.md](01-ingestao-e-arquivos.md) | varredura/indexação incremental, importação, biblioteca externa/WebDAV, backup, purge, integridade, CLI de operação | `agente-arquivos` |
| [02-metadados-imagem-e-visao.md](02-metadados-imagem-e-visao.md) | precedência EXIF/XMP/IPTC, timezone, conversão RAW/HEIC, thumbnails, modelo de dados de faces, o que sobrevive do pipeline de visão ao corte de pixel | `agente-imagem` |
| [03-ux-e-organizacao.md](03-ux-e-organizacao.md) | busca por DSL, edição em lote, seleção, navegação por teclado, revisão/triagem em massa | `agente-ux` |

Cada mapa fecha com uma seção separando "vale considerar para o
foto-organizer" de "não vale (por quê, calibrado pelo acervo real)" — e,
onde aplicável, onde o PhotoPrism perde para o que o foto-organizer ou o
Immich já fazem melhor.

## O que saiu daqui

A leitura destes três mapas, cruzada com os cinco do `referencia-immich`,
produziu
[`docs/prompts/fase-14-photoprism-e-sintese.md`](../prompts/fase-14-photoprism-e-sintese.md):
os itens que sobrevivem a dois filtros em sequência — **diferencial real vs.
produtos de mercado** (não "o PhotoPrism/Immich faz X", e sim "X não é o que
apps mainstream fazem") e, só depois, **valor por unidade de custo para este
acervo**. A maior parte do que os dois mapas anteriores marcaram como "vale
considerar" morre no primeiro filtro — é bom mecanismo, mas é table stakes
de qualquer app de fotos decente, não vantagem competitiva.

Resumo do julgamento, para quem não for ler a fase inteira: três itens
sobrevivem — um filtro composto de busca sobre a proveniência que já existe
em `evidence` (nenhum concorrente de mercado tem os campos para oferecer
isso), proteção da camada de julgamento que não se refaz (export legível +
backup agendado + checagem de esquema no boot), e detecção incremental de
sidecar `.xmp` alterado sem o arquivo de mídia mudar (hoje cai no chão). Ver
a fase para âncoras, esforço e o que foi descartado com o critério que
matou cada item.
