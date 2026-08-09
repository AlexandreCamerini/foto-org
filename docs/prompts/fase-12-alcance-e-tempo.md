# Fase 12 — alcance dos arquivos e modelo de tempo

Proposta derivada da leitura do Immich (`docs/referencia-immich/`, 2026-08-08).
São os três itens — de cinco áreas mapeadas — que sobrevivem à régua do
`ROADMAP.md`: **valor por unidade de custo para este acervo**.

O corte foi grande e é o certo. Busca semântica, CLIP, faces, OCR, HLS, índice
vetorial e layout justificado consomem pixel, e pixel alcança ~5% do acervo
(D-028). Nada disso entra agora, pelo mesmo motivo que já rebaixou os itens 6 e
7 do roadmap.

Os três que ficam não dependem de pixel nenhum.

---

## Item A — reapontar fonte que mudou de lugar

**O achado é específico e o código já admite o buraco.**
`fotoorganizer/sources/disponibilidade.py:99-107` detecta que o volume voltou
noutro ponto de montagem e **recusa-se explicitamente a agir**:

> `# O volume voltou noutro ponto. Não reescrevemos o caminho aqui: mover 45 mil
> linhas de mídia é operação do usuário, não efeito colateral de uma
> verificação.`

A recusa está certa. O problema é que **a operação do usuário não existe**:
`fotoorganizer/cli.py:156-158` imprime "Reaponte a fonte para o caminho novo
antes de varrer" e não há comando, endpoint nem tela que faça isso. O usuário é
instruído a executar algo que o app não oferece.

O Immich resolve exatamente este caso com `migrateFilePaths(previous, current)`
(`repositories/database.repository.ts:403`, chamado de
`services/storage.service.ts:97-132`): quando a raiz muda, reescreve os prefixos
de caminho em massa no banco, **sem tocar em arquivo**, e valida uma amostra
contra o prefixo esperado antes de aceitar — se não bate, lança
`InconsistentMediaLocation` em vez de corromper o catálogo. Ver
`docs/referencia-immich/01-ingestao-e-storage.md`, §1.C8.

- *Muda o quê:* 45.397 fotos em volume desmontado (D-028) voltam sozinhas no dia
  em que o disco montar, mesmo com nome de ponto diferente
  (`/Volumes/photo` → `/Volumes/photo 1`), sem re-scan e sem recatalogar do zero.
  É a causa direta da queda dos itens 6, 7, 8 e 9 do roadmap — o "item que a
  lista ainda não tem", na formulação do próprio arquivo.
- *Esforço:* **S**. A detecção está pronta (`ponto_atual`, `volume_id`,
  `EstadoDaFonte.mudou_de_lugar`); a identidade de volume já é estável
  (`security/volumes.py`). Falta a escrita: um `UPDATE` de prefixo em
  `media_files.caminho` + `Source.caminho`, numa transação.
- *Custo recorrente:* zero.
- *Desbloqueia:* tudo que depende de pixel. Não implementa nada novo de análise —
  reconecta o que já foi catalogado.

**Como fazer, com as garantias que o projeto já exige:**

1. Dry-run obrigatório antes: quantas linhas, prefixo velho → prefixo novo,
   amostra de 10 caminhos resultantes. Reusa a disciplina do M5.
2. Validação de amostra à la Immich: antes de commitar, `stat` de N caminhos
   novos. Se algum não existe, aborta inteiro — prefixo errado reescreve 45 mil
   linhas para lugar nenhum.
3. Entrada em `audit_log` (`models/operations.py:70`), porque é escrita em massa
   no catálogo.
4. Reversível: guardar o prefixo anterior na entrada de auditoria permite desfazer
   com o mesmo mecanismo.
5. Superfície: comando `reapontar` no CLI **e** ação na tela de fontes — o caso
   de uso ("plugei o HD") acontece com o app aberto.

**Classe C do protocolo** (`00-protocolo.md`): é escrita em massa no catálogo.
Dry-run e confirmação explícita, sem timeout.

---

## Item B — o terceiro estado de alcance, e o laço que o mantém

Hoje o app distingue **dois** estados, e a distinção está bem-feita:

- `MediaFile.arquivo_ausente` (`models/catalog.py:132`) — referência de catálogo
  externo, sem arquivo neste Mac (iCloud);
