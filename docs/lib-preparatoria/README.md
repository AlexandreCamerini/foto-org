# Lib preparatória — fase 14 + roadmap item 5

Staging fora da fronteira de `fotoorganizer/**`/`webapp/src/**`, enquanto o
dono não aprova o plano da fase 5 (`docs/prompts/00-protocolo.md:80-88`).
Cada subdiretório é um item independente, pronto para integrar quando a
fronteira abrir: `lib.py` (reimplementação), `test_lib.py` (cobertura) e
`README.md` (evidência do estado atual, decisões e ponto exato de
integração, com `arquivo:linha` real).

- `filtro-proveniencia/` — Item A da fase 14.
- `protecao-julgamento/` — Item B da fase 14.
- `deteccao-sidecar-xmp/` — Item C da fase 14.
- `timezone-por-pais/` — Item D, item 5 de "Próximas versões" em
  `docs/ROADMAP.md` (100% foto-organizer, sem restrição de licença).

Registro completo em `docs/DECISOES.md` (D-045).

## Rodar os testes

Cada item é um par `lib.py`/`test_lib.py` autocontido, sem `__init__.py`
nem pacote compartilhado — de propósito, para cada item poder ser copiado
isoladamente quando integrar. Rode **um item por vez**:

```bash
pytest docs/lib-preparatoria/filtro-proveniencia/test_lib.py -v
pytest docs/lib-preparatoria/protecao-julgamento/test_lib.py -v
pytest docs/lib-preparatoria/deteccao-sidecar-xmp/test_lib.py -v
pytest docs/lib-preparatoria/timezone-por-pais/test_lib.py -v
```

Coletar os quatro `test_lib.py` numa única invocação
(`pytest docs/lib-preparatoria/*/test_lib.py`) falha na coleta — os quatro
arquivos têm o MESMO nome (`test_lib.py`) e nenhum pacote (`__init__.py`)
os distingue, então o pytest confunde os módulos entre si. Isso é um
efeito do modo de import padrão do pytest com nomes de arquivo repetidos,
não um problema no código: cada item passa 100% quando rodado sozinho (97
testes no total — 34+24+22+17), que é como o critério de aceite do prompt
de origem pede.

## Restrição de licença

PhotoPrism e Immich, os dois projetos de referência lidos para os itens da
fase 14, são AGPLv3. Nenhuma linha em `docs/lib-preparatoria/` vem de abrir
os repositórios locais desses projetos — só da descrição de mecanismo já
registrada em `docs/referencia-photoprism/` e `docs/referencia-immich/`, e
do schema real do foto-organizer. A checagem de contaminação usada nesta
tarefa (busca pelos caminhos locais dos dois repositórios dentro de
`docs/lib-preparatoria/`) e o resultado dela estão registrados em D-045,
`docs/DECISOES.md`.
