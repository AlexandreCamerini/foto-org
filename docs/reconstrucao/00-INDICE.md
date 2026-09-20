# Mapa de reconstrução — Foto Organizer

> Gerado em 2026-09-19 a partir do commit `524903d` (branch `main`) por leitura direta do
> código, dos docs normativos e do catálogo real (somente `SELECT`), com quatro agentes de
> domínio (arquivos, imagem/inferência, UX, arte), síntese transversal e um verificador
> independente. Público: um agente (ou pessoa) que vai **reconstruir a aplicação do zero**
> sem acesso a este repositório além desta pasta.

## Como usar

1. Leia na ordem abaixo. Cada arquivo é autocontido, mas os posteriores assumem os anteriores.
2. Toda afirmação cita `arquivo:linha` do repositório original — é a trilha para conferir, não
   um convite a copiar. Onde o mapa diz "verificar", o autor não conseguiu confirmar.
3. `08` e `09` dizem o que **não** reproduzir. Reconstruir bug conhecido é falha de leitura.
4. `10` é o critério de "terminei". Não declare pronto sem ele.
5. `MAPA_COMPLETO.md` é a concatenação 00→11 **mais os docs normativos citados** (`CLAUDE.md`,
   `docs/DECISOES.md`, `CONFIANCA.md`, `AGRUPAMENTO.md`, `EVENTOS.md`, `LOCAL_ESTIMADO.md`,
   `NAVEGACAO.md`, `PRIVACIDADE.md`, `PERFORMANCE.md`, `DIRECAO_DE_ARTE.md`,
   `EMPACOTAMENTO.md`) como anexos — é o pacote autocontido para colar num agente sem acesso
   ao repositório. Dentro do repo, esses docs vivem em `docs/` e são a fonte.

| Ordem | Arquivo | Responde |
|---|---|---|
| 1 | `01-PRODUTO.md` | O que é, valor central, os 8 invariantes, o acervo real, a stack fixa, as decisões a preservar |
| 2 | `02-FUNCIONALIDADES.md` | Inventário funcional com contrato de 10 campos por item (F-A = arquivos, F-I = imagem/inferência, F-U = experiência do usuário) |
| 3 | `04-PIPELINES.md` | Como o dado flui: scan → metadados → thumbnails → evidências → agrupamento → geo → duplicatas → sugestões → revisão → operações/EXIF; GenAI; jobs — com todas as constantes |
| 4 | `03-DADOS.md` | As 25 tabelas, enums, relações, migrações, modelo de evidência/confiança |
| 5 | `05-API_E_CLI.md` | 62 rotas, 12 subcomandos, guard de origem, config |
| 6 | `06-UI.md` | 21 telas/componentes, navegação, teclado, estados, camada de dados; § tokens e regras visuais |
| 7 | `07-INTEGRACOES.md` | exiftool, osxphotos, Takeout, Lightroom, reverse_geocode, Anthropic, Tauri, Keychain |
| 8 | `08-ERROS_CONHECIDOS.md` | Auditoria 2026-09-19 + dívida + histórico, com status e "o que fazer diferente" |
| 9 | `09-MELHORIAS.md` | Milestone v2.0, backlog, dívida, o que **não** carregar, ideias sem decisão |
| 10 | `10-VERIFICACAO.md` | Suítes, fixtures, contagens, invariante → prova, baselines, checklist |
| 11 | `11-DADOS_ESTATICOS.md` | Gerado do código: `TEMPLATE_PADRAO`, `ROTULOS`, `_TELAS`, `LACUNAS`, `ALCANCES`, `PAISES_PT`, `TZ_POR_PAIS`, prompts `_SYSTEM` literais, mensagens 409, shapes JSON sem contrato, valores reais de `evidence.campo/origem`, os 19 cenários do benchmark, formato do `INVENTARIO.md` |

## O que preservar × o que descartar (resumo; detalhe em 01 §8 e 09 §7)

**Preservar sem discussão:** os 8 invariantes; confiança como quantidade e elo mais fraco;
evidência estruturada com "por quê"; rebaixar-nunca-apagar (`papel`); janelas de herança por
campo (10 min / 2 h / 12 h) e raio de incerteza medido; álbum nomeia, não divide; geo-resolução
cedo; exiftool padrão com fallback; opt-in real para qualquer chamada externa com prévia do
payload; dry-run → aprovação → execução verificada → audit; webapp como única UI; SQLite como
única verdade local.

