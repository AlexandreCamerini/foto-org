# Roadmap — fatias verticais (ágil)

Cada milestone é uma fatia entregável e testável. Definition of done comum:
`pytest` verde, nenhuma violação dos invariantes do CLAUDE.md, app abre e a
fatia é demonstrável de ponta a ponta.

**Status: M0–M7 CONCLUÍDOS** (MVP completo). Próximos passos em
"Próximas versões" no fim deste arquivo.

## M0 — Fundação (esqueleto executável)
- Estrutura `fotoorganizer/`, config TOML, logging estruturado.
- SQLite WAL + SQLAlchemy 2 + Alembic com a migração inicial (schema em
  docs/ARQUITETURA.md).
- Janela PySide6 vazia com layout de 3 painéis e tema QSS dark aplicado.
- `docs/PRIVACIDADE.md` e `docs/CONFIANCA.md` iniciais.
- Aceite: `python -m fotoorganizer` abre a janela; migração roda; testes de
  DB e config passam.

## M1 — Catálogo e scanner (núcleo seguro, sem UI nova)
- Portar do legado: descoberta de arquivos (JPEG/PNG/HEIC/HEIF/HIF/TIFF/WebP/
  RAW), extração EXIF (sub-IFD DateTimeOriginal, data RAW via libraw),
  xxhash sempre + SHA-256 sob demanda.
- Varredura incremental (tamanho+mtime+inode), checkpoints, pause/resume,
  fontes (sources) com detecção de volume indisponível, exclusão de pastas,
  symlinks não atravessados, arquivos ocultos ignorados por padrão.
- Erros de leitura registrados sem interromper o scan. Métricas simples
  (arquivos/s, restantes, erros) + mini benchmark de indexação.
- Aceite: CLI interna indexa uma pasta de fixtures sintéticas duas vezes e a
  segunda passada não relê arquivos inalterados; testes de scanner,
  metadados, unicode, arquivo corrompido e interrupção/retomada passam.

## M2 — UI de catálogo (primeira experiência real)
- Painel inicial: fontes, contagens, progresso do scan, erros.
- Grade de miniaturas virtualizada (QListView modo IconMode + lazy load),
  cache de thumbs em disco, geração em background, slider de tamanho.
- Inspetor (painel direito): preview, caminho original, metadados, datas.
- Filtros básicos: data, pasta/fonte, extensão; busca textual; ordenação.
- Aceite: 10k fixtures navegam fluido sem carregar tudo em memória; UI
  responsiva durante scan.

## M3 — Evidências, agrupamento e sugestões
- Motor de evidências estruturadas (tabela `evidence`) + modelo de confiança
  documentado.
- Agrupamento temporal por lacunas/timezone/câmera (portar e evoluir o
  gap de viagem do legado); agrupamento geográfico: GPS → reverse geocoding
  offline; sem GPS → nome de pasta e vizinhança temporal, com confiança baixa.
- Templates de destino (`{categoria}/{ano}/{evento}`…), normalização de nomes,
  colisões, limites de tamanho.
- Tela de revisão: aprovar/rejeitar/editar, lote, desfazer, filtro por
  confiança, justificativas visíveis.
- Aceite: cada sugestão exibe critérios e confiança por evidência; testes de
  templates, normalização e confiança passam.

## M4 — Duplicatas
- 3 níveis (hash exato, mesmo conteúdo, phash) com grupos persistidos.
- UI lado a lado: manter todos, marcar versões, escolher principal, ignorar.
- Aceite: nenhuma ação automática; testes de duplicatas passam.

## M5 — Plano de operações (dry-run e cópia segura)
- Plano: origem, destino, operação, conflitos, espaço necessário, erros
  potenciais. Dry-run obrigatório antes de executar.
- Executor de cópia: verificação de hash antes/depois, sem sobrescrita,
  cancelamento seguro, retomada, disco cheio, volume desconectado, audit log.
- Aceite: teste prova que sobrescrita é impossível; execução interrompida
  retoma sem duplicar nem corromper.

## M6 — Stubs de visão e rostos + privacidade
- `VisionProvider` e `FaceRecognitionProvider` (Protocols) com stub local:
  cadastro de pessoas, fotos de referência, detecção local de rostos,
  associação manual; estrutura para embeddings criptografados.
- Limpeza de cache, remoção completa do catálogo, indicação visual de envio
  externo (ainda sem provider externo real).
- Aceite: recurso desligado por padrão; perfil apagável por completo.

