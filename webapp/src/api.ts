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
  ordenacao?: string;
}

async function json<T>(url: string): Promise<T> {
  const resposta = await fetch(url);
  if (!resposta.ok) throw new Error(`${resposta.status} em ${url}`);
  return resposta.json() as Promise<T>;
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
  thumbUrl: (id: number) => `/api/midia/${id}/thumb`,
  previewUrl: (id: number) => `/api/midia/${id}/preview`,
};
