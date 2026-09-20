# 10 — Verificação: como o reconstrutor sabe que terminou

> Parte do mapa de reconstrução. Critério de aceite por funcionalidade está no campo
> "Testes que provam" de cada item em `02-FUNCIONALIDADES.md`; este arquivo cobre o que é
> transversal: suítes, fixtures, baselines, contagens de superfície, invariantes → prova, e a
> verificação da própria spec.

## 1. O gate único: `scripts/verificar.sh`

Não faz commit nem altera arquivo; sai ≠ 0 se qualquer passo falhar. Quatro passos:

| # | Passo | Comando real | Verde significa |
|---|---|---|---|
| 1 | Testes do motor | `.venv/bin/python -m pytest -q --no-header` | 58 arquivos em `tests/`; em `524903d`: **966 passed**, 26 falhas/erros que são só sandbox (ver §6) |
| 2 | Benchmark de agrupamento | `.venv/bin/python scripts/avaliar_agrupamento.py` | linha `MELHOR: ... (N/N)` com **N = N** — hoje **19/19** (lista dos cenários em `11-DADOS_ESTATICOS.md`); nenhum cenário rotulado regride. Regra: erro novo vira cenário aqui **antes** de mexer em limiar (`docs/AGRUPAMENTO.md`) |
| 3 | Testes da UI | `cd webapp && npm test` (= `vitest run`, jsdom, setup em `webapp/src/test/setup.ts`) | 19 arquivos, **186 passed** |
| 4 | Build da UI | `cd webapp && npm run build` (= `tsc -b && vite build`) | `tsc` sem erro, `✓ built` |

`--rapido` pula 3 e 4 (só quando `node_modules` ausente ou npm indisponível). Pré-requisitos:
`.venv` via `scripts/instalar.sh`; `exiftool` no PATH (`brew install exiftool`) — sem ele os
testes de escrita EXIF **pulam em silêncio** (`08` M6); `cd webapp && npm install`; permissão
de `bind()` em 127.0.0.1 e leitura do CA bundle do sistema.

Não há CI. Uma reconstrução deve nascer com um workflow que rode o gate com exiftool instalado.

## 2. Fixtures — nunca foto real

- `tests/fixtures.py`: `make_jpeg(path, ..., gps=?, data=?)` gera JPEG sintético com EXIF
  (GPS em DMS via `_dms`), `make_png`, `make_corrupt_jpeg`. Tudo gerado em runtime em
  `tmp_path`.
- `tests/conftest.py`: `db_path(tmp_path)` e `migrated_engine(db_path)` — banco novo migrado
  até head por teste.
- Catálogo real **nunca** entra em teste. Medições contra o acervo usam cópia descartável ou
  `HOME` redirecionado (D-010) e `--data-dir`.
- Testes de escrita EXIF usam `make_jpeg` + exiftool real; sidecar é lido com
  `exiftool -G1 -n`.

## 3. Contagens de superfície (o reconstruído tem no mínimo isto)

| Superfície | Onde contar | Valor em `524903d` |
|---|---|---|
| Rotas FastAPI | `grep -c "@app\.\(get\|post\|put\|delete\|patch\)" fotoorganizer/server/app.py` | **62** decoradores / **59** paths únicos (GET+PUT no mesmo path contam 2) |
| Tabelas | `grep -rh "__tablename__ = " fotoorganizer/models/` (24) + `Table(` associativa `suggestion_evidence` (1) | **25** (+ `alembic_version`) |
| Migrações Alembic | `ls fotoorganizer/database/migrations/versions/*.py` | **20** (`0001_schema_inicial` … `0020_pasta_classificacoes_genai`) — schema recriável do zero com `upgrade_to_head()` (`test_database.py`) |
| Componentes React | `ls webapp/src/components/*.tsx \| grep -v test` | **21** |
| Subcomandos CLI | `grep -c "add_parser(" fotoorganizer/cli.py` | **12** |
| `Protocol`s substituíveis | `grep -rn "class .*(Protocol)" fotoorganizer/` | **9**: `MetadataExtractor` (`metadata/base.py:99`), `GeocodingProvider` (`geolocation/base.py:21`), `VisionProvider` (`vision/base.py:29`), `FaceRecognitionProvider` (`faces/base.py:26`), `ExternalCatalogProvider` (`sources/base.py:71`), `ClassificationAdvisor` (`classification/advisor.py:51`), `ClassificadorDePasta` (`location_advisor.py:84`), `ClassificadorDeNomes` (`lexico.py:110`), `KeyStore` (`security/crypto.py:26`). **`SyncProvider` é prometido em `CLAUDE.md` e não existe** (`AVALIACAO_ARQUITETURA.md` §7 risco 7) |
| Testes Python / TS | `ls tests/test_*.py \| wc -l` / `find webapp/src -name "*.test.ts*" \| wc -l` | **58 / 19** |
| Decisões registradas | `grep -c "^## D-" docs/DECISOES.md` | **81** |

## 4. Invariante → prova executável

