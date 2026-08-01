# Auditoria: onde a IA alcança o que a regra não alcança

Feita a pedido do dono, com a skill `ai-firstify` como enquadramento e o
acervo real como evidência. A pergunta não era "onde daria para usar IA" —
era **onde um modelo ganha da cascata determinística de forma demonstrável**.

Veredito curto: **a hipótese de que não há uso possível cai, mas por uma
margem estreita e nomeável.** Há exatamente três situações em que os
metadados são mudos e só o conteúdo da imagem responde. Fora delas, a regra
ganha — e em dois casos que eu ia implementar, a regra que eu propus estava
errada.

---

## O que a regra já resolve, e bem

Medido neste acervo, sem modelo nenhum:

| | |
|---|---|
| Cenários rotulados de agrupamento | 17/17 |
| Fotos com lugar por correlação temporal | 4.928 |
| Classificação foto × captura × recebida × baixada | 5.191 |
| Álbuns separados entre "nomeia" e "é aparelho/app" | 36/36 |
| Miniatura interna do Apple Fotos separada do acervo | 45.822 |

Nada disso melhoraria com um modelo. São regras sobre metadados que o arquivo
já carrega, e a regra tem duas vantagens que o modelo não tem aqui: responde
"por quê?" numa frase e custa zero por foto.

## Onde a regra falha e o conserto NÃO é IA

Dois casos que eu descobri tentando validar a régua que eu mesmo havia
proposto para separar eventos. Registro porque quase viraram justificativa
para chamar um modelo:

**1. O corte da meia-noite.** A régua "intervalo de 4 h separa eventos"
aplicada por dia de calendário parte uma viagem contínua ao meia-noite. Nos 28
dias alcançáveis do acervo, 8 acusaram "dois blocos" — e os 8 são a mesma
viagem a Dubai, com blocos `22:41–23:59` e `01:53–06:57` que são a mesma
noite. O conserto é não vincular a régua ao calendário, não um modelo.

**2. Álbum não é evento.** Eu ia usar as 25.304 nomeações de álbum como
fronteira de acontecimento. Elas se aninham: no mesmo dia, "Férias" (431),
"Portugal e Italia com as Meninas" (235) e "Family" (177) são a MESMA foto
contada três vezes. Álbum é etiqueta hierárquica, não partição. Serve para
nomear, nunca para dividir.

## Onde só o conteúdo responde

As três situações em que nenhum metadado deste acervo distingue os casos.

### 1. Dois acontecimentos, mesmo dia, mesmo lugar, mesma câmera

É o problema que o dono levantou. Aniversário de manhã e show à noite têm o
mesmo dia, a mesma cidade, o mesmo corpo de câmera e, muitas vezes, intervalo
de tempo indistinguível de um almoço longo dentro de um evento só.

O que separa é o que está na foto: bolo e mesa contra palco e plateia.
Timestamp e coordenada não têm essa informação — não é questão de régua
melhor, é ausência de sinal.

**O que um modelo ganha:** a fronteira que a régua não consegue traçar.
**O que ele custa:** um vetor por foto, e a fronteira deixa de ser explicável
por uma frase.

### 2. Vinte e cinco anos de acervo, quatro com GPS

O inventário de câmeras mostra 58 aparelhos, de 2001 a 2026. Só a **Canon EOS
5D Mark IV** tem receptor embutido: 2.878 fotos com coordenada, cobrindo
2019–2023.

Para 2001–2018 — Rebel XSi (17.132 fotos), 5D Mark III (11.235), 7D (6.806) —
não existe coordenada própria nem doador para herdar. A correlação temporal
não tem de onde puxar.

**O que um modelo ganha:** lugar a partir de marco visual reconhecível.
**A ressalva honesta:** funciona para Torre Eiffel, não para a casa da avó — e
a maior parte de um acervo pessoal é a casa da avó.

### 3. Metadado corrompido

1.135 fotos sem modelo de câmera no EXIF, com datas que o Lightroom registra
no intervalo "2002–2100". Um scanner de filme (`OpticFilm 7500i`) grava a data
da digitalização, não a da foto.

**O que um modelo ganha:** estimar a época pelo conteúdo — roupa, carro,
qualidade da imagem — quando a data é impossível.
**O que a regra já faz:** detectar a incoerência. Sinalizar é regra; datar é
modelo.

---

## A distinção que o princípio 5 força

O princípio "não construa seu próprio agente" da skill proíbe embutir chamadas
de LLM em código de aplicação. O app tem exatamente isso: o
`ClassificationAdvisor` chama `anthropic` de dentro de
`fotoorganizer/classification/advisor.py`.

Mas o princípio conflaciona duas coisas que aqui precisam ficar separadas:

**Agente embutido** — LLM que decide, com prompt e resposta em linguagem
natural. É o advisor. Não é auditável foto a foto, custa por chamada, e manda
dado para fora. Está desligado por padrão e deve continuar.

**Modelo local** — função de imagem para vetor. Roda offline, é determinística
(a mesma foto dá o mesmo vetor), não manda nada para lugar nenhum, e custa
tempo de CPU uma vez por foto. Não é agente; é um extrator de característica,
como o phash que o app já usa para duplicatas.

D-004 diz "regra determinística antes de modelo". Um embedding local **é**
determinístico. A decisão que ele contradiz é outra — a de não baixar modelo —
e essa nunca foi tomada explicitamente.

---

## Recomendação

1. **Manter o advisor desligado.** Ele é o uso de IA que o princípio 5
   condena, e nenhum dos três casos acima precisa dele.
2. **Não tratar embedding local como se fosse a mesma coisa.** É a única
   ferramenta que alcança o caso 1, que é o problema em aberto do dono.
3. **Consertar a régua antes de chamar modelo.** O corte da meia-noite e a
   confusão álbum/evento são erros de regra, e resolvê-los pode reduzir o caso
   1 a um resíduo pequeno o bastante para não justificar o download.
4. **Medir antes de adotar.** O caso 1 não tem exemplo rotulado no acervo
   alcançável — os eventos reais estão no `/Volumes/photo`, desmontado. Sem
   cenário que a cascata erre e o modelo acerte, adotar é fé.

## O que fica em aberto para o dono

Baixar um modelo de visão local (~150–400 MB, extra `[visao]`) para resolver o
caso 1 é a decisão. Ela não fere privacidade — nada sai da máquina — e não
fere auditabilidade, desde que a evidência diga "separado por conteúdo visual"
com score baixo, e não invente uma justificativa que ninguém pode conferir.

O que ela fere é a simplicidade: o app deixa de rodar em qualquer máquina com
Python e passa a ter uma dependência pesada e opcional.