- `Source.disponivel` (`models/catalog.py:82`) — a fonte inteira não responde
  agora.

`server/app.py:244-249` (`_motivo_indisponivel`) resolve a UI com esses dois, e a
decisão de responder pela **fonte** em vez de um `stat` por miniatura está certa
e documentada.

Falta o terceiro caso: **arquivo que sumiu de uma fonte que está montada.** Hoje
ele é indistinguível de "sempre esteve lá" até alguém tentar abrir. E falta o
laço que mantém os três estados vivos.

O Immich tem os dois: `asset.isOffline` + o ciclo
`handleQueueSyncAssets` → `checkExistingAsset` (`services/library.service.ts:494-630`),
que por lote faz `stat`, marca offline o que sumiu, re-extrai o que mudou de
`mtime`, e — o que importa aqui — **reonlina o que reapareceu** (`CHECK_OFFLINE`).
Mais a tabela `integrity_report` com três tipos nomeados: `untracked_file`,
`missing_file`, `checksum_mismatch` (`enum.ts:404`). Ver
`docs/referencia-immich/01-ingestao-e-storage.md` §1.B4 e
`03-modelo-de-dados.md` §5.

- *Muda o quê:* o app passa a dizer a verdade sobre o acervo sem que o usuário
  descubra por acidente. "Sumiu" e "está na gaveta" viram respostas diferentes, e
  arquivo que reaparece volta sozinho. É o invariante 8 aplicado ao alcance:
  nunca apagar registro, sempre saber o que ele é.
- *Esforço:* **M**. Coluna de estado + tabela de relatório + o laço em lote com
  auto-limitação.
- *Custo recorrente:* zero em dinheiro; I/O periódico controlado.
- *Depende de:* nada. *Complementa* o item A — juntos fecham "onde está cada
  arquivo".

**Duas coisas a copiar do desenho deles:**

**A varredura se auto-limita.** O `IntegrityChecksumCheckpoint`
(`services/integrity.service.ts:539,556,574`) guarda a data do último item
processado, processa por N minutos **ou** X% do acervo, e se reenfileira. Para
re-verificar 101 mil registros num desktop sem travar a máquina do dono, é o
desenho certo — e encaixa no `ScanSession.checkpoint`
(`models/catalog.py:108`), que já existe.

**Mudança detectada por `mtime`, não por rehash** (`library.service.ts:593-630`).
O índice `ix_media_files_mtime_tamanho` (`models/catalog.py:122`) já existe
exatamente para isso. Rehash só sob demanda, como manda o M1.

---

## Item C — modelo de tempo de dois instantes

**Este é o item com prazo.** Hoje há uma coluna de data
(`MediaFile.data_capturada`, `models/catalog.py:146`) e uma de fuso
(`tz_estimado`, `:147`), esta última ainda sem nenhum leitor ou escritor
(confirmado em `fase-11-timezone-estimado.md`).

O Immich guarda **dois instantes** e nenhuma coluna de offset
(`docs/referencia-immich/03-modelo-de-dados.md` §3):

| Coluna | Semântica |
|---|---|
| `fileCreatedAt` | o instante absoluto (UTC real) da captura |
| `localDateTime` | a **hora de parede** da captura, gravada como se fosse UTC |
| `timeZone` | o nome da zona resolvida |

O offset nunca é armazenado: sai da diferença entre os dois
(`queries/asset.repository.sql:391-397`). E é isso que permite indexar
`("localDateTime" at time zone 'UTC')::date` e ordenar a grade pela hora que a
pessoa viveu, não pela hora absoluta.

**Por que importa agora, e não depois:** a fase 11 vai escrever `tz_estimado` a
partir do país herdado. Com uma coluna de data só, esse campo não muda nada do
que o usuário vê — a grade continua ordenando e agrupando pelo mesmo instante,
e o fuso vira metadado decorativo. Pior: passa a existir uma coluna cujo
significado depende de outra estar preenchida, que é a receita de bug silencioso
em acervo de 25 anos com viagens internacionais (Portugal/Itália, D-029).

Com dois instantes, `tz_estimado` vira enriquecimento de um modelo que já é
coerente sozinho.

