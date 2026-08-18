# Milestones

## v1.0 MVP + Preparação para lançamento (Shipped: 2026-08-18)

**Phases completed:** 5 phases, 16 plans, 41 tasks

**Key accomplishments:**

- Tabela estática TZ_POR_PAIS (250 países, IANA validado) alimentando `media.tz_estimado`, gravado direto em `_persistir_sugestao` e servido em `GET /api/midia/{id}` — fecha o modelo de dois instantes de D-038.
- Filtro "Tudo" da Biblioteca (`alcance=tudo`, o default) para de misturar miniatura/derivado interno com o acervo real, preservando a visibilidade de referência externa sem arquivo local (iCloud, volume desmontado) que o commit `1b125f7` havia introduzido de propósito.
- Os 3 pontos de entrada restantes (botão de troca de aba, `Sidebar.onSelecionarPasta`, `StatusBar.aoIrPara`) agora chamam `setBusca("")`, fechando REV-03 com 5/5 pontos cobertos e 4 testes de regressão novos.
- 9 trocas de classe Tailwind `text-texto-3`→`text-texto-2` em Review.tsx/Inspector.tsx/Operations.tsx, contagens e diff programaticamente conferidos contra a lista fechada de D-02, com aprovação visual do dono confirmada em conteúdo real.
- Token `--font-weight-titulo: 500` criado no `@theme` do Tailwind 4, 17 call sites de `font-semibold`/`font-medium` migrados para o utilitário `font-titulo` gerado por ele, e teste de guarda que falha se o desvio voltar.
- "Retomar" e "Gerar/atualizar sugestões" caem no contorno padrão de `Botao.tsx` (zero `variante="solido"`/override de acento fora do único preenchido legítimo), e o "Cancelar" de cópia em andamento de Operações vira `variante="fantasma"` + `className="hover:text-erro"` — vermelho só na intenção, igual ao StatusBar.
- Loupe e Duplicatas ganham estado de erro explícito (glifo `⊘` + cópia travada no UI-SPEC) quando `api.previewUrl` falha, substituindo o ícone quebrado do browser (Loupe) e o retângulo preto (Duplicatas); `Duplicates.tsx` extrai `MembroFigura` para dar a cada membro do grid seu próprio estado de falha.
- Cards da seção Eventos que colidem no nome ganham, cada um, um selo "Álbum" ou "Evento detectado" derivado de `Agrupamento.metodo` — zero mudança de backend, TDD com RED confirmado antes do GREEN.
- Barra da Biblioteca reagrupada em dois blocos por intenção que empilham abaixo de 1024px, sem nunca produzir uma terceira linha nem cobrir o Inspetor, com escala de correção iterativa validada por captura real de tela nas larguras ~700px/~900px/1200px.
- ModalCaminho extraído para módulo próprio e sua posse movida de `Sidebar.tsx` (estado privado) para `App.tsx` (dono único, distribuído por prop aos quatro pontos que precisam dele — Sidebar e os três estados vazios), fechando CONS-05/D-07 com erro de scan visível no próprio modal.
- Duas sugestões vizinhas com mesmo nome+data+câmera mas media_id diferente agora mostram, cada uma, um selo neutro com o nome da fonte de origem — via um campo aditivo de 1 linha no backend (`source_id`), colisão por adjacência computada no cliente e o cache `["fontes"]` já existente, sem requisição nova.
- 9 índices de FK ausentes com consumidor real citado, 4 índices de drift reconciliados no modelo, e `PRAGMA case_sensitive_like=ON` — sem essa última linha, `ix_media_files_pasta` existia e o filtro de pasta continuava em `SCAN media_files`.
- `Foto Organizer.app` construído a partir do scaffold Tauri v2 existente, com runtime Python (PBS 3.12.14 arm64) e webapp de produção embarcados, assinatura ad-hoc `Signature=adhoc` aplicada automaticamente sem configuração — resolve a suposição A1 da pesquisa da Fase 5.
- Critério de aceite do Marco 1 (`docs/EMPACOTAMENTO.md`) exercido pela primeira vez contra o bundle `Foto Organizer.app` — catálogo descartável, fixtures sintéticas, grade populada, zero processo Python órfão nos dois caminhos de encerramento — e confirmado visualmente pelo dono via Finder.
- Script reproduzível de medição contra o acervo real (59 arq/s de varredura, 1.33s de sugestões, 4.54s de duplicatas sobre 1382 fotos) e docs/PERFORMANCE.md com metodologia P-1/P-2/P-3 registrada para comparação futura.
- Teste de usuário real revelou bloqueador genuíno no ModalCaminho (texto sobreposto por backdrop translúcido demais); diagnosticado por screenshot, corrigido com `bg-black/60` → `bg-black/95`, reverificado visualmente e travado por regressão em `App.test.tsx`.

---
