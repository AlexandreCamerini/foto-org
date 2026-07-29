# Protocolo das fases de avaliação — autonomia, evidência e registro

Leia este arquivo antes de executar qualquer prompt `fase-N-*.md`. Ele vale
para todas as fases; os prompts de fase não repetem estas regras.

## Autonomia

O dono do produto pode não estar acompanhando. Decida sozinho e siga — o que
importa é que a decisão fique registrada e reversível, não que ela espere.

Três classes de decisão:

**Classe A — decida e registre, sem avisar.** Escolha de formato, ordem de
investigação, qual biblioteca medir primeiro, como estruturar um documento,
qual amostra usar, nomes de arquivos e de colunas propostas. Registre em
`docs/DECISOES.md` e continue.

**Classe B — avise, recomende, siga em 10 minutos.** Decisão que muda o
desenho do produto ou o esforço de forma material: modelo de dados
concorrente, dependência externa nova, mudança de escopo de uma fase,
trade-off de privacidade, custo recorrente. Procedimento:

1. Escreva a decisão em `docs/DECISOES.md` com as opções, a recomendada e o
   porquê.
2. Dispare uma notificação (`PushNotification`) de uma linha: o que está em
   jogo e qual é a recomendação.
3. Continue trabalhando no que não depende da resposta.
4. Passados 10 minutos sem resposta, siga com a recomendada, marque no
   registro `decidido por timeout` e siga em frente. Não pare a fase.

**Classe C — sempre espera, mesmo depois dos 10 minutos.** O timeout não se
aplica a ação difícil de reverter ou de efeito externo:

- escrever, mover, renomear ou apagar qualquer arquivo original de foto;
- rodar operação física fora de dry-run;
- apagar ou reescrever `~/Library/Application Support/FotoOrganizer/catalog.db`;
- `git push`, abrir PR, publicar qualquer coisa;
- enviar qualquer dado do acervo para fora da máquina, inclusive para API de
  IA, mesmo em teste;
- instalar dependência de sistema (por exemplo `exiftool`) no ambiente do
  dono.

Nessas, descreva o que faria, deixe pronto o comando ou o plano, e siga com
o resto da fase. Um bloqueio de classe C nunca é motivo para parar o
trabalho restante.

## Registro de decisões — `docs/DECISOES.md`

Uma entrada por decisão, em ordem cronológica, no formato:

```
## D-007 — Título curto da decisão
- Fase: 3
- Classe: B
- Data: 2026-07-29
- Contexto: por que a decisão apareceu, em duas linhas.
- Opções: (a) …  (b) …  (c) …
- Escolhida: (b)
- Por quê: o critério que decidiu, não a lista de vantagens.
- Como reverter: o que exatamente desfaz isso.
- Status: decidido | decidido por timeout | aguardando (classe C)
```

O registro é o entregável que torna a autonomia aceitável. Uma fase sem
decisões registradas é suspeita: significa que nada foi escolhido ou que as
escolhas ficaram invisíveis.

## Evidência

Toda afirmação sobre o estado atual do sistema aponta para uma das quatro:
`arquivo:linha`, saída de comando colada, resultado de teste, ou captura de
tela em `docs/prototipos/` ou `docs/capturas/`.

Onde faltar evidência, escreva **"não verificado"** e siga. Isso é uma
resposta aceitável e melhor que uma suposição apresentada como leitura.

Números vêm de medição, não de estimativa. Se não deu para medir, diga o que
faltou para medir.

## Fronteira do que pode ser alterado

Enquanto o dono não aprovar o plano da fase 5:

- **Pode criar e alterar:** `docs/**`, `docs/prototipos/**`,
  `docs/capturas/**`, `scripts/medir_*.py` (scripts de medição novos,
  somente leitura sobre o acervo).
- **Não altera:** `fotoorganizer/**`, `webapp/src/**`, migrações Alembic,
  `pyproject.toml`, `CLAUDE.md`.

Bug encontrado durante o diagnóstico entra no relatório com `arquivo:linha` e
o efeito observado — não vira correção nesta rodada.

## Forma de cada fase

Cada fase segue a mesma espinha, na ordem:

1. **Requisitos** — o que o produto precisa que isto faça (funcional) e sob
   que restrição de escala, latência, custo e privacidade.
2. **Estado atual** — o que existe, com evidência.
3. **Desenho proposto** — componentes, fluxo de dados, contratos, esquema.
4. **Escala e confiabilidade** — o que acontece em 500 mil arquivos, o que
   falha primeiro, o que é observável.
5. **Trade-offs** — cada escolha com o que se ganha e o que se perde. Sem
   trade-off declarado, a recomendação não está pronta.
6. **O que eu revisitaria** — o que muda de resposta quando o acervo, o
   número de dispositivos ou o número de usuários crescer.

Diagramas em ASCII, dentro do documento. Sem imagem gerada por ferramenta
externa.

## Execução

- Cada fase é autônoma: roda em sessão limpa, lendo só este protocolo, o
  prompt da fase e os documentos que o prompt indica.
- No máximo 2 subagentes por fase, e só para varredura ampla e independente.
  Leitura pontual e verificação você faz direto — subagente que relê o que
  você já leu custa e não acrescenta.
- Fim de fase: o documento existe, `docs/DECISOES.md` tem as entradas da
  fase, e há um commit convencional em português com os dois.
- Fases são independentes. Se uma travar, registre o bloqueio e siga para a
  próxima.

## Lentes que valem em todas as fases

**Invariantes como piso de produto.** Os seis invariantes do `CLAUDE.md` não
são obstáculo a contornar na comercialização — são a proposta de valor de um
DAM local-first. Qualquer proposta de nuvem, IA externa ou sync diz como os
respeita.

**Aprovação humana antes de ação externa.** Nada que altere arquivo do
usuário ou saia da máquina acontece sem gate explícito, inclusive em
automação e agendamento.

**Determinismo antes de modelo.** Onde uma regra sobre metadados resolve, a
regra ganha: é auditável, reproduzível e de graça. Modelo entra onde a regra
não alcança, e entra como evidência com confiança e justificativa — nunca
como decisão automática.

**Imagem é linguagem.** Trabalho visual se avalia por captura de tela, não
por descrição de captura de tela.
