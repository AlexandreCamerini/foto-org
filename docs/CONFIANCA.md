# Sistema de confiança

Toda inferência vira uma linha em `evidence` com: campo alvo, origem, valor,
nível (alta/média/baixa), score de referência, justificativa legível e versão
da lógica. Nada de somar pontos arbitrários (o score aditivo do protótipo v1
foi descartado por isso).

## Níveis por origem (tabela de referência)

| Origem da evidência                          | Nível  | Score ref. |
|----------------------------------------------|--------|-----------|
| Data EXIF (DateTimeOriginal) coerente        | Alta   | 0.95 |
| GPS EXIF válido                              | Alta   | 0.95 |
| Geocodificação reversa de GPS (offline)      | Alta   | 0.85 |
| Geocodificação reversa de GPS (serviço ext.) | Média  | 0.75 |
| GPS herdado de foto de outra fonte a minutos de distância (correlação temporal; score cai com o Δt) | Média | 0.75×fator |
| País/cidade extraído do nome da pasta        | Média  | 0.60 |
| Nome de álbum de catálogo externo que cobre o período (Apple Fotos, Lightroom) | Média | 0.55 |
| Local inferido de fotos vizinhas no tempo    | Média  | 0.55 |
| Categoria/evento sugerido por LLM (metadados, opt-in) | Média | 0.55 |
| Cidade/país/categoria de pasta sugeridos por LLM a partir do NOME da pasta (opt-in, GenAI de pasta, origem `llm_pasta`) | Média | 0.55 |
| Data do filesystem (sem EXIF)                | Baixa  | 0.40 |
| Cena/local sugerido só por análise visual    | Baixa  | 0.30 |
| Pessoa reconhecida automaticamente           | — sempre exige confirmação humana, nível derivado da similaridade |

Correção manual do usuário tem nível **alta (1.0)** e prevalece sobre tudo.

O nome de álbum fica **abaixo** do nome de pasta de propósito, embora as duas
sejam palavras que o dono escreveu: a foto *está* na pasta, e apenas *coincide
no tempo* com o álbum — 100% das nomeações deste acervo vivem em registros sem
arquivo local (D-030/D-034), então o vínculo é de contemporaneidade, da mesma
natureza da vizinhança temporal. Quem decide o desempate é
`docs/AGRUPAMENTO.md`, seção 2c.

`llm_pasta` (Cidade/país/categoria de pasta por LLM, opt-in) é o Claude
inferindo cidade/país/categoria a partir do NOME da pasta e do metadado já
catalogado, uma vez por sessão de pasta — nunca abre imagem, nunca sai da
máquina sem o consentimento próprio do recurso
(`classification/pasta_classificacao`, GENAI-03). NÃO é o advisor de cluster
(`llm`, 0.55 também, mas chave separada — lê metadado de mídia individual,
não nome de pasta) e NÃO é parse determinístico (`pasta`, 0.60 — segmento de
caminho já nomeia o lugar; aqui o modelo julga uma string ambígua como
"Praia 2019"). Score medido (D-081, 07-09) contra verdade determinística do
próprio catálogo: amostra pequena (4 pastas), zero erros observados nos dois
campos — categoria acertou 2/2, cidade/país recusou 2/2 (`null`,
comportamento seguro de D-06, não falha). Preliminar: revisitar quando a
base de medição crescer (ARCH-01, `.planning/STATE.md` § Blockers/Concerns).

## Regra de agregação (elo mais fraco)

Uma sugestão de destino é composta por campos do template (ex.:
`{categoria}/{ano}/{pais}/{cidade}`):

1. Cada campo usa a **melhor** evidência disponível para ele (maior score;
   empate resolvido pela ordem da tabela).
2. A confiança do campo é a dessa evidência.
3. A confiança da sugestão é a do **campo mais fraco** usado no destino.

Sem médias nem somas: uma cadeia é tão forte quanto seu elo mais fraco, e o
usuário vê exatamente qual campo puxou a confiança para baixo.

## Regras adicionais

- Evidências conflitantes para o mesmo campo: todas ficam registradas; a
  escolhida é marcada; o conflito aparece na UI como "precisa de confirmação".
- Sem evidência suficiente, o campo fica vazio — **nunca inventar** valor
  (em especial localização).
- `versao_logica` permite re-gerar sugestões quando a metodologia evoluir e
  auditar com qual regra cada sugestão foi produzida.
- Os scores de referência são configuráveis no futuro; os níveis (alta ≥0.8,
  média ≥0.5, baixa <0.5) são a interface estável com a UI (badges).
