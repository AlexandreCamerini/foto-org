# Itens fora de escopo — 07-classifica-o-de-pasta-por-genai

Descobertas durante a execução que NÃO foram corrigidas por estarem fora do
escopo do arquivo/task em execução (ver `deviation_rules` — SCOPE BOUNDARY).

## 1. Evidence espúria: `campo="categoria"` com `origem="geocoding_offline"`

**Encontrado durante:** 07-09 Task 1 (`scripts/medir_score_llm_pasta.py`),
ao construir a amostra de verdade determinística.

**O quê:** o catálogo de produção tem 13 linhas em `evidence` com
`campo='categoria'` e `origem='geocoding_offline'` (todas com
`valor='Viagens'`), concentradas em duas pastas:
`/Volumes/Externo/Fotos/Do Peru ao Chile` (12 linhas) e
`/Users/acamerini/Desktop/teste-exif` (1 linha).

`fotoorganizer/classification/engine.py::_categoria` (lido nesta sessão,
07-09 Task 1) NÃO tem nenhum caminho que escreva `categoria` com
`origem="geocoding_offline"` hoje — as origens possíveis para `categoria`
são `pasta`, `sessao.origem` (`gps`/`agrupamento`/`llm`), `curadoria`,
`llm_pasta`. Isso sugere uma versão anterior da lógica (ou um outro módulo
já removido) escreveu essas linhas, e elas nunca foram limpas do catálogo
(`versao_logica` deveria permitir auditar isso, mas não foi investigado
aqui — fora do escopo desta task).

**Efeito observado:** nas duas pastas acima, a evidência espúria
(`geocoding_offline` → `Viagens`) CONFLITA com a evidência legítima
(`pasta` → `Eventos`, do segmento explícito do caminho). O script de
medição (07-09 Task 1) exige unanimidade entre origens determinísticas
antes de aceitar um valor como "verdade" — por isso essas duas pastas
foram corretamente EXCLUÍDAS da amostra de medição (comportamento
desejado: dado ambíguo não vira verdade nenhuma), mas isso reduz a amostra
de categoria de 4 para 2 pastas nesta base pequena (~1.400 arquivos,
STATE.md § Blockers).

**Por que não foi corrigido aqui:** `fotoorganizer/classification/engine.py`
não está nos `files_modified` de 07-09 Task 1 (só
`scripts/medir_score_llm_pasta.py`). Investigar a origem da escrita
espúria e decidir se é dado legado a limpar ou um bug ativo a corrigir é
trabalho de outra task/plano — não Rule 1/2/3 (não bloqueia a Task 1, que
lida corretamente com a ambiguidade por design).

**Sugestão para o dono:** ao revisar o relatório real da Task 2, checar se
essas duas pastas aparecem excluídas da amostra por este motivo (o
`--dry-run --limite 200` mostra só 4 pastas no total, 2 de categoria) —
se a amostra parecer pequena demais, esta é uma causa concreta e vale
decidir separadamente se as 13 linhas espúrias devem ser apagadas do
catálogo (não é exclusão de arquivo real, é limpeza de linha de evidência
órfã — não esbarra na invariante 8).
