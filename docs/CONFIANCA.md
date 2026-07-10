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
| País/cidade extraído do nome da pasta        | Média  | 0.60 |
| Local inferido de fotos vizinhas no tempo    | Média  | 0.55 |
| Categoria/evento sugerido por LLM (metadados, opt-in) | Média | 0.55 |
| Data do filesystem (sem EXIF)                | Baixa  | 0.40 |
| Cena/local sugerido só por análise visual    | Baixa  | 0.30 |
| Pessoa reconhecida automaticamente           | — sempre exige confirmação humana, nível derivado da similaridade |

Correção manual do usuário tem nível **alta (1.0)** e prevalece sobre tudo.

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
