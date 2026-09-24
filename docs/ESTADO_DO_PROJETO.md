# Estado do projeto — checkpoint para retomada após hold

Gerado em 2026-09-24, ao pausar o projeto. HEAD: `80f1427` (D-097 + addendum),
2 commits à frente de `origin/main` (D-097 e o addendum ainda não foram
enviados). Working tree limpo, exceto os três arquivos que nunca são
commitados (`.claude/launch.json`, `AGENTS.md`,
`webapp/tsconfig.app.tsbuildinfo`).

Este documento é o ponto de retomada: o que o app já faz, o que falta
construir, o que precisa de correção, e o que está pendurado agora mesmo
(plano 3 de escrita EXIF, interrompido). Não decide prioridade — isso é
call do dono na volta.

## 1. Operação em andamento — plano 3 de escrita EXIF (interrompido)

- **Status no banco**: `INTERROMPIDA`, `executavel = true`. Servidor
  parado deliberadamente (não caiu).
- **Progresso real**: de 9.843 itens prontos originais, ~1.941 foram
  processados antes da primeira interrupção; ~1.579 gravados com sucesso,
  329 reprovaram por um alarme falso (D-097) já corrigido no código.
- **Pendência para retomar**: a correção do D-097 (allowlist do aviso
  IPTCDigest) e do addendum (limpar `item.erro` velho) estão no código e
  testadas, mas **ainda não foram aplicadas ao catálogo real** — a
  terceira rodada de `dry_run(3)` que aplicaria isso foi interrompida
  junto com o servidor. `com_erro` no banco ainda mostra 329 (deveria
  cair para ~15, os que de fato têm valor inválido).
- **Para retomar**: religar o servidor (`scripts/executar.sh web` ou
  `preview_start`), rodar `POST /api/exif/3/dry-run` de novo (síncrono,
  pode levar 20-45 min pelo achado do item 3 abaixo) e só depois
  `POST /api/exif/3/executar`.
- **Achado novo, sem correção ainda, registrado aqui pela primeira vez**:
  `verificacao.dump_lote()` usa lote fixo de 200 arquivos com timeout fixo
  de 30s (`_TIMEOUT_S`). Numa leitura real contra `/Volumes/photo` (SMB),
  todo lote bateu no teto de 30s de forma sistemática — não é lentidão
  pontual (uma leitura isolada do mesmo compartilhamento levou 2s). Efeito:
  `dry_run()` fica bem mais lento que os ~32 min históricos e pode inflar
  a contagem de "prontos" para itens cujo lote falhou (tratados como
  "campo vazio" quando na verdade não foram lidos). Sem risco de gravação
  errada — a escrita real reconfere cada arquivo individualmente, com
  timeout de 30s por arquivo (bem dentro da folga), e tem guarda própria
  para leitura vazia (D-095). Vale calibrar `tamanho_lote`/`_TIMEOUT_S`
  para esse compartilhamento antes da próxima rodada grande.
- **~314 arquivos `_original` órfãos**: os 314 itens que reprovaram por
  D-097 e já foram corrigidos têm backup `_original` ainda no disco, sem
  rota de limpeza automática (eles não voltam a entrar no branch que
  apaga backup, porque não têm mais nada `PRONTO` a escrever). Seguro
  (invariante 8), só acumula arquivo na árvore que o scanner trata como
  somente-leitura.
- **3 propostas GenAI de classificação de pasta** seguem pendentes de
  aprovação ou descarte (Peru→Chile, Nazaré da Mata 2023, seguro de
  equipamentos) — de uma sessão paga anterior.

## 2. Inventário funcional — o que o app já faz

Fonte: `docs/reconstrucao/02-FUNCIONALIDADES.md` (62 rotas, 25 tabelas,
20 migrações, 21 componentes React, 12 subcomandos CLI), conferido contra
o que mudou depois desse mapa (D-082 a D-097).