| Inv. | O que provar | Onde está a prova hoje | Lacuna |
|---|---|---|---|
| 1 catalogação só leitura | scan não altera nenhum byte nem mtime das origens | `tests/test_scanner.py` (varredura dupla, retomada, corrompido) | adicionar assert de hash do diretório antes/depois |
| 2 dry-run obrigatório, copiar nunca mover | executar sem dry-run levanta; nenhum `move`/`rename` de origem | `tests/test_operations.py` (`DryRunObrigatorio`); `tests/test_exif_write_executor.py::test_executar_sem_dry_run_levanta`, `::test_dry_run_nao_escreve` | — |
| 3 nunca sobrescrever; hash pré/pós; audit | `open("xb")` recusa destino existente; hash divergente remove a cópia e marca erro; audit por item | `tests/test_operations.py` (sobrescrita bloqueada, `hash_pre == hash_pos`, cancelamento e retomada, inventário corrompido) | **A3**: ramo `hash_pos != hash_pre` sem teste |
| 4 nada sai por padrão; opt-in com prévia | payload do GenAI só com allowlist; gate `servicos_externos` False; nenhuma chamada sem opt-in | `tests/test_classification_pasta_genai.py::test_payload_nunca_envia_imagem`, `::test_modelo_e_thinking`; `tests/test_faces_privacy.py` | **M2**: teste não pega caminho absoluto — usar fixture `/Users/...` e proibir `/` |
| 5 subprocesso sem shell, caminhos validados, sem symlink | argumentos em lista; `paths.py` recusa traversal; discovery não segue symlink | `tests/test_security*.py`, `tests/test_scanner.py` (symlink/ciclo) — confirmar com `grep -rn "shell=True" fotoorganizer/` = 0 | — |
| 6 rosto off por padrão, local, cifrado | default False; `FileKeyStore` cifra/decifra | `tests/test_faces_privacy.py` | `KeychainKeyStore` sem teste (B5); provider é stub |
| 7 sem exclusão; EXIF só localização e só campo vazio; hash pré/pós; audit | nenhum `unlink` de original; campo preenchido é PULADO; tags fora de localização nunca escritas; backup só apagado após verificação | `test_exif_write_executor.py::test_dry_run_promove_campo_vazio_e_pula_preenchido`, `::test_nunca_escreve_fora_de_localizacao`, `::test_escreve_e_verifica_por_diff`, `::test_diff_detecta_falha_parcial`, `::test_backup_apagado_so_apos_sucesso_verificado`, `::test_sidecar_existente_nunca_e_sobrescrito`, `::test_executar_nao_regride_por_deslocamento_de_offset`; `test_exif_write_writer.py` | **A4** (TOCTOU direto), **A2** (valor do sidecar), **M8** (cancelamento) |
| 8 nada apagado, só rebaixado | nenhum `DELETE` em `media_files`; `papel` muda; sinal continua doando | `grep -rn "session.delete\|\.delete(" fotoorganizer/` só em tabelas derivadas (sugestões, grupos); `tests/test_reconciliacao.py` (ausente ≠ apagado) | — |

## 5. Baselines de performance (comparar, não projetar)

`docs/PERFORMANCE.md`, 2026-08-17, MacBook Pro M2 16 GB, 1.382 arquivos / 8,1 GB, schema
com índices de FK (migração 0018), `advisor=None`:

| Medida | Valor | Como reproduzir |
|---|---|---|
| Varredura | 59 arq/s (23,58 s) | `.venv/bin/python scripts/medir_baseline_producao.py --pasta "$HOME/Pictures/2026"` |
| Geração de sugestões | 1,33 s (1.382 sugestões, 2 eventos) | idem (em cópia descartável do catálogo) |
| Detecção de duplicatas | 4,54 s (13 visuais, 242 sequência) | idem |

Regras: medir antes de otimizar; motor e detector são full-scan (não escalar linearmente para
100 mil+); importadores Apple/Lightroom não entram nessa taxa; grade virtualizada, sem N+1,
sem imagem em resolução completa — requisitos, não otimizações. Já medido: 200 itens da grade
em 98 ms; contagem de 103.938 registros em 2 ms (`NAVEGACAO.md`).

## 6. Falhas de ambiente que não são defeito

Em sandbox sem rede/keychain: `tests/test_http_seguro.py` (23, `bind()` bloqueado),
`tests/test_web_launch.py::test_web_porta_efemera_anuncio_guard_e_shutdown` (subprocesso não
consegue `bind()`), `tests/test_apple_photos.py` (2, `osxphotos` → `requests` → CA bundle).
Rodar fora do sandbox ou isolar num job de CI com rede. **Confirmado em 2026-09-20:** os três arquivos rodados fora do sandbox → `45 passed in 9.47s`; gate real = 100% verde (pytest + benchmark 19/19 + vitest 186 + build).

## 7. O que a reconstrução precisa ADICIONAR de prova (hoje ausente)