**Descartar:** tudo em `09 §7` — UIs antigas, `http_seguro` sem consumidor, endpoints órfãos,
`select()` fora de repositories, `skipif` silencioso, duplicação de `pastaCurta`, docs
históricos como se fossem spec, qualquer score único/soma/semáforo, qualquer `DELETE`/`move`.

**Corrigir ao reconstruir (não reproduzir):** `08 §A` — A1 (lock de jobs), A2 (sidecar com
sinal + verificação por valor), M1/M5 (base de tempo única), M2 (nome da pasta no payload),
M3 (retomada tolerante), M4 (`exif_transpose` no phash).

## Glossário (termos do domínio, como o código os usa)

- **Fonte (`sources`)** — raiz varrida (`PASTA`) ou catálogo externo importado
  (`APPLE_PHOTOS`, `LIGHTROOM`, Takeout). Tem identidade de volume (`volume_id`) para
  reconhecer o mesmo disco noutro ponto de montagem; **reapontar** é o ato explícito do dono
  de mover a fonte — nunca automático (D-036).
- **Alcance** — se o arquivo responde agora: `disponivel` (fonte), `arquivo_ausente` (não visto
  no walk — não significa apagado, D-037), `arquivo_offline` (volume desmontado). **Reconciliação
  de alcance** é a varredura leve que só confere existência, com orçamento de tempo.
- **Papel (`media_files.papel`)** — `ACERVO` (foto real do dono) vs testemunha/referência
  (miniatura interna, derivado, registro só-iCloud). Registro que não é acervo é **fonte de
  sinal**: sai da grade, da revisão e do plano; continua doando data, GPS e correlação (D-024).
- **Metadados brutos (`metadata_entries`)** — chave-valor de tudo que o extrator leu (3,6 M
  linhas). `media_files` guarda o que foi promovido a coluna tipada.
- **`data_capturada`** — hora de **parede local** da captura (o relógio no lugar), sem fuso.
  **`data_capturada_utc`** — o instante. **`tz_estimado`** — IANA inferido do país. `mtime` é
  UTC naive (`_ts`). Uma foto tem dois instantes; o offset não é coluna (D-038).
- **Evidência (`evidence`)** — uma linha por inferência: origem (`exif`, `gps`, `geocoding`,
  `pasta`, `album`, `nome_arquivo`, `fs`, `llm`, `llm_pasta`, `heranca`, `xmp`…), campo, valor,
  confiança (nível alta/média/baixa + score), justificativa legível, `versao_logica`.
- **Confiança** — quantidade, não cor (D-017). Níveis por origem em `docs/CONFIANCA.md` (EXIF
  0,95; geocoding offline 0,85; pasta 0,60; álbum 0,55; LLM 0,55; filesystem 0,40; visão 0,30;
  correção manual 1,0). **Elo mais fraco:** a sugestão vale o campo mais fraco do destino.
- **Sugestão (`suggestions`)** — destino proposto para uma mídia, renderizado por **template**
  (`{categoria}/{ano} - {viagem}/{evento}/{pais}/{regiao}/{cidade}` por padrão — `classification/templates.py:24`), com as evidências
  usadas (`suggestion_evidence`). Estados: pendente → aprovada/rejeitada. Decisão registrada do dono: reprocessamento que
  muda o destino **reabre** a aprovada; o código atual **congela** a aprovada
  (`engine.py:1120-1124`) — ver § Decisões em aberto, item 1.
- **Sessão** — cluster temporal (gap > 3 dias separa; corte adicional ao cruzar o raio de
  **casa** = 50 km, com confirmação). Ainda não é viagem.
- **Viagem (`trips`)** — sessão classificada pela cascata (pasta "Viagens", país no nome,
  mediana GPS > 100 km de casa, ou geocodificada ≥ 3 dias sem casa conhecida). Multi-país é
  nomeada pelas pernas.
- **Acontecimento / evento (`events`)** — divisão de uma sessão por ritmo local (fator 6× a
  mediana de 12 intervalos), piso 90 min, teto 8 h, deslocamento ≥ 3 km, mínimo 10 fotos, estadia
  > 20 h não se divide; viagem nunca se divide (`docs/EVENTOS.md`). Álbum nomeia, não divide.
- **Neutra** — sessão que nenhuma regra classificou; única que vai ao **advisor de cluster**
  (LLM, opt-in) ou fica sem rótulo. Nunca se inventa viagem nem evento.
- **Casa** — célula GPS modal (~11 km) com ≥ 20 fotos com GPS e ≥ 30% nela; senão "casa
  desconhecida".
