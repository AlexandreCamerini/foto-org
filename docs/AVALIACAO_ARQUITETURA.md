# Avaliação de arquitetura — fase 1

Executada em 2026-07-29 sobre a branch `claude/digital-assets-architecture-f81e18`.
Método e regras em `docs/prompts/00-protocolo.md`. Decisões desta fase em
`docs/DECISOES.md` (D-006 a D-009).

**Resumo em uma frase:** o desenho em camadas está real e disciplinado — as
violações são localizadas e nominais, não estruturais — mas o esquema do banco
está modelado para *catalogar e sugerir*, não para *gerir assets*, e é aí que
o produto comercial encontra a parede, não na organização do código.

---

## 1. Requisitos

Alvos assumidos para um produto comercial de acervo pessoal grande. Nenhum
deles está medido hoje; a coluna "verificado" diz o que a fase 1 conseguiu
confirmar.

| Dimensão | Alvo | Verificado |
|---|---|---|
| Volume | 500 mil arquivos, 8 TB, catálogo único | não — maior medição documentada é de 300 arquivos (`docs/COBERTURA_METADADOS.md`) |
| Dispositivos | 5 a 10 fontes distintas | parcial — `sources` suporta; correlação entre fontes existe |
| Latência de UI | grade e filtros < 100 ms com catálogo cheio | não |
| Scan | incremental, retomável | sim — `scanner/scanner.py:192,239` |
| Concorrência | scan, thumbs e navegação simultâneos | não — um trabalho por vez, por desenho |
| Privacidade | núcleo offline, nuvem opt-in | sim, estruturalmente |
| Distribuição | app assinado, instalado por não-programador | não — `docs/EMPACOTAMENTO.md` é plano, não entrega |

---

## 2. Estado atual

### 2.1 Camadas reais

```
   ┌────────────────────────────┐   ┌──────────────────────────┐
   │ webapp/ (React/TS)         │   │ fotoorganizer/ui/        │
   │ 2.574 LOC                  │   │ PySide6 — 1.928 LOC      │
   └─────────────┬──────────────┘   └────────────┬─────────────┘
                 │ HTTP/SSE                      │ ViewModels
   ┌─────────────▼──────────────┐   ┌────────────▼─────────────┐
   │ server/app.py + jobs.py    │   │ workers/ — 207 LOC       │
   │ 814 LOC                    │   │ (QThreadPool)            │
   └─────────────┬──────────────┘   └────────────┬─────────────┘
                 │        ┌──────────────────────┘
   ┌─────────────▼────────▼─────┐
   │ repositories/ — 806 LOC    │◄── 4 de 5 repositórios usados por app.py
   │ Media Suggestion Duplicate │    ⚠ 4 consultas escapam direto ao ORM
   │ Operation People           │
   └─────────────┬──────────────┘
   ┌─────────────▼──────────────────────────────────────────────┐
   │ domínio: classification 1019 · grouping 718 · geolocation  │
   │ 528 · scanner 460 · operations 391 · duplicates 312         │
   │ metadata 277 · security 181 · thumbnails 117               │
   │ vision 61 · faces 72   ← stubs                            │
   └─────────────┬──────────────────────────────────────────────┘
   ┌─────────────▼──────────────┐
   │ models/ 579 · database/ 526 │  SQLite WAL, 21 tabelas, 4 migrações
   └────────────────────────────┘
```

O desenho prometido em `docs/ARQUITETURA.md:17` — "os handlers nunca tocam
filesystem/DB direto" — é **majoritariamente cumprido**: `server/app.py` usa
quatro repositórios. As exceções são quatro consultas e algumas construções de
`Path`, listadas abaixo. Isso não é decadência arquitetural; é método de
repositório faltando.

### 2.2 Violações de camada, nominais

| Local | O que faz | Diagnóstico |
|---|---|---|
| `server/app.py:226` | `select(Suggestion).where(media_id == …)` | falta `SuggestionRepository.por_media()` |
| `server/app.py:281` | `select(MediaFile)` | falta método de listagem no `MediaRepository` |
| `server/app.py:292-296` | `select(modelo)` + `COUNT` por grupo | falta agregação no repositório — e é N+1, ver 4.1 |
| `server/app.py:254,270` | `Path(media.caminho)` para thumb e preview | aceitável: o caminho vem do catálogo, não do usuário |
| `server/app.py:436,508,522` | `Path(body.…).expanduser()` de corpo de requisição | ver 2.5 |

