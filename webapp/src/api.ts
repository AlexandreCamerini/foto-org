/** Cliente da API local (127.0.0.1) — tipos espelham fotoorganizer/server. */

export interface Fonte {
  id: number;
  caminho: string;
  apelido: string | null;
  tipo: "pasta" | "apple_photos" | "google_takeout";
  disponivel: boolean;
  fotos: number;
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
  itens: SugestaoRow[];
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

export const api = {
  status: () =>
    json<{ versao: string; total: number; erros: number; fontes: number }>(
      "/api/status",
    ),
  fontes: () => json<Fonte[]>("/api/fontes"),
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
  opcoesFiltros: () =>
    json<{ extensoes: string[]; anos: number[] }>("/api/midia/filtros"),
  panorama: () => json<PanoramaDados>("/api/panorama"),
  viagens: () => json<Agrupamento[]>("/api/viagens"),
  eventos: () => json<Agrupamento[]>("/api/eventos"),
  sugestoes: (status: string, offset = 0, limit = 200) =>
    json<PaginaSugestoes>(
      `/api/sugestoes?status=${status}&offset=${offset}&limit=${limit}`,
    ),
  acaoSugestoes: (ids: number[], acao: string) =>
    post<{ afetadas: number }>("/api/sugestoes/acao", { ids, acao }),
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
