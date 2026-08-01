# O lugar estimado e o tamanho da sua dúvida

Quando uma foto não tem GPS, o motor de correlação
(`fotoorganizer/grouping/correlacao.py`) empresta a coordenada da foto mais
próxima no tempo, de outra origem, que tem GPS. É informação real e é a única
que existe para 4.944 fotos do acervo — mas a coordenada é a da **doadora**,
não a da foto. Desenhá-la como ponto no mapa afirma uma precisão que o dado
não tem.

Este documento fixa o tamanho da dúvida: um **raio em metros**, função do Δt
até a doadora, que o mapa desenha como círculo. É D-025 dito em números — em
dez minutos não se troca de cidade, em doze horas não se troca de país.

## A fórmula

```
raio(Δt) = min(TETO, max(PISO, VELOCIDADE × |Δt|))
```

| constante | valor | onde | o que é |
|---|---|---|---|
| `VELOCIDADE_PLAUSIVEL_MS` | `6.0` m/s (≈ 22 km/h) | `grouping/correlacao.py` | a taxa com que a distância até a doadora cresce no acervo medido |
| `RAIO_PISO_M` | `15.0` m | idem | a imprecisão do próprio receptor de GPS da doadora |
| `RAIO_TETO_M` | `50_000.0` m | idem | a distância em que o crescimento para, medida |

Função pura, testável, sem estado: `raio_incerteza(delta: timedelta) -> float`
(metros). `Heranca.raio_m` a aplica ao Δt já corrigido de deriva de relógio.

O que ela diz nas três janelas de D-025:

| Δt | raio | escala |
|---|---|---|
| 0 | 15 m | o erro do GPS, nada mais |
| 10 min (janela da cidade) | 3,6 km | um bairro |
| 2 h (janela da região) | 43,2 km | uma região metropolitana |
| 8 h 20 min em diante | 50 km | o teto — deixa de crescer |
| 12 h (janela do país) | 50 km | idem |

**A frase para a tela**, quando o dono clicar no círculo e perguntar por quê:
*"A foto que emprestou o lugar está a 2 h daqui. A 22 km/h — a velocidade de
quem anda por uma cidade contando as paradas — isso dá 43 km de dúvida. Em 9
de cada 10 casos medidos no seu acervo, o lugar verdadeiro cabe nesse
círculo."* Quem monta a frase deve pedir o raio ao Python, nunca recalcular
`6.0 × Δt` em TypeScript: constante duplicada é constante que diverge.

## Como foi calibrada

`scripts/calibrar_raio_incerteza.py` — somente leitura, abre o catálogo em
modo `ro`, não escreve nada.

O erro de uma herança é justamente o que não se conhece: se soubéssemos onde
a foto foi tirada, não haveria o que estimar. Mas o acervo tem **19.746 fotos
com GPS próprio**. Tratando uma delas como se fosse herdeira e aplicando a
**mesma regra de escolha de `herdar_gps`** (a foto de outra origem mais
próxima no tempo, dentro de 12 h) para achar a doadora hipotética, a distância
entre as duas é medida, não estimada — e dá para perguntar se o raio proposto
a conteria.

Isso rendeu **2.083 pares em 45 dias de fotografia**. Todos cruzam origem,
como a herança real cruza: no acervo, 100% das heranças vêm de outra fonte
(Apple Fotos → Lightroom e pastas; Lightroom → Apple Fotos).

A cobertura é lida de três formas porque uma só esconderia as outras duas:

- **bruta** — cada par pesa igual;
- **ponderada** — cada banda de Δt pesa quanto pesa no acervo de verdade (as
  herdeiras reais estão concentradas em 30 min–12 h, não em segundos);
- **por dia** — cada dia de fotografia pesa igual, para que uma viagem com 318
  pares não escolha a constante sozinha.

## O resultado medido

Rodado em 2026-08-01 sobre `~/Library/Application Support/FotoOrganizer/catalog.db`:

```
pares medidos: 2083  dias de fotografia: 45
fórmula: min(50 km, max(15 m, 6.0 m/s × Δt))

banda          n  dias   p50 real   p90 real  raio no fim  cobertura
<=1min       269    25       0.0k       0.3k         0.4k      88.8%
1-10min      242    11       0.0k       0.2k         3.6k      97.1%
10-30min     195     9       0.2k     162.8k        10.8k      88.7%
30min-2h     325    18       1.4k      39.1k        43.2k      90.8%
2-6h         785    18       9.6k      45.6k        50.0k      95.8%
6-12h        267    12      17.4k      25.1k        50.0k      97.4%

cobertura bruta ............ 93.8%
cobertura ponderada ........ 93.6%
cobertura por dia .......... 96.2%
bootstrap por dia .......... p5=92.4% mediana=96.2% p95=99.5%
```

**93,6% ponderada pelo acervo** — acima da mira de 9 em 10. Reamostrando por
dia (bootstrap, 400 repetições, semente fixa), o percentil 5 fica em 92,4%: a
margem sobrevive a trocar quais dias entraram na conta. A reamostragem é por
dia e não por par de propósito — pares do mesmo dia são o mesmo trajeto
contado várias vezes, e tratá-los como independentes inventaria precisão.

### O que a medição derrubou

