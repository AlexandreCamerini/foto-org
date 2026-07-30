# Auditoria de funcionalidades — fase 2

Executada em 2026-07-29. Método em `docs/prompts/00-protocolo.md`. Decisões em
`docs/DECISOES.md` (D-010 a D-013).

Tudo abaixo foi exercitado num catálogo isolado (`HOME` redirecionado para um
diretório temporário). O catálogo real do dono — 31 MB, `mtime` 14:02 — não foi
aberto nem modificado em nenhum momento.

**Resumo em uma frase:** a percepção de que "muitas funcionalidades não
funcionam" não se confirma no motor — 284 testes verdes, todos os fluxos
principais exercitados de ponta a ponta — mas se confirma na **apresentação**:
a inferência mais valiosa que o sistema faz é justamente a única que o usuário
não consegue ver.

---

## 1. O achado central

O sistema herda GPS entre dispositivos, grava a evidência com uma
justificativa em português impecável, e **não mostra isso em lugar nenhum**.

Cenário construído para disparar (`scripts/medir_heranca_gps.py`, criado nesta
fase): iPhone com GPS às 10:30 e 10:40, Canon sem GPS às 10:32 e 10:38, pastas
e fontes diferentes. É o caso descrito pelo dono do produto, ao pé da letra.

No banco, depois de gerar sugestões:

```
DSC_0100.jpg | cidade | vizinhanca_temporal | Avignon | MEDIA | 0.75 |
  GPS herdado de 'IMG_9100.jpg' (Apple iPhone 15 Pro) — tirada a 2min de distância
DSC_0100.jpg | pais   | vizinhanca_temporal | França  | MEDIA | 0.75 | (idem)
DSC_0100.jpg | regiao | vizinhanca_temporal | Provence-Alpes-Côte d'Azur | MEDIA | 0.75 | (idem)
```

Na API, para a mesma foto (`GET /api/midia/62`), a lista `evidencias` traz
**três** itens: `data`, `viagem`, `categoria`. As três de `vizinhanca_temporal`
não aparecem. O Inspetor, que lê a mesma lista, mostra os mesmos três sob
"POR QUÊ?" — verificado no navegador.

A causa é precisa: as evidências geográficas são gravadas em `evidence` mas
**não são vinculadas à sugestão** em `suggestion_evidence`.

```
evidências no banco para media 62 ....... 6  (3 delas de vizinhanca_temporal)
evidências vinculadas à sugestão 121 .... 3  (nenhuma de vizinhanca_temporal)
```

`server/app.py:243` serializa `sugestao.evidencias` — o conjunto vinculado.
Logo o corte acontece antes da API, no vínculo.

Efeitos em cadeia, todos verificados:

- `media_files.gps_lat` continua `NULL` na foto que herdou — a coordenada em si
  não é persistida, só o `location_id` resolvido a partir dela;
- o Panorama conta essa foto em "sem coordenada" (25 no catálogo de teste),
  porque conta `gps_lat IS NULL`;
- a API não expõe `location` em resposta alguma — `país`, `região` e `cidade`
  estão no banco (`locations`, `media_files.location_id`) e não saem de lá;
- o Δt e a deriva aplicada existem apenas dentro do texto da justificativa,
  não como campo — não dá para filtrar "estimativas com Δt acima de 5 min".

**Classificação: Parcial.** O motor está correto e é melhor do que o pedido
original. O produto ao redor dele não existe. Isto é o insumo direto da fase 4,
e explica a percepção do dono melhor que qualquer outro achado desta auditoria.

---

## 2. Verificação obrigatória B — namespaces de metadados

Catálogo de demonstração (59 arquivos sintéticos: 58 JPG, 1 PNG):

| namespace | linhas | fotos | chaves distintas |
|---|---:|---:|---:|
| `exif` | 252 | 54 | 5 |
| `gps` | 144 | 36 | 4 |
| `iptc` | **0** | 0 | 0 |
| `xmp` | **0** | 0 | 0 |
| `fs` | **0** | 0 | 0 |

