# Organizador de Fotos

Varre diretórios de fotos no seu Mac, cataloga metadados, detecta duplicatas
(exatas e visualmente parecidas), e sugere agrupamento por viagem/país/
região/cidade a partir do nome das pastas e da linha do tempo das fotos.

## Stack

Backend FastAPI + SQLAlchemy, banco SQLite local (`database/fotos.db`),
frontend Streamlit. Tudo local — sem deploy, sem conta, sem API externa.

## Como rodar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Terminal 1 — backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd streamlit_app && streamlit run app.py
```

Abra o Streamlit (endereço que ele imprime, normalmente
http://localhost:8501), cole o caminho de uma ou mais pastas na aba
"Varrer pastas" e clique em "Varrer agora".

## Estrutura

```
backend/app/
  main.py          endpoints FastAPI (POST /scan, GET /photos|duplicates|suggestions)
  models.py        tabela `photos` (SQLAlchemy)
  database.py      engine/sessão SQLite
  scanner.py       varredura de diretório + hash md5/perceptual + EXIF
  duplicates.py    detecção de duplicatas exatas e visuais
  suggestions.py   hierarquia geográfica (nome de pasta) + agrupamento por viagem
  geo_data.py      lista estática de países (PT/EN) pra reconhecer pastas
streamlit_app/app.py  interface (varrer, ver fotos, duplicatas, sugestões)
database/             fotos.db vive aqui (não versionado)
```

## Como funciona a detecção de duplicatas

- **Exata**: mesmo hash MD5 do arquivo (bytes idênticos).
- **Visual**: hash perceptual (`imagehash.phash`) com distância de Hamming
  ≤ 8 — pega fotos reexportadas/comprimidas que não são bit-a-bit iguais.

Cada grupo de duplicatas reporta quanto espaço em disco dá pra economizar
mantendo só a maior cópia.

## Como funciona a sugestão de agrupamento

1. **Hierarquia geográfica**: os segmentos do caminho da pasta são
   comparados contra uma lista de países conhecidos (`geo_data.py`). Se
   `.../Viagens/Japão/Tóquio/foto.jpg` bate com "Japão", o resto do caminho
   vira região/cidade.
2. **Viagem**: as fotos são ordenadas por data (EXIF, ou data do arquivo se
   não tiver EXIF) e agrupadas — uma lacuna de mais de 3 dias sem foto
   nenhuma marca o início de uma viagem nova.
3. **Score de confiança** (0 a 1): soma pontos por sinal encontrado — país
   reconhecido na pasta (+0.4), cidade específica (+0.2), data EXIF real
   (+0.2), GPS no EXIF (+0.2).

## Limitações conhecidas (v1)

- HEIC/HEIF (formato padrão do iPhone) é suportado via `pillow-heif`
  (já em `requirements.txt`) — se essa lib não estiver instalada, o scanner
  ignora `.heic`/`.heif` silenciosamente em vez de quebrar.
- Lista de países é estática, não geocodifica coordenadas GPS pra
  nome de lugar (`localizacao_exif` fica como "lat,lon" cru).
- `/scan` é síncrono — coleções muito grandes (milhares de fotos) vão
  demorar, porque calcula hash de cada arquivo na hora.
