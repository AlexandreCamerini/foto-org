import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { useJob } from "./useJob";
import { EventSourceFalso } from "../test/setup";
import { erro, servirApi } from "../test/servidor";

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

describe("useJob — janela entre o clique e a resposta do POST (A1/D-090)", () => {
  it("fica 'rodando' desde o clique, antes do POST responder", async () => {
    // Sem isto, um botão com `disabled={!podeX || job.rodando}` não
    // protegia nada entre o clique e a resposta — o duplo clique real que
    // iniciava duas threads no servidor (D-090) passava batido pelo botão
    // "desabilitado" a olho nu.
    servirApi({
      "/api/operacoes/1/executar": { status: "rodando", tipo: "operacao" },
    });
    const { result } = renderHook(() => useJob(), { wrapper });

    expect(result.current.rodando).toBe(false);
    let promessa!: Promise<void>;
    act(() => {
      promessa = result.current.executarPlano(1);
    });
    expect(result.current.rodando).toBe(true);

    await act(async () => {
      await promessa;
    });
    expect(result.current.rodando).toBe(true); // servidor confirmou "rodando"
  });

  it("um POST que falha ainda libera o guard (finally cobre o 409 engolido)", async () => {
    servirApi({
      "/api/operacoes/1/executar": erro(409, "já tem um job rodando"),
    });
    const { result } = renderHook(() => useJob(), { wrapper });

    await act(async () => {
      await expect(result.current.executarPlano(1)).rejects.toThrow();
    });
    expect(result.current.rodando).toBe(false);
  });
});