Média de 7,3 tags por foto (mín. 4, máx. 9). O PNG rendeu **zero** tags.

As nove chaves existentes são todas: `exif.DateTimeOriginal`, `exif.ExifOffset`,
`exif.GPSInfo`, `exif.Make`, `exif.Model`, `gps.GPSLatitude`,
`gps.GPSLatitudeRef`, `gps.GPSLongitude`, `gps.GPSLongitudeRef`.

Três observações:

1. `iptc` e `xmp` estão declarados no esquema
   (`models/catalog.py:133`) e em `docs/ARQUITETURA.md:42`, e nunca recebem
   linha — o extrator puro-Python não os lê. Confirma a premissa da fase 3.
2. `gps` é um namespace **real e não documentado**; `fs`, que está documentado,
   não existe. A lista em `docs/ARQUITETURA.md` está errada nos dois sentidos.
3. Os números acima são de JPEG sintético, que é o piso. Para arquivo real
   vale `docs/COBERTURA_METADADOS.md`, medido sobre 300 arquivos: lá o achado
   é que **nenhuma das 300 fotos tem coordenada** e que os 99 CR3 não expõem
   fabricante.

---

## 3. Verificação de sanidade — `scripts/verificar.sh`

O script exige `.venv/bin/python` **dentro do diretório de trabalho** e o
worktree não tem venv, então ele aborta antes do primeiro teste. Rodei os
quatro passos à mão, com o interpretador do checkout principal e `cwd` no
worktree (confirmado que importa `fotoorganizer` do worktree, não do principal).

| Passo | Resultado |
|---|---|
| 1. pytest | **284 passed** em 219 s |
| 2. benchmark de agrupamento | **17/17** na variante vencedora |
| 3. vitest (webapp) | **11 passed**, 2 arquivos |
| 4. build do webapp | **✓ built in 847ms**, 249 kB JS / 19 kB CSS |

Duas ressalvas sobre esses verdes:

**O rótulo do benchmark está velho.** A variante vencedora chama-se
"D: estadia só com casa desconhecida (**proposta**)", mas
`grouping/classifier.py:35` já traz `estadia_exige_casa_desconhecida: bool =
True` — ela **é** o padrão em produção. O que está em produção acerta 17/17; o
nome sugere o contrário e induz a leitura errada.

**A cobertura do webapp é fina.** 11 testes em 2 arquivos
(`App.test.tsx`, `Operations.test.tsx`) para 11 componentes e 2.574 linhas.
O `CLAUDE.md` diz que o webapp tem "cobertura própria" — tem, para 2 dos 11
componentes.

---

## 4. Inventário e classificação

### 4.1 CLI — 8 comandos

| Comando | Estado | Evidência |
|---|---|---|
| `scan` | Funciona | 59 indexados; 2ª passada 0 indexados / 59 pulados |
| `web` | Funciona | servidor de pé em 127.0.0.1:8799 |
| `importar` | Não verificado | exige acervo Apple Fotos / Takeout real (classe C) |
| `planos` | Funciona | via API equivalente |
| `plano` | Funciona | plano 1 criado |
| `dry-run` | Funciona | 5 prontos, 0 problemas, espaço conferido |
| `executar` | **Não exercitado por decisão** | classe C do protocolo — ver D-011 |
| `bench` | Não verificado | — |

### 4.2 Servidor — 28 endpoints

Exercitados e funcionando: `/api/status`, `/api/fontes`, `/api/midia`,
`/api/midia/{id}`, `/api/panorama`, `/api/viagens`, `/api/eventos`,
`/api/sugestoes`, `/api/sugestoes/gerar`, `/api/sugestoes/acao`,
`/api/duplicatas`, `/api/duplicatas/detectar`, `/api/operacoes` (GET e POST),
`/api/operacoes/{id}/dry-run`, `/api/scan`, `/api/job`.