| Área | Pronto | Parcial | Stub |
|---|---|---|---|
| Catalogação / scan | Scan incremental, retomada de scan interrompido, marcação de sumiço, disponibilidade de fonte, benchmark de indexação, inventário do acervo | Pausa/cancelamento só existe para scan (não para importação/execução/escrita EXIF); reconciliação de alcance sem consumidor na UI | — |
| Importação externa | Apple Fotos, Google Takeout (local) | Lightroom `.lrcat` só via CLI, sem UI/API | — |
| Metadados / thumbnails | Extração EXIF/RAW/CR3, sidecar XMP, thumbnail em cache, preview do loupe, detecção e confirmação de tipo de imagem | Instante absoluto por offset só no caminho exiftool; nota/rótulo/`crs:` lidos e não usados | — |
| Sugestões de localização/classificação | Evidência de data e lugar, herança de GPS entre fontes, correção de deriva de relógio, cascata de sessão determinística, montagem de destino e confiança, geocodificação offline, correção manual de local no Inspector (D-091) | Sugestão aprovada fica congelada, sem reabertura automática; revisão por grupo sem superfície de erro | — |
| Agrupamento temporal/geográfico | Sessões, transição casa↔fora, viagem multi-país por pernas, subdivisão em acontecimentos, cards de viagem/evento | Recorte por pasta não é respeitado pela régua de tempo | — |
| Duplicatas | Exatas por hash, decisão do usuário por grupo, rajadas, variante RAW+JPEG | Phash da miniatura ≠ original em foto rotacionada (falta `exif_transpose`) | — |
| Operações físicas (cópia) | Plano, dry-run, execução com hash antes/depois, inventário por pasta, auditoria | Falha pós-verificação deixa destino órfão sem retomada (M3, aberto) | — |
| Escrita EXIF de localização | Plano, dry-run, seleção de itens, execução por diff de tags, sidecar XMP, timeout com SIGINT/SIGKILL, reconciliação de plano órfão no boot (D-095), cancelamento testado ponta a ponta | Sem comando de restaurar backup `_original` via app | — |
| GenAI de pasta | Advisor de cluster, classificação de pasta (nome curto, nunca caminho absoluto — D-094), léxico de nomes | Confiança fixa em "média" na UI; mensagem de erro duplicada | Reconhecimento facial e análise visual — só `Protocol` e provider nulo |
| UI web | Grade virtualizada, painéis recolhíveis, panorama de lacunas, inventário por pasta, funil do acervo, cards de viagem, mapa do lugar, loupe, inspetor com evidências | Filtros de câmera/país/cidade/palavra-chave existem no contrato e não têm controle na UI; tela de Configurações só grava template e opt-in de GenAI | — |
| Infra/servidor | Bind só em 127.0.0.1, guard de origem, SSE de progresso, config em camadas com gates de privacidade | Empacotamento Tauri assinado/notarizado é Marco 2 futuro, não exercitado | — |

## 3. Backlog de funcionalidades novas (nada disto é bug)

| # | Item | Esforço | Fonte |
|---|---|---|---|
| 1 | Sidebar navegável (busca incremental + teclado) | — | `09-MELHORIAS.md` §1 |
| 2 | Picker de pasta nativo (Tauri) + progresso de importação (taxa/ETA) | — | `09-MELHORIAS.md` §1 |
| 3 | Confiança como eixo de navegação + saúde do acervo por dimensão | — | `09-MELHORIAS.md` §1 |
| 4 | Motor de corroboração generalizado (padrão D-074 para data/cidade/país) | maior risco — toca herança de GPS calibrada em 40.678 fotos | `09-MELHORIAS.md` §1 |
| 5 | Modo ativo de aprendizado (perguntar o que mais reduz incerteza) | deferido até 3 e 4 existirem | `09-MELHORIAS.md` §1 |
| 6 | Reconectar volumes desmontados/só-iCloud (~90 mil registros) | S | `ROADMAP.md`, `09-MELHORIAS.md` §1 |
| 7 | Detecção facial local (ONNX) | L, CPU alta | `ROADMAP.md` |
| 8 | Análise visual local (`VisionProvider`) | M/L, rebaixada (só 18 fotos têm pixel local pré-2019) | `ROADMAP.md` |
| 9 | UI de pessoas (perfis, revisão de rostos) | S/M, bloqueada pelo item 7 | `ROADMAP.md` |
| 10 | Sidecar XMP para todos os metadados aprovados (não só localização) | M, bloqueada por acesso a ~90 mil registros | `ROADMAP.md` |
| 11 | Empacotamento assinado/notarizado (Marco 2) | M, US$ 99/ano recorrente | `ROADMAP.md` |
| 12 | Provider externo opt-in (geocoding/visão por API) | L, custo por foto sem teto conhecido | `ROADMAP.md` |
| 13 | Linha do tempo por fonte (protótipo `04-linha-do-tempo.html`) | — | `09-MELHORIAS.md` §6 |
| 14 | Plano antes-e-depois (protótipo `05-plano-antes-depois.html`) | — | `09-MELHORIAS.md` §6 |
| 15 | Rejeitar sugestões em lote (hoje só existe aprovar em lote) | — | `09-MELHORIAS.md` §6, D-069 Tier 2 |
| 16 | Badge de confiança clicável leva à evidência que a puxou pra baixo | — | `09-MELHORIAS.md` §6 |
| 17 | Fila de jobs (em vez de "um por vez") | pré-condição (lock, A1) já satisfeita desde D-090 | `09-MELHORIAS.md` §8 |
| 18 | Série temporal de métricas de desempenho (detectar regressão) | — | `09-MELHORIAS.md` §8 |
| 19 | Balde "sem data" na grade (~1.129 fotos sem `data_capturada`) | — | `09-MELHORIAS.md` §8 |
| 20 | Reabertura de sugestão aprovada (hoje fica congelada para sempre) | — | `02-FUNCIONALIDADES.md` lacuna 1 |
| 21 | Tela de Configurações completa (tema, workers, cache, revogar consentimento) | — | `02-FUNCIONALIDADES.md` lacuna 2 |

