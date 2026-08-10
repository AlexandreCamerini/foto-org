# Resumo de instruções — Foto Organizer

Consolidação das regras de trabalho (preferências pessoais globais) e das regras
do projeto. Serve como referência rápida; as fontes completas são o CLAUDE.md
global e o CLAUDE.md do projeto.

## Como trabalhar comigo (preferências gerais)

- **Chat vs. tarefa:** pedidos curtos (dúvida, explicação, brainstorm) são chat
  comum — não abrir fluxo multi-etapa à toa. Entregáveis (arquivo, pasta
  organizada, planilha, pesquisa, documento) são tarefa completa de Cowork.
- **Foco no resultado final**, não só nos passos descritos. Perguntar só o
  essencial; não travar por ambiguidades secundárias.
- **Reusar contexto** de projetos anteriores (BolsIA, TIA, ITQC, FQA) antes de
  perguntar algo já respondido. **Não misturar premissas** entre projetos.
- **Agrupar** tarefas relacionadas em uma sessão só.
- **Nunca deletar** arquivo permanentemente sem confirmação explícita.
  "Organizar" ou "limpar" nunca inclui apagar por conta própria.
- **Não tocar** em arquivos financeiros, senhas ou dados sensíveis, a menos que
  apontados explicitamente na tarefa.
- **Baixo risco** (organização, rascunhos, resumos): entregar e eu reviso.
  **Alto risco** (afeta terceiros, envia mensagem, ação financeira, exclusão de
  dados): avisar antes da etapa crítica e aguardar confirmação.

### Seleção de modelo (quando não especificado, escolher e justificar em 1 linha)

- **Sonnet 5** — padrão do dia a dia: coding, análise de documentos, conhecimento geral.
- **Opus 4.8** — arquitetura complexa, decisões de alto risco, coding agêntico pesado.
- **Haiku 4.5** — rotina, classificação, resumos rápidos, sensível a custo/velocidade.
- **Fable 5** — o problema mais difícil do momento ou agentes de execução longa.

## Projeto Foto Organizer (essência)

App desktop macOS, 100% local, para catalogar, analisar e organizar (assistido e
não destrutivo) uma grande coleção pessoal de fotos.
**Princípio central:** primeiro catalogar → sugerir → revisar → só por último
executar operações físicas.

### Invariantes de segurança (nunca violar)

1. Catalogação é **somente leitura** — nada é movido, renomeado, excluído ou tem
   metadados alterados durante scan/análise.
2. Operações físicas só existem como **plano (dry-run)** até aprovação explícita;
   execução padrão é **copiar**, nunca mover.
3. **Nunca sobrescrever** destino. Verificar hash antes e depois de cada cópia.
   Registrar tudo em audit log.
4. **Nada sai da máquina** por padrão. Serviços externos (geocoding, visão) são
   opt-in explícito, com indicação visual do que será enviado.
5. Subprocessos sempre **sem `shell=True`**, argumentos em lista, caminhos
   validados (anti path traversal). Não atravessar symlinks por padrão.
6. Reconhecimento facial **desativado por padrão**, local, embeddings
   criptografados, resultados sempre como sugestão a confirmar.
7. MVP **não** exclui fotos nem escreve EXIF (futuro: só sidecar XMP).

### Stack (decidida — não trocar sem justificar)

Python 3.12+, SQLite (WAL) via SQLAlchemy 2 + Alembic. UI web local
(FastAPI + React/Vite/TS/Tailwind), única interface — a UI PySide6 foi
removida por inteiro. Metadados por
exiftool em batch (`-stay_open`) com fallback puro-Python (Pillow + exifread +
pillow-heif + rawpy). Hashing xxhash + SHA-256 sob demanda; duplicata visual
`imagehash.phash`. Geocoding reverso offline (opt-in externo com cache/rate
limit). Thumbnails em cache de disco, geração em background. Testes com pytest e
fixtures sintéticas. Config em TOML, logging sem conteúdo sensível.

### Arquitetura

Camadas desacopladas — a UI nunca chama filesystem/DB direto, passa por serviços;
trabalho pesado sempre fora da main thread. Módulos-chave: `scanner`, `metadata`,
`thumbnails`, `classification`, `grouping`, `geolocation`, `duplicates`,
`operations`, `security`, `workers`. Componentes substituíveis via `Protocol`
(MetadataExtractor, VisionProvider, FaceRecognitionProvider, GeocodingProvider).

### Evidências e confiança

Cada inferência é uma linha em `evidence` (origem, campo, valor, confiança
alta/média/baixa + score, justificativa legível, versão da lógica). Toda sugestão
deve responder "por quê?". Não somar scores arbitrariamente (regra em
docs/CONFIANCA.md).

### Método de trabalho

Fatias verticais pelo docs/ROADMAP.md (M0→M7); não avançar de milestone com
testes quebrados. Rodar `pytest` a cada etapa; erro de leitura de arquivo nunca
derruba a varredura (registrar e continuar). UI segue docs/DIRECAO_DE_ARTE.md
(dark-first, 3 painéis, badges de confiança). O protótipo v1 (`backend/`,
`streamlit_app/`, `database/fotos.db`) foi portado e removido; o catálogo é o
de `~/Library/Application Support/FotoOrganizer/catalog.db`. Commits pequenos,
convencionais (feat/fix/docs/test), em português.
