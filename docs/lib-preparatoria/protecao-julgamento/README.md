# Item B — proteger a camada de julgamento

Staging pronto para integrar quando a fase 5 abrir a fronteira. Nasce de
`docs/prompts/fase-14-photoprism-e-sintese.md` §4 — a FORMA (export legível
+ backup agendável com retenção do PhotoPrism, checagem de esquema no boot
do Immich), descrita em `docs/referencia-photoprism/` e
`docs/referencia-immich/`. Nenhuma linha vem dos repositórios de referência
em si (ambos AGPLv3), só das descrições de mecanismo nos dois diretórios
acima.

## O que existe hoje (evidência)

- **Backup ad-hoc, em quatro scripts, todos com `sqlite3 .backup`** (nunca
  `cp`, porque copiar um WAL aberto em transação pode gravar arquivo
  inconsistente):
  - `scripts/preparar_versao.sh:121-125` — via CLI `sqlite3 "$DB"
    ".backup '$BACKUP'"`, com fallback `cp` avisando para fechar o app
    primeiro.
  - `scripts/rebaixar_nao_acervo.py:88-90` (`_copiar`) — mesma CLI,
    `destino = db.with_name(f"{db.stem}-antes-do-rebaixamento-{carimbo}.db")`.
  - `scripts/podar_metadados.py:55` (`_copiar`) — idêntico, sufixo
    `-antes-da-poda-`.
  - `scripts/medir_nome_de_album.py:105-110` — usa a API Python
    `sqlite3.Connection.backup()` (não a CLI), citando explicitamente "o
    catálogo roda em WAL, e copiar só o `.db` deixaria de fora o que ainda
    está no journal".
  - Nenhum dos quatro tem retenção — cada rodada acumula um arquivo novo,
    para sempre, e nenhum roda sozinho (é disciplina do script, não do
    app).
- **Nenhuma checagem de esquema no boot.** `fotoorganizer/database/migrate.py`
  (`upgrade_to_head`) roda `alembic upgrade head` sempre que o app inicia,
  sem antes comparar o que o banco diz que é com o que o código espera.
  D-038 (em `docs/DECISOES.md`) registra por escrito que a migração `0014`
  não é atômica: sob pysqlite, `ADD COLUMN` comita sozinho, então uma
  interrupção entre a coluna criada e `alembic_version` seria atualizado
  deixaria a tentativa seguinte morrer em "duplicate column name" — o app
  para de abrir sem dizer por quê.
- **Schema real das tabelas de julgamento**:
  `fotoorganizer/models/inference.py:39-58` (`Evidence`) e `:61-79`
  (`Suggestion`). A revisão Alembic mais recente no repositório é `0016`
  (`fotoorganizer/database/migrations/versions/0016_resolvido_automaticamente_em_duplicate_groups.py`).

## O que este item entrega

`lib.py`, em três blocos independentes:

1. **Export legível** — `LinhaEvidencia`/`LinhaSugestao` (dataclasses que
   espelham `Evidence`/`Suggestion`), `exportar_julgamento(...)` (puro,
   monta o dict) e `salvar_export(documento, destino)` (grava JSON com
   `indent=2`, `ensure_ascii=False`, `sort_keys=True` — diff limpo em git).
2. **Backup com retenção** — `fazer_backup` (mesma disciplina `sqlite3
   .backup`/API Python já validada nos quatro scripts), `nome_backup`,
   `listar_backups`, `aplicar_retencao(db_path, reter)`,
   `executar_backup_com_retencao` (laço completo) e `deve_rodar_backup`
   (função pura de agendamento, testável sem esperar relógio real).
3. **Checagem de esquema** — `verificar_esquema(con, revisao_esperada)`
   devolve um veredito de três estados (`ok`, `desatualizado`,
   `downgrade`, `nao_inicializado`); `exigir_esquema_compativel` é o que o
   boot chamaria de verdade — só levanta `EsquemaDivergente` em downgrade,
   porque `desatualizado` é retomável rodando a migração de novo (é
   exatamente o cenário D-038, coberto no teste
   `test_migracao_0014_interrompida_e_desatualizado_nao_downgrade`).