- **Herança de GPS** — foto sem GPS recebe lugar de uma **doadora** de outra fonte próxima no
  tempo; janela por campo: cidade 10 min, região 2 h, país 12 h (D-025); confronta doadora
  antes **e** depois (D-074). Resultado: `gps_lat_estimado`, `gps_estimado_de_id`,
  `gps_estimado_delta_s`. **Lugar estimado** com **raio de incerteza**
  `min(50 km, max(15 m, 6 m/s × Δt))` (D-032), desenhado sem tiles (D-031).
- **Location (`locations`)** — resultado de geocodificação reversa offline (cidade, região,
  país) compartilhado por mídias.
- **Duplicata** — níveis: `exato` (xxhash + tamanho + SHA-256), `conteudo`, `visual` (phash,
  distância de Hamming ≤ `LIMIAR_VISUAL`), `sequencia` (rajada/burst — irmãs, não duplicatas),
  `variante` (RAW+JPEG da mesma captura; excluir uma exige aviso, D-070). Nenhuma ação
  automática; `preservados` são decisões do dono.
- **Plano de operação (`operation_plans/items`)** — lista origem → destino calculada pelo
  template. **Dry-run** obrigatório (recalcula conflitos, espaço, alcance) → aprovação →
  **execução** (cópia exclusiva `xb`, hash pré/pós, `copystat`, audit) → **inventário**
  (`inventario.json` + `INVENTARIO.md` na pasta destino, aditivo). Enum único `OperationStatus`
  (`models/operations.py:18-24`): `planejada · aprovada · executando · concluida · cancelada ·
  erro`, usado por plano e por item (item vai `planejada → concluida | erro`); "prontos",
  "pulados" e "copiados" são contadores do dry-run/execução, não estados persistidos.
- **Escrita EXIF (`exif_write_plans/items`)** — só GPS lat/long, cidade, país; só campo vazio;
  **direta** (`.jpg/.jpeg/.cr2`, allowlist medida byte a byte, D-077) ou **sidecar XMP** (demais
  formatos). Verificação por diff de tags, reconferência ao vivo (TOCTOU), backup `_original`
  apagado só após sucesso; estados por campo (PRONTO/GRAVADO/PULADO/…).
- **Advisor de cluster** (`llm`) — Claude Sonnet 5, sem thinking, só para sessões neutras, só
  metadado (pastas, amostra de nomes, período, contagem, lugares). **GenAI de pasta**
  (`llm_pasta`) — sessão interativa: candidatas por pasta, custo estimado antes, payload com
  allowlist, aprovação → `pasta_classificacoes_genai` → evidência 0,55 (D-081). **Léxico de
  nomes** (`nomes_classificados`) — cache do que cada nome significa. Todos opt-in.
- **Job** — trabalho em background do servidor: `scan`, `import`, `sugestoes`, `duplicatas`,
  `reconciliacao`, `operacao`, `escrita_exif`. Um por vez; estado por polling; pausa só para
  scan; cancelamento cooperativo (`ScanControl`) ou com limpeza de parcial (`ExecutionControl`).
- **Hash rápido** (xxhash, sempre) / **SHA-256** (sob demanda, candidatos a duplicata exata) /
  **phash** (perceptual 64 bits, BK-tree).
- **`versao_logica`** — versão da regra que gerou uma evidência/sugestão; muda → regenerar.
- **Organizável** — mídia de acervo cuja fonte responde agora (D-068); é o funil do Panorama.

## Cobertura mecânica da spec (Fase 3)

Script de `10-VERIFICACAO.md` § anexo, rodado em 2026-09-20 sobre `524903d`:

| Superfície | No código | Ausentes no mapa |
|---|---|---|
| Rotas FastAPI (paths únicos; `{plan_id}`≡`{id}`) | 59 (62 decoradores) | 0 |
| Tabelas (24 ORM + `suggestion_evidence`) | 25 | 0 |
| Componentes React | 21 | 0 |
| Subcomandos CLI | 12 | 0 |
| Migrações Alembic (por número) | 20 | 0 |

## Decisões em aberto para o reconstrutor (do dry-run independente)

Levantadas por um agente independente que leu só esta pasta (2026-09-20) e tentou
reconstruir. Cada uma muda a implementação; a coluna "default" é o que o reconstrutor faz se
ninguém responder — e deve registrar como decisão própria.

