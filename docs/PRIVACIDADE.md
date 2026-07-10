# Privacidade

## Compromissos

- **Tudo local por padrão.** Catálogo, miniaturas, logs e config vivem em
  `~/Library/Application Support/FotoOrganizer` e
  `~/Library/Caches/FotoOrganizer`. Nenhuma foto ou metadado sai da máquina
  sem opt-in explícito (`[privacidade] servicos_externos`, desligado por
  padrão) — e, quando ligado, a UI indica visualmente o que será enviado e
  permite cancelar.
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
