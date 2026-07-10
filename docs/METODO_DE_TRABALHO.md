# Método de trabalho — engenharia, UX e performance

Guia reutilizável para qualquer aplicação que eu construir. Objetivo: apps
**profissionais, com UX no nível das melhores ferramentas de mercado**,
**arquitetura simples de manter porém poderosa**, e **o mais performáticas
possível** — otimizando custo e velocidade de processamento.
Exemplos usam o foto-organizer, mas os princípios valem para todos os projetos.

## 1. Princípios de execução

- **Resultado antes dos passos.** Entender o desfecho desejado; perguntar só o
  essencial, não travar por ambiguidade secundária.
- **Fatias verticais.** Entregar valor ponta a ponta (dado → lógica → UI) por
  incremento pequeno, sempre com testes verdes antes de avançar.
- **Simples por padrão, poderoso quando necessário.** Nenhuma abstração sem uma
  segunda necessidade concreta. Complexidade só entra pagando o próprio custo.
- **Reversível e auditável.** Operações que alteram estado do usuário existem
  primeiro como plano (dry-run), só executam após confirmação, e ficam em log.
- **Segurança e privacidade não são opcionais.** Nada sensível sai da máquina
  sem opt-in explícito e indicação visual do que será enviado.

## 2. Arquitetura: simples de manter, difícil de quebrar

- **Camadas desacopladas.** UI → serviços/casos de uso → repositórios → dados.
  A UI nunca fala com filesystem/DB direto. Trabalho pesado sempre fora da
  main/UI thread.
- **Fronteiras por `Protocol`/interface.** Componentes plugáveis (extrator,
  provider de visão, geocoder, storage). Trocar implementação sem tocar em quem
  chama. Facilita teste com fakes.
- **Domínio no centro, infraestrutura na borda.** Regras de negócio puras e
  testáveis sem I/O; adaptadores concretos (SQLite, Postgres, HTTP) só nas
  extremidades.
- **Um agregado, um repositório.** Cada repositório dono de uma entidade
  principal; nada de queries espalhadas pela UI.
- **Config declarativa** (TOML/env), sem segredos no código, sem `shell=True`,
  argumentos de subprocesso em lista, caminhos validados.
- **Migrações versionadas** (Alembic) — schema evolui com histórico, nunca
  editado à mão em produção.

## 3. UX no padrão das melhores ferramentas

Referência de qualidade: Linear, Vercel, Raycast, Notion, Arc. Não copiar
estilo; adotar os princípios que fazem essas ferramentas parecerem rápidas e
confiáveis.

- **Percepção de velocidade > velocidade bruta.** Resposta visual em <100 ms:
  optimistic UI, skeletons em vez de spinners, estados de carregamento por
  região (nunca tela inteira travada).
- **Zero jank.** Nada de trabalho pesado na thread de renderização.
  Virtualização de listas/grades grandes (renderizar só o visível). Thumbnails
  e dados carregam sob demanda e em background.
- **Teclado em primeiro lugar.** Command palette (Cmd+K), atalhos para as ações
  frequentes, navegação sem depender do mouse.
- **Hierarquia visual clara.** Tema dark-first, espaçamento consistente via
  tokens, tipografia com escala definida, densidade informacional alta mas
  legível. Um sistema de design (tokens de cor/espaço/tipo), nunca estilo ad-hoc.
- **Feedback honesto.** Estados de vazio, erro e sucesso desenhados. Toda
  sugestão do sistema explica "por quê" (badge de confiança + justificativa).
- **Ações destrutivas com fricção proporcional**: confirmação, desfazer,
  preview do impacto.
- **Acessibilidade real:** contraste AA, foco visível, navegação por teclado,
  respeitar `prefers-reduced-motion`.

## 4. Dados: local-first híbrido (nuvem opcional)

Estratégia padrão: **local-first, nuvem como opt-in**. Preserva privacidade e
latência zero por padrão; escala para sync/backup quando o usuário ligar.

