# Cobertura de metadados — o que os arquivos realmente têm

Medido com `scripts/cobertura_metadados.py` (somente leitura, nenhum
catálogo escrito) sobre **300 arquivos** amostrados de forma estratificada
por pasta em `Dubai, Thai & Viet`, `Estrada Real` e `2025_05_24`.
Composição: 103 JPG, 99 CR3, 96 DNG, 2 HIF. Semente fixa — a mesma amostra
é reproduzível.

## Antes e depois

| Campo | Vazios antes | Vazios depois |
|---|---:|---:|
| data_capturada | 0 (0%) | 0 (0%) |
| largura / altura | 0 (0%) | 0 (0%) |
| **lente** | **195 (65%)** | **0 (0%)** |
| **orientacao** | **195 (65%)** | **0 (0%)** |
| make / model | 99 (33%) | 99 (33%) |
| gps_lat | 300 (100%) | 300 (100%) |

## O que a medição mandou fazer

**Lente e orientação: resolvido.** Os 195 vazios eram exatamente os 195
arquivos RAW. O `exifread` só lê contêineres TIFF/IFD, e o CR3 é ISO-BMFF —
mas o `libraw` expõe `raw.lens.model` e `raw.sizes.flip` em qualquer RAW.
A rotação vem no vocabulário do dcraw e é convertida para o da EXIF
(`0→1, 3→3, 5→8, 6→6`); `flip = -1` significa "não sei" e vira `None`, não
"sem rotação".

**make/model no CR3: deixado em branco de propósito.** São os 99 CR3. O
`libraw` não expõe o fabricante, e o único sinal disponível seria deduzir
"Canon" do prefixo `EF` da lente. Isso é adivinhação, e adivinhação que
entra no catálogo como se fosse leitura de arquivo contamina o modelo de
evidências (docs/CONFIANCA.md).

## O achado que muda a estratégia

**Nenhuma das 300 fotos tem coordenada.** Não é falha de leitura: os JPGs
trazem o bloco GPS da EXIF presente e *vazio* — só `GPSVersionID`, sem
latitude nem longitude. A câmera escreve o compartimento e não preenche.

A consequência é que **ampliar a extração de EXIF nunca vai dar localização
para este acervo.** Câmeras dedicadas sem GPS não gravam onde a foto foi
tirada, e é disso que o acervo é feito. Os caminhos que restam para
localizar uma foto são dois, ambos já construídos:

1. **Correlação entre fontes** (`grouping/correlacao.py`): fotos de celular
   tiradas nos mesmos minutos *têm* GPS, e a herança por proximidade
   temporal (±10 min, com correção de deriva de relógio) transfere a
   coordenada como evidência rastreável. Depende de o usuário importar
   Apple Fotos ou Google Takeout.
2. **Nome de pasta** (`classification/`), que já é usado e responde com
   confiança média.

Ou seja: o gargalo de localização deste acervo é de **importação de
fontes**, não de extração. É isso que a lacuna "sem coordenada" no
Panorama deve levar o usuário a fazer.

## Como refazer a medição

```sh
.venv/bin/python scripts/cobertura_metadados.py ~/Pictures/<pasta> -n 300
```

Rode antes de propor qualquer ampliação de extração. Campo que já vem
cheio não precisa de código novo, e campo que o arquivo não tem não se
resolve com código nenhum.