Custo de correção: baixo. São quatro métodos de repositório.

### 2.3 Os `Protocol` substituíveis — a hipótese não testada

`CLAUDE.md` declara cinco componentes substituíveis. A varredura encontrou
sete protocolos, e a lista não coincide:

| Protocolo | Declarado no CLAUDE.md | Existe | Implementações |
|---|:---:|:---:|---|
| `MetadataExtractor` | sim | sim | **1** — `PurePythonExtractor` |
| `GeocodingProvider` | sim | sim | **1** — `offline.py` |
| `VisionProvider` | sim | sim | **1** — `stub.py` |
| `FaceRecognitionProvider` | sim | sim | **1** — `stub.py` |
| `SyncProvider` | sim | **não** | zero ocorrências no código |
| `ExternalCatalogProvider` | não | sim | **2** — Apple Fotos, Google Takeout |
| `ClassificationAdvisor` | não | sim | 1 |

Dois achados aqui:

**`SyncProvider` não existe.** É o único ponto de extensão que o `CLAUDE.md`
promete para o adaptador de nuvem — "o adaptador de nuvem deve ficar na
infraestrutura; domínio e UI não dependem do Railway". A fronteira que
sustentaria essa promessa não foi escrita. Não é urgente (não há sync), mas a
promessa arquitetural está descoberta.

**O único protocolo com duas implementações reais é o que não está
documentado.** `ExternalCatalogProvider` tem Apple Fotos e Google Takeout, e é
o único que provou que a abstração funciona. Os quatro declarados têm uma
implementação cada — dois deles são stubs. Uma abstração com um implementador
é uma hipótese sobre a forma da fronteira; a fase 3 (exiftool como segundo
`MetadataExtractor`) é o primeiro teste real dessa hipótese, e vale tratá-la
como teste, não como formalidade.

### 2.4 Trabalho em background

`server/jobs.py:39-56`: `JobManager` com uma thread, um `threading.Lock`, e
`_estado` como `dict` em memória. Um trabalho por vez, por decisão explícita
("a mesma disciplina da UI nativa").

Consequências, todas verificadas por leitura:

- reiniciar o processo perde o estado do trabalho; o `checkpoint` no banco
  (`scan_sessions.checkpoint`, `scanner.py:251`) permite retomar o *scan*, mas
  a UI não sabe que havia um trabalho;
- um scan de 500 mil arquivos bloqueia importação, sugestões e duplicatas pelo
  tempo inteiro — não há fila, há recusa (`HTTP 409`, `app.py:511`);
- não há métrica exportada além do `dict` de progresso: nada de duração
  histórica, taxa, nem regressão detectável entre versões.

O controle de cancelamento é cuidadoso e merece registro: a execução de plano
tem `ExecutionControl` próprio porque parar uma cópia exige remover o parcial,
enquanto os demais usam o `ScanControl` cooperativo. Essa distinção está certa.

### 2.5 Segurança de caminho — melhor do que parece, com uma lacuna

`security/paths.py` oferece `caminho_relativo_seguro`, `resolver_destino` e
`destino_recursivo`, com `CaminhoInvalido`. É usado no fluxo de operações — o
caminho por onde arquivos são escritos. Correto.

Os endpoints que recebem caminho do usuário (`/api/scan`, `/api/importar`,
`/api/operacoes`) validam só `is_absolute()` e `is_dir()`, sem passar pelo
módulo. Hoje isso é defensável: o servidor escuta apenas 127.0.0.1 e o usuário
é o dono da máquina, então um caminho arbitrário não é escalada de privilégio.
A lacuna é que a defensabilidade depende inteiramente dessa premissa.

**E a premissa está bem defendida.** `app.py:61` mantém
`_HOSTS_LOCAIS = {"127.0.0.1", "localhost", "::1"}` e `app.py:134` documenta e
implementa a checagem de `Origin`/`Host` contra DNS-rebinding — o ataque real
contra servidores locais, em que um site no navegador do usuário faz POST para
127.0.0.1. Isto está tratado e é um ponto forte que não deve ser perdido em
nenhuma refatoração.

### 2.6 Duas UIs

`ui/` + `workers/` somam 2.135 LOC contra 2.574 LOC do webapp: o fallback tem
**83% do tamanho** da UI principal. O `CLAUDE.md` diz que o webapp já tem
paridade de telas e cobertura própria, e que a remoção sai em commit próprio
levando `tests/test_ui_smoke.py`.

