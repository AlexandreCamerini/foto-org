# Foto Organizer — guia do projeto para o Claude Code

App desktop macOS, local-first, para catalogar, analisar e organizar (de forma
assistida e não destrutiva) uma grande coleção pessoal de fotos. O núcleo
funciona integralmente offline; recursos de nuvem são opcionais e nunca são
pré-requisito para catalogar, revisar ou executar operações.

Princípio central: **primeiro catalogar, depois sugerir, então revisar e
somente por último executar operações físicas.**

## Invariantes de segurança (nunca violar)

1. A catalogação é somente leitura. Nenhum arquivo original é movido,
   renomeado, excluído ou tem metadados alterados durante scan/análise.
2. Operações físicas só existem como **plano** (dry-run) até aprovação
   explícita do usuário; a execução é "copiar" por padrão, nunca "mover".
3. Nunca sobrescrever arquivo existente no destino. Verificar hash antes e
   depois de cada cópia. Registrar tudo em audit log.
4. Nenhum dado sai da máquina por padrão. Serviços externos e sincronização
   são opt-in explícito, desligados inicialmente e com indicação visual prévia
   de quais dados serão enviados, finalidade, destino e forma de revogação.
   Aplicar minimização de dados, criptografia em trânsito e nunca sincronizar
   fotos/RAW ou embeddings faciais sem consentimento específico e separado.
5. Subprocessos sempre sem `shell=True`, com argumentos em lista e caminhos
   validados (proteção contra path traversal). Não atravessar symlinks por
   padrão.
6. Reconhecimento facial: desativado por padrão, processamento local,
   embeddings criptografados, resultados sempre como sugestão a confirmar.
7. MVP não implementa exclusão de fotos nem escrita de EXIF (futuro: sidecar
   XMP apenas).
8. Nada que possa ser a referência real de uma foto é apagado — nem do disco,
   nem do catálogo. Registro que não serve como acervo pode ser **rebaixado a
   fonte de sinal** (sai da grade, da revisão e do plano, continua doando data,
   GPS e correlação), nunca removido. Uma miniatura interna, um derivado ou uma
   referência de catálogo externo costuma ser a única testemunha do lugar e da
   hora de uma foto que não tem GPS próprio: apagá-la destrói informação que
   não se recupera. Medido em 2026-07-31 — apagar as 45.822 miniaturas do
   Apple Fotos levaria as fotos reais com lugar estimado de 2.117 para 162.
   Ver D-024 em `docs/DECISOES.md`.

## Stack (decidida — não trocar sem justificar)

- Python 3.12+, SQLite em WAL via SQLAlchemy 2 + Alembic.
- SQLite continua sendo a fonte local de verdade e o modo padrão. Railway/
  Postgres pode ser adicionado como adaptador opcional para sincronização,
  backup de metadados ou colaboração — nunca como dependência do fluxo local.
  Binários ficam locais ou em object storage próprio; não vão para o Postgres.
- **UI: web local** (decisão de 2026-07-24, a pedido do dono do produto) —
  FastAPI servindo apenas 127.0.0.1 (`fotoorganizer/server/`) + React/
  Vite/TypeScript/Tailwind (`webapp/`), grade virtualizada, teclado-first.
  A UI PySide6 (`fotoorganizer/ui/`) permanece como fallback até paridade
  e será removida em commit próprio. Streamlit foi avaliado e rejeitado
  (era a stack da v1: sem grade virtualizada, sem teclado, re-render por
  interação). Empacotamento Tauri é milestone futuro.
- Metadados: exiftool via subprocesso em batch (`-stay_open`) quando
  instalado; fallback puro-Python (Pillow + exifread + pillow-heif + rawpy).
- Hashing: xxhash (rápido, sempre) + SHA-256 (completo, sob demanda).
  Duplicata visual: `imagehash.phash`.
- Geocodificação reversa: dataset offline local (ex.: `reverse_geocoder`);
  serviço externo somente opt-in, com cache local e rate limit.
- Thumbnails: cache em disco (`~/Library/Caches/FotoOrganizer/thumbs`),
  geração em background (QThreadPool), nunca carregar resolução completa
  para a grade.
- Testes: pytest com fixtures sintéticas (nunca fotos pessoais reais no repo).
- Config local em TOML; logging estruturado sem conteúdo sensível.

## Arquitetura

Camadas desacopladas — UI nunca chama filesystem/DB direto; passa por
serviços. Trabalho pesado sempre fora da main thread.

