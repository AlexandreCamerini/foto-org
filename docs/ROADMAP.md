# Roadmap — fatias verticais (ágil)

Cada milestone é uma fatia entregável e testável. Definition of done comum:
`pytest` verde, nenhuma violação dos invariantes do CLAUDE.md, app abre e a
fatia é demonstrável de ponta a ponta.

## M0 — Fundação (esqueleto executável)
- Estrutura `fotoorganizer/`, config TOML, logging estruturado.
- SQLite WAL + SQLAlchemy 2 + Alembic com a migração inicial (schema em
  docs/ARQUITETURA.md).
- Janela PySide6 vazia com layout de 3 painéis e tema QSS dark aplicado.
- `docs/PRIVACIDADE.md` e `docs/CONFIANCA.md` iniciais.
- Aceite: `python -m fotoorganizer` abre a janela; migração roda; testes de
  DB e config passam.

## M1 — Catálogo e scanner (núcleo seguro, sem UI nova)
- Portar do legado: descoberta de arquivos (JPEG/PNG/HEIC/HEIF/HIF/TIFF/WebP/
  RAW), extração EXIF (sub-IFD DateTimeOriginal, data RAW via libraw),
  xxhash sempre + SHA-256 sob demanda.
- Varredura incremental (tamanho+mtime+inode), checkpoints, pause/resume,
  fontes (sources) com detecção de volume indisponível, exclusão de pastas,
  symlinks não atravessados, arquivos ocultos ignorados por padrão.
- Erros de leitura registrados sem interromper o scan. Métricas simples
  (arquivos/s, restantes, erros) + mini benchmark de indexação.
- Aceite: CLI interna indexa uma pasta de fixtures sintéticas duas vezes e a
  segunda passada não relê arquivos inalterados; testes de scanner,
  metadados, unicode, arquivo corrompido e interrupção/retomada passam.

## M2 — UI de catálogo (primeira experiência real)
- Painel inicial: fontes, contagens, progresso do scan, erros.
- Grade de miniaturas virtualizada (QListView modo IconMode + lazy load),
  cache de thumbs em disco, geração em background, slider de tamanho.
- Inspetor (painel direito): preview, caminho original, metadados, datas.
- Filtros básicos: data, pasta/fonte, extensão; busca textual; ordenação.
- Aceite: 10k fixtures navegam fluido sem carregar tudo em memória; UI
  responsiva durante scan.

## M3 — Evidências, agrupamento e sugestões
- Motor de evidências estruturadas (tabela `evidence`) + modelo de confiança
  documentado.
- Agrupamento temporal por lacunas/timezone/câmera (portar e evoluir o
  gap de viagem do legado); agrupamento geográfico: GPS → reverse geocoding
  offline; sem GPS → nome de pasta e vizinhança temporal, com confiança baixa.
- Templates de destino (`{categoria}/{ano}/{evento}`…), normalização de nomes,
  colisões, limites de tamanho.
- Tela de revisão: aprovar/rejeitar/editar, lote, desfazer, filtro por
  confiança, justificativas visíveis.
- Aceite: cada sugestão exibe critérios e confiança por evidência; testes de
  templates, normalização e confiança passam.

## M4 — Duplicatas
- 3 níveis (hash exato, mesmo conteúdo, phash) com grupos persistidos.
- UI lado a lado: manter todos, marcar versões, escolher principal, ignorar.
- Aceite: nenhuma ação automática; testes de duplicatas passam.

## M5 — Plano de operações (dry-run e cópia segura)
- Plano: origem, destino, operação, conflitos, espaço necessário, erros
  potenciais. Dry-run obrigatório antes de executar.
- Executor de cópia: verificação de hash antes/depois, sem sobrescrita,
  cancelamento seguro, retomada, disco cheio, volume desconectado, audit log.
- Aceite: teste prova que sobrescrita é impossível; execução interrompida
  retoma sem duplicar nem corromper.

## M6 — Stubs de visão e rostos + privacidade
- `VisionProvider` e `FaceRecognitionProvider` (Protocols) com stub local:
  cadastro de pessoas, fotos de referência, detecção local de rostos,
  associação manual; estrutura para embeddings criptografados.
- Limpeza de cache, remoção completa do catálogo, indicação visual de envio
  externo (ainda sem provider externo real).
- Aceite: recurso desligado por padrão; perfil apagável por completo.

## M7 — Polimento e empacotamento
- Remoção do legado `backend/`+`streamlit_app/` (commit próprio).
- Dados de demonstração sintéticos, README novo, instruções de empacotamento
  (PyInstaller/briefcase), roadmap v2 (providers externos, sidecar XMP,
  reconhecimento automático).
