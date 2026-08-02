# Fase 10 — template de destino configurável na UI

Item 4 do backlog (`docs/ROADMAP.md`). Esforço S: motor já aceita template
arbitrário; falta onde digitar.

## O que existe hoje

- `fotoorganizer/classification/templates.py::TEMPLATE_PADRAO =
  "{categoria}/{ano} - {viagem}/{evento}/{pais}/{regiao}/{cidade}"` e
  `render_destino(template, campos) -> str`, função pura já testada
  (`tests/test_templates.py` — conferir nome exato do arquivo de teste
  existente antes de duplicar cobertura).
- `SuggestionEngine.__init__` (`fotoorganizer/classification/engine.py:221`)
  recebe `template: str = TEMPLATE_PADRAO` e usa em `render_destino` na
  linha ~976. Cada `Suggestion` grava o template usado
  (`Suggestion.template`, linha ~1001).
- Placeholders válidos hoje, todos opcionais e descartados em cascata se
  vazios (ver docstring de `templates.py`): `{categoria}` `{ano}`
  `{viagem}` `{evento}` `{pais}` `{regiao}` `{cidade}`. Não inventar
  placeholder novo nesta fase.
- `fotoorganizer/models/settings.py::ApplicationSetting` — tabela
  `application_settings` (chave PK + valor JSON), já migrada
  (`0001_schema_inicial.py`), **zero uso hoje** em repositório, API ou
  webapp. É o lugar certo para persistir "qual template o usuário
  escolheu" — não criar tabela nova, não usar `config.toml` (esse é
  editado à mão pelo usuário, não pela UI, ver comentário na própria
  classe).
- `fotoorganizer/server/jobs.py:175-184` — `_rodar_sugestoes` instancia
  `SuggestionEngine(self._factory, LocationResolver(...), advisor=...)`
  sem passar `template`, então hoje sempre usa `TEMPLATE_PADRAO`. É aqui
  que o valor persistido precisa entrar.
- `POST /api/sugestoes/gerar` (`fotoorganizer/server/app.py:840`) já
  dispara `jobs.iniciar_sugestoes()` — é o mecanismo de regeneração que já
  existe; não criar rota nova para "regenerar".
- Webapp: não existe `Configurações`/`Settings` como aba (`ABAS` em
  `webapp/src/App.tsx:21`); a aba mais próxima em espírito é "Operações"
  (`webapp/src/components/Operations.tsx`), que é onde o template passa a
  valer no disco. Não existe hoje nenhuma referência a "template" em
  `webapp/src/`.

## O que fazer

### Backend (`fotoorganizer/`)

1. Repositório mínimo para `ApplicationSetting` — get/set por chave
   (`repositories/`, seguindo o padrão de uma classe por agregado já usado
   no projeto). Chave sugerida: `"template_destino"`, valor = string do
   template.
2. Endpoints REST:
   - `GET /api/configuracoes/template` → `{ "template": str }` (devolve
     `TEMPLATE_PADRAO` se não houver linha salva — nunca 404 por ausência
     de preferência).
   - `PUT /api/configuracoes/template` com body `{ "template": str }` →
     valida antes de salvar: template tem que conter só placeholders da
     lista válida (rejeitar com 422 e mensagem clara se tiver
     `{qualquer_outra_coisa}`), e não pode ser vazio. Salvar. **Não**
     regenerar sugestões automaticamente aqui — é ação explícita separada
     (evita surpresa: trocar o texto no editor não deveria disparar um job
     pesado a cada tecla).
   - `POST /api/configuracoes/template/preview` (ou GET com query) com
     body de campos de exemplo fixos no backend (ex.: um conjunto sintético
     representativo: categoria="Viagens", ano="2024", viagem="Tailândia",
     evento=None, pais="Tailândia", regiao=None, cidade="Chiang Mai" — e um
     segundo exemplo sem viagem/evento para mostrar o fallback por
     país/região/cidade) → devolve os destinos renderizados chamando
     `render_destino` de verdade, não reimplementação no frontend. Motivo:
     `render_destino` tem regras não triviais (dedupe de valor repetido,
     normalização, colapso de segmento vazio) — reimplementar no
     TypeScript diverge da fonte da verdade na primeira mudança de regra.
3. `jobs.py::_rodar_sugestoes` passa a ler o template salvo (via o
   repositório novo) e passá-lo para `SuggestionEngine(template=...)`. Se
   não houver preferência salva, cai no default atual (comportamento
   idêntico a hoje).
4. Testes: repositório (get default, set, get depois de set), validação de
   placeholder inválido (422), preview usando o `render_destino` real,
   `jobs` usando o template persistido ao gerar sugestões.

### Webapp (`webapp/`)

5. Editor de template dentro da aba **Operações** (não criar aba nova —
   é a única tela sobre "como o destino é decidido no disco", e ganhar uma
   sétima aba para uma única linha de texto pesa mais do que ajuda). Um
   painel/seção no topo, recolhível ou não conforme o espaço disponível
   sem brigar com a lista de planos que já existe ali.
6. Campo de texto para o template + lista visível dos placeholders válidos
   (o usuário não vai adivinhar `{regiao}` vs `{região}`) + preview ao
   vivo chamando o endpoint de preview (debounce — não uma requisição por
   tecla).
7. Botão "Salvar" (PUT) separado de qualquer ação de regenerar. Depois de
   salvar, oferecer explicitamente "regenerar sugestões pendentes com o
   novo template" (chama `POST /api/sugestoes/gerar`, que já existe) como
   ação distinta, com aviso de que isso substitui sugestões pendentes
   ainda não aprovadas (o comportamento já existente do job: relê
   `Suggestion.status == PENDENTE` e recria — sugestões já aprovadas ou
   com destino editado manualmente não são tocadas, confirmar isso lendo
   `_persistir_sugestao`).
8. Estado de erro do PUT (template com placeholder inválido) mostrado
   inline, sem travar o campo de texto.
9. `webapp/src/api.ts`: tipos e funções para os três endpoints, seguindo o
   padrão dos outros métodos do objeto `api`.
10. Testes (`webapp/src/components/Operations.test.tsx` ou arquivo próprio
    se ficar grande): editor mostra template atual, preview atualiza,
    salvar chama PUT, placeholder inválido mostra erro, regenerar chama
    `/api/sugestoes/gerar`.

## Fora de escopo nesta fase

- Múltiplos templates nomeados/perfis — só existe UM template ativo por
  catálogo, como hoje.
- Editor visual de arrastar-placeholder — campo de texto simples com a
  lista de placeholders ao lado é suficiente para o esforço S orçado.
- Mudar quais placeholders existem, ou a lógica de `render_destino` —
  fora de escopo, é motor já pronto e testado.

## Aceite

- `PUT` com template usando `{fantasia}` (placeholder inexistente) rejeita
  com 422 e mensagem, não salva nada.
- Trocar o template e clicar "salvar" persiste entre reinícios do
  servidor (linha em `application_settings`).
- Preview no editor bate exatamente com o que `render_destino` produziria
  para os mesmos campos (mesma função, não reimplementação).
- Gerar sugestões depois de trocar o template usa o template novo (medir:
  `Suggestion.template` das sugestões recém-geradas == template salvo).
- `scripts/verificar.sh` verde.