## Decisões (Classe A, ver também `docs/DECISOES.md`)

1. **JSON, não YAML, para o export.** O PhotoPrism usa YAML
   (`internal/photoprism/backup/albums.go:19`, descrito em
   `docs/referencia-photoprism/`), mas o prompt de origem dá liberdade de
   escolha. JSON é biblioteca padrão — zero dependência nova, relevante
   porque este item não pode editar `pyproject.toml` enquanto a fronteira
   estiver fechada — e é git-diffável com `indent=2`, que é o requisito
   real ("legível, versionável em git, dá diff"), não a sintaxe YAML em
   si.
2. **Export aceita dados já lidos (dataclasses), não sessão SQLAlchemy.**
   Mantém `lib.py` sem dependência do ORM do foto-organizer — testável
   isoladamente, sem banco. Ver "Onde plugar" abaixo para o ponto de
   leitura real.
3. **`exigir_esquema_compativel` só bloqueia downgrade, nunca
   "desatualizado".** Rodar a migração já é o comportamento existente do
   app (`upgrade_to_head`); esta checagem existe para o caso que hoje não
   tem tratamento — um catálogo mais novo que o binário atual, ou uma
   `alembic_version` incoerente que indicaria corrupção.
4. **Comparação de revisão é lexicográfica.** Vale enquanto as migrações
   deste projeto usarem numeração com zero à esquerda (`0001`..`0016`,
   confirmado em `fotoorganizer/database/migrations/versions/`). Se o
   esquema de nomenclatura do Alembic mudar para hash, este comparador
   precisa mudar junto — documentado no docstring de `verificar_esquema`
   para não virar bug silencioso.

## Onde plugar quando a fronteira abrir

- **Export**: novo comando/rota (ex.: `scripts/exportar_julgamento.py` ou
  endpoint em `server/app.py`) que faz `select(Evidence)`/`select(Suggestion)`
  reais, monta `LinhaEvidencia`/`LinhaSugestao` a partir das linhas do ORM,
  e chama `exportar_julgamento` + `salvar_export`. Local natural ao lado do
  catálogo: `~/Library/Application Support/FotoOrganizer/julgamento-<data>.json`.
- **Backup**: `fotoorganizer/app/` (entrypoint) ou um worker de background
  (`fotoorganizer/workers/`) chama `deve_rodar_backup` a cada tick do laço
  que já existe (o mesmo que roda `scanner/reconciliacao.py` hoje) e, se
  `True`, chama `executar_backup_com_retencao(db_path, agora, reter=N)` com
  `N` vindo de `config/` (TOML, mesmo padrão do resto das configurações).
- **Checagem de esquema**: `fotoorganizer/database/engine.py` ou
  `migrate.py`, chamado logo após `create_db_engine` e antes de
  `upgrade_to_head` — `exigir_esquema_compativel(engine.raw_connection(),
  REVISAO_ESPERADA)`, com `REVISAO_ESPERADA` sendo a revisão `head` que o
  Alembic do próprio app conhece (`alembic.script.ScriptDirectory` já
  resolve isso sem hardcode; hardcodar "0016" seria a última linha a
  atualizar a cada migração nova, e é exatamente o tipo de coisa que este
  módulo existe para não deixar acontecer em silêncio — a integração real
  deve ler do `ScriptDirectory`, não copiar a constante deste README).

## Limitações declaradas

- Retenção é só por contagem (`reter=N` backups), não por idade
  (`reter últimos 30 dias`). O prompt de origem não pede o segundo modo;
  se aparecer necessidade, é função nova ao lado, não mudança de
  assinatura.
- `deve_rodar_backup` não lida com fuso horário — assume que `agora` e
  `ultimo_backup` vêm do mesmo relógio (consistente com o resto do
  catálogo, que grava `datetime` naive — ver comentário de
  `MediaFile.data_capturada_utc` em `models/catalog.py:172-200`).
