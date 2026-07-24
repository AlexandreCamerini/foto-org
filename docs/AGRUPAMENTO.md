# Modelo de agrupamento inteligente

Motivação (caso real): uma pasta `2026/Serena 15 Anos` com fotos de 4 horas
foi rotulada "Viagem de 09-05" — o motor v3 só olhava lacuna temporal.
O modelo v4 é uma cascata: **determinístico quando há informação; LLM como
apoio opt-in quando não há**. Nunca soma pontos: cada regra produz
evidências com origem e confiança próprias (docs/CONFIANCA.md).

## 1. Sessões (base temporal + transição casa↔fora)

Fotos são agrupadas em *sessões* por lacuna temporal (> 3 dias sem fotos
separa sessões — inalterado). Uma sessão ainda NÃO é uma viagem: é só um
cluster que precisa ser classificado.

Com casa conhecida, a sessão é adicionalmente cortada quando a linha do
tempo cruza o raio de casa (50 km, `raio_casa_km`): duas viagens com menos
de 3 dias em casa no meio deixavam o gap temporal cego
([viagem A][2 dias em casa][viagem B] virava uma sessão só). A transição
exige confirmação pela foto com GPS seguinte no mesmo estado — um frame
isolado (GPS errado, escala rápida perto de casa) não divide uma viagem
real. Sem GPS ou sem casa conhecida, nada muda.

## 2. Cascata determinística (por sessão, na ordem)

| # | Regra | Resultado | Origem/score |
|---|-------|-----------|--------------|
| 1 | Caminho contém pasta de categoria "Viagens" | VIAGEM | pasta 0.60 |
| 2 | Pasta com palavra-chave de evento (aniversário, "N anos", casamento, formatura, festa, natal, réveillon, batizado, show…) | EVENTO nomeado pela pasta | pasta 0.60 |
| 3 | País reconhecido no nome das pastas | VIAGEM | pasta 0.60 |
| 4 | GPS: distância mediana até "casa" > 100 km | VIAGEM | gps 0.85 |
| 5 | GPS geocodificado (país conhecido) E duração ≥ 3 dias E **casa desconhecida** | VIAGEM | geocoding 0.85 |
| 6 | Pasta com nome de álbum (não técnico) E duração ≤ 2 dias | EVENTO nomeado pela pasta | pasta 0.60 |
| 7 | Nada acima | NEUTRA → advisor LLM (opt-in) ou sem rótulo | llm 0.55 |

Definições:
- **Casa**: célula GPS modal do acervo (~11 km), exigindo ≥ 20 fotos com
  GPS e ≥ 30% delas na célula — senão "casa desconhecida" e a regra 4 não
  se aplica. (Acervos sem GPS, como RAW exportado, pulam direto.)
- **Duração**: fim − início da sessão. **Um cluster de horas nunca é
  viagem** — era o defeito original.
- **Nome de álbum**: segmento de pasta que não é técnico (datas
  `2025_05_24`, `[Originals]`, `RAW`, `exports`, `fotos`…), não é país,
  não é categoria. Ex.: "Quizomba", "Serena 15 Anos".
- Sem regra satisfeita, **não se inventa** viagem nem evento.

Consequências no destino:
- VIAGEM → campo `viagem` (país dominante ou período) + categoria Viagens.
  Viagem multi-país (≥ 2 países com ≥ 3 fotos geocodificadas cada) é
  nomeada pelas pernas em ordem cronológica de chegada — "Emirados Árabes
  – Tailândia – Vietnã" — em vez de só o país com mais fotos; a hierarquia
  região/cidade de cada foto continua refletindo a perna dela.
- EVENTO → campo `evento` + categoria Eventos; níveis geográficos
  (país/região/cidade) são suprimidos do destino — "Eventos/2026/Serena 15
  Anos", não ".../Serena 15 Anos/São Paulo".
- Template padrão: `{categoria}/{ano} - {viagem}/{evento}/{regiao}/{cidade}`.

## 2a. Correlação temporal entre fontes (lógica 4.1)

A câmera boa não grava GPS; o telefone grava. Antes da cascata, o motor
cruza as fontes (`grouping/correlacao.py`):

1. **Deriva de relógio** — a MESMA foto presente em duas fontes (mesmo
   hash rápido, ou mesmo phash quando o export recomprimiu) é um
   par-âncora; a mediana de (hora na fonte com GPS − hora na câmera) por
   câmera corrige relógio errado/fuso não ajustado. Âncoras dispersas
   (MAD > 3 min) ou insuficientes (< 2) são descartadas.
2. **Herança de GPS** — foto sem GPS herda a localização da foto com GPS
   de OUTRA origem (fonte ou câmera diferente) mais próxima na linha do
   tempo corrigida, janela ±10 min. Evidência `vizinhanca_temporal`
   (0.75×fator, fator 1.0 até Δt de 2 min decaindo a 0.6 na borda) com
   justificativa nomeando a doadora.

As coordenadas efetivas (próprias ou herdadas) alimentam a cascata
(regras 4/5), as pernas multi-país e a transição casa↔fora. "Casa" usa
só GPS real — herdadas repetiriam as doadoras e inflariam a célula.
Nada é escrito em EXIF; a herança existe apenas como evidência.

## 2b. Escolha do modelo (benchmark)

A cascata vive em `grouping/classifier.py` como função pura
parametrizável; `scripts/avaliar_agrupamento.py` compara variantes contra
cenários rotulados (incluindo os casos reais que motivaram o modelo) —
17 cenários em 2026-07-23, com D em 17/17. Cada erro real encontrado na
revisão deve virar um cenário novo ANTES de qualquer ajuste de regra.
Resultado original (2026-07-10, 16 cenários):

| Variante | Acertos | Erro típico |
|---|---|---|
| A — v4 original (estadia≥3d, sem exigir casa desconhecida) | 15/16 | férias EM CASA (6 dias de GPS a 2 km) viram "viagem" |
| B — estadia ≥ 2 dias | 15/16 | idem |
| C — álbum vira evento sem limite de duração | 14/16 | "Obra da casa" (10 dias) vira evento |
| **D — estadia só com casa desconhecida (adotada)** | **16/16** | — |
| E — D + estadia ≥ 2 dias | 16/16 | empate; D preferida por ser mais conservadora |

Com casa conhecida, quem decide deslocamento é a regra 4 (distância); a
regra 5 só cobre acervos sem GPS suficiente para saber onde é casa.

## 3. Advisor LLM (apoio, nunca decisão final)

`ClassificationAdvisor` (Protocol) é consultado APENAS para sessões
NEUTRAS, e apenas quando `[privacidade] servicos_externos = true` no
config.toml E a biblioteca `anthropic` está instalada (`pip install -e
".[llm]"`) E há credencial (`ANTHROPIC_API_KEY` ou perfil `ant auth`).

Privacidade (docs/PRIVACIDADE.md):
- **Só metadados** saem da máquina: nomes de pastas, amostra de nomes de
  arquivos, período, contagem e nomes de lugares já geocodificados.
  **Nunca a imagem.**
- Resultado vira evidência origem `llm`, nível MÉDIA-baixa (0.55) — abaixo
  de qualquer evidência determinística; sugestões continuam pendentes de
  revisão humana como sempre.
- `NullAdvisor` (padrão) não faz nada.

Implementação: `ClaudeAdvisor` usa o SDK oficial (`claude-opus-4-8`,
structured outputs com JSON Schema estrito). Falha de rede/recusa nunca
derruba a geração — a sessão simplesmente fica sem rótulo.
