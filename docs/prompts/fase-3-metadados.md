# Fase 3 — Base de metadados completa

Leia `docs/prompts/00-protocolo.md` primeiro. Entregável:
`docs/PLANO_METADADOS.md`. Depende da medição de namespaces da fase 2; se ela
não existir, meça aqui.

O objetivo do dono: cada foto tem, na base, tudo o que o arquivo carrega.
Estude os padrões e proponha o modelo de dados que os acomoda.

## Leituras de partida

`docs/COBERTURA_METADADOS.md` (medição real sobre 300 arquivos),
`docs/INVENTARIO_DE_SINAIS.md`, `fotoorganizer/metadata/base.py` e
`purepython.py`, `fotoorganizer/models/catalog.py`, item 6 de "Próximas
versões" em `docs/ROADMAP.md`.

Dois fatos já medidos, que são o ponto de partida e não precisam ser
redescobertos: nenhuma das 300 fotos da amostra tem coordenada GPS, e
`make`/`model` está vazio nos 99 CR3 porque o `libraw` não expõe o fabricante.

## Requisitos

- Leitura completa do que existe no arquivo, por formato: JPEG, HEIC/HIF,
  TIFF, PNG, WebP, CR3, DNG e demais RAW.
- Padrões cobertos: EXIF (incluindo MakerNotes), XMP, IPTC/IIM e IPTC Core,
  ICC, e o que o formato específico trouxer.
- Somente leitura. Nada de escrita em arquivo original nesta fase nem nas
  seguintes (sidecar XMP é fase posterior por design).
- Custo de scan medido, não estimado.
- Degradação graciosa: o app funciona sem nenhuma dependência de sistema
  instalada.

## Mapa dos padrões

Para cada padrão: o que ele traz que os outros não trazem, onde ele vive
dentro do arquivo, quais formatos o suportam, e o que muda por fabricante.
Trate MakerNotes explicitamente — é onde vive o dado mais rico e o menos
padronizado.

Marque, para cada campo que interessa a um DAM (data, câmera, lente,
exposição, GPS, orientação, autor, direitos, palavras-chave, legenda,
hierarquia de assunto, rating, região de face), em quais padrões ele pode
aparecer e qual é a ordem de precedência quando aparecem em mais de um com
valores diferentes. Essa ordem de precedência é decisão de produto: registre
em `docs/DECISOES.md`.

## Estratégia de extração

Hoje existe só o extrator puro-Python. O ROADMAP prevê exiftool em batch
(`-stay_open`). Decida se entra agora, com:

- ganho medido: rode `exiftool` sobre a mesma amostra estratificada de
  `docs/COBERTURA_METADADOS.md` e conte quantas tags a mais por formato, e
  quais campos vazios ele preenche;
- custo medido: tempo por arquivo e por lote, com e sem `-stay_open`;
- política de fallback quando não estiver instalado, e como a UI comunica
  que o catálogo está em modo reduzido;
- como isso passa pela regra de subprocesso segura do `CLAUDE.md`
  (sem `shell=True`, argumentos em lista, caminhos validados).

Se `exiftool` não estiver instalado no ambiente, instalar é classe C: descreva
a medição que faria, deixe o script pronto em `scripts/medir_exiftool.py`, e
siga com a proposta marcada como não medida.

## Modelo de dados

A decisão central desta fase: chave-valor genérico em `metadata_entries`
versus colunas tipadas para o que é consultado com frequência. Avalie os dois
e proponha o híbrido, se for o caso, com:

- quais campos merecem coluna tipada, pelo critério "a UI filtra ou ordena
  por isso";
- o que fica em chave-valor e como é consultado sem varrer a tabela;
- volume estimado: linhas por foto × 500 mil fotos, tamanho do catálogo,
  impacto no tempo de abertura e nos índices;
- migração Alembic proposta, escrita como proposta no documento — não
  aplicada;
- como reprocessar metadados de um acervo já catalogado sem reler pixels.

## Vocabulário canônico

Como o mesmo conceito vindo de EXIF, XMP e IPTC converge para um campo só sem
perder a origem. Isto alimenta direto o modelo de evidências do
`docs/CONFIANCA.md`: o valor canônico é a conclusão, cada leitura de padrão é
uma evidência com origem e confiança. Mostre um exemplo completo com um campo
que aparece em três padrões com valores divergentes.

## Interoperabilidade e saída

O que precisa estar na base para exportar e importar em formatos que outros
DAMs leem, e qual é a estratégia de saída do usuário — se ele desistir do
produto, o que ele leva.

## Aceite

`docs/PLANO_METADADOS.md` na forma do protocolo, com o mapa de padrões, a
tabela de precedência por campo, a medição de ganho e custo do exiftool (ou a
marcação de não medido com o script pronto), o modelo de dados proposto com
diagrama ASCII, e a migração escrita como proposta.