```
fotoorganizer/
  app/            entrypoint, injeção de dependências, config
  ui/             PySide6 (views, viewmodels, widgets, tema QSS)
  database/       engine, migrações Alembic
  models/         ORM + dataclasses de domínio
  repositories/   acesso a dados (uma classe por agregado)
  sync/           sincronização opcional, incremental e revogável
  scanner/        descoberta incremental de arquivos, checkpoints, pause/resume
  metadata/       extratores (ExifToolExtractor | PurePythonExtractor)
  thumbnails/     geração + cache
  classification/ motor de evidências e sugestões (versão da lógica gravada)
  grouping/       agrupamento temporal (sessões/viagens) e geográfico
  geolocation/    reverse geocoding offline + provider externo opt-in
  faces/          FaceRecognitionProvider (stub no MVP)
  vision/         VisionProvider (stub no MVP)
  duplicates/     3 níveis: hash exato, mesmo conteúdo, similaridade visual
  operations/     planos, dry-run, executor de cópia com verificação
  security/       validação de caminhos, subprocesso seguro, audit log
  workers/        fila de background, limites de CPU/workers
  config/         settings TOML + defaults
tests/            espelha os módulos; fixtures geradas em runtime
docs/             ARQUITETURA, ROADMAP, DIRECAO_DE_ARTE, PRIVACIDADE, CONFIANCA
```

Componentes substituíveis (`Protocol`): MetadataExtractor, VisionProvider,
FaceRecognitionProvider, GeocodingProvider e SyncProvider. O adaptador de
nuvem deve ficar na infraestrutura; domínio e UI não dependem do Railway.

## Modelo de evidências e confiança

Cada inferência é uma linha estruturada em `evidence`: origem, campo, valor,
confiança (enum: alta/média/baixa + score), justificativa legível, versão da
lógica. A confiança final de uma sugestão preserva as evidências individuais
(não somar números arbitrariamente — regra documentada em docs/CONFIANCA.md).
Toda sugestão deve conseguir responder "por quê?" (ex.: "país inferido do GPS
EXIF, confiança alta; cidade veio do nome da pasta, confiança média").

## Método de trabalho

- Siga `docs/METODO_DE_TRABALHO.md` para decisões gerais de arquitetura, UX,
  performance e custo; este arquivo prevalece nas regras específicas e nos
  invariantes de segurança do Foto Organizer.
- Trabalhe em fatias verticais pelo docs/ROADMAP.md (M0→M7). Não avance de
  milestone com testes quebrados.
- Rode `pytest` após cada etapa. Erros de leitura de arquivo nunca derrubam
  a varredura: registrar e continuar.
- UI segue docs/DIRECAO_DE_ARTE.md (dark-first, 3 painéis, badges de
  confiança). Não inventar estilo ad-hoc.
- Validar UX no fluxo real, não só por build: estados de loading, vazio, erro,
  progresso, cancelamento e retomada; navegação por teclado; foco visível;
  grade virtualizada; feedback imediato sem bloquear a interface.
- Tratar performance como requisito mensurável. Antes de otimizar, registrar
  baseline com catálogo representativo; depois comparar tempo, memória e
  responsividade. Processar incrementalmente, em batch e com workers limitados;
  evitar N+1, reprocessamento e carregamento de imagens em resolução completa.
- Escolher infraestrutura pelo menor custo total que atenda ao caso real:
  SQLite local primeiro; Railway somente quando sync, backup remoto ou
  colaboração justificarem latência, operação e custo recorrente. Toda adoção
  de nuvem exige estimativa simples de custo, volume e estratégia de saída.
- O protótipo v1 (`backend/`, `streamlit_app/`, `database/fotos.db`) foi
  portado e removido por inteiro. O catálogo vive em
  `~/Library/Application Support/FotoOrganizer/catalog.db` e é o único.
- A UI PySide6 (`fotoorganizer/ui/`, `fotoorganizer/workers/`) é fallback e
  está pronta para sair: o webapp tem paridade de telas (incluindo
  Operações) e cobertura própria (vitest, `webapp/src/**/*.test.tsx`,
  no `scripts/verificar.sh`). A remoção sai em commit próprio, não aos
  pedaços, e leva junto `tests/test_ui_smoke.py`.
- Commits pequenos com mensagens convencionais (feat/fix/docs/test), em
  português como o histórico existente.
