# Privacidade

## Compromissos

- **Advisor LLM (opcional, desligado por padrão).** Com
  `[privacidade] servicos_externos = true`, sessões que as regras locais
  não classificam podem ser consultadas na API da Anthropic — enviando
  APENAS metadados (nomes de pastas/arquivos, datas, contagem, nomes de
  lugares já resolvidos), nunca a imagem. A credencial vem do ambiente
  (Keychain/`ANTHROPIC_API_KEY`), jamais do código. Detalhes em
  docs/AGRUPAMENTO.md §3.
- **Classificação de pasta por GenAI (opcional, desligada por padrão, dois
  consentimentos).** Sob dois flags — a chave mestra
  `[privacidade] servicos_externos = true` no TOML **E** o opt-in próprio do
  recurso `classificacao_pasta_genai` (gravado por checkbox na própria tela,
  em `application_settings`, nunca no TOML) — o dono pode pedir que o Claude
  Sonnet 5 (API da Anthropic) sugira cidade, país, categoria e evento para
  pastas cuja hierarquia local não resolveu sozinha. Os dois flags precisam
  estar ligados; um só não basta (a mesma disciplina de dois consentimentos
  que abriu esse recurso, para não repetir o gate de um flag só que
  `jobs.py::_advisor` usa para o Advisor de cluster).
  - **O que sai da máquina, por pasta candidata:** nome da pasta, contagem de
    fotos, período (data mais antiga/mais recente), a lista dos campos a
    preencher e quais campos já estão preenchidos (`ja_conhecido`, para o
    modelo nunca reafirmar o que já se sabe). **Nenhuma imagem, byte de
    imagem, miniatura ou caminho de arquivo sai.** O payload é montado por
    allowlist literal (nunca serialização genérica de objeto) e o teste
    `tests/test_classification_pasta_genai.py::test_payload_nunca_envia_imagem`
    prova isso: verifica por igualdade de conjunto que só as cinco chaves
    (`pasta`, `n_fotos`, `periodo`, `campos_a_preencher`, `ja_conhecido`)
    saem no corpo da chamada, e varre cada valor contra uma lista de termos
    proibidos (`caminho`, `thumb`, `miniatura`, `base64`, `image`, `.jpg`,
    `.cr2`, `.heic`) — a declaração de privacidade deste projeto aponta para
    essa prova, não só afirma.
  - **Para quê:** preencher cidade/país/categoria/evento em pastas onde as
    regras determinísticas (nome de pasta, GPS, geocoding offline, vizinhança
    de sessão) e o Advisor de cluster já falharam — sempre como último
    recurso da cascata (`origem="llm_pasta"` em `Evidence`), nunca substitui
    um valor já resolvido por outra fonte.
  - **Para onde:** API da Anthropic, modelo `claude-sonnet-5`, thinking
    desabilitado, UMA chamada por sessão para todas as pastas confirmadas de
    uma vez (nunca uma chamada por pasta).
  - **Quando exatamente a transmissão acontece (D-079, decisão híbrida do
    dono):** a prévia de custo (passo 2 do assistente) usa uma contagem de
    tokens LOCAL, deliberadamente conservadora — nada sai da máquina antes de
    "Confirmar e classificar". A alternativa óbvia (`client.messages
    .count_tokens`) foi descartada porque ela mesma já transmite o payload
    inteiro só para contar, o que violaria o critério "nada é enviado antes
    de confirmar" mesmo sem gastar dinheiro. Só depois que o dono confirma,
    `contar_exato()` roda — imediatamente antes de `messages.create`, a mesma
    chamada de rede que já ia acontecer, com a contagem exata de entrada
    aproveitada dessa mesma transmissão consentida — e o número exato aparece
    no resumo pós-execução (passo 5), não na prévia.
  - **Sob quais dois consentimentos:** ver acima — mestre (`servicos_externos`,
    TOML) e opt-in do recurso (`classificacao_pasta_genai`,
    `application_settings`, D-080).
  - **Como revogar:** link "Desligar" na própria tela do assistente
    (desliga `classificacao_pasta_genai` na hora, sem reiniciar); ou desligar
    `[privacidade] servicos_externos` no TOML (mestre, derruba este e todos
    os outros recursos externos, incluindo o Advisor de cluster) e reiniciar
    o servidor. Propostas já persistidas (aprovadas ou não) não são apagadas
    ao revogar — revogar impede sessões NOVAS, não desfaz classificações já
    aprovadas (isso é decisão separada do dono na tela de revisão).
- **Tudo local por padrão.** Catálogo, miniaturas, logs e config vivem em
  `~/Library/Application Support/FotoOrganizer` e
  `~/Library/Caches/FotoOrganizer`. Nenhuma foto ou metadado sai da máquina
  sem opt-in explícito (`[privacidade] servicos_externos`, desligado por
  padrão) — e, quando ligado, a UI indica visualmente o que será enviado e
  permite cancelar.
- **Catálogos externos sem rede.** A importação do Apple Fotos lê a
  biblioteca local via osxphotos (somente leitura; exige Acesso Total ao
  Disco concedido pelo usuário) e a do Google Photos usa a pasta do
  Google Takeout que o usuário baixou — o app não fala com a API do
  Google nem com o iCloud. O cruzamento de informações entre fontes
  (herança de GPS, deriva de relógio) acontece inteiramente no catálogo
  local e vira evidência revisável; nada é escrito de volta nos arquivos
  nem nos catálogos de origem.
- **Sem telemetria.** O app não coleta uso, não liga para casa, não tem conta.
- **Logs sem conteúdo sensível.** Logs registram eventos e caminhos de
  arquivo (necessários para diagnóstico local), nunca conteúdo de imagem,
  coordenadas GPS ou nomes de pessoas.
- **Sem segredos no código.** Chaves de serviços externos (se um dia
  configurados) vão para o Keychain do macOS, nunca para arquivos do repo.
- **Reversível.** O catálogo e o cache podem ser apagados por completo sem
  tocar nas fotos originais (o app nunca as modifica — ver CLAUDE.md).

## Dados biométricos (rostos)

Recurso opcional e desativado por padrão. Quando habilitado:

- processamento 100% local; nenhuma busca de identidade na internet;
- embeddings faciais gravados criptografados (chave no Keychain);
- apagar um perfil remove pessoa + embeddings + ocorrências (cascade);
- resultados são sempre sugestão; associação de nome exige confirmação.

## Limitações honestas da criptografia local

Num app desktop, a chave de criptografia precisa estar acessível ao próprio
app — quem tem a sessão do usuário desbloqueada tem, na prática, acesso aos
dados. A criptografia dos embeddings protege contra leitura do arquivo do
banco fora da sessão (backup copiado, disco acessado por outra conta), não
contra malware rodando como o usuário. Proteções reais complementares:
FileVault ligado e senha de sessão. O app não promete mais do que isso.
