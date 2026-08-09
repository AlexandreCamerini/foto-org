/** Cliente da API local (127.0.0.1) — tipos espelham fotoorganizer/server. */

export interface Fonte {
  id: number;
  caminho: string;
  apelido: string | null;
  tipo: "pasta" | "apple_photos" | "google_takeout";
  disponivel: boolean;
  fotos: number;
}

/** O volume desta fonte voltou montado noutro ponto (`/Volumes/photo` →
 *  `/Volumes/photo 1`) — dá para reapontar o catálogo em vez de recatalogar. */
export interface Reapontamento {
  source_id: number;
  apelido: string;
  prefixo_antigo: string;
  prefixo_novo: string;
}

export interface PreviaReapontamento {
  source_id: number;
  apelido: string;
  prefixo_antigo: string;
  prefixo_novo: string;
  /** Só as linhas que de fato começam com `prefixo_antigo` — não o total
   *  de mídia da fonte. */
  total_media_files: number;
  /** Referências sem esse prefixo (ex. `apple://uuid`, `lightroom://uuid`)
   *  que ficam intocadas — a fonte tem mais mídia do que o que vai mudar. */
  total_ignoradas_sem_prefixo: number;
  amostra: { antigo: string; novo: string }[];
}

export interface Media {
  id: number;
  nome: string;
  caminho: string;
  pasta: string;
  extensao: string;
  tamanho: number;
  data_capturada: string | null;
  make: string | null;
  model: string | null;
  lente: string | null;
  largura: number | null;
  altura: number | null;
  gps_lat: number | null;
  gps_lon: number | null;
  source_id: number;
  trip_id: number | null;
  event_id: number | null;
  erro_leitura: string | null;
  /** Por que esta foto não pode ser aberta agora; `null` quando pode. A
   *  grade precisa separar "miniatura ainda vindo" de "não tenho o arquivo" —
   *  sem isso desenha imagem quebrada e o usuário conclui que o app quebrou. */
  motivo_indisponivel: string | null;
  /** foto | captura | recebida | baixada. null = não avaliado. */
  tipo_imagem: string | null;
  /** true = o detector opinou e você ainda não respondeu. */
  tipo_provisorio: boolean;
  /** true quando a coordenada veio de outra câmera, não do arquivo. */
  gps_estimado: boolean;
  gps_lat_efetivo: number | null;
  gps_lon_efetivo: number | null;
  /** Ausente quando a foto não tem lugar resolvido. */
  local?: {
    pais: string | null;
    regiao: string | null;
    cidade: string | null;
    fonte: string;
    estimado: boolean;
    /** Até onde o lugar pode ser afirmado: "cidade" | "regiao" | "pais".
     *  Lugar herdado de horas atrás diz o país, não a cidade (D-025). */
    granularidade: string | null;
  };
  /** Só no detalhe, e só quando a coordenada foi herdada: de quem veio e a
   *  que distância no tempo. É o que torna a estimativa auditável. */
  estimativa?: {
    doadora_id: number;
    doadora_nome: string;
    doadora_camera: string | null;
    delta_s: number | null;
    lat: number | null;
    lon: number | null;
  };
}

export interface Evidencia {
  campo: string;
  origem: string;
  valor: string;
  nivel: "alta" | "media" | "baixa";
  score: number;
  justificativa: string;
}

export interface Sugestao {
  id: number;
  destino: string;
  nivel: "alta" | "media" | "baixa";
  status: string;
  evidencias: Evidencia[];
}

export type MediaDetalhe = Media & { sugestao?: Sugestao };

/** Tudo que estava gravado no arquivo, agrupado por padrão. */
export interface NamespaceMetadados {
  nome: string;
  rotulo: string;
  itens: { chave: string; valor: string }[];
}

export interface Metadados {
  total: number;
  namespaces: NamespaceMetadados[];
}

export interface PaginaMidia {
  total: number;
  offset: number;
  itens: Media[];
}

export interface FiltrosMidia {
  busca?: string;
  extensao?: string;
  source_id?: number;
  ano?: number;
  trip_id?: number;
  event_id?: number;
  lacuna?: string;
  ordenacao?: string;
  /** "tudo" | "organizaveis" | "faltantes". Uma foto sem arquivo continua
   *  fora da revisão e do plano — aqui se decide se ela é VISÍVEL. */
  alcance?: string;
  /** "2026-05" — a âncora temporal salta filtrando, não rolando. */
  mes?: string;
}

export interface MesDaLinha {
  mes: string;
  quantidade: number;
}

export interface Faceta {
  chave: string;
  quantidade: number;
}

/** Lacuna = o que impede a foto de se organizar sozinha. Cada uma é um
 * filtro pronto: o número na tela e o conjunto filtrado são o mesmo. */