Recomendação: remover. Não por asseio, por três custos concretos — toda
mudança de domínio tem dois caminhos de UI para validar; `ExternalCatalogProvider`
já tem consumidor em `ui/main_window.py`, o que amarra o protocolo à UI antiga;
e o `workers/` (QThreadPool) é uma segunda infraestrutura de background que não
serve ao webapp. Esforço estimado: 1 commit, meio dia, baixo risco. **Não
executado nesta fase** — está fora da fronteira do protocolo.

---

## 3. Desenho proposto — o que falta no esquema

Aqui está a lacuna que importa. As 21 tabelas cobrem bem catalogar, inferir,
revisar e copiar. Um DAM precisa de mais quatro coisas, e nenhuma tem lugar no
esquema atual.

**Derivados e linhagem pai-filho.** A prática de DAM trata o RAW e seus
derivados editados como um asset com versões. Hoje o mais próximo é
`duplicate_groups` com papel `principal | versão | ignorado` — mas isso é
resultado de *detecção de duplicata*, não linhagem declarada. Um CR3 e o JPEG
exportado dele são o mesmo asset em dois estados; o esquema não sabe disso.
Falta `media_files.parent_id` ou uma tabela `asset_versions`.

**Taxonomia hierárquica.** `tags` é `(id, nome, tipo)` com `nome` unique —
lista plana. A prática de DAM exige hierarquia de palavras-chave e vocabulário
controlado ("Praia" sob "Paisagem" sob "Natureza"), porque é o que faz a busca
escalar junto do acervo. Falta `tags.parent_id` e a noção de vocabulário
fechado versus livre.

**Direitos e autoria.** `media_files` não tem autor, detentor de direitos,
licença nem crédito. IPTC Core define todos, e a fase 3 vai lê-los do arquivo
— sem coluna, eles caem em `metadata_entries` e não são filtráveis. Para
produto comercial, é ausência estrutural.

**Coleções curadas.** `trips` e `events` são agrupamentos *inferidos* (têm
coluna `metodo`). Não há tabela para o conjunto que o usuário monta à mão e
que não corresponde a nenhuma inferência. É uma das primeiras coisas que um
usuário de DAM procura.

Nenhuma dessas quatro é bloqueio de MVP. Todas ficam mais caras depois de
500 mil linhas catalogadas, e as duas primeiras (`parent_id` em `media_files`
e em `tags`) são migrações baratas hoje. Registrado como D-008.

---

## 4. Escala e confiabilidade

### 4.1 O N+1 concreto

`server/app.py:292-296` percorre viagens e, para cada uma, roda
`SELECT COUNT(id) FROM media_files WHERE trip_id = ?`. E
`media_files.trip_id` é chave estrangeira **sem índice** — SQLite não indexa
FK automaticamente. Com 200 viagens e 500 mil linhas, isso é 200 varreduras
completas da tabela maior do catálogo, a cada abertura da tela de viagens.
Mesmo padrão para eventos.

Correção: um índice em cada FK e um `GROUP BY` no repositório. Duas linhas de
migração e um método. É o item de melhor relação impacto/esforço da fase.

### 4.2 Índices ausentes

Existem 6 índices. Faltam, nos caminhos que a UI usa:

| Tabela.coluna | Por que | Sintoma em 500 mil |
|---|---|---|
| `media_files.trip_id` | FK + contagem por grupo | tela de viagens varre a tabela N vezes |
| `media_files.event_id` | idem | tela de eventos, idem |
| `media_files.location_id` | filtro geográfico | filtro por cidade varre tudo |
| `media_files.hash_perceptual` | migração 0002, busca de similares | duplicata visual varre tudo |
| `duplicate_members.media_id` | FK, junção por foto | inspetor lento por foto |
| `face_occurrences.media_id` | FK | idem, quando rostos entrarem |
| `media_tags.media_id` | FK | filtro por tag |
| `operation_items.media_id` | FK | resumo de plano grande |

`evidence(media_id)` e `metadata_entries(media_id)` já têm — os dois que mais
crescem em linhas estão cobertos, o que sugere que a lista acima é descuido,
não desenho.

### 4.3 O que falha primeiro

Ordem esperada conforme o acervo cresce, sem nenhuma das correções acima:

