---
name: fatia-vertical
description: "Implementa uma fatia vertical do Foto Organizer (dado → lógica → UI) com verificação e commit, seguindo o método do projeto"
---

# Fatia vertical

Workflow padrão de entrega deste projeto: incremento pequeno e completo,
testado e commitado. Use para qualquer mudança de comportamento — não use
para pergunta, leitura de código ou ajuste de doc solto.

## Instruções

1. **Situe-se antes de escrever código.** Leia `git log --oneline -5` e a
   seção relevante de `docs/ROADMAP.md`. Se a fatia envolve classificação
   ou agrupamento, leia `docs/AGRUPAMENTO.md`; se envolve confiança de
   sugestão, `docs/CONFIANCA.md`; se envolve UI, `docs/DIRECAO_DE_ARTE.md`.
2. **Confira os invariantes de segurança** no `CLAUDE.md` antes de tocar em
   scanner, operações ou fontes externas. Eles não são negociáveis: nenhum
   original é alterado, operação física só como plano até aprovação, nada
   sai da máquina sem opt-in.
3. **Escreva o teste junto com o código**, não depois. Fixtures sintéticas
   em `tests/fixtures.py` — nunca fotos pessoais no repo. Se a fatia é de
   classificação, adicione o cenário em `scripts/avaliar_agrupamento.py`
   ANTES de mexer em qualquer limiar.
4. **Implemente atravessando as camadas** que a fatia exige (repositório →
   serviço → API → webapp), sem abstração especulativa: nenhuma camada
   nova sem uma segunda necessidade concreta.
5. **Verifique com a ferramenta, não de memória:** rode
   `scripts/verificar.sh`. Ela roda a suíte, o benchmark de cenários e o
   build da UI web. Fatia só avança com tudo verde.
6. **Prove na UI real** quando a fatia é observável: suba o servidor
   (`scripts/executar.sh web`), exercite o fluxo e capture a tela. Não
   peça ao usuário para conferir aquilo que você pode verificar.
7. **Revise com olhos frescos** antes do commit: abra um sub-agente de
   revisão (Task) com contexto isolado, passando só o diff e a intenção da
   fatia. Incorpore o que ele achar antes de commitar.
8. **Commit único e pequeno**, mensagem convencional em português
   (`feat:`/`fix:`/`docs:`/`test:`/`perf:`/`chore:`) explicando o **porquê**
   e o comportamento observável — não a lista de arquivos.

## Referências

- `docs/METODO_DE_TRABALHO.md`: método completo (engenharia, UX,
  performance) — leia quando a decisão for de arquitetura ou de trade-off,
  não a cada fatia.
- `docs/ARQUITETURA.md`: camadas, schema e fluxo de dados.
- `docs/PRIVACIDADE.md`: o que pode ou não sair da máquina.

## Ferramentas

- `scripts/verificar.sh`: testes + benchmark de agrupamento + build da UI
  (`--rapido` pula o build). Exit != 0 bloqueia o commit.
- `scripts/executar.sh web`: sobe a UI web local para verificação visual.
- `scripts/avaliar_agrupamento.py`: benchmark de cenários rotulados de
  classificação.
