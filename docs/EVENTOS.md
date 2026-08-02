# Dividir uma sessão em acontecimentos

Complementa `docs/AGRUPAMENTO.md` — não repete a cascata sessão → viagem/
evento (seção 2 de lá continua valendo inteira). Este documento cobre o
nível que a cascata não tinha: uma sessão pode conter **mais de um**
acontecimento.

## O problema (fase 8, Problema 3)

A cascata de `AGRUPAMENTO.md` corta sessões só em lacuna temporal > 3 dias
(ou transição casa↔fora). Um dia inteiro, por mais coisas diferentes que
tenha acontecido nele, é sempre uma sessão só — porque a régua era o
intervalo entre fotos, e dentro de um dia esse intervalo nunca passa de 3
dias.

O dono apontou o caso: **aniversário de manhã e show à noite**, mesmo dia,
mesma cidade, possivelmente a mesma câmera. Nenhum campo de metadado
diferencia os dois — nem país, nem pasta, nem em geral GPS (só a 5D Mark IV
grava coordenada neste acervo, D-029). O único sinal que sobra é o próprio
ritmo de disparo: as fotos da manhã formam um grupo denso, as da noite
outro, e entre os dois grupos há uma lacuna de horas sem fotos.

`fotoorganizer/grouping/eventos_temporais.py` resolve isso com uma régua de
ritmo relativo, não um intervalo fixo — a motivação de por que não pode ser
fixo está documentada no topo do próprio arquivo (dois erros medidos no
acervo real: um limiar de 4h por dia de calendário parte a viagem a Dubai
na meia-noite, e o ritmo de disparo varia por ordem de grandeza entre um
ensaio e um dia de turismo).

## O modelo — sinais realmente implementados

A lista de sinais cogitados no prompt da fase 8 era mais ampla do que o que
o código acabou usando. Isto é o que `dividir_em_eventos` e `dividir_sessao`
realmente fazem, lidos direto do código:

| Sinal | Como age | Constante |
|---|---|---|
| Ritmo local relativo | Corta quando o intervalo atual excede `FATOR` (6×) vezes a mediana dos `JANELA` (12) intervalos **anteriores** — a janela só olha para trás, de propósito (uma janela simétrica se contamina com o bloco seguinte) | `FATOR`, `JANELA` |
| Piso absoluto | Nunca corta abaixo de 90 min, mesmo que o ritmo geral seja de segundos — protege pausa de almoço e o respiro de uma rajada | `PISO` |
| Teto absoluto | Sempre corta acima de 8h, mesmo que o ritmo geral seja de horas — protege a fronteira seguinte num dia de fotos esparsas | `TETO` |
| Deslocamento | Corta independente do tempo quando há coordenada GPS dos dois lados e a distância ≥ 3 km | `DESLOCAMENTO_KM` |
| Absorção de blocos pequenos | Bloco com menos de 10 fotos funde no vizinho mais próximo no tempo, em vez de virar acontecimento próprio | `MIN_FOTOS_EVENTO` |
| Duração máxima de acontecimento | Sessão com mais de 20h corridas do início ao fim é estadia (dorme no meio), não se divide — mesmo que o classificador a tenha rotulado "evento" por não alcançar o limiar de viagem de 3 dias | `DURACAO_MAX_ACONTECIMENTO` |
| Viagem não se divide | `dividir_sessao(..., e_viagem=True)` sempre devolve um bloco só — dividir uma viagem produz uma saída por manhã e por tarde, o que desfaz o commit 9670765 | flag do chamador |

### Sinais cogitados na fase 8 e não implementados

O prompt da fase 8 listava também câmera/lente, intenção declarada de
álbum e hora do dia. Nenhum dos três virou regra:

- **Câmera/lente** — o próprio código cita troca de lente como exemplo do
  que **não** deve cortar (fica dentro do piso de 90 min, junto de almoço e
  caminhada até o próximo ponto). Trocar de equipamento não é tratado como
  mudança de contexto.