1. **~50 mil fotos** — tela de viagens e eventos degrada visivelmente (4.1).
2. **~100 mil** — filtros por local e tag ficam lentos (4.2); ainda usável.
3. **~250 mil** — `metadata_entries` domina o tamanho do banco. Com exiftool
   (fase 3) escrevendo dezenas de tags por arquivo em vez de poucas, este é o
   ponto em que o modelo chave-valor puro precisa da decisão da fase 3.
4. **~500 mil** — um scan completo passa a bloquear o app por horas sem fila
   nem paralelismo (2.4). É onde "um trabalho por vez" deixa de ser
   disciplina e passa a ser limite.

### 4.4 Observabilidade

Praticamente ausente como requisito de produto: há logging estruturado, mas
não há métrica persistida de duração de scan, taxa de arquivos por segundo por
versão, nem contagem de erro por tipo ao longo do tempo. `scan_sessions` tem
os contadores de uma sessão — a matéria-prima existe, falta a série. Sem isso,
"o desempenho regrediu" não é uma afirmação verificável, e `docs/METODO_DE_TRABALHO.md`
exige baseline antes de otimizar.

---

## 5. Trade-offs

| Escolha atual | Ganha | Perde | Veredito |
|---|---|---|---|
| SQLite local como única fonte de verdade | zero operação, offline real, privacidade estrutural, custo zero | concorrência de escrita, sem colaboração | **manter.** digiKam sustenta 100 mil+ em SQLite e oferece MySQL só para escala massiva; o precedente favorece SQLite para acervo pessoal |
| Um trabalho por vez | simplicidade, sem contenção de escrita no SQLite | scan longo bloqueia tudo | **revisar em 4.3 nível 4.** Fila com prioridade antes de paralelismo real |
| Chave-valor em `metadata_entries` | acomoda qualquer padrão sem migração | não é filtrável nem indexável por campo | **decisão da fase 3.** Híbrido é o caminho provável |
| Protocolos com uma implementação | fronteira desenhada cedo, escopo congelado | fronteira não validada | **aceitar,** tratando a fase 3 como teste da fronteira |
| Duas UIs em paralelo | fallback durante transição | 2.135 LOC de custo duplo, protocolo amarrado à UI antiga | **remover o PySide6** |
| Geocoding offline por padrão | privacidade, sem custo, sem rate limit | precisão menor que serviço online | **manter** — é a proposta de valor, não uma limitação |

---

## 6. O que eu revisitaria

- **Ao passar de 250 mil fotos:** o modelo de `metadata_entries`, junto da
  decisão da fase 3. É a tabela que cresce mais rápido e a mais difícil de
  remodelar depois.
- **Ao chegar o segundo `MetadataExtractor`:** se a fronteira do protocolo
  aguenta o exiftool em batch com `-stay_open` — um processo persistente tem
  ciclo de vida que um extrator puro-Python não tem, e isso pode não caber na
  assinatura atual.
- **Se sync entrar no roadmap:** `SyncProvider` precisa existir *antes* do
  primeiro adaptador, ou o Railway vaza para o domínio exatamente como o
  `CLAUDE.md` proíbe.
- **Se um segundo usuário aparecer:** o esquema não tem noção de dono, e a
  premissa de 127.0.0.1 é o que sustenta a segurança hoje. As duas coisas
  mudam juntas, e nenhuma delas é barata.
- **Se o app for distribuído:** a validação de caminho dos endpoints (2.5)
  deixa de ser defensável no momento em que a UI puder ser exposta.

---

## 7. Riscos arquiteturais, por impacto

| # | Risco | Sintoma que aparece primeiro | Esforço |
|---|---|---|---|
| 1 | FK sem índice + N+1 na tela de agrupamentos | tela de viagens lenta com poucas dezenas de milhares de fotos | baixo — 8 índices + 1 método |
| 2 | Esquema sem derivados, hierarquia de tags, direitos e coleções | usuário pede "mostre só as editadas" e não há resposta possível | médio — 2 migrações baratas agora, caras depois |
| 3 | `metadata_entries` chave-valor puro sob exiftool | catálogo infla e filtro por campo não existe | decidido na fase 3 |
| 4 | Um trabalho por vez sem fila | scan de acervo grande bloqueia o app por horas | médio |
| 5 | Ausência de série de métricas | regressão de desempenho não é detectável | baixo |
| 6 | Duas UIs | custo duplo em toda mudança de domínio | baixo — 1 commit |
| 7 | `SyncProvider` prometido e inexistente | primeiro adaptador de nuvem vaza para o domínio | baixo hoje, alto depois |
| 8 | Validação de caminho fora do módulo de segurança nos endpoints | irrelevante enquanto for 127.0.0.1; grave se a UI for exposta | baixo |