## M7 — Polimento e empacotamento
- Remoção do legado `backend/`+`streamlit_app/` (commit próprio).
- Dados de demonstração sintéticos (scripts/gerar_demo.py), README novo,
  instruções de empacotamento (docs/EMPACOTAMENTO.md), roadmap v2 abaixo.

---

# Próximas versões (v2+)

**Ordem recalibrada em 2026-08-01 com dado medido deste acervo** (D-024 a
D-030 em `docs/DECISOES.md`), e não com valor abstrato de funcionalidade. A
régua é **valor entregue por unidade de custo para este acervo**: item cujo
valor depende de dado que este acervo não tem desce, por melhor que seja em
abstrato.

Os três fatos que mais mexeram na ordem:

- **Pixel local é raro.** 44.661 registros do Apple Fotos têm original só no
  iCloud e 45.397 do Lightroom estão em volume desmontado (D-028). De ~99 mil
  registros conhecidos, só ~5,2 mil arquivos reais são legíveis hoje. Tudo que
  precisa abrir a imagem alcança ~5% do acervo.
- **GPS é raro e recente.** 58 câmeras entre 2001 e 2026, só a EOS 5D Mark IV
  com receptor próprio (2.878 de 3.633); 25 anos de acervo e só 4 com GPS
  (D-029). Nenhum dos 5.601 arquivos locais tem GPS no próprio arquivo
  (D-024). Tudo que depende de coordenada nasce cego em 2001–2018.
- **Intenção declarada é abundante.** 25.304 nomeações de álbum já no catálogo
  (D-030), mais nota, sinalização e palavra-chave do Lightroom (D-028) — dado
  que já está no banco, cobre o acervo inteiro e não custa nada para ler.

**Saiu da lista por já estar feito:** *exiftool opcional em batch* (era o item
6) virou o extrator padrão em D-026/D-027 — medido 0/40 → 40/40 câmeras
identificadas em CR3, e mais rápido que o fallback.

## Ordem

1. **Mapa do lugar estimado com raio de incerteza** — *em execução (fase 9)*.
   Cada foto herdeira vira círculo cujo raio é a incerteza do Δt até a
   doadora, com o traço até ela.
   - *Muda o quê:* 4.944 das 5.191 fotos do catálogo só têm lugar por herança
     (D-025); hoje elas são desenhadas como ponto e mentem sobre a própria
     precisão. É a primeira tela que responde "onde isto foi tirado" para o
     acervo que não tem GPS nenhum.
   - *Esforço:* M — o dado (`gps_estimado_de_id`, `gps_estimado_delta_s`) já
     está no banco e já corrigido de deriva; falta a fórmula do raio, sua
     calibração e o desenho.
   - *Custo recorrente:* zero, desde que a cartografia não peça tile externo
     (invariante 4 — tile revela coordenada sem nenhum arquivo sair).
   - *Desbloqueia:* correção manual de lugar (com aviso de cascata) e leitura
     visual de viagem; é pré-requisito de qualquer confiança no item 6.
   - *Movimentação:* item novo, entra no topo — já está sendo construído.

2. **`docs/EVENTOS.md`** — *dívida da fase 8, não funcionalidade nova*.
   Registrar o modelo de evento temporal que já foi implementado e medido.
   - *Muda o quê:* nada no produto; o modelo já roda. Muda a capacidade de
     revisar, calibrar e reverter o que ele faz.
   - *Esforço:* XS — é escrever o que já foi decidido e medido, sem código.
   - *Custo recorrente:* zero.
   - *Bloqueia:* o item 3 mexe no mesmo modelo; documentar antes evita
     reconstruir o raciocínio duas vezes.
   - *Movimentação:* pendência da fase anterior, sobe por ser quase de graça.

