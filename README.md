# Foto Organizer

App desktop para macOS que cataloga, analisa e organiza (de forma
**assistida e não destrutiva**) grandes coleções de fotos espalhadas por
pastas e volumes. 100% local: sem conta, sem nuvem, sem telemetria.

Princípio central: **primeiro catalogar, depois sugerir, então revisar e
somente por último executar operações físicas** — e mesmo então, apenas
cópias verificadas por hash. O app nunca move, renomeia, altera ou exclui
uma foto original.

## O que ele faz

- **Cataloga** JPEG/PNG/HEIC/HEIF/HIF/TIFF/WebP e RAW (DNG, CR2, CR3, NEF,
  ARW, RAF, ORF, RW2) sem tocar nos originais, com varredura incremental,
  pausável e retomável.
- **Extrai** EXIF (data de captura, câmera, lente, GPS), dimensões e datas
  do filesystem; RAW via libraw (inclusive CR3).
- **Sugere organização** com evidências estruturadas: geocodificação
  reversa **offline** do GPS, país/cidade pelo nome das pastas, viagens por
  lacuna temporal, tudo com nível de confiança e justificativa ("o país
  veio do GPS", "a cidade veio da pasta, confiança média").
- **Cruza fontes** para usar a informação mais correta disponível: importa
  os catálogos do **Apple Fotos** (leitura local, opt-in) e do **Google
  Takeout** (pasta exportada, sem rede) e correlaciona a linha do tempo —
  a foto da câmera sem GPS herda a localização da foto do telefone tirada
  minutos antes, com deriva de relógio corrigida automaticamente e
  evidência dizendo de onde veio.
- **Detecta duplicatas** em 4 níveis: idênticas (SHA-256), mesmo conteúdo
  (phash igual), visualmente parecidas e sequências/rajadas (mesma câmera
  em segundos) — revisão lado a lado, nunca exclusão automática. A mesma
  foto em duas fontes é tratada como vínculo entre catálogos, não lixo.
- **Planeja e executa cópias** com dry-run obrigatório, sobrescrita
  impossível (criação exclusiva no SO), verificação de hash antes/depois e
  audit log completo.

## Instalação e execução

Requisitos: macOS, Python 3.12+ (`brew install python@3.12` se faltar).

```bash
scripts/instalar.sh          # uma vez (use --llm p/ incluir o advisor Claude)
scripts/executar.sh          # abre a interface gráfica
scripts/atualizar.sh         # traz código novo + re-sincroniza dependências
```

A CLI usa o mesmo lançador:

```bash
scripts/executar.sh scan ~/Pictures/MinhasFotos   # varredura headless
scripts/executar.sh bench -n 1000                 # benchmark de indexação
```

> Preferindo comandos diretos: `.venv/bin/python -m fotoorganizer` (no
> macOS, `python` sem o 3 só existe dentro do venv — os scripts cuidam
> disso por você).

Dados do app: `~/Library/Application Support/FotoOrganizer/` (catálogo
SQLite, config.toml, logs) e `~/Library/Caches/FotoOrganizer/`
(miniaturas). Apagar essas pastas remove o catálogo por completo sem
afetar nenhuma foto.

## Dados de demonstração

Nunca use fotos pessoais para testar: gere uma biblioteca sintética.

```bash
python scripts/gerar_demo.py /tmp/demo_fotos
python -m fotoorganizer   # adicione /tmp/demo_fotos como fonte
```

## Fluxo de uso

1. **Biblioteca** — adicione pastas; a varredura roda em background com
   progresso, pausa e retomada. Filtre por data, tipo, fonte e busca.
2. **Revisão** — gere sugestões; cada uma mostra destino proposto, badge
   de confiança e o painel "por quê?" com as evidências. Aprove, rejeite
   ou edite (em lote, com desfazer).
3. **Duplicatas** — detecte e resolva lado a lado (principal/versão/
   ignorar).
4. **Operações** — escolha o destino, crie o plano das aprovadas, rode o
   dry-run (obrigatório) e execute a cópia verificada.

## Testes

```bash
.venv/bin/python -m pytest
```

A suíte usa apenas arquivos sintéticos gerados em tempo de teste — nenhuma
fotografia real no repositório.

## Documentação

- [Guia do projeto (CLAUDE.md)](CLAUDE.md) — invariantes de segurança e stack
- [Arquitetura, schema e decisões](docs/ARQUITETURA.md)
- [Sistema de confiança](docs/CONFIANCA.md)
- [Privacidade](docs/PRIVACIDADE.md)
- [Roadmap](docs/ROADMAP.md)
- [Direção de arte](docs/DIRECAO_DE_ARTE.md)
- [Empacotamento (.app)](docs/EMPACOTAMENTO.md)