---

## 8. Arquitetura de trabalho com agentes

Avaliação separada: isto é infraestrutura de desenvolvimento, não do produto.

**O que está bem.** `CLAUDE.md` tem 132 linhas — dentro do que se recomenda
para instrução de projeto, com invariantes, stack e módulos, sem virar
enciclopédia. Conhecimento reutilizável está em skills (`fatia-vertical`,
`orquestrar`) em vez de inflar o prompt. Os quatro agentes
(`agente-arquivos`, `agente-imagem`, `agente-ux`, `agente-arte`) têm fronteira
por domínio de módulo, o que é a divisão certa — cada um mapeia para pastas
específicas. Existe `scripts/verificar.sh` como verificação determinística.

**Uma coisa a corrigir.** `CLAUDE.md` e `AGENTS.md` são **byte-a-byte
idênticos** (132 linhas, 7.748 bytes cada) e não são o mesmo arquivo. São duas
fontes de verdade que vão divergir na primeira edição de uma delas. Um symlink
resolve: `ln -sf CLAUDE.md AGENTS.md`. Registrado como D-009; não executado,
por estar fora da fronteira desta fase.

**Uma observação.** O `CLAUDE.md` lista os cinco `Protocol` substituíveis
incluindo `SyncProvider`, que não existe (2.3), e omite os dois que existem.
Instrução de projeto que descreve código inexistente induz o agente a assumir
que a fronteira está lá. Vale corrigir junto da decisão sobre sync.

---

## Comparação com o mercado

Consultado em 2026-07-29.

**digiKam** é o precedente mais próximo: local-first, com SQLite para
simplicidade e MySQL para escala massiva, com relatos de catálogos de 100 mil+
imagens e busca de metadados sem latência perceptível. Sustenta a decisão de
manter SQLite — e mostra que o caminho de saída, se um dia for necessário, é
trocar o backend, não o modelo.

**Lightroom** separa o catálogo (índice, metadados, previews) dos arquivos
físicos numa estrutura ordenada. O Foto Organizer segue o mesmo modelo, com
uma diferença a favor: o catálogo aqui é a única fonte de verdade e os
originais nunca são tocados, enquanto no fluxo Lightroom o usuário
frequentemente delega a organização física à ferramenta.

**Prática canônica de DAM** organiza-se em ingestão → anotação → catalogação →
armazenamento → recuperação, com derivados (cópias em resolução menor)
explicitamente modelados, relações pai-filho ligando o RAW às suas versões
editadas, e taxonomia expressa como hierarquia de palavras-chave e vocabulário
controlado. Sistemas maduros ingerem metadados embutidos (IPTC/XMP) de
arquivos legados preservando o dado histórico e reestruturando-o na taxonomia
própria — que é exatamente o desenho da fase 3.

**Onde este produto está bem posicionado:** o modelo de evidências com origem,
confiança e justificativa legível não tem paralelo direto nos produtos
consultados — DAMs comerciais tratam metadado inferido como fato. Para um
acervo pessoal, "por que você acha que isto é Dubai?" é a pergunta que decide
a confiança do usuário, e o `docs/CONFIANCA.md` responde por desenho. Somado a
local-first e a não-destrutivo estrutural, é a diferenciação defensável.

**Onde está subdimensionado:** derivados, hierarquia de taxonomia, direitos de
uso e coleções curadas — os quatro itens da seção 3. São mesa posta em
qualquer DAM maduro.

Fontes: [digiKam / DAM para fotógrafos](https://cyme.io/en/blog/digital-asset-management/) ·
[Lightroom como DAM](https://dam-u.tech/lightroom-as-dam/) ·
[Lightroom como DAM — Henry's](https://blog.henrys.com/managing-your-digital-assets-with-lightroom/) ·
[Metadados embutidos em DAM](https://www.bynder.com/en/blog/dam-embedded-metadata-exercises/) ·
[Taxonomia em DAM](https://www.bynder.com/en/blog/dam-taxonomy-best-practices/) ·
[Estratégia de metadados](https://www.wedia-group.com/blog/dam-and-metadata-best-practices-and-how-to-get-the-most-out-of-it) ·
[Glossário DAM](https://damglossary.org/)