3. **Eventos nomeados pelo que já existe** — *implementado em 2026-08-01
   (D-034); a régua de desempate está em `docs/AGRUPAMENTO.md`, seção 2c.*
   Usar as 27.226 nomeações de álbum (eram 25.304 quando esta linha foi
   escrita) e o nome de pasta para *nomear* os eventos que o agrupamento
   temporal já detecta. **Não** detectar aniversário/casamento por rosto e
   visão, que era a formulação antiga.
   - *Entregou o quê:* zero nomes novos **hoje** — 7 grupos antes, 7 depois,
     nenhum com nome diferente. O motivo é o mesmo bloqueio dos itens 5, 7,
     8 e 9: nenhuma das 27.226 marcações está numa foto alcançável (D-028).
     Os 21 períodos com álbum aproveitável (20.515 fotos, 20 deles sem nome
     de pasta nenhum) ganham nome no dia em que os arquivos aparecerem, sem
     código novo. Reforça, medido, o "item que a lista ainda não tem" no fim
     deste arquivo: reencontrar os arquivos multiplica agora cinco itens, não
     quatro.
   - *Muda o quê:* o acervo ganha nome humano ("Portugal e Itália com as
     Meninas") onde hoje tem intervalo de datas — inclusive em 2001–2018,
     onde nome de pasta e álbum são o único sinal de lugar que existe (D-029).
   - *Esforço:* S/M — os nomes já estão no banco e o evento já é detectado;
     é ligação e desempate, não detecção. D-030 já fixou a regra difícil:
     álbum nomeia, nunca divide (os álbuns se aninham — mesma foto contada
     três vezes em 29 dias).
   - *Custo recorrente:* zero.
   - *Desbloqueia:* rótulo legível em template de destino (item 4) e no mapa
     (item 1). *Não depende* de rosto nem de visão — foi isso que o tirou do
     fim da lista.
   - *Movimentação:* sobe de 9º para 3º. A versão antiga dependia de rosto e
     calendário (dados que este acervo não tem); a versão reescrita usa dado
     que já está no banco.

4. **Templates configuráveis na UI** — *implementado em 2026-08-02.* Editor
   de template com preview, dentro da aba Operações.
   - *Entregou o quê:* `application_settings` (tabela já migrada, zero uso
     até então) passou a guardar o template escolhido; três endpoints
     (`GET`/`PUT /api/configuracoes/template`, `POST .../preview`, este
     último chamando `render_destino` de verdade — o webapp nunca
     reimplementa a lógica de renderização); editor colapsável em
     Operações com preview ao vivo (debounce), erro 422 inline para
     placeholder inválido, e "regenerar sugestões pendentes" como ação
     separada do "salvar" — desabilitada enquanto há edição não salva, para
     nunca regenerar a partir de um rascunho não confirmado. Verificado ao
     vivo contra o catálogo real (101.516 fotos): preview, erro de
     validação e persistência entre reinício do servidor confirmados por
     `curl`, não só por reload de página.
   - *Muda o quê:* é a alavanca que transforma catálogo em pastas quando os
     discos montarem. O motor já aceita template arbitrário; hoje só não há
     onde digitá-lo.
   - *Esforço:* S — formulário mais preview sobre motor pronto.
   - *Custo recorrente:* zero.
   - *Desbloqueia:* uso real do plano de operações (M5) sem editar TOML.
   - *Movimentação:* sobe de 4º para 4º na posição, mas passa à frente de
     tudo que depende de pixel — é o único item alto que não depende de dado
     ausente.

5. **Análise visual local** (`VisionProvider`: cena, qualidade, screenshot vs.
   foto).
   - *Muda o quê:* candidato a ser o único sinal novo para 2001–2018. As
     45.822 miniaturas do Apple Fotos rebaixadas em D-024 são pixel **local**
     (540×360) e já provaram carregar informação que o resto do acervo não
     tem — apagá-las derrubaria as fotos com lugar estimado de 2.117 para 162.
     Cena grosseira (praia/montanha/urbano) sobrevive a 540×360.
   - *A medir antes de construir:* a distribuição de datas dessas 45.822. Se
     elas não cobrem 2001–2018, este item cai para o fundo junto com o 7.
   - *Esforço:* M/L — modelo local, fila de background, rótulos como evidência
     de baixa confiança no motor.
   - *Custo recorrente:* zero em dinheiro; CPU por foto, uma vez.
   - *Movimentação:* sobe de 2º… para 5º na ordem, mas sobe *acima da
     detecção facial*, invertendo a ordem antiga: cena tolera miniatura,
     identidade não.

6. **Timezone estimado** — reformulado: inferir `tz_estimado` do **país
   herdado** (janela de 12 h de D-025), não do GPS próprio.
   - *Muda o quê:* na formulação antiga (GPS + hora local) alcançaria 4 dos
     25 anos do acervo — as viagens internacionais que mais precisam de
     timezone (Portugal/Itália) estão justamente no período sem GPS. Pelo país
     herdado, alcança as ~2.235 fotos que hoje só conseguem afirmar país.
   - *Esforço:* S/M — a coluna existe e a janela de país já está implementada
     em `grouping/correlacao.py`.
   - *Custo recorrente:* zero.
   - *Depende de:* item 1 — sem a incerteza desenhada e calibrada, herdar
     timezone de país estimado empilha inferência sobre inferência em
     silêncio.
   - *Movimentação:* desce de 5º para 6º e muda de fonte. A versão antiga
     dependia de GPS que existe em 4 de 25 anos.

7. **Detecção facial local real** (`FaceRecognitionProvider` com modelo ONNX).
   - *Muda o quê:* pouco hoje, muito depois. Precisa de pixel em resolução
     útil, e ~90 mil dos ~99 mil registros conhecidos não têm arquivo local
     legível (D-028). Miniatura de 540×360 permite *detectar* rosto, não
     *identificar* pessoa com limiar conservador.
   - *Esforço:* L — modelo, embeddings cifrados, fila, limiar calibrado,
     revisão. A infraestrutura do M6 cobre a parte fácil.
   - *Custo recorrente:* zero em dinheiro; CPU alta por foto.
   - *Desbloqueia:* item 8 (UI de pessoas), e reforçaria o item 3.
   - *Movimentação:* **desce de 1º para 7º** — é a maior queda da lista, e a
     razão é uma só: o dado que ela consome (pixel) está a 90% fora de
     alcance. Volta ao topo no dia em que os volumes do Lightroom montarem.

8. **UI de pessoas** — cadastro/gestão de perfis e revisão de rostos.
   - *Muda o quê:* sem o item 7, é uma tela para revisar rostos que ninguém
     detectou.
   - *Esforço:* S/M — backend do M6 pronto; é tela.
   - *Custo recorrente:* zero.
   - *Bloqueada por:* item 7. Não faz sentido antes.
   - *Movimentação:* desce de 3º para 8º, arrastada pela dependência.

9. **Sidecar XMP** — gravar metadados aprovados em `.xmp` ao lado dos
   originais.
   - *Muda o quê:* valor real e específico — o dono usa Lightroom, que lê XMP,
     então isto devolve ao fluxo dele o que o app decidiu. Mas **não há onde
     escrever** para ~90 mil registros: 45.397 em volume desmontado, 44.661
     com original no iCloud (D-028).
   - *Esforço:* M — escrita é caminho novo, com todas as garantias do
     invariante 3 (nunca sobrescrever, verificar antes e depois).
   - *Custo recorrente:* zero.
   - *Bloqueado por:* acesso físico aos volumes, e pelo invariante 7 do
     `CLAUDE.md` (escrita só como sidecar, e só em fase posterior por design).
   - *Movimentação:* desce de 7º para 9º — o destino da escrita está offline.

10. **Empacotamento assinado** — bundle `.app` notarizado.
    - *Muda o quê:* nada na capacidade do app; muda a distribuição. Usuário
      único, na própria máquina, com Tauri já em pé.
    - *Esforço:* M — notarização, credenciais e CI.
    - *Custo recorrente:* **US$ 99/ano** de Apple Developer Program.
    - *Movimentação:* desce de 10º para 10º; mantido no fim, agora com o custo
      recorrente dito em número.

11. **Provider externo opt-in** (geocoding e/ou visão via API).
    - *Muda o quê:* o geocoding offline já cobre o caso; sobra a visão por
      API, que só existiria para compensar o item 5 — e enviaria pixel ou
      coordenada, exatamente o que o invariante 4 e `docs/PRIVACIDADE.md`
      mandam evitar por padrão.
    - *Esforço:* L — provider, indicação visual prévia de o quê/para onde/como
      revogar, lista de arquivos, cancelamento, cache e rate limit.
    - *Custo recorrente:* **por foto**. A ~US$ 0,001/imagem, uma passada nos
      ~99 mil registros conhecidos custa ~US$ 100 — e o acervo real é maior e
      ainda desconhecido (D-028), então o custo não tem teto medido.
    - *Movimentação:* desce de 8º para o último. Único item da lista com custo
      recorrente proporcional ao tamanho do acervo, contra um acervo cujo
      tamanho ainda não se conhece.

## O item que a lista ainda não tem

A régua acima aponta, sozinha, para algo que não está entre os dez: **reencontrar
os arquivos**. 45.397 fotos num volume desmontado e 44.661 com original só no
iCloud (D-028) são a causa direta da queda dos itens 5, 7, 8 e 9. Qualquer
fatia que reconecte volume por identidade (hash, caminho original, tamanho +
data) multiplica o valor de quatro itens de uma vez. Fica registrado aqui como
candidato, não como decisão — a forma exata é assunto de uma fase própria.