A direção sugerida era `raio ≈ velocidade × Δt` com teto na janela de
granularidade. A parte linear se confirmou; **o teto não**. A distância real
não cresce até as 12 h — ela **satura**: o p90 da banda de 6–12 h (25 km) é
*menor* que o da banda de 30 min–2 h (39 km). Quem fotografa por doze horas
seguidas passa o dia na mesma região; quem some por doze horas não fotografa
no meio. Um teto derivado da janela de país daria 259 km de raio a 12 h — um
círculo que cobre tudo e não informa nada, com cobertura idêntica à do teto de
50 km neste acervo (93,6% nos dois casos). O teto medido venceu o teto
suposto.

### Sensibilidade das constantes

`scripts/calibrar_raio_incerteza.py --grade`, cobertura ponderada:

| V \ teto | 40 km | 45 km | 50 km | 60 km | 80 km |
|---|---|---|---|---|---|
| 4 m/s | 82,7% | 83,3% | 87,7% | 87,7% | 87,7% |
| 5 m/s | 83,5% | 84,0% | 89,2% | 89,2% | 89,2% |
| **6 m/s** | 87,2% | 88,1% | **93,6%** | 93,6% | 93,6% |
| 7 m/s | 89,5% | 91,3% | 97,6% | 97,6% | 97,6% |
| 8 m/s | 89,5% | 91,3% | 97,6% | 97,6% | 97,6% |

6 m/s com 50 km é o **menor** par que passa dos 90% — a escolha é o menor
círculo que cumpre a promessa, não o maior que a cumpre com folga. De 50 para
80 km a cobertura não muda: acima de 50 km não há mais nada para cobrir neste
acervo.

O degrau entre 45 e 50 km é real e vem de um dia só (2020-02-14, 318 pares
entre 45 e 49 km). Sem esse dia a constante poderia ser menor; com ele, 50 km
é o arredondamento honesto logo acima do p90 da pior banda (48 km).

### Onde o raio não alcança — e por quê

Os 6,4% descobertos não são ruído uniforme: moram em **5 dias**, e são de três
tipos diferentes.

1. **Doadora com coordenada errada** (2019-04-19, 53 pares). O dia inteiro em
   Penedo (−22,33, −44,62), e a biblioteca do Apple Fotos tem, nos mesmos
   segundos exatos, registros marcados na casa no Rio, a 163 km. Não é
   deslocamento: é coordenada errada na doadora. Nenhum raio conserta isso —
   um raio de 163 km a Δt = 0 seria mentira maior que o ponto. Isso sozinho
   trava as bandas `<=1min` e `10-30min` perto de 89%.
2. **Viagem de verdade dentro da janela** (2015-06-05/06). 105–111 km em ~11 h,
   com o raio no teto de 50 km. É o caso em que o teto está errado — e ele
   está errado de propósito: cobri-lo exigiria um teto de 120 km que inutiliza
   o círculo nos outros 44 dias.
3. **Passar raspando** (2020-02-14: 49,3 km reais contra 46,7 km de raio;
   2019-09-06: 300 m reais contra 300 m de raio). O raio está certo em escala
   e erra na casa decimal.

O tipo 1 é um problema de **qualidade da doadora**, não de raio, e merece
tratamento próprio (uma doadora que contradiz suas vizinhas no mesmo instante
é suspeita). Fica registrado aqui, sem correção nesta fatia.

## A tensão, dita em voz alta

A mira de 90% e a utilidade do círculo puxam para lados opostos, e o acervo
mostra exatamente onde:

- Um círculo de 50 km sobre um mapa do Rio cobre a cidade inteira e boa parte
  da Baixada. Ele **não** diz em que bairro a foto foi tirada — e não deveria:
  a maior parte das herdeiras reais (14.852 das 17.819) está a mais de 30 min
  da doadora, e a essa distância o bairro não é afirmável. Quem quiser
  precisão de bairro precisa de Δt de minutos, não de horas.
- O raio é honesto sobre a **posição**, não sobre a **qualidade da doadora**.
  Δt pequeno com doadora errada dá círculo pequeno em volta do lugar errado —
  como no 2019-04-19. O círculo responde "quanto ela pode ter andado", não
  "a doadora sabe onde estava".
- As constantes são deste acervo: um dono baseado no Rio, cujas viagens
  concentram a fotografia numa região por dia. Alguém que fotografe em voos
  diários teria outro teto. Recalibrar é rodar o script.

## Como reverter

Tudo mora em três constantes de `fotoorganizer/grouping/correlacao.py`:

| quero | mudo |
|---|---|
| círculos maiores/menores em geral | `VELOCIDADE_PLAUSIVEL_MS` |
| tirar o teto (voltar ao linear puro) | `RAIO_TETO_M = float("inf")` |
| círculo colado no ponto a Δt zero | `RAIO_PISO_M` |
| a fórmula inteira | `raio_incerteza()` — função pura, um lugar só |

Nada disso é persistido: o raio é calculado na leitura, a cada exibição.
Mudar constante não exige migração, rescan nem regeração de sugestão — o mapa
seguinte já sai diferente. Depois de mudar, rode
`.venv/bin/python scripts/calibrar_raio_incerteza.py --grade` e atualize a
cobertura declarada aqui: número de cobertura desatualizado é pior que
nenhum, porque a interface promete honestidade em cima dele.

Os testes que fixam o comportamento estão em `tests/test_correlacao.py`
(bloco "raio de incerteza"); mudar constante quebra
`test_raio_por_granularidade_bate_com_a_escala_do_campo` de propósito — é o
teste que obriga a decisão a passar por aqui.
