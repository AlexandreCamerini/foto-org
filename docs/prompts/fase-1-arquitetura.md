# Fase 1 — Arquitetura

Leia `docs/prompts/00-protocolo.md` primeiro. Entregável:
`docs/AVALIACAO_ARQUITETURA.md`.

Você é especialista em arquitetura de sistemas de gestão de digital assets.
Avalie se o desenho atual do Foto Organizer sustenta um produto comercial, ou
onde ele quebra antes disso.

## Leituras de partida

`CLAUDE.md`, `docs/ARQUITETURA.md`, `docs/METODO_DE_TRABALHO.md`,
`docs/CONFIANCA.md`. Depois o código: `fotoorganizer/` por módulo e
`webapp/src/`.

## Requisitos que o desenho precisa sustentar

Assuma, e corrija no documento se o código indicar outra coisa:

| Dimensão | Alvo |
|---|---|
| Volume | 500 mil arquivos, 8 TB, num único catálogo local |
| Dispositivos | 5 a 10 fontes distintas (câmeras, telefones, cartões, backups) |
| Latência de UI | grade e filtros respondem em menos de 100 ms com o catálogo cheio |
| Scan | incremental, retomável, sem reler o que não mudou |
| Concorrência | scan, geração de thumbs e navegação simultâneos |
| Privacidade | núcleo funciona offline; nuvem é opt-in e revogável |
| Distribuição | app assinado para macOS, instalado por não-programador |

## O que avaliar

**Camadas.** `docs/ARQUITETURA.md` promete UI que nunca toca filesystem ou DB
direto. Verifique se `webapp/`, `fotoorganizer/server/` e `fotoorganizer/ui/`
respeitam isso. Liste as violações com `arquivo:linha`.

**Os cinco `Protocol` substituíveis.** MetadataExtractor, VisionProvider,
FaceRecognitionProvider, GeocodingProvider, SyncProvider. Para cada um:
existe o protocolo? existe mais de uma implementação? o domínio depende do
protocolo ou da implementação concreta? o que falta para um terceiro escrever
uma implementação sem tocar no núcleo? Note que `fotoorganizer/metadata/` tem
só `purepython.py` — um protocolo com uma implementação só é uma hipótese não
testada.

**Esquema do banco.** Avalie `fotoorganizer/models/` e a migração inicial
contra o que um DAM precisa: metadados por namespace, evidências, derivados,
taxonomia, versões, coleções, direitos de uso. Diga o que falta e o que está
modelado de forma que vai doer em 500 mil linhas. Aponte índices ausentes nos
caminhos de consulta que a UI usa.

**Trabalho em background.** `fotoorganizer/workers/` e
`fotoorganizer/server/jobs`: como um scan longo convive com a UI, o que
acontece se o processo morre no meio, onde estão os checkpoints, o que é
observável enquanto roda.

**Duas UIs.** Custo real de manter PySide6 e webapp em paralelo, e o que
falta para a remoção do PySide6 sair num commit só, como o `CLAUDE.md`
prevê. Isto é uma recomendação com esforço estimado, não uma execução.

**Arquitetura de trabalho com agentes.** Separado do produto: avalie
`CLAUDE.md`, `AGENTS.md`, `.claude/agents/` e `.claude/skills/` como
infraestrutura de desenvolvimento. Tamanho e foco do `CLAUDE.md`, se o
conhecimento reutilizável está em skill com referências carregadas sob
demanda ou inflado no prompt, se os quatro agentes têm fronteira clara, se há
script determinístico onde o comportamento precisa ser exato. Uma seção
curta, no fim.

## Comparação com o mercado

Como produtos de referência de DAM organizam catálogo, ingestão, derivados,
taxonomia e busca. Onde este desenho está bem posicionado e onde está
subdimensionado. Nomeie os produtos que usar como referência e a data da
consulta.

## Aceite

`docs/AVALIACAO_ARQUITETURA.md` na forma da seção "Forma de cada fase" do
protocolo, com um diagrama ASCII das camadas reais (não das prometidas) e uma
tabela de riscos arquiteturais ordenada por impacto, cada um com o sintoma
que aparece primeiro.