| # | Pergunta ao dono | Onde a spec silencia | Default do reconstrutor |
|---|---|---|---|
| 1 | Construir o mecanismo de **reabertura de sugestão aprovada**? Gatilho: destino mudou, evidência mudou ou `versao_logica` mudou? | `02` F-I24; `04` § Lacunas 5; código congela (`engine.py:1120-1124`), decisão do dono diz reabrir | Implementar reabertura por "destino renderizado mudou", com a decisão anterior preservada no histórico |
| 2 | **Base de tempo única** (M1/M5): normalizar `mtime` por `tz_estimado`, excluir só-mtime da linha do tempo, ou manter? | `04` § Lacunas 1; `08` M1/M5 | Um `quando(media)`: EXIF → nome do arquivo → mtime convertido para parede local; cenário novo no benchmark antes |
| 3 | M2: enviar `Path(pasta).name` (perde hierarquia que ajuda o modelo) ou enviar relativo à raiz da fonte? | `08` M2 | Relativo à raiz da fonte, com prévia mostrando exatamente o que sai |
| 4 | Corrigir `exif_transpose` no phash invalida todos os `hash_perceptual` e os 1.348 grupos. Invalidar e recomputar? | `08` M4; `04` § Lacunas 2 | Corrigir + migração que zera `hash_perceptual` + rerodar detecção |
| 5 | Recriar as **20 migrações** históricas ou nascer com uma inicial já no head? | `03` §4 dá só o efeito de cada uma | Uma inicial no head; o histórico fica como documentação |
| 6 | Os 11 achados "verificar" de `08` §C são bugs a corrigir ou não-reproduzíveis? | `08` §C | Tratar como abertos: escrever um teste para cada antes de decidir |
| 7 | Origens declaradas sem produtor (`gps` 0,95, `geocoding_externo` 0,75, `visao` 0,30, `agrupamento` 0,70): contrato futuro ou dívida? | `04` § Lacunas 4; `11` § evidence.origem | Manter na tabela de confiança, sem produtor, documentado |
| 8 | Preços do modelo (`$2/$10` por MTok) e câmbio fixo 5,0 na estimativa de custo estão datados. Atualizar como? | `07` § Lacunas 3/4 | Ler preço de config, câmbio fixo com ressalva na UI |
| 9 | Endpoints sem consumidor (`/api/midia/alcances`, `POST /api/reconciliacao`, `/api/midia/filtros`): construir com consumidor ou não construir? | `09` §7 × `10` §9 | Construir com consumidor (reconciliação na UI; filtros ligados) |
| 10 | Lightroom continua só na CLI (sem rota nem UI)? | `05` § Lacunas 4 | Sim, pelo motivo de TCC/volume desmontado |
| 11 | `ConfigClassificacao` (5 limiares) vira configurável em runtime? | `04` § Lacunas 6 | Não; só por código + benchmark |
| 12 | `faces/`, `vision/`, `crypto.py`, `tags`/`media_tags`, `http_seguro.py`: carregar como stub/tabela vazia ou deixar fora? | `09` §7 só decide `http_seguro` | Carregar os `Protocol` + tabelas; `http_seguro` fora até ter consumidor com SSRF fechado |
| 13 | Restaurar backup `_original` vira rota/comando ou continua manual? | `02` F-A24/F-U25 (parcial); `06` § Lacunas 9 | Manual; o app preserva e expõe o caminho |
| 14 | Allowlist de avisos do exiftool (`IPTCDigest is not current`)? | `09` §1; `.planning/STATE.md:222` | Sem allowlist: aviso novo reprova (fail-safe) |
| 15 | Tasks 2/3 do plano 07-10 (sessão real de 10 pastas com a chave do dono; marcar GENAI-01..03 após checkpoint humano) entram na reconstrução? | `09` §1 | Fora de escopo; GENAI fica "feito na essência, não homologado" |

Contradições internas encontradas pelo mesmo verificador foram **corrigidas no mapa** em
2026-09-20 (template com `{pais}`, enum `OperationStatus`, condição da miniatura, dependência
conjunta `rawpy`+`exifread`, D-057 × D-051, 19 cenários do benchmark, 6 etapas do assistente
GenAI, aprovação que descarta as demais, `GET /api/status` com 6 chaves, `Fonte.tipo` sem
`lightroom` no TS, teto 500 de `limit`). Buracos de dado puro viraram `11-DADOS_ESTATICOS.md`;
docs normativos fora da pasta viraram anexos do `MAPA_COMPLETO.md`.