export interface Lacuna extends Faceta {
  rotulo: string;
}

export interface CelulaCruzamento {
  ano: string;
  source_id: number;
  quantidade: number;
}

export interface PanoramaDados {
  total: number;
  lacunas: Lacuna[];
  por_ano: Faceta[];
  por_camera: Faceta[];
  por_extensao: Faceta[];
  cruzamento_ano_fonte: CelulaCruzamento[];
}

export interface Agrupamento {
  id: number;
  nome: string;
  inicio: string | null;
  fim: string | null;
  metodo: string;
  fotos: number;
  capa_id: number | null;
}

/** Uma foto no mapa. `estimado=false` é ponto cheio (coordenada lida do
 *  arquivo) e `raio_m` é null; `estimado=true` é círculo, e `raio_m` é o
 *  tamanho da dúvida. `porque` já vem pronta do servidor — a frase cita o
 *  raio e a velocidade que a produziram, e remontá-la aqui duplicaria as
 *  constantes da calibração. */
export interface PontoMapa {
  media_id: number;
  nome: string;
  lat: number;
  lon: number;
  data_capturada: string | null;
  camera: string | null;
  /** Arquivo inalcançável (disco desligado, iCloud). A COORDENADA continua
   *  válida — o ponto é desenhado, só não tem miniatura. */
  motivo_indisponivel: string | null;
  estimado: boolean;
  raio_m: number | null;
  delta_s: number | null;
  doadora_id: number | null;
  doadora_nome: string | null;
  porque: string | null;
}

/** A foto que emprestou a coordenada. Costuma estar FORA do grupo — no
 *  acervo real é uma referência do Apple Fotos, sem viagem nem evento. */
export interface DoadoraMapa {
  id: number;
  nome: string;
  lat: number;
  lon: number;
  camera: string | null;
  no_grupo: boolean;
}

export interface LimitesMapa {
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
}

export interface EscalaMapa {
  metros_por_grau_lat: number;
  metros_por_grau_lon: number;
}

export interface DadosMapa {
  grupo: {
    tipo: "viagem" | "evento";
    id: number;
    nome: string;
    inicio: string | null;
    fim: string | null;
  };
  /** `no_mapa + sem_coordenada == total`. `fora_de_alcance` é SUBCONJUNTO
   *  de `no_mapa` — não soma com os outros dois. */
  contagens: {
    total: number;
    no_mapa: number;
    sem_coordenada: number;
    fora_de_alcance: number;
  };
  pontos: PontoMapa[];
  doadoras: DoadoraMapa[];
  /** Já esticado pelo raio de cada círculo. Null quando não há ponto. */
  limites: LimitesMapa | null;
  escala: EscalaMapa | null;
  nota_do_raio: string;
}

export interface SugestaoRow {
  id: number;
  media_id: number;
  nome: string;
  pasta: string;
  destino: string;
  nivel: "alta" | "media" | "baixa";
  status: string;
}

export interface PaginaSugestoes {
  contagens: Record<string, number>;
  /** O total do RECORTE, contado no banco. A tela deduzia o tamanho de um
   *  grupo a partir da página carregada e dizia "85 fotos" para um de 597. */
  total: number;
  itens: SugestaoRow[];
}

/** Um destino proposto e o que a decisão sobre ele precisa saber.
 *
 *  A unidade de decisão é o grupo (D-018): no acervo real, 5.048 sugestões
 *  pendentes são 10 destinos, com confiança constante dentro de cada um. */
export interface GrupoSugestoes {
  destino: string;
  total: number;
  nivel: string;
  estimadas: number;
  fora_de_alcance: number;
  origens: { pasta: string; fotos: number }[];
}

/** Plano de cópia: nada sai do lugar até dry-run + aprovação explícita. */
export interface Plano {
  id: number;
  nome: string;
  status: string;
  dry_run_em: string | null;
  criado_em: string;
  total_itens: number;
  concluidos: number;
  com_conflito: number;
  com_erro: number;
  /** Veredito do último dry-run. `com_erro` conta erro de EXECUÇÃO e fica
   *  em zero num plano intransitável — sem estes campos a tela diria
   *  "0 erros" para um plano que não copiaria nada. */
  prontos: number | null;
  problemas: number | null;
  executavel: boolean;
}

export interface ItemPlano {
  id: number;
  origem: string;
  destino: string;
  status: string;
  conflito: string | null;
  erro: string | null;
}

export type PlanoDetalhe = Plano & { itens: ItemPlano[] };

export interface RelatorioDryRun {
  prontos: number;
  problemas: string[];
  bytes_necessarios: number;
  bytes_livres: number | null;
  espaco_suficiente: boolean;
}

