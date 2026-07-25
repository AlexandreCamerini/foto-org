# Foto Organizer — guia do projeto para o Codex

App desktop macOS, 100% local, para catalogar, analisar e organizar (de forma
assistida e não destrutiva) uma grande coleção pessoal de fotos.

Princípio central: **primeiro catalogar, depois sugerir, então revisar e
somente por último executar operações físicas.**

## Invariantes de segurança (nunca violar)

1. A catalogação é somente leitura. Nenhum arquivo original é movido,
   renomeado, excluído ou tem metadados alterados durante scan/análise.
2. Operações físicas só existem como **plano** (dry-run) até aprovação
   explícita do usuário; a execução é "copiar" por padrão, nunca "mover".
3. Nunca sobrescrever arquivo existente no destino. Verificar hash antes e
   depois de cada cópia. Registrar tudo em audit log.
4. Nenhum dado sai da máquina por padrão. Serviços externos (geocoding,
   visão, etc.) são opt-in explícito, com indicação visual do que será enviado.
5. Subprocessos sempre sem `shell=True`, com argumentos em lista e caminhos
   validados (proteção contra path traversal). Não atravessar symlinks por
   padrão.
6. Reconhecimento facial: desativado por padrão, processamento local,
   embeddings criptografados, resultados sempre como sugestão a confirmar.
7. MVP não implementa exclusão de fotos nem escrita de EXIF (futuro: sidecar
   XMP apenas).

## Stack (decidida — não trocar sem justificar)

- Python 3.12+, SQLite em WAL via SQLAlchemy 2 + Alembic.
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
FaceRecognitionProvider, GeocodingProvider.

## Modelo de evidências e confiança

Cada inferência é uma linha estruturada em `evidence`: origem, campo, valor,
confiança (enum: alta/média/baixa + score), justificativa legível, versão da
lógica. A confiança final de uma sugestão preserva as evidências individuais
(não somar números arbitrariamente — regra documentada em docs/CONFIANCA.md).
Toda sugestão deve conseguir responder "por quê?" (ex.: "país inferido do GPS
EXIF, confiança alta; cidade veio do nome da pasta, confiança média").

## Método de trabalho

- Trabalhe em fatias verticais pelo docs/ROADMAP.md (M0→M7). Não avance de
  milestone com testes quebrados.
- Rode `pytest` após cada etapa. Erros de leitura de arquivo nunca derrubam
  a varredura: registrar e continuar.
- UI segue docs/DIRECAO_DE_ARTE.md (dark-first, 3 painéis, badges de
  confiança). Não inventar estilo ad-hoc.
- O protótipo v1 (`backend/`, `streamlit_app/`) já foi portado e removido.
  Sobrou `database/fotos.db` (schema v1, tabela única `photos`): dado do
  usuário, não versionar, não apagar sem pedir. O catálogo atual vive em
  `~/Library/Application Support/FotoOrganizer/catalog.db`.
- A UI PySide6 (`fotoorganizer/ui/`, `fotoorganizer/workers/`) é fallback
  até o webapp ter paridade (falta a tela de Operações); sai em commit
  próprio, não aos pedaços.
- Commits pequenos com mensagens convencionais (feat/fix/docs/test), em
  português como o histórico existente.

## Imported Claude Cowork project instructions
