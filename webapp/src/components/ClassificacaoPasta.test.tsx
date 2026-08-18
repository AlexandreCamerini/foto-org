// As asserções deste arquivo são presas às strings exatas do Copywriting
// Contract da UI-SPEC (07-UI-SPEC.md): é a cópia que o dono lê que precisa
// não regredir — não o estado interno do componente. Checkbox é sempre
// achado por role/label, nunca preso à estrutura do DOM. Mesmo molde de
// EscritaExif.test.tsx (Fase 6): `servirApi`/`montar` do dublê fetch-level,
// nenhum `vi.mock` do módulo `api`.
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ClassificacaoPasta } from "./ClassificacaoPasta";
import type { CandidataGenaiPasta, ConfigGenaiPasta, CustoGenaiPasta } from "../api";
import { erro, montar, servirApi } from "../test/servidor";

function config(
  servicos_externos: boolean,
  classificacao_pasta_genai: boolean,
): ConfigGenaiPasta {
  return { servicos_externos, classificacao_pasta_genai };
}

function candidata(
  pasta: string,
  n_fotos: number,
  campos_ausentes: CandidataGenaiPasta["campos_ausentes"],
): CandidataGenaiPasta {
  return { pasta, n_fotos, campos_ausentes, periodo: null };
}

function custo(extra: Partial<CustoGenaiPasta> = {}): CustoGenaiPasta {
  return {
    tokens_entrada: 3420,
    entrada_exata: false,
    custo_entrada_usd: 0.0068,
    teto_tokens_saida: 6000,
    teto_custo_saida_usd: 0.06,
    teto_custo_total_usd: 0.0668,
    teto_custo_total_brl: 0.334,
    cambio_usd_brl: 5,
    cambio_fonte: "fixo-teste",
    ...extra,
  };
}

/** Dublê que nunca resolve a rota de `rodar` — os testes que precisam
 * observar o passo 3 (não-cancelável) não podem depender de uma corrida
 * entre o clique e a resposta simulada; a chamada fica em voo pelo tempo
 * de vida do teste, exatamente como o passo 3 pressupõe. */
function servirApiComRodarPendente(rotas: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (entrada: RequestInfo | URL) => {
      const caminho = new URL(String(entrada), "http://127.0.0.1").pathname;
      if (caminho === "/api/genai-pasta/rodar") {
        return new Promise<Response>(() => {
          // nunca resolve — o teste só observa o passo 3 renderizado.
        });
      }
      const corpo = rotas[caminho];
      const cabecalhos = { "content-type": "application/json" };
      if (corpo === undefined) {
        return new Response(
          JSON.stringify({ detail: `rota não simulada: ${caminho}` }),
          { status: 404, headers: cabecalhos },
        );
      }
      return new Response(JSON.stringify(corpo), {
        status: 200,
        headers: cabecalhos,
      });
    }),
  );
}