- *Muda o quê:* a hora que a interface mostra passa a ser a hora que a pessoa
  viveu, de forma consistente, com ou sem fuso conhecido. Habilita agrupamento
  por dia local correto — que é a base de evento e viagem.
- *Esforço:* **M**. Migração Alembic + preenchimento retroativo (para foto sem
  fuso conhecido, os dois instantes são iguais — é exatamente o `keepLocalTime`
  deles, `metadata.service.ts:1023`) + ajuste dos pontos de leitura.
- *Custo recorrente:* zero.
- *Bloqueia:* deveria entrar **antes ou junto** da fase 11. Depois de 101 mil
  registros processados e do timezone estimado implementado, a migração custa
  várias vezes mais.

**Nota sobre o wire format:** o Immich manda `fileCreatedAt` + `localOffsetHours`
(float) e reconstrói no cliente. Isso é economia de bytes para servidor
multiusuário; aqui, mandar a hora local direto no JSON é mais simples. A
recomendação vale para o **armazenamento**, não para o transporte —
`docs/referencia-immich/05-ui-web.md` §4.3 registra a distinção.

---

## Baratos, se sobrar fôlego

**Padrões de exclusão default no scanner.** O Immich nasce com `@eaDir`, `._*`,
`#recycle`, `#snapshot`, `.stversions`, `.stfolder`
(`services/library.service.ts:238-245`). `Source.padroes_ignorados`
(`models/catalog.py:91`) já existe e nasce vazio. `._*` sozinho (AppleDouble)
evita lixo real em disco externo formatado no macOS.

**Separar pista extraída de agrupamento efetivo nas rajadas.** O padrão que este
projeto já aplica em `gps_lat` vs `gps_lat_estimado` e em `tipo_imagem` vs
`tipo_confirmado` o Immich aplica também às rajadas: `asset_exif.autoStackId`
guarda o BurstID lido do arquivo, `asset.stackId` guarda a pilha que existe
(`03-modelo-de-dados.md` §4). Vale estender.

---

## O que este mapa recomenda **não** fazer

Registrado porque a tentação é real ao ler o Immich:

- **Duplicata por embedding CLIP.** Eles reusam o índice de busca semântica com
  `maxDistance = 0.01` (quase-idêntico). O `phash` daqui responde a mesma
  pergunta sem depender de pixel em resolução útil nem de índice vetorial.
- **Grade com bucket colunar + `ratio` + `thumbhash`.** O contrato de duas
  chamadas é elegante e `/api/midia/linha-do-tempo` já é metade dele — mas a
  grade já é virtualizada (`@tanstack/react-virtual`,
  `webapp/src/components/PhotoGrid.tsx:45`) com células uniformes, onde `ratio`
  não muda nada, e 95% dos registros não têm imagem para pré-visualizar.
- **Journal de move em duas fases.** Seria a recomendação óbvia, mas
  `operations/executor.py:231-243` já cria com `'xb'` (sobrescrever é impossível
  no nível do SO) e retoma por status de item. Como a operação daqui é **cópia**,
  não move, o journal resolveria um problema que este projeto não tem.

## Onde este projeto já está à frente

Não mexer nisto achando que o Immich faz melhor:

- A tabela `evidence` (`models/inference.py:39`) com origem, confiança e
  justificativa é muito mais rica que o `lockedProperties` deles — um array de
  nomes de coluna, sete campos, sem quem, quando ou valor anterior, usado como
  *dirty bit* de write-back para o sidecar (`03-modelo-de-dados.md` §4).
- `MediaRole.ACERVO/SINAL` (`models/catalog.py:45`) resolve com mais precisão o
  que eles espalham entre `visibility` e `isOffline`.
- Reconhecimento facial: o Immich **não tem estado de sugestão** — grava
  `personId` como fato e não registra discordância
  (`04-machine-learning.md` §5.3). O invariante 6 daqui exige o contrário.

O único mecanismo do `lockedProperties` que vale importar é o de aplicação: no
UPSERT, cada coluna vira
`CASE WHEN 'col' = ANY(locked) THEN <valor atual> ELSE <novo> END`
(`repositories/asset.repository.ts:259-263`) — a proteção do que o usuário editou
acontece dentro da própria escrita, não numa checagem prévia que dá para
esquecer.