- **Intenção declarada de álbum** (nomeação do Apple Fotos/Lightroom) — foi
  cogitada e medida, e rejeitada: D-030 em `docs/DECISOES.md` mostra que os
  álbuns se aninham (a mesma foto contada em "Férias", "Portugal e Italia
  com as Meninas" e "Family" ao mesmo tempo, em 29 dias do acervo). Álbum
  entra como nome e evidência de intenção, nunca como divisor — decisão que
  vale também aqui, não só na cascata de sessão. A metade que **foi**
  implementada (o álbum como nome, e o desempate contra o nome de pasta)
  está em `docs/AGRUPAMENTO.md`, seção 2c, e em D-034; nada dela toca a
  divisão descrita neste documento — `dividir_sessao` não recebe álbum, e
  os blocos que ela devolve são reclassificados e renomeados um a um, cada
  um com os álbuns do seu próprio período.
- **Hora do dia** — não existe uma regra "manhã ≠ noite". O efeito aparece
  só indiretamente: a lacuna entre os dois grupos de um dia real tende a
  estourar o teto ou o fator do ritmo local, não porque o horário em si é
  comparado.

## Onde entra no pipeline

`SuggestionEngine._subdividir` (`fotoorganizer/classification/engine.py`)
chama `dividir_sessao` para cada sessão, **depois** de ela já ter sido
classificada pela cascata de `AGRUPAMENTO.md`, e reclassifica cada pedaço
de novo:

> A ordem importa e é contraintuitiva: classificar primeiro, subdividir
> depois, reclassificar os pedaços. Sem a classificação não dá para saber
> se subdividir é permitido — viagem é uma pasta só — e cada pedaço precisa
> de veredito próprio, porque tem duração e lugar próprios e pode nomear
> onde o conjunto não nomeava. (commit 6214828)

Cada bloco final vira seu próprio `Event` (ou `Trip`, se a sessão inteira
já era viagem — que nunca se divide). Isto é inferência pura: nenhum
arquivo é tocado, só as tabelas `trips`/`events` e `destino_sugerido` são
regeneradas a cada `gerar()`.

## Medida de antes e depois

`scripts/avaliar_agrupamento.py` mede a cascata de sessão (viagem × evento ×
neutra) — os 17 cenários lá não cobrem subdivisão de acontecimento, e
continuam sendo o piso a não regredir para aquele nível (ver
`docs/AGRUPAMENTO.md`, seção 2b). Não existe hoje um script de avaliação
equivalente para o nível de acontecimento; a evidência disponível é de
teste automatizado e de medição pontual registrada em commit.

**Prova de que o mecanismo separa (sintética):**

- `tests/test_eventos_temporais.py::test_aniversario_de_manha_e_show_a_noite_sao_dois`
  — reproduz o caso do dono como função pura: 30 fotos a cada 3 min pela
  manhã, 30 fotos no mesmo ritmo 13h depois. `dividir_em_eventos` devolve 2
  blocos de 30. É o cenário rotulado que a fase 8 pediu no critério de
  aceite 5, no nível da régua.
- `tests/test_suggestion_engine.py::test_aniversario_de_manha_e_show_a_noite_viram_dois_eventos`
  — o mesmo cenário, agora ponta a ponta pelo `SuggestionEngine`: as 60
  fotos vivem na mesma pasta ("Aniversário da Ana", mesma câmera implícita,
  sem GPS). Antes do commit 6214828 (sem `_subdividir` ligado), a sessão
  inteira virava um único `Event`, de 08:00 a 22:27 (14h27). O teste prova
  que hoje viram **dois** `Event` distintos — `media.event_id` diferente
  para cada metade, cada `Event` cobrindo menos de 2h, não o dia inteiro.
  Este teste foi adicionado nesta revisão para fechar a lacuna: só existia
  a versão de função pura, não uma prova no nível do motor completo.

**Prova de que o mecanismo não superdivide o acervo real (medida em
commit, não em script):**

- `git show 076630f` — a régua escrita mas ainda não ligada ao motor,
  medida numa cópia do catálogo real: TERG 597 fotos → 1 bloco, Quizomba
  450 → 1, Pantanal 97 → 4 saídas em 3 dias, e **Serena 15 Anos 319 → 2**
  (cinco fotos de teste às 17h25, separadas da festa das 19h28 por só 2h de
  intervalo — tecnicamente correto, mas o dono não reconhece 5 fotos como
  evento da própria vida).
- `git show 6214828` — a absorção de blocos pequenos (`MIN_FOTOS_EVENTO`) e
  a ligação ao motor, medidas na mesma cópia do catálogo: Serena volta a
  1 bloco (319, "os mesmos de antes"), TERG e Quizomba continuam em 1,
  Pantanal continua em 4 saídas internas mas 1 destino (estadia, não se
  divide). Nenhuma sessão foi partida indevidamente e os 17 cenários de
  `avaliar_agrupamento.py` seguiram verdes.

**O que não está medido:** não há, até este documento, uma medição no
acervo real de um dia com dois acontecimentos genuinamente distintos (como
aniversário de manhã + show à noite) sendo corretamente separado. A
evidência do acervo real (Serena/TERG/Quizomba/Pantanal) prova que o
mecanismo **não superdivide** o que já estava certo — não prova, com dados
reais, o caso positivo que motivou a feature. Esse caso está provado só
com timestamps sintéticos que reproduzem a descrição verbal do dono. Se um
dia real assim aparecer no acervo (revisado e confirmado pelo dono), ele
devia virar cenário novo antes de qualquer ajuste de limiar — mesma regra
que vale para `avaliar_agrupamento.py`.

## Como reverter ou desligar

Não existe flag em `config.toml` para isto — ao contrário do advisor LLM
(`[privacidade] servicos_externos`) ou do provider de geocodificação
externo, a subdivisão de acontecimento é incondicional: roda para toda
sessão que não for viagem, sempre que `SuggestionEngine.gerar()` é chamado.

Para desligar é preciso mexer em código, não em configuração:

- Remover a chamada a `self._subdividir(...)` no laço de
  `fotoorganizer/classification/engine.py` (por volta da linha 312-316) faz
  o motor voltar ao comportamento anterior ao commit 6214828 — uma sessão,
  um `Trip`/`Event`.
- Ajustar as constantes de `eventos_temporais.py` (`TETO` maior,
  `MIN_FOTOS_EVENTO` maior, `FATOR` maior) torna a régua menos sensível,
  mas não é um desligamento — é uma régua mais frouxa, e muda o resultado
  de outros cenários. Qualquer mudança de limiar segue a regra do projeto:
  cenário novo em `scripts/avaliar_agrupamento.py` (ou em
  `tests/test_eventos_temporais.py`, que é onde os cenários deste nível
  vivem hoje) antes do ajuste, `scripts/verificar.sh` depois.

A subdivisão nunca escreve em disco nem apaga registro (invariantes 1 e 8
do `CLAUDE.md`): regenerar a sugestão é sempre seguro, porque
`_persistir_agrupamentos` recria `trips`/`events` do zero a cada `gerar()`.