describe("ClassificacaoPasta", () => {
  it("mestre desligado não oferece caixa", async () => {
    servirApi({ "/api/genai-pasta/config": config(false, false) });
    montar(<ClassificacaoPasta onFechar={vi.fn()} />);

    expect(
      await screen.findByText(/Serviços externos estão desligados/),
    ).toBeInTheDocument();
    expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
  });

  it("habilitar exige a caixa marcada", async () => {
    servirApi({ "/api/genai-pasta/config": config(true, false) });
    const usuario = userEvent.setup();
    montar(<ClassificacaoPasta onFechar={vi.fn()} />);

    const habilitar = await screen.findByRole("button", {
      name: "Habilitar e continuar",
    });
    expect(habilitar).toBeDisabled();

    await usuario.click(
      screen.getByLabelText("Habilitar classificação de pasta por IA"),
    );
    expect(habilitar).toBeEnabled();
  });

  it("candidatas nascem todas marcadas", async () => {
    servirApi({
      "/api/genai-pasta/config": config(true, true),
      "/api/genai-pasta/candidatas": [
        candidata("/fotos/a", 10, ["categoria"]),
        candidata("/fotos/b", 20, ["cidade_pais"]),
        candidata("/fotos/c", 30, ["categoria", "cidade_pais"]),
      ],
    });
    montar(<ClassificacaoPasta onFechar={vi.fn()} />);

    expect(
      await screen.findByText("3 de 3 pastas selecionadas"),
    ).toBeInTheDocument();
  });

  it("desmarcar atualiza a contagem e o botão", async () => {
    servirApi({
      "/api/genai-pasta/config": config(true, true),
      "/api/genai-pasta/candidatas": [
        candidata("/fotos/a", 10, ["categoria"]),
        candidata("/fotos/b", 20, ["cidade_pais"]),
        candidata("/fotos/c", 30, ["categoria", "cidade_pais"]),
      ],
    });
    const usuario = userEvent.setup();
    montar(<ClassificacaoPasta onFechar={vi.fn()} />);

    await screen.findByText("3 de 3 pastas selecionadas");
    const checkboxes = screen.getAllByRole("checkbox");
    for (const checkbox of checkboxes) {
      await usuario.click(checkbox);
    }

    expect(
      await screen.findByText("0 de 3 pastas selecionadas"),
    ).toBeInTheDocument();
    const avancar = screen.getByRole("button", { name: "Avançar" });
    expect(avancar).toBeDisabled();
    expect(avancar).toHaveAttribute("title", "Selecione ao menos uma pasta");
  });

  it("etiqueta de campo ausente", async () => {
    servirApi({
      "/api/genai-pasta/config": config(true, true),
      "/api/genai-pasta/candidatas": [
        candidata("/fotos/a", 10, ["categoria"]),
        candidata("/fotos/b", 20, ["cidade_pais"]),
        candidata("/fotos/c", 30, ["categoria", "cidade_pais"]),
      ],
    });
    montar(<ClassificacaoPasta onFechar={vi.fn()} />);

    expect(
      await screen.findByText("categoria · 10 fotos"),
    ).toBeInTheDocument();
    expect(screen.getByText("cidade/país · 20 fotos")).toBeInTheDocument();
    expect(
      screen.getByText("categoria · cidade/país · 30 fotos"),
    ).toBeInTheDocument();
  });

  it("estado vazio", async () => {
    servirApi({
      "/api/genai-pasta/config": config(true, true),
      "/api/genai-pasta/candidatas": [],
    });
    montar(<ClassificacaoPasta onFechar={vi.fn()} />);

    expect(
      await screen.findByText(
        "Nenhuma pasta com categoria ou cidade/país vazios no catálogo atual.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Fechar" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Avançar" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Cancelar" }),
    ).not.toBeInTheDocument();
  });

  it('passo de custo mostra "até" no total', async () => {
    servirApi({
      "/api/genai-pasta/config": config(true, true),
      "/api/genai-pasta/candidatas": [candidata("/fotos/a", 10, ["categoria"])],
      "/api/genai-pasta/estimar-custo": custo(),
    });
    const usuario = userEvent.setup();
    montar(<ClassificacaoPasta onFechar={vi.fn()} />);

    await usuario.click(await screen.findByRole("button", { name: "Avançar" }));

    const total = await screen.findByText(/^até R\$.*\(US\$.*\)$/);
    expect(total).toBeInTheDocument();

    const linhaSaida = screen.getByText("Saída (estimativa):").parentElement;
    expect(linhaSaida?.textContent).toMatch(/^Saída \(estimativa\):até /);
  });

  it("durante a rodada não há como fechar", async () => {
    const onFechar = vi.fn();
    servirApiComRodarPendente({
      "/api/genai-pasta/config": config(true, true),
      "/api/genai-pasta/candidatas": [candidata("/fotos/a", 10, ["categoria"])],
      "/api/genai-pasta/estimar-custo": custo(),
    });
    const usuario = userEvent.setup();
    montar(<ClassificacaoPasta onFechar={onFechar} />);

    await usuario.click(await screen.findByRole("button", { name: "Avançar" }));
    await usuario.click(
      await screen.findByRole("button", { name: "Confirmar e classificar" }),
    );

    expect(
      await screen.findByText(/Consultando Claude Sonnet 5…/),
    ).toBeInTheDocument();

    await usuario.keyboard("{Escape}");
    expect(onFechar).not.toHaveBeenCalled();
    expect(
      screen.queryByRole("button", { name: /Fechar|Cancelar/ }),
    ).not.toBeInTheDocument();
  });

  it("erro do servidor vira a cópia do contrato", async () => {
    servirApi({
      "/api/genai-pasta/config": config(true, true),
      "/api/genai-pasta/candidatas": [candidata("/fotos/a", 10, ["categoria"])],
      "/api/genai-pasta/estimar-custo": custo(),
      "/api/genai-pasta/rodar": erro(502, "modelo indisponível no momento"),
    });
    const usuario = userEvent.setup();
    montar(<ClassificacaoPasta onFechar={vi.fn()} />);

    await usuario.click(await screen.findByRole("button", { name: "Avançar" }));
    await usuario.click(
      await screen.findByRole("button", { name: "Confirmar e classificar" }),
    );

    expect(
      await screen.findByText(
        "Não foi possível classificar: modelo indisponível no momento. " +
          "Nenhum dado foi perdido — tente novamente quando quiser.",
      ),
    ).toBeInTheDocument();
  });
});
