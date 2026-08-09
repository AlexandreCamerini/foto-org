# Plano de IA e produto — fase 5

Executada em 2026-07-30. Método em `docs/prompts/00-protocolo.md`. IDs de
modelo e preços vêm da skill `claude-api`, não de memória. Decisões: D-022 e
D-023.

**Esta fase termina num gate.** O plano é a entrega; implementar o que está
aqui depende da sua aprovação. As três decisões que precisam dela estão no
fim.

**Resumo em uma frase:** a maior parte do que parecia precisar de IA já está
resolvida por regra determinística neste código, e a conclusão honesta desta
fase é que **quase nada de novo precisa de modelo** — o que falta é local, é
barato, e o que é remoto continua não valendo o custo nem o risco.

---

## 1. A tensão, resolvida

O princípio AI-first diz: não coloque chamadas de LLM no código da aplicação.
Para ferramenta pessoal está certo. Para um DAM comercial a inferência é o
valor entregue, e o conselho se inverte — foi o que D-004 registrou.

O que **não** se inverte virou as três restrições desta fase, e as três já
estão respeitadas pelo código existente:

1. **Regra determinística primeiro.** A cascata de
   `classification/engine.py` resolve pasta → keyword de evento → país na
   pasta → deslocamento GPS → estadia geocodificada → nome de álbum, e só
   então consulta o advisor. O benchmark rotulado acerta 17/17 sem modelo
   nenhum.
2. **Nenhuma infraestrutura de agente caseira.** `ClassificationAdvisor` é um
   `Protocol` com uma implementação de ~70 linhas usando o SDK oficial e
   structured outputs. Não há cadeia de prompts, não há orquestrador.
3. **Saída de modelo é evidência.** O advisor devolve categoria, evento e
   justificativa, e o motor grava como evidência de nível médio-baixo,
   abaixo das regras determinísticas, sujeita à mesma revisão.

---

## 2. O que decide o quê, hoje

| Eixo de catalogação | Como é decidido | Precisa de modelo? |
|---|---|---|
| Ano | `data_capturada` do EXIF | não |
| Viagem | lacuna temporal + transição casa↔fora + estadia geocodificada | não |
| Evento | keyword na pasta, duração curta, álbum nomeado | não |
| Local | GPS → geocodificação offline; sem GPS → herança entre câmeras → nome de pasta | não |
| Categoria (Viagens/Família/Eventos) | pasta; senão advisor | **só o resíduo** |
| Rajada | proximidade temporal + phash | não |
| Duplicata | hash exato, conteúdo, phash | não |
| Pessoa | — | sim, e não existe |
| Cena, qualidade, screenshot | — | sim, e não existe |

O advisor é chamado **apenas** para sessões que a cascata classificou como
"neutra" (`engine.py:283`). No catálogo de demonstração isso é zero de 63.
Num acervo real desorganizado seria mais, mas continua sendo resíduo — não é
o caminho principal.

---

## 3. Local, remoto e custo

### O que muda de imediato, sem decisão sua

`MODELO_PADRAO` do advisor estava em `claude-opus-4-8`, uma geração atrás.
Foi atualizado para `claude-opus-5` **junto com uma correção que a troca
exigia**: o advisor não passava `thinking`, e o significado disso mudou entre
as duas gerações — no Opus 4.8 omitir era não pensar; no Opus 5 o padrão
passou a ser pensar, e `max_tokens` cobre raciocínio mais resposta. Com
`max_tokens=1024`, o JSON truncaria no meio. Agora vai `thinking:
{"type": "disabled"}` explícito, o que também é mais barato.

### A aritmética

Preços por milhão de tokens (skill `claude-api`, 2026-07-30):

| Modelo | Entrada | Saída |
|---|---:|---:|
| `claude-opus-5` | $5,00 | $25,00 |
| `claude-sonnet-5` | $3,00 ($2,00 promocional até 31/08/2026) | $15,00 ($10,00) |
| `claude-haiku-4-5` | $1,00 | $5,00 |

**Advisor (metadados, sem imagem).** Um cluster são ~400 tokens de entrada e
~120 de saída. Supondo 1 consulta por 200 fotos num acervo desorganizado:

| Acervo | Consultas | Opus 5 | Haiku 4.5 |
|---|---:|---:|---:|
| 10 mil fotos | 50 | $0,02 | $0,004 |
| 100 mil fotos | 500 | $0,16 | $0,04 |

Custo desprezível nos dois casos. **A recomendação de descer para Haiku 4.5
não é sobre dinheiro — é sobre proporção.** Rotular metadados em três
categorias com o modelo mais caro do catálogo é usar o instrumento errado; e
a latência menor importa quando o usuário está esperando a geração terminar.

**Visão (a imagem sai da máquina).** É outra ordem de grandeza. Uma foto
custa ~1.600 tokens de entrada mais ~200 de prompt e ~100 de saída:

| Acervo | Haiku 4.5 | Sonnet 5 | Com Batches (−50%) |
|---|---:|---:|---:|
| 10 mil fotos | $23 | $69 | $12 / $35 |
| 100 mil fotos | $230 | $690 | $115 / $345 |