export interface LinhaAuditoria {
  id: number;
  quando: string;
  acao: string;
  resultado: string;
  detalhe: Record<string, unknown> | null;
}

/** Template ativo que decide em que pasta cada foto cai ao criar um plano.
 *  `GET` nunca falha por ausência de preferência — cai no default do motor. */
export interface TemplateConfiguravel {
  template: string;
}

/** Um dos dois exemplos fixos do backend: `destino` já vem renderizado por
 *  `render_destino` de verdade — o webapp só mostra o que voltou, nunca
 *  reimplementa a lógica de colapso/dedupe de segmento. */
export interface ExemploPreviewTemplate {
  rotulo: string;
  campos: Record<string, string | null>;
  destino: string;
}

export interface PreviewTemplate {
  exemplos: ExemploPreviewTemplate[];
}

/** Varredura que morreu com o processo — a mais recente de cada fonte.
 *  O servidor carimba no boot; a retomada é um novo scan do mesmo caminho
 *  (o incremental pula o que já foi indexado). */
export interface ScanInterrompido {
  source_id: number;
  caminho: string;
  apelido: string;
  disponivel: boolean;
  quando: string | null;
  vistos: number;
  indexados: number;
}

/** Os degraus entre "o app sabe que existe" e "dá para organizar". Uma
 *  leitura só, para as telas pararem de contar a mesma coisa de jeitos
 *  diferentes — ver `components/Funil.tsx`. */
export interface FunilAcervo {
  conhecidas: number;
  alcancaveis: number;
  organizaveis: number;
  registros: number;
}

async function json<T>(url: string): Promise<T> {
  const resposta = await fetch(url);
  if (!resposta.ok) throw new Error(`${resposta.status} em ${url}`);
  return resposta.json() as Promise<T>;
}

/** POST com a mensagem do servidor preservada — o usuário precisa ler
 * "rode o dry-run antes de executar", não "erro 409". */
async function post<T>(url: string, body?: unknown): Promise<T> {
  const resposta = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.detail ?? `erro ${resposta.status}`);
  return dados as T;
}

/** Mesma ideia do `post`, para edições pontuais (PATCH) — o 422 de um
 * destino inválido também vem com mensagem legível, não só o status. */
async function patch<T>(url: string, body: unknown): Promise<T> {
  const resposta = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.detail ?? `erro ${resposta.status}`);
  return dados as T;
}

/** Mesma ideia do `post`, para substituir um recurso inteiro (PUT) — o 422
 * de um template com placeholder inválido também vem com mensagem legível. */
async function put<T>(url: string, body: unknown): Promise<T> {
  const resposta = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.detail ?? `erro ${resposta.status}`);
  return dados as T;
}

