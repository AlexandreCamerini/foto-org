# Fase 2 — Auditoria de funcionalidades

Leia `docs/prompts/00-protocolo.md` primeiro. Entregável:
`docs/AUDITORIA_FUNCIONALIDADES.md`.

A percepção do dono é que muitas funcionalidades não funcionam de ponta a
ponta. Confirme ou refute por execução real. Leitura de código não fecha um
item desta fase.

## Inventário

Levante a lista de funcionalidades declaradas, de quatro fontes:

1. `docs/ROADMAP.md`, milestones M0–M7 (marcados como concluídos).
2. Comandos de `fotoorganizer/cli.py`.
3. Endpoints de `fotoorganizer/server/`.
4. Telas e ações de `webapp/src/components/`.

## Classificação

Uma linha por funcionalidade:

| Estado | Critério |
|---|---|
| Funciona | exercitada de ponta a ponta, com evidência anexada |
| Parcial | núcleo roda, falta caminho de UI, persistência ou caso de borda |
| Órfã | código existe, tem teste, e nada no fluxo real chama |
| Quebrada | falhou ao ser exercitada — cole o erro |
| Ausente | prometida em documento, sem implementação |

"Órfã" é a categoria que explica a percepção do dono e a que leitura de
código sozinha não detecta: o teste passa, a função está correta, e nenhum
caminho de usuário chega até ela. Para cada candidata, procure quem a chama
partindo da UI ou do CLI, não do teste.

## Execução

Ambiente de trabalho, sem tocar no acervo nem no catálogo real:

1. `pytest` e `scripts/verificar.sh` — cole o resumo, e a falha inteira se
   houver.
2. `scripts/gerar_demo.py` para dados sintéticos.
3. Suba o servidor local e o webapp; exercite cada tela com os dados de
   demonstração; capture em `docs/capturas/`.
4. Para cada funcionalidade de backend sem tela, exercite pelo CLI ou pelo
   endpoint e cole a saída.

Se o catálogo real for necessário para algum item, isso é classe C do
protocolo: descreva o que faria e siga.

## Dois pontos com verificação obrigatória

Ambos parecem prontos no código e podem não estar no fluxo:

**Herança de GPS entre fontes.** `fotoorganizer/grouping/correlacao.py`
implementa doação de coordenada entre dispositivos com correção de deriva de
relógio, e `fotoorganizer/classification/engine.py:209` consome. Determine:
o resultado é persistido ou vive só em memória durante a sugestão? aparece na
UI? aparece no inventário de uma pasta organizada? sobrevive a reiniciar o
app? Responda com evidência — este é o insumo da fase 4.

**Namespaces de metadados.** A tabela `metadata_entries` declara
`exif | iptc | xmp | fs` (`fotoorganizer/models/catalog.py:133`) e é gravada
em `scanner/scanner.py:338` e `sources/importer.py:295`, com o que o extrator
devolver em `meta.extras`. Meça, num catálogo de demonstração e num
representativo se possível: quais namespaces têm linhas, quantas tags por
arquivo, e quantas por formato (JPG, CR3, DNG, HIF). Este é o insumo da
fase 3.

## Aceite

`docs/AUDITORIA_FUNCIONALIDADES.md` com:

- tabela completa do inventário, com estado, evidência e esforço estimado
  para fechar o que não está em "Funciona";
- as duas verificações obrigatórias respondidas com evidência;
- a lista ordenada por impacto no usuário — não por facilidade de correção;
- uma seção "o que a auditoria contradiz" com o que o ROADMAP declara
  concluído e a execução não sustenta.
