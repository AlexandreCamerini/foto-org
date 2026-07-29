# Fase 5 — IA sobre a base e plano de produto

Leia `docs/prompts/00-protocolo.md` primeiro. Entregável:
`docs/PLANO_IA_E_PRODUTO.md`. Depende das fases 3 e 4.

Com a base estruturada, decidir como a IA escolhe o melhor critério de
catalogação por foto — ano, evento, viagem, pessoa, local — e como as fotos
são agrupadas fisicamente junto de seu inventário.

**Esta fase termina no gate.** O plano é a entrega; a implementação começa
depois da aprovação do dono. Se ele não responder, o plano fica pronto e
aguardando — não comece a implementar por timeout. Este é o único ponto do
processo onde o timeout de 10 minutos não se aplica ao trabalho seguinte.

## Leituras de partida

`fotoorganizer/classification/engine.py`, `confidence.py`, `templates.py`,
`advisor.py`; `docs/CONFIANCA.md`; `docs/AGRUPAMENTO.md`;
`docs/PRIVACIDADE.md`; os entregáveis das fases 3 e 4.

## A tensão que esta fase precisa resolver primeiro

Há um princípio de projeto de sistemas com IA que diz: não coloque chamadas
de LLM dentro do código da aplicação — use o agente que já existe e mantenha
a aplicação determinística. Para ferramenta pessoal, o conselho está certo.
Para um produto comercial de DAM, a inferência *é* superfície de produto, e o
conselho se inverte.

O que não se inverte é a preocupação por trás dele. Ela vira restrição desta
fase:

1. **Regra determinística primeiro.** Onde uma regra sobre os metadados
   resolve, a regra ganha — é auditável, reproduzível, instantânea e de
   graça. Modelo entra onde a regra demonstravelmente não alcança.
2. **Nenhuma infraestrutura de agente caseira.** Sem framework de
   orquestração próprio, sem cadeia de prompts artesanal dentro do app. A
   inferência entra atrás de `VisionProvider` / `FaceRecognitionProvider`,
   que já existem como `Protocol`.
3. **Saída de modelo é evidência, não decisão.** Entra em `evidence` com
   origem, confiança, justificativa legível e versão da lógica, e passa pela
   mesma tela de revisão que o resto.

Abra o documento separando explicitamente: o que é regra, o que é modelo
local, o que é modelo remoto, e o critério que colocou cada coisa na sua
coluna.

## Escolha do critério de catalogação

Para cada foto o sistema precisa decidir sob que eixo ela é catalogada. Diga
como essa decisão é tomada e como ela se justifica ao usuário. Cubra:

- os eixos disponíveis (ano, viagem, evento, local, pessoa, câmera, projeto)
  e como o sistema escolhe entre eles quando mais de um se aplica;
- o que decide sem modelo: continuidade temporal, GPS, deriva corrigida,
  nome de pasta, rajada, duplicata, EXIF de câmera e lente — quase tudo isso
  já existe no motor atual;
- o que só um modelo resolve: cena, qualidade, screenshot versus foto,
  identidade de pessoa, tipo de evento;
- como a decisão fica explicável em uma frase, com as evidências por trás.

## Local versus remoto

Para cada capacidade que pede modelo, decida local ou remoto com:

- ganho esperado e como medi-lo;
- custo: para remoto, estimativa por 10 mil e por 100 mil fotos; para local,
  tamanho do modelo, tempo por foto e impacto na bateria;
- privacidade: exatamente que dados sairiam, com que finalidade, como o
  usuário consente por capacidade, como revoga, e o que acontece com o que já
  foi enviado. `docs/PRIVACIDADE.md` é o piso.

Para IDs de modelo, preços e parâmetros correntes de API, use a skill
`claude-api` — não a memória. Se nenhuma chamada externa for recomendada,
diga isso e por quê; é uma conclusão legítima e coerente com o produto.

**Nenhum dado real sai da máquina nesta fase, nem para teste.** Isso é
classe C do protocolo. Medição de custo é aritmética sobre contagem de
tokens, não chamada com fotos do acervo.

## Agrupamento físico e inventário

- Formato do inventário que acompanha cada pasta agrupada: que campos, em que
  formato legível por máquina e por humano, e como ele permite reconstruir o
  catálogo se o banco se perder.
- Como o inventário registra o que foi inferido versus lido, para que a pasta
  organizada seja auditável fora do app.
- Como isso convive com o executor de cópia verificada que já existe em
  `fotoorganizer/operations/`.

## Roadmap do piloto ao produto

Ordenado, com o que é pré-requisito de lançamento separado do que é
posterior. Cubra confiabilidade, empacotamento e assinatura, onboarding do
primeiro acervo, importação de acervos legados e de outros DAMs, desempenho
medido, e diferenciação frente aos produtos de referência do mercado.

Para cada item: esforço estimado, risco, e o que o desbloqueia.

## Aceite

`docs/PLANO_IA_E_PRODUTO.md` na forma do protocolo, com a separação
regra/modelo-local/modelo-remoto justificada item por item, estimativa de
custo com a aritmética à vista, formato do inventário com exemplo completo de
uma pasta, e o roadmap priorizado com a linha de corte do lançamento marcada.

Termine com as três decisões desta fase que o dono precisa aprovar antes de
qualquer implementação, cada uma em duas linhas.
