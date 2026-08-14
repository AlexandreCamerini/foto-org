# Desenho — inventário por pasta

Decisão 3 do gate da fase 5 (D-061): implementar antes do lançamento,
antes da primeira execução física real. Este documento é só desenho —
nenhum código escrito ainda. Implementação fica para quando o dono
aprovar esta fatia especificamente (escopo próprio, fora do que D-056
abriu).

## Proposta original (`docs/PLANO_IA_E_PRODUTO.md` §5)

Cada pasta de destino recebe um `inventario.json` e um `INVENTARIO.md`
irmão. O JSON carrega, por foto: nome no destino, caminho de origem,
tamanho, `hash_sha256`, data de captura, câmera, lugar, e a lista de
evidências que decidiram o destino (origem, confiança, justificativa).
Duas propriedades buscadas: **auditável fora do app** (abrir a pasta em
qualquer lugar e saber por que cada foto está ali) e **reconstrução**
(se `catalog.db` se perder, os inventários reconstroem o catálogo sem
reprocessar pixel).

## Onde entra no pipeline

`fotoorganizer/operations/executor.py::_executar_item` já faz, nesta
ordem, para cada foto: calcula `hash_pre`, copia com criação exclusiva
(`_copiar_exclusivo`), calcula `hash_pos`, verifica igualdade, marca
`CONCLUIDA`, grava `AuditLog`. O inventário entra logo **depois** de
`self._audit_item(session, item, "copia_verificada", "ok")` — só quando
a cópia já foi verificada, nunca antes. Módulo novo,
`fotoorganizer/operations/inventario.py`, mantém `executor.py` focado
(mesmo padrão de separação que o projeto já usa entre `planner.py` e
`executor.py`).

`OperationItem.media_id` liga direto a `MediaFile`; de lá,
`Suggestion.evidencias` (relationship já existente, `secondary=
suggestion_evidence`) dá a lista de `Evidence` sem consulta nova — é o
mesmo dado que o Inspector já exibe, só que persistido em arquivo.

## Onde os arquivos moram

Um par `inventario.json` + `INVENTARIO.md` por **pasta de destino**
(`Path(item.destino).parent`), não por foto e não por plano — várias
execuções ao longo do tempo, de planos diferentes, que mandam fotos para
a mesma pasta (`Viagens/2024/França`, por exemplo, hoje e de novo daqui
a duas semanas) escrevem no MESMO par de arquivos, aditivamente.

## Schema do `inventario.json`

```json
{
  "pasta": "Viagens/2024/França",
  "gerado_por": "Foto Organizer",
  "fotos": [
    {
      "arquivo": "IMG_0001.jpg",
      "origem": "/Volumes/Fotos/2024/franca_0.jpg",
      "tamanho": 4821932,
      "hash_sha256": "e3b0c4...",
      "copiado_em": "2026-08-13T21:40:00",
      "data_capturada": "2024-05-04T10:00:00",
      "camera": "Canon EOS R5",
      "lugar": {"pais": "França", "regiao": "Provence", "cidade": "Avignon"},
      "evidencias": [
        {
          "campo": "pais", "origem": "geocoding_offline", "valor": "França",
          "nivel": "alta", "score": 0.85,
          "justificativa": "geocodificação offline das coordenadas GPS do EXIF (43.9500, 4.8083)"
        },
        {
          "campo": "viagem", "origem": "geocoding_offline", "valor": "França",
          "nivel": "alta", "score": 0.85,
          "justificativa": "3 fotos entre 04/05/2024 e 06/05/2024 — estadia geocodificada"
        }
      ],
      "versao_logica": "4.1"
    }
  ]
}
```

Cada entrada carrega a própria `versao_logica` (não só um cabeçalho
único) — evidências de fotos coladas na mesma pasta em execuções
diferentes podem ter sido geradas por versões diferentes da lógica de
classificação; ficar isso implícito no cabeçalho perderia a informação
exata que `docs/CONFIANCA.md` já exige por evidência.

`hash_sha256` é `item.hash_pos` (o que o executor já verificou) — nenhum
recálculo, nenhuma leitura extra do arquivo.

## `INVENTARIO.md`

Renderização humana do MESMO json — **regenerado por inteiro** a cada
escrita, nunca editado incrementalmente à parte. Isso evita o par
json/md divergir: o JSON é a fonte de verdade, o Markdown é sempre
derivado dele. Formato: uma seção por foto, nome como título, tabela ou
lista com data/câmera/lugar, e a lista de evidências como está no
Inspector (`campo: valor` + justificativa), em ordem de confiança.

## Idempotência e re-execução

Antes de acrescentar uma entrada, checar se `arquivo` (nome final no
destino) já existe no array `fotos` do JSON carregado — se existir, não
duplicar (mesmo espírito da barreira de "já copiadas" que
`planner.py::criar_plano` já aplica antes de gerar itens novos; esta é
uma segunda barreira, mais barata que confiar só na primeira).

## Falha na escrita do inventário não desfaz a cópia

A cópia do arquivo real já foi verificada por hash quando o inventário é
escrito — se a escrita do JSON/MD falhar (permissão, disco cheio bem
naquele instante), a foto **continua copiada e válida**: apagar uma
cópia verificada por causa de uma falha num arquivo auxiliar violaria o
invariante "nunca apagar o que já foi verificado". Comportamento:
registrar `AuditLog` com `acao="inventario"`, `resultado="erro: ..."`,
manter `item.status = CONCLUIDA`, e expor um contador
`stats["inventario_falhou"]` no retorno de `executar()` — visível, não
silencioso, mas não bloqueante.

## O que NÃO muda

- Nenhuma migração Alembic — os arquivos vivem no filesystem de destino,
  não em `catalog.db`.
- Nenhuma mudança em `planner.py` ou na lógica de resolução de destino/
  colisão — o inventário só lê o que o executor já decidiu.
- Nenhuma mudança em `classification/**` — consome `Evidence` já
  persistida, não gera evidência nova.

## Escopo desta fatia, quando implementada

1. `fotoorganizer/operations/inventario.py`: função que recebe
   `session`, `item: OperationItem`, devolve nada — lê/escreve os dois
   arquivos na pasta de destino.
2. Uma chamada em `executor.py::_executar_item`, depois do
   `_audit_item("copia_verificada", "ok")`.
3. `stats["inventario_falhou"]` no retorno de `executar()`.
4. Testes: fixture com `tmp_path` como raiz de destino, plano sintético,
   `_executar_item` chamado duas vezes (mesma foto e foto nova na mesma
   pasta) — cobre idempotência e acréscimo. Teste de falha de escrita
   (permissão negada via `tmp_path` read-only) — cobre o caminho de erro
   não-bloqueante.
5. Verificação: `scripts/verificar.sh` verde + prova manual (rodar um
   plano real contra um catálogo sintético isolado, abrir o
   `INVENTARIO.md` gerado).

Não desenhado ainda, decisão em aberto para quando isto for aprovado:
formato exato do Markdown (tabela vs. lista) — fica para revisão junto
da implementação, não bloqueia o desenho de dados acima.
