# Plan 06-09 — Fechamento da Fase 6 (Escrita EXIF de localização)

**Status:** Complete
**Tasks:** 3/3 (1 automática, 2 checkpoints humanos)

## O que foi feito

### Task 1 — Documentação de arquitetura + gate completo (automática)

`docs/ARQUITETURA.md` ganhou a seção `## Módulo exif_write/`: o que o
módulo faz, por que é próprio (não estende `operations/` — o truque de
segurança da cópia via criação exclusiva não tem equivalente para mutação
in-place), o fluxo planner→dry-run→seleção→executor→`AuditLog`, a
armadilha da FK de `AuditLog.plan_id` (contorno: `plan_id=NULL` + id do
plano em `detalhe` JSON), o que nunca é escrito, e a cadeia de decisões
medidas D-075→D-076→D-077→D-078. `## Decisões registradas` e
`## Riscos principais` atualizados com referências cruzadas.

`scripts/verificar.sh`: **✅ Fatia verde** — 939 testes de backend, 19/19
cenários de benchmark de agrupamento, 163 testes de webapp, build limpo.
Commit `93a36aa`.

### Task 2 — Dono percorre o fluxo real na UI (checkpoint humano, bloqueante)

Executado em conjunto (dono + orquestrador) diretamente na sessão, não
por um roteiro escrito isolado — evidência real, não simulada:

- Pasta descartável `~/Desktop/teste-exif` criada com cópias reais (nunca
  os originais): 2 `.jpg` da Canon EOS R6m2 (`Serena 15 Anos`), 1 `.cr2`
  e 1 `.dng` da Canon EOS 7D (`Do Peru ao Chile`). GPS de teste (Cristo
  Redentor, -22.9519/-43.2105) embutido via exiftool nas cópias — nunca
  nos arquivos reais.
- Cadastro de fonte, varredura, geração e aprovação seletiva de
  sugestões (só os itens de teste, nunca sugestões de fotos reais do
  dono) — tudo pela UI real em `http://localhost:8406`.
- **Achado de processo:** o primeiro "Criar plano de escrita" varreu
  **329 arquivos reais** do acervo (cidade/país já inferido do nome de
  pasta/álbum em sugestões aprovadas antes desta sessão — achado
  legítimo, não bug). Sem endpoint de descarte/escopo no produto hoje.
  Resolvido com o próprio mecanismo D-02 (seleção explícita de item):
  `POST /api/exif/{id}/executar` com `itens` contendo só os 3 IDs de
  teste, nunca os 325 reais — nenhum arquivo do acervo real foi tocado
  ou teve sugestão aprovada além do necessário para o teste.
- **Resultado da gravação:**
  - `IMG_5875.CR2`: gravado com sucesso, backup `_original` limpo após
    diff aprovar.
  - `IMG_8638-Aprimorado-NR.dng`: formato reprovado (D-077) → fallback
    sidecar `.xmp` funcionou, cidade/país gravados no sidecar, original
    intocado.
  - `ACM_7122.JPG`: **achado real** — reprovou por `IPTC:EnvelopeRecordVersion`
    não catalogado (ver Task 3/D-078 abaixo). Corrigido durante este
    plano.
- Idempotência confirmada: reexecutar o plano sobre os mesmos itens
  mostra os campos já gravados como `pulado — já preenchido`, sem
  segunda escrita.
- Checkbox de opt-out (D-02) exercitado na prática via seleção
  explícita de itens (equivalente funcional ao desmarcar linhas na UI).

**Divergência da UI-SPEC:** nenhuma. Copywriting Contract e Row anatomy
bateram com o que a tela mostrou (badge "formato não suportado" com
motivo visível, oferta de sidecar, chips por campo).

### Task 3 — Leitura de volta na ferramenta real (checkpoint humano, bloqueante)

Premissa de D-075 testada: cidade/país gravados em `IMG_5875.CR2`
confirmados via `exiftool -City -Country` lendo o arquivo depois da
escrita — `City: Rio de Janeiro`, `Country: Brasil` presentes. Dono
confirmou via Finder na fixture inicial (checkpoint anterior a este
plano, mesmo dia).

**Achado real desta task** (não estava no roteiro original, descoberto
ao testar contra arquivo real de produção, não sintético):
`ACM_7122.JPG` (cópia de foto real da Canon R6m2) reprovou a verificação
por `IPTC:EnvelopeRecordVersion` — tag de versão de andaime do registro
IPTC (mesma classe de `ApplicationRecordVersion`, já aceita), não
catalogada até então. A escrita em si funcionou (cidade/país presentes
no arquivo, confirmado), mas o sistema recusou por segurança (fail-safe
correto — nunca aprova por omissão). Corrigido nesta sessão: tag
adicionada a `TAGS_ESTRUTURAIS_ESPERADAS`, 2 testes de regressão, D-078
registrada em `docs/DECISOES.md`, suíte inteira revalidada (939 testes).

**Achado secundário, registrado como pendência (não corrigido, decisão
arquitetural fora de escopo desta correção):** arquivos com bloco IPTC
pré-existente (ex.: já editados no Lightroom antes de entrar no Foto
Organizer) disparam um aviso NOVO do exiftool
(`"IPTCDigest is not current"`) que reprova pelo critério de avisos do
D-04 — mecanismo diferente do allowlist de tags. Não existe hoje
allowlist equivalente para avisos. Documentado em D-078 e em
`STATE.md` Blockers/Concerns — extensão real no acervo do dono não
medida ainda.

## Requirements

EXIF-01, EXIF-02, EXIF-03, EXIF-04, EXIF-05 — todos com comportamento
fim-a-fim confirmado nesta task, contra arquivo real (não só teste
unitário): dry-run lista campos vazios, escreve só campo vazio, verifica
por diff, registra falha parcial, oferece sidecar pra formato não
suportado.

## Decisões e correções registradas nesta fase

- D-075 (autoriza a fase), D-076 (allowlist medida, zero formatos
  aprovados inicialmente), D-077 (verificação byte-a-byte reabilita
  jpg/cr2), D-078 (EnvelopeRecordVersion catalogado; achado do
  IPTCDigest de arquivo pós-Lightroom registrado como pendência).

## Riscos abertos, não bloqueantes para fechar a fase

1. Aviso `IPTCDigest is not current` em arquivo com IPTC pré-existente
   (provável indicador de edição prévia em Lightroom) — extensão no
   acervo real não medida. Ver D-078 e STATE.md.
2. `.dng` e `.tif` seguem fora do escopo de escrita direta (D-077),
   fallback sidecar XMP disponível.
3. `.cr3`/`.heic` sem amostra testável no acervo atual (D-09) — mesmo
   fallback.

## Verificação

- `scripts/verificar.sh`: ✅ Fatia verde.
- Os dois checkpoints humanos: respondidos com evidência real (dono +
  orquestrador, sessão ao vivo), não simulados.