**Recomendação: não fazer.** Não pelo custo — $115 por um acervo inteiro é
aceitável. Pelo que o custo compra: cena, qualidade e "screenshot ou foto"
não decidem nada que a cascata já não resolva melhor, e mandar 100 mil fotos
pessoais para fora contraria o invariante 4 de forma que nenhum consentimento
bem escrito compensa. Visão, quando entrar, entra **local** — via
`VisionProvider`, que já existe como `Protocol` com stub.

Reconhecimento facial idem: já está desenhado como local, com embeddings
cifrados, e é o item 1 do v2 do ROADMAP.

**Nenhum dado saiu da máquina nesta fase.** Os números acima são aritmética
sobre contagem de tokens, não medição com fotos suas.

---

## 4. Escolha do eixo de catalogação

Hoje o template é fixo (`{categoria}/{ano}/{evento}` e variações) e o motor
escolhe o eixo pela cascata. A pergunta "qual o melhor parâmetro para
catalogar ESTA foto" já tem resposta implícita: o primeiro critério da
cascata que produz nome.

O que falta não é inteligência, é **controle**: o template não é editável na
UI (item 4 do v2 do ROADMAP). Um usuário que organiza por ano-primeiro não
tem como pedir isso. Isso é trabalho de UI sobre um motor que já aceita
template arbitrário — não é trabalho de IA.

---

## 5. Inventário da pasta organizada

Proposta: cada pasta de destino recebe um `inventario.json` e um
`INVENTARIO.md` irmão — máquina e humano.

O JSON carrega, por foto: nome no destino, caminho de origem, tamanho,
`hash_sha256` (o que a cópia verificou), data de captura, câmera, lugar, e
**a lista de evidências que decidiram o destino**, com origem, confiança e
justificativa. Mais um cabeçalho com o plano, a versão da lógica e a data.

Duas propriedades que isso compra:

- **Auditável fora do app.** Abrir a pasta em qualquer lugar e saber por que
  cada foto está ali, inclusive que o lugar era estimado e de quem veio.
- **Reconstrução.** Se o `catalog.db` se perder, os inventários reconstroem
  o catálogo sem reprocessar pixel nenhum.

Convive com `operations/` sem mudança de desenho: o executor já grava hash
pré e pós cópia; o inventário é o mesmo dado, escrito ao lado em vez de só no
banco. **Não implementado** — depende do gate.

---

## 6. Do piloto ao produto

### Pré-requisito de lançamento

| # | Item | Estado |
|---|---|---|
| 1 | Empacotamento assinado e notarizado | plano em `docs/EMPACOTAMENTO.md`, não feito |
| 2 | Remover a UI PySide6 | **feito** (`2e0ef1a`) |
| 3 | Índices de FK ausentes | 8 índices, migração de 2 linhas |
| 4 | Onboarding do primeiro acervo | não existe |
| 5 | `--data-dir` para suporte | **feito** (`7249318`) |
| 6 | Derivados, hierarquia de tags, direitos, coleções | 4 lacunas de esquema (arquitetura §3) |
| 7 | Série de métricas de desempenho | não existe |

### Posterior

Sync opcional (exige criar `SyncProvider`, que o `CLAUDE.md` promete e não
existe), visão local, rostos, template editável, eventos nomeados,
importação de outros DAMs.

### Diferenciação

A avaliação de arquitetura e a de UX chegaram à mesma conclusão por caminhos
diferentes: **o modelo de evidências não tem paralelo nos produtos
consultados.** DAMs comerciais tratam metadado inferido como fato — a foto
simplesmente "está" em Avignon. Aqui ela está em Avignon *porque* uma foto do
iPhone tirada 2 min antes tinha coordenada, e isso é dizível na interface.

Somado a local-first e não-destrutivo estrutural, é a proposta de valor. Não é
"mais IA": é IA que presta contas.

---

## 7. Trade-offs

| Escolha | Ganha | Perde |
|---|---|---|
| Regra antes de modelo | auditável, reproduzível, de graça, offline | teto menor em casos ambíguos |
| Advisor só no resíduo | custo desprezível, privacidade preservada | não ajuda onde a cascata erra com confiança |
| Visão local em vez de remota | invariante 4 intacto, sem custo recorrente | qualidade menor que modelo de fronteira |
| Inventário em JSON + Markdown | auditável fora do app, reconstrói catálogo | duplica dado; pode divergir do banco se editado à mão |
| Haiku no advisor | proporcional, mais rápido | menos margem em cluster ambíguo |

---

## 8. As três decisões que dependem de você

**1. Descer o advisor de Opus 5 para Haiku 4.5.** Custo cai 4×, latência cai,
e a tarefa — rotular metadados em três categorias — não pede mais que isso. O
risco é perder margem em cluster ambíguo, e o advisor já devolve `null`
quando não sabe. *Recomendo sim.*

**2. Visão e rostos ficam locais, sem opção remota.** Fecha a porta para
qualidade de modelo de fronteira em cena e qualidade, e mantém o invariante 4
sem asterisco. A alternativa é oferecer opt-in remoto, que traz UI de
consentimento, custo recorrente e uma superfície de risco que o produto hoje
não tem. *Recomendo fechar a porta.*

**3. O inventário por pasta entra antes ou depois do lançamento.** Antes:
todo acervo organizado nasce auditável e reconstruível. Depois: as pastas já
copiadas não têm inventário, e gerar retroativamente exige reler o catálogo.
*Recomendo antes* — é barato agora e caro depois.