Não exercitados: thumb e preview (verificados só indiretamente pela grade),
auditoria de plano, ações de duplicata, `/api/importar`, `/api/progresso`,
`/api/job/cancelar`, `/api/operacoes/{id}/executar`.

**Nenhum endpoint quebrado foi encontrado.** Dois retornaram erro correto:
criar plano sem sugestão aprovada devolve *"nenhuma sugestão aprovada
aguardando cópia"*, e o corpo malformado em `/api/sugestoes/acao` devolve 422
com o campo faltante. Os dois são o comportamento certo.

### 4.3 Telas — 6 abas

| Tela | Estado | Observação |
|---|---|---|
| Panorama | Funciona | lacunas, ano por fonte, por câmera, por formato. A tela mais informativa do app |
| Biblioteca | Funciona | grade + Inspetor com seção "POR QUÊ?" |
| Viagens | Funciona, com defeito de dados | ver 5.1 |
| Revisão | **Parcial** | ver 5.2 |
| Duplicatas | Funciona | 3 grupos detectados: 1 exato, 2 por conteúdo |
| Operações | Funciona | plano → dry-run, com checagem de espaço |

**Nenhuma funcionalidade órfã foi encontrada.** Era a hipótese principal ao
começar a fase, e ela não se sustentou: tudo que tem código tem caminho de
usuário. O problema é outro — dado que existe e não é apresentado.

---

## 5. Defeitos encontrados

### 5.1 Viagem fantasma na data do scan

A tela de Viagens mostra **"Viagem de 29-07 · 29 de julho de 2026 · 5 fotos"**.
São os 5 arquivos sem `DateTimeOriginal`: o scanner cai para o `mtime`, que é a
data em que o arquivo foi criado no disco, e o agrupador temporal trata isso
como uma estadia real — criando uma viagem no dia do scan.

Impacto num acervo real: todo arquivo sem data de EXIF (PNG, captura de tela,
arquivo recuperado) entra numa viagem falsa datada de hoje. Com 500 mil
arquivos, isso é uma viagem gigante e sem sentido no topo da lista.

Correção provável: distinguir `data_capturada` de `mtime` no agrupamento, e
tratar "sem data" como categoria própria, não como data. A coluna já existe —
`media_files.data_capturada` é nullable e o Panorama já sabe contar "5 sem data
de captura". O agrupador é que não faz a distinção.

### 5.2 A tela de Revisão não mostra o porquê

É a tela cuja função inteira é decidir sobre inferências, e é a única sem
acesso à justificativa. Cada linha traz: caminho absoluto truncado, destino
sugerido, badge de confiança, Aprovar, Rejeitar.

Três problemas concretos, visíveis na captura:

- **O caminho é truncado exatamente onde começaria a parte distintiva.** As 63
  linhas exibem o mesmo prefixo `/private/tmp/claude-501/-Users-acamerini-...`
  e cortam antes do nome do arquivo. Não dá para saber de qual foto é a linha.
- **Não há miniatura.** Uma tela de revisão de fotos sem fotos.
- **Não há caminho até a evidência.** O badge diz "Média" e não leva a lugar
  nenhum. O Inspetor tem "POR QUÊ?"; a Revisão, não.

O contraste com o Inspetor é o achado: a capacidade de explicar existe e está
implementada — só não está onde as decisões em lote acontecem.

### 5.3 Linhas duplicadas em `locations`

Duas linhas idênticas — `id 2` e `id 3`, ambas
`França / Provence-Alpes-Côte d'Azur / Avignon`, mesma fonte. O `cache_key` é
único por coordenada, então coordenadas diferentes que resolvem para o mesmo
lugar criam linhas distintas. Em 500 mil fotos, `locations` cresce com o número
de coordenadas distintas, não de lugares.

### 5.4 Não há como apontar o app para um catálogo alternativo

