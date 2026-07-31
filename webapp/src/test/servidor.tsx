import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";

export interface Chamada {
  caminho: string;
  metodo: string;
  corpo?: unknown;
}

const ERRO_SIMULADO = Symbol("erro-simulado");

interface ErroSimulado {
  [ERRO_SIMULADO]: true;
  status: number;
  corpo: unknown;
}

/** Marca uma rota para responder com um status de erro (409/422/...) em vez
 * de 200 — útil para testar como a UI trata erros de negócio, não só o
 * caminho feliz. */
export function erro(status: number, detail: string): ErroSimulado {
  return { [ERRO_SIMULADO]: true, status, corpo: { detail } };
}

function ehErroSimulado(valor: unknown): valor is ErroSimulado {
  return (
    typeof valor === "object" && valor !== null && ERRO_SIMULADO in valor
  );
}

/** Dublê do servidor local: roteia por pathname e devolve JSON. Rota não
 * declarada responde 404 com a mensagem dizendo qual faltou — teste que
 * quebra por fixture ausente deve dizer isso, não "undefined". */
export function servirApi(rotas: Record<string, unknown>): Chamada[] {
  const chamadas: Chamada[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (entrada: RequestInfo | URL, init?: RequestInit) => {
      const caminho = new URL(String(entrada), "http://127.0.0.1").pathname;
      chamadas.push({
        caminho,
        metodo: init?.method ?? "GET",
        corpo: init?.body ? JSON.parse(String(init.body)) : undefined,
      });
      const corpo = rotas[caminho];
      const cabecalhos = { "content-type": "application/json" };
      if (corpo === undefined) {
        return new Response(
          JSON.stringify({ detail: `rota não simulada: ${caminho}` }),
          { status: 404, headers: cabecalhos },
        );
      }
      if (ehErroSimulado(corpo)) {
        return new Response(JSON.stringify(corpo.corpo), {
          status: corpo.status,
          headers: cabecalhos,
        });
      }
      return new Response(JSON.stringify(corpo), {
        status: 200,
        headers: cabecalhos,
      });
    }),
  );
  return chamadas;
}

export function montar(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

/** Catálogo mínimo que faz qualquer tela renderizar. */
export const ROTAS_BASE: Record<string, unknown> = {
  "/api/status": { versao: "0.1.0", total: 8, erros: 0, fontes: 1 },
  "/api/fontes": [
    {
      id: 1,
      caminho: "/Users/eu/Pictures/bagunca",
      apelido: null,
      tipo: "pasta",
      disponivel: true,
      fotos: 8,
    },
  ],
  "/api/job": { status: "nenhum" },
  "/api/midia": { total: 0, offset: 0, itens: [] },
  "/api/midia/filtros": { extensoes: ["jpg"], anos: [2024] },
  "/api/viagens": [],
  "/api/eventos": [],
  "/api/sugestoes": { contagens: {}, itens: [] },
  "/api/duplicatas": [],
  "/api/operacoes": [],
  "/api/panorama": {
    total: 8,
    lacunas: [
      { chave: "sem_data", rotulo: "sem data de captura", quantidade: 3 },
      { chave: "sem_gps", rotulo: "sem coordenada", quantidade: 6 },
      { chave: "erro_leitura", rotulo: "erro ao ler o arquivo", quantidade: 0 },
    ],
    por_ano: [
      { chave: "2024", quantidade: 5 },
      { chave: "sem data", quantidade: 3 },
    ],
    por_camera: [{ chave: "TestMake TestModel", quantidade: 5 }],
    por_extensao: [{ chave: "jpg", quantidade: 8 }],
    cruzamento_ano_fonte: [
      { ano: "2024", source_id: 1, quantidade: 5 },
      { ano: "sem data", source_id: 1, quantidade: 3 },
    ],
  },
};
