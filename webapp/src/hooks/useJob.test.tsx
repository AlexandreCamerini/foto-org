import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { useJob } from "./useJob";
import { EventSourceFalso } from "../test/setup";
import { servirApi } from "../test/servidor";

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

const RODANDO = {
  status: "rodando",
  tipo: "scan",
  processados: 5,
  vistos: 100,
};

describe("useJob — reconexão do SSE", () => {
  it("um erro na conexão não congela os contadores: reassina e segue", async () => {
    const rotas: Record<string, unknown> = { "/api/job": RODANDO };
    servirApi(rotas);
    const { result } = renderHook(() => useJob(), { wrapper });

    // Reconectou ao job em andamento (fluxo que já existia).
    await waitFor(() =>
      expect(EventSourceFalso.instancias).toHaveLength(1),
    );
    act(() => EventSourceFalso.instancias[0].emitir(RODANDO));
    expect(result.current.estado.processados).toBe(5);

    // A rede caiu (Mac dormiu, servidor engasgou). Antes: close() e
    // silêncio para sempre — o sintoma "contadores congelados com o
    // disco girando". Agora: backoff, /api/job, nova assinatura.
    act(() => EventSourceFalso.instancias[0].onerror?.());
    await waitFor(
      () => expect(EventSourceFalso.instancias).toHaveLength(2),
      { timeout: 4000 },
    );

    act(() =>
      EventSourceFalso.instancias[1].emitir({
        ...RODANDO,
        processados: 42,
      }),
    );
    expect(result.current.estado.processados).toBe(42);
  });

  it("se o trabalho terminou durante a queda, mostra o estado final sem reassinar", async () => {
    const rotas: Record<string, unknown> = { "/api/job": RODANDO };
    servirApi(rotas);
    const { result } = renderHook(() => useJob(), { wrapper });
    await waitFor(() =>
      expect(EventSourceFalso.instancias).toHaveLength(1),
    );

    // Enquanto estávamos fora, o job concluiu.
    rotas["/api/job"] = { status: "concluido", tipo: "scan", processados: 100 };
    act(() => EventSourceFalso.instancias[0].onerror?.());

    await waitFor(
      () => expect(result.current.estado.status).toBe("concluido"),
      { timeout: 4000 },
    );
    expect(EventSourceFalso.instancias).toHaveLength(1); // nada novo assinado
  });
});