- **Local (padrão):** SQLite em modo **WAL**, com `pragma` de performance
  (`synchronous=NORMAL`, `cache_size` amplo, `mmap_size`, `temp_store=MEMORY`),
  índices nas colunas de filtro/junção, e `ANALYZE`/`VACUUM` periódicos.
  Rápido, sem custo, sem rede. Ideal para dados pessoais/volumosos (ex.: milhares
  de fotos).
- **Nuvem opcional (Railway / Postgres):** opt-in explícito, só para sync entre
  dispositivos, backup ou colaboração. Mesma camada de repositório, outro
  adaptador — o app não sabe qual está ativo.
- **Camada de repositório única** abstrai SQLite e Postgres sob a mesma
  interface: começar local, promover para nuvem sem reescrever o domínio.
- **Só suba à nuvem o necessário.** Metadados/índices podem sincronizar;
  binários pesados (fotos, RAW) ficam locais ou vão para object storage barato,
  não para o Postgres.
- **Quando o Railway compensa:** múltiplos dispositivos, acesso remoto, dado
  compartilhado entre usuários. **Quando não:** app single-user, offline, ou
  dataset grande de binários — aí local ganha em custo e velocidade.

## 5. Performance de processamento

- **Medir antes de otimizar.** Profile real (não palpite) para achar o gargalo;
  otimizar o caminho quente, deixar o resto legível.
- **Paralelizar o pesado.** Pool de workers com limite de CPU configurável;
  I/O-bound → async/threads, CPU-bound → processos. Nunca bloquear a UI.
- **Incremental e retomável.** Trabalho longo (scan, indexação) com checkpoints,
  pause/resume, e "erro em um item nunca derruba o lote" (registrar e seguir).
- **Batch em vez de item-a-item.** Agrupar chamadas caras (subprocessos com
  `-stay_open`, inserts em transação, requests em lote).
- **Barato primeiro, caro sob demanda.** Hash rápido (xxhash) antes do completo
  (SHA-256); thumbnail antes da resolução plena; heurística local antes de
  chamar serviço externo.
- **Cache com invalidação clara.** Disco para thumbnails/derivados, memória para
  hot path. Cache é dado descartável, nunca fonte de verdade.
- **Fazer uma vez.** Idempotência e deduplicação — não reprocessar o que já foi
  processado (comparar por hash/mtime).

## 6. Otimização de custo

- **Local por padrão = custo marginal zero.** Só pagar nuvem pelo que dá retorno
  real (sync, backup, acesso remoto).
- **Serviços externos são opt-in, com cache e rate limit.** Geocoding, visão,
  LLM: cachear resultado localmente para nunca pagar duas vezes pela mesma
  entrada.
- **Certo modelo para a tarefa** (quando houver IA/LLM): tarefa simples →
  modelo barato/rápido; só escalar para o modelo forte quando a confiabilidade
  justificar o custo.
- **Dimensionar a nuvem pelo uso.** Preferir serviços que escalam a zero /
  cobram por uso a instâncias sempre ligadas. No Railway, monitorar consumo e
  desligar o que não precisa rodar 24/7.
- **Binários fora do banco relacional.** Object storage barato para fotos/vídeos;
  Postgres só para metadados. Reduz custo e acelera queries.

## 7. Definition of Done (checklist por fatia)

- [ ] Comportamento coberto por testes; suíte verde (`pytest` ou equivalente).
- [ ] Sem trabalho pesado na thread de UI; estados de loading/erro/vazio prontos.
- [ ] Operações destrutivas têm dry-run + confirmação + log de auditoria.
- [ ] Nada sensível sai da máquina sem opt-in explícito e visível.
- [ ] Caminho quente medido; sem regressão de performance perceptível.
- [ ] Migração de schema versionada; config sem segredos hard-coded.
- [ ] Commit pequeno e convencional (feat/fix/docs/test), em português.