export const api = {
  status: () =>
    json<{ versao: string; total: number; erros: number; fontes: number }>(
      "/api/status",
    ),
  fontes: () => json<Fonte[]>("/api/fontes"),
  /** Fontes fora de alcance porque o volume remontou noutro ponto — a
   *  affordance "reapontar" aparece só para elas. Custa um `diskutil` por
   *  fonte, então a sidebar chama isto sob demanda, não a cada render. */
  reapontamentos: () => json<Reapontamento[]>("/api/fontes/reapontamentos"),
  previaReapontamento: (sourceId: number) =>
    post<PreviaReapontamento>(`/api/fontes/${sourceId}/reapontar/preview`),
  reapontarFonte: (sourceId: number) =>
    post<{
      source_id: number;
      prefixo_antigo: string;
      prefixo_novo: string;
      linhas_media_files: number;
      audit_log_id: number;
    }>(`/api/fontes/${sourceId}/reapontar`, { confirmar: true }),
  midia: (filtros: FiltrosMidia, offset: number, limit: number) => {
    const params = new URLSearchParams();
    for (const [chave, valor] of Object.entries(filtros)) {
      if (valor !== undefined && valor !== "") params.set(chave, String(valor));
    }
    params.set("offset", String(offset));
    params.set("limit", String(limit));
    return json<PaginaMidia>(`/api/midia?${params}`);
  },
  detalhe: (id: number) => json<MediaDetalhe>(`/api/midia/${id}`),
  metadados: (id: number) => json<Metadados>(`/api/midia/${id}/metadados`),
  confirmarTipo: (id: number, tipo: string | null) =>
    post<{ tipo_imagem: string | null; tipo_provisorio: boolean }>(
      `/api/midia/${id}/tipo`,
      { tipo },
    ),
  opcoesFiltros: () =>
    json<{ extensoes: string[]; anos: number[] }>("/api/midia/filtros"),
  panorama: () => json<PanoramaDados>("/api/panorama"),
  inventario: () => json<Inventario>("/api/inventario"),
  linhaDoTempo: (filtros: FiltrosMidia) => {
    const params = new URLSearchParams();
    for (const [chave, valor] of Object.entries(filtros)) {
      if (valor !== undefined && valor !== "") params.set(chave, String(valor));
    }
    return json<MesDaLinha[]>(`/api/midia/linha-do-tempo?${params}`);
  },
  viagens: (sourceId?: number) =>
    json<Agrupamento[]>(`/api/viagens${sourceId ? `?source_id=${sourceId}` : ""}`),
  eventos: (sourceId?: number) =>
    json<Agrupamento[]>(`/api/eventos${sourceId ? `?source_id=${sourceId}` : ""}`),
  /** A geometria do lugar de UM grupo. Exatamente um dos dois ids. */
  mapa: (filtro: { trip_id?: number; event_id?: number }) => {
    const params = new URLSearchParams();
    if (filtro.trip_id !== undefined) params.set("trip_id", String(filtro.trip_id));
    if (filtro.event_id !== undefined)
      params.set("event_id", String(filtro.event_id));
    return json<DadosMapa>(`/api/mapa?${params}`);
  },
  sugestoes: (
    status: string, offset = 0, limit = 200, sourceId?: number,
    /** Recorta um grupo de destino — é o que permite abrir "Dubai" e
     *  paginar dentro das 2.406 sem carregar a fila inteira. */
    destino?: string,
  ) =>
    json<PaginaSugestoes>(
      `/api/sugestoes?status=${status}&offset=${offset}&limit=${limit}` +
        (sourceId ? `&source_id=${sourceId}` : "") +
        (destino ? `&destino=${encodeURIComponent(destino)}` : ""),
    ),
  acaoSugestoes: (ids: number[], acao: string) =>
    post<{ afetadas: number }>("/api/sugestoes/acao", { ids, acao }),
  editarDestino: (id: number, destino: string) =>
    patch<SugestaoRow>(`/api/sugestoes/${id}/destino`, { destino }),
  duplicatas: () => json<GrupoDuplicatas[]>("/api/duplicatas"),
  planos: () => json<Plano[]>("/api/operacoes"),
  plano: (id: number) => json<PlanoDetalhe>(`/api/operacoes/${id}`),
  criarPlano: (raiz_destino: string, nome?: string) =>
    post<Plano>("/api/operacoes", { raiz_destino, nome }),
  dryRun: (id: number) =>
    post<RelatorioDryRun>(`/api/operacoes/${id}/dry-run`),
  auditoria: (id: number) =>
    json<LinhaAuditoria[]>(`/api/operacoes/${id}/auditoria`),
  thumbUrl: (id: number) => `/api/midia/${id}/thumb`,
  previewUrl: (id: number) => `/api/midia/${id}/preview`,
  funil: () => json<FunilAcervo>("/api/funil"),
  scansInterrompidos: () =>
    json<ScanInterrompido[]>("/api/scan/interrompidos"),
  gruposDeSugestoes: (status: string, source_id?: number) =>
    json<GrupoSugestoes[]>(
      `/api/sugestoes/grupos?status=${status}` +
        (source_id != null ? `&source_id=${source_id}` : ""),
    ),
  /** Age sobre o grupo inteiro: a tela manda o destino, o servidor resolve
   *  os ids. Sem isto "Aprovar 597" aprovava as 85 da página carregada. */
  acaoNoGrupo: (destino: string, acao: string, status: string, source_id?: number) =>
    post<{ afetadas: number }>("/api/sugestoes/acao", {
      acao,
      destino,
      status,
      source_id: source_id ?? null,
    }),
  template: () => json<TemplateConfiguravel>("/api/configuracoes/template"),
  salvarTemplate: (template: string) =>
    put<TemplateConfiguravel>("/api/configuracoes/template", { template }),
  previewTemplate: (template: string) =>
    post<PreviewTemplate>("/api/configuracoes/template/preview", { template }),
};

export interface MembroDuplicata {
  member_id: number;
  media_id: number;
  nome: string;
  caminho: string;
  tamanho: number;
  papel: string;
  source_id: number;
}

export interface GrupoDuplicatas {
  id: number;
  nivel: string;
  rotulo: string;
  decidido: boolean;
  bytes_recuperaveis: number;
  n_fontes: number;
  membros: MembroDuplicata[];
}

/** O acervo inteiro — alcançável ou não. A grade responde "o que dá para
 *  abrir agora"; num acervo em NAS e discos externos isso é a minoria. */
export interface Inventario {
  fotos: number;
  alcancaveis: number;
  registros: number;
  sem_caminho: number;
  lugares: {
    raiz: string;
    fotos: number;
    alcancaveis: number;
    so_no_catalogo: number;
    fontes: string[];
  }[];
}
