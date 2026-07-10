# Modelo de agrupamento inteligente

Motivação (caso real): uma pasta `2026/Serena 15 Anos` com fotos de 4 horas
foi rotulada "Viagem de 09-05" — o motor v3 só olhava lacuna temporal.
O modelo v4 é uma cascata: **determinístico quando há informação; LLM como
apoio opt-in quando não há**. Nunca soma pontos: cada regra produz
evidências com origem e confiança próprias (docs/CONFIANCA.md).

## 1. Sessões (base temporal)

Fotos são agrupadas em *sessões* por lacuna temporal (> 3 dias sem fotos
separa sessões — inalterado). Uma sessão ainda NÃO é uma viagem: é só um
cluster que precisa ser classificado.

## 2. Cascata determinística (por sessão, na ordem)

| # | Regra | Resultado | Origem/score |
|---|-------|-----------|--------------|
| 1 | Caminho contém pasta de categoria "Viagens" | VIAGEM | pasta 0.60 |
| 2 | Pasta com palavra-chave de evento (aniversário, "N anos", casamento, formatura, festa, natal, réveillon, batizado, show…) | EVENTO nomeado pela pasta | pasta 0.60 |
| 3 | País reconhecido no nome das pastas | VIAGEM | pasta 0.60 |
| 4 | GPS: distância mediana até "casa" > 100 km | VIAGEM | gps 0.85 |
| 5 | GPS geocodificado (país conhecido) E duração ≥ 3 dias | VIAGEM | geocoding 0.85 |
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
- EVENTO → campo `evento` + categoria Eventos; níveis geográficos
  (país/região/cidade) são suprimidos do destino — "Eventos/2026/Serena 15
  Anos", não ".../Serena 15 Anos/São Paulo".
- Template padrão: `{categoria}/{ano} - {viagem}/{evento}/{regiao}/{cidade}`.

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