Divergência sem resolver: itens 4-5 (corroboração generalizada) descrevem
um padrão que D-082 a D-088 já aplicaram várias vezes de forma pontual
(país por nome de pasta, janela de herança de GPS, desempate de doadora)
sem que nenhum commit se declare como "isto implementa o item 4". Não dá
para saber pelos documentos se o item já está parcialmente feito ou se o
trabalho recente é paralelo e distinto.

## 4. Correções e dívida técnica pendentes

Cruzamento entre a auditoria de 2026-09-19 (`08-ERROS_CONHECIDOS.md`) e os
18 commits desta sessão (D-082 a D-097 + addendum). **Já corrigido** não
precisa de ação; só a lista aberta importa para a retomada.

### Já corrigido nesta sessão (não precisa reabrir)

A1 (corrida no JobManager), A2 (hemisfério errado em GPS), M1/M5 (duas
bases de tempo), M2 (caminho absoluto pro Anthropic), M6 (CI ausente),
M8 (cancelamento sem teste), B3 (`_exec_control` órfão), B13 (timeout do
writer EXIF), e a allowlist de aviso IPTCDigest (D-097 + addendum, achado
nesta própria sessão ao retomar o plano 3).

### Aberto — alto

| Item | Descrição |
|---|---|
| A3 | Ramo de hash divergente em `operations/executor.py:211-213` sem teste que force a divergência |
| A4 | TOCTOU no alvo direto de escrita EXIF sem teste que grave por fora entre `dry_run()` e `executar()` |

### Aberto — médio

| Item | Descrição |
|---|---|
| M3 | Falha pós-verificação em `operations/executor.py` deixa destino órfão sem retomada. D-095 resolveu o equivalente para escrita EXIF; cópia física continua com o mesmo buraco, decisão separada já registrada em D-095. |
| M4 | `duplicates/phash.py` sem `exif_transpose` — phash da miniatura diverge do original em foto rotacionada |
| M7 | `src-tauri/Entitlements.plist` — `allow-unsigned-executable-memory=true` contradiz o próprio comentário |
| — | `verificacao.dump_lote()` com lote/timeout fixos (200 arquivos / 30s) mal calibrados para SMB lento — achado novo desta sessão, seção 1 acima |

### Aberto — baixo

B1 (guard de Origin sem porta), B2 (sem CSP), B4 (`except Exception`
engole erro de flush no scanner), B5 (`KeychainKeyStore` sem teste/
consumidor), B6 (ENOSPC sem teste), B7 (testes sem assert), B8 (2 rotas
sem consumidor), B9 (12 `select()` diretos fora de repository em
`app.py`), B10 (docs desatualizados: `ROADMAP.md:252,126,300`,
`DECISOES.md:2788`, `REQUIREMENTS.md`, `.planning/codebase/*`), B11
(Lightroom sem entrada no tipo de fonte da UI), B12 (limite de 500 em
`GET /api/sugestoes` sem "mostrar mais"), B14 (origens de confiança sem
produtor: `gps`, `geocoding_externo`, `visao`, `agrupamento`), B15
(`docs/EVENTOS.md` diz 17 cenários; o script real tem 27 desde D-082 —
distância cresceu, não diminuiu).

### Achados "verificar" da auditoria pós-Fase-5 (D-069), nenhum tocado

Confiança agregada contradiz evidência no popover; categoria "Eventos"
por heurística fraca; ação de duplicata falha em silêncio; inventário por
pasta O(n²); destino sem prefixo de categoria; viagem fragmentada em
grafias diferentes; cards "Brasil" genéricos; rótulo da sidebar ≠ total
do filtro; painel "O acervo" sem loading state; sem timestamp da última
detecção de duplicata; grupos de duplicata não explicam por que foram
agrupados.

### Dívida estrutural sem correção

Motor de sugestões e detector de duplicatas fazem full-scan em memória
sem caminho incremental (D-092 melhorou só a persistência, ~4x, não
criou incremental); `_completar_sha256` serial sem `ThreadPoolExecutor`;
`security/http_seguro.py` sem consumidor (SSRF/DNS rebinding adiados);
`PhotoGrid.tsx`/`ClaudeAdvisor` sem teste dedicado; score de `llm_pasta`
(D-081, 0,55) precisa remedição com o payload de nome curto do D-094,
registrado no próprio commit e nunca feito.

## 5. Pra quando voltar

1. Religar o servidor, rodar `dry_run(3)` de novo (aplica a correção do
   addendum aos 329 itens) e então `executar(3)` para os itens restantes.
2. Decidir as 3 propostas GenAI pendentes.
3. Calibrar `dump_lote()` para o compartilhamento SMB antes de qualquer
   próxima operação grande sobre `/Volumes/photo`.
4. Escolher entre seguir o backlog de funcionalidades (seção 3) ou fechar
   a dívida técnica aberta (seção 4) — nenhuma das duas foi priorizada
   aqui, é decisão do dono.