1. `hash_pos != hash_pre` remove a cópia (A3).
2. Reconferência ao vivo no alvo direto entre dry-run e execução (A4).
3. Sidecar XMP: valor lido == valor pretendido, com sinal (A2).
4. Concorrência: 2+ POST simultâneos de executar → exatamente um job (A1), com `Barrier`.
5. Cancelamento ponta a ponta via `JobManager.cancelar()` em execução e em escrita EXIF (M8).
6. `skipif` de exiftool vira falha quando `FOTOORG_EXIGIR_EXIFTOOL=1` (M6).
7. ENOSPC (B6), `KeychainKeyStore` (B5), asserts reais em `test_migracao_e_idempotente` e
   `test_validar_campos_aceita_valores_validos` (B7).
8. Teste dedicado de `PhotoGrid.tsx` e `ClaudeAdvisor` (CONCERNS).
9. Base de tempo única: foto só-mtime a +3 h herda cidade da doadora a 5 min reais (M1/M5).

## 8. Verificação da própria spec (`docs/reconstrucao/`)

- **Checagem mecânica** (script em `10-VERIFICACAO.md` § anexo, rodado em 2026-09-19): toda
  rota de `app.py`, toda tabela, todo componente, todo subcomando e toda migração aparece em
  algum arquivo do mapa. Resultado registrado em `00-INDICE.md`.
- **Dry-run de reconstrução**: agente independente recebe só esta pasta e lista as perguntas
  que precisaria fazer e as contradições internas. Perguntas remanescentes ficam em
  `00-INDICE.md` § "Decisões em aberto para o reconstrutor" — nunca escondidas.
- Cada item de `02-FUNCIONALIDADES.md` tem os 10 campos do template preenchidos.

## 9. Checklist final de aceite da reconstrução

- [ ] `scripts/verificar.sh` verde com exiftool instalado e rede local liberada.
- [ ] Contagens da §3 iguais ou maiores; toda rota/tabela/tela/comando do mapa existe — **exceto**
  o que `09 §7` manda não carregar (endpoints órfãos, `http_seguro`), cuja decisão fica registrada
  em `00-INDICE` § Decisões em aberto (item 9/12).
- [ ] Tabela da §4 sem lacuna: os 9 itens da §7 implementados como teste.
- [ ] Os 8 invariantes têm pelo menos um teste que **falha** se o invariante for violado
  (mutation check manual: comentar a guarda, ver o teste cair).
- [ ] Baselines da §5 medidos no mesmo acervo e sem regressão > 10%.
- [ ] Payload de qualquer chamada externa visível ao dono antes do envio e idêntico ao enviado.
  GenAI de pasta já tem prévia na UI; o advisor de cluster hoje só tem o gate (`jobs.py:335`) — a
  reconstrução adiciona a prévia (`09 §3` item 9) ou registra a exceção como decisão.
- [ ] Nenhum `DELETE` de mídia, nenhum `move`, nenhum `shell=True`, nenhum tile externo.
- [ ] `docs/DECISOES.md` preservado e apontado pelo código onde a regra é não-óbvia.

## Anexo — script de checagem de cobertura do mapa

```python
# checar_cobertura_mapa.py — read-only; roda da raiz do repo
import re, glob, pathlib
raiz = pathlib.Path(".")
mapa = "\n".join(pathlib.Path(p).read_text() for p in sorted(glob.glob("docs/reconstrucao/*.md")))
norm = lambda s: re.sub(r"\{[^}]+\}", "{id}", s)   # {plan_id} ≡ {id} ≡ {suggestion_id}
mapa_n = norm(mapa)
def faltam(nomes, rotulo, alvo=None):
    alvo = mapa if alvo is None else alvo
    f = [n for n in nomes if n not in alvo]
    print(f"{rotulo}: {len(nomes)} no código, {len(f)} ausentes no mapa", f or "")
app = (raiz/"fotoorganizer/server/app.py").read_text()
decor = re.findall(r'@app\.(?:get|post|put|delete|patch)\("([^"]+)"', app)
print(f"rotas: {len(decor)} decoradores, {len(set(decor))} paths únicos")
faltam(sorted({norm(p) for p in decor}), "rotas (paths únicos, {x}→{id})", mapa_n)
models = "\n".join(p.read_text() for p in raiz.glob("fotoorganizer/models/*.py"))
tabs = set(re.findall(r'__tablename__ = "([^"]+)"', models)) | set(re.findall(r'^(\w+) = Table\(', models, re.M))
faltam(sorted(tabs), "tabelas")
faltam(sorted(p.stem for p in raiz.glob("webapp/src/components/*.tsx") if ".test" not in p.name), "componentes")
faltam(sorted(set(re.findall(r'add_parser\(\s*"([^"]+)"', (raiz/"fotoorganizer/cli.py").read_text()))), "cli")
migs = sorted(p.stem for p in raiz.glob("fotoorganizer/database/migrations/versions/*.py"))
faltam([m[:4] for m in migs], "migracoes (por número)", re.sub(r"\s+", " ", mapa))
```