`load_settings()` aceita um caminho de config, e o CLI nunca passa um — não há
`--config` nem `--data-dir`. Tudo deriva de `Path.home()`. Para auditar sem
tocar no catálogo real tive de redirecionar `HOME`, que funciona mas é um
truque, não um recurso. Para um produto comercial isso é um problema de
suporte: não há como pedir a um usuário que rode contra um catálogo limpo para
isolar um defeito.

### 5.5 O ambiente de desenvolvimento não funciona em worktree

`scripts/verificar.sh` aborta com *"ERRO: .venv não existe"* em qualquer
worktree, e `.claude/launch.json` aponta para o **checkout principal** com
caminho absoluto — subir o preview por ele serviria o código de outra branch
contra o **catálogo real**. Nenhum dos dois é defeito de produto, mas os dois
tornam a verificação em branch mais difícil do que precisa.

---

## 6. O que a auditoria contradiz

| Afirmação | Onde | Realidade |
|---|---|---|
| M0–M7 concluídos | `docs/ROADMAP.md:6` | Sustenta-se. Todos os fluxos exercitados funcionam |
| namespaces `exif/iptc/xmp/fs` | `docs/ARQUITETURA.md:42` | `iptc`, `xmp` e `fs` sempre vazios; existe `gps`, não documentado |
| "webapp tem cobertura própria" | `CLAUDE.md` | 11 testes cobrindo 2 dos 11 componentes |
| "D: … (proposta)" | `scripts/avaliar_agrupamento.py:108` | É o padrão em produção desde `classifier.py:35` |

E uma correção a mim mesmo: durante a execução concluí cedo demais que o
Inspetor estava quebrado, porque um clique meu errou o alvo no navegador
automatizado. Ele funciona, tem a seção "POR QUÊ?", e é o melhor componente do
app do ponto de vista de transparência. O defeito real é mais estreito e está
em 5.2 e na seção 1.

---

## 7. Ordenado por impacto no usuário

| # | Item | Impacto | Esforço |
|---|---|---|---|
| 1 | Evidência de GPS herdado não chega à API nem à UI (§1) | o diferencial do produto é invisível | baixo — vincular a evidência à sugestão |
| 2 | Revisão sem miniatura, sem nome e sem porquê (§5.2) | a tela de decisão em lote é cega | médio |
| 3 | Viagem fantasma na data do scan (§5.1) | lixo visível no topo da lista de viagens | baixo |
| 4 | `location` não exposto pela API (§1) | país/cidade existem no banco e não aparecem | baixo |
| 5 | Coordenada herdada não persistida (§1) | impossível mapear foto sem GPS próprio | médio — decisão da fase 4 |
| 6 | `iptc`/`xmp` sempre vazios (§2) | metade dos metadados do arquivo é ignorada | decisão da fase 3 |
| 7 | Sem `--data-dir` no CLI (§5.4) | suporte não consegue isolar defeito | baixo |
| 8 | `locations` duplicadas (§5.3) | crescimento desnecessário de tabela | baixo |
| 9 | Cobertura do webapp em 2 de 11 componentes (§3) | regressão de UI passa despercebida | médio |

Os itens 1, 3, 4 e 7 somam pouco esforço e mudam bastante a percepção de
qualidade do produto. Se houver uma única rodada de implementação antes das
fases 3 e 4, é essa.

---

## 8. Artefatos desta fase

- `scripts/medir_heranca_gps.py` — gera o cenário mínimo que dispara a herança
  de GPS entre dispositivos. Fixtures sintéticas; não lê acervo real. É o que
  faltava para a funcionalidade ser demonstrável de ponta a ponta, e serve de
  base para o experimento de precisão da fase 4.
- Catálogo de teste, capturas e saídas de API ficaram no diretório temporário
  da sessão e **não foram versionados** — as evidências que importam estão
  transcritas neste documento. Ver D-013.
