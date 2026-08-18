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
import type {
  CandidataGenaiPasta,
  ConfigGenaiPasta,
  CustoGenaiPasta,
  PropostaGenaiPasta,
} from "../api";
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

function proposta(
  pasta: string,
  campo: PropostaGenaiPasta["campo"],
  valor_proposto: string,
  justificativa = "justificativa de teste",
): PropostaGenaiPasta {
  return { pasta, campo, valor_antes: null, valor_proposto, justificativa };
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

/** Monta o assistente já com config/candidatas/custo de fundo prontos —
 * cada teste só precisa fornecer `/api/genai-pasta/rodar` (e, quando
 * quiser, `/api/genai-pasta/aprovar`) para chegar no passo 4. */
function servirEMontar(
  extra: Record<string, unknown>,
  onFechar: () => void = vi.fn(),
) {
  const chamadas = servirApi({
    "/api/genai-pasta/config": config(true, true),
    "/api/genai-pasta/candidatas": [candidata("/fotos/a", 10, ["categoria"])],
    "/api/genai-pasta/estimar-custo": custo(),
    ...extra,
  });
  const usuario = userEvent.setup();
  montar(<ClassificacaoPasta onFechar={onFechar} />);
  return { usuario, chamadas };
}

/** Passos 1 e 2 percorridos com um clique cada — o que os testes do passo 4
 * têm em comum, não o que cada um testa. */
async function irParaRevisao(usuario: ReturnType<typeof userEvent.setup>) {
  await usuario.click(await screen.findByRole("button", { name: "Avançar" }));
  await usuario.click(
    await screen.findByRole("button", { name: "Confirmar e classificar" }),
  );
  await screen.findByText(/^Revisão — /);
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

  it("propostas nascem todas marcadas", async () => {
    const { usuario } = servirEMontar({
      "/api/genai-pasta/rodar": {
        propostas: [
          proposta("/fotos/a", "categoria", "Viagens"),
          proposta("/fotos/b", "cidade", "Lisboa"),
        ],
        pastas_sem_resposta: [],
        custo_real: null,
      },
    });
    await irParaRevisao(usuario);

    expect(
      await screen.findByText("2 de 2 propostas selecionadas"),
    ).toBeInTheDocument();
  });

  it("pastilha de origem aparece na linha depois", async () => {
    const { usuario } = servirEMontar({
      "/api/genai-pasta/rodar": {
        propostas: [
          proposta("/fotos/a", "categoria", "Viagens"),
          proposta("/fotos/b", "cidade", "Lisboa"),
        ],
        pastas_sem_resposta: [],
        custo_real: null,
      },
    });
    await irParaRevisao(usuario);

    expect(screen.getAllByText("IA · pasta")).toHaveLength(2);
  });

  it("duas propostas da mesma pasta viram uma linha", async () => {
    const { usuario } = servirEMontar({
      "/api/genai-pasta/rodar": {
        propostas: [
          proposta("/fotos/a", "categoria", "Viagens"),
          proposta("/fotos/a", "cidade", "Lisboa"),
        ],
        pastas_sem_resposta: [],
        custo_real: null,
      },
    });
    await irParaRevisao(usuario);

    expect(screen.getAllByText("/fotos/a")).toHaveLength(1);
    expect(screen.getAllByText(/^depois:/)).toHaveLength(2);
    expect(
      await screen.findByText("1 de 1 propostas selecionadas"),
    ).toBeInTheDocument();
  });

  it("resumo de sem-resposta é uma linha só", async () => {
    const { usuario } = servirEMontar({
      "/api/genai-pasta/rodar": {
        propostas: [proposta("/fotos/a", "categoria", "Viagens")],
        pastas_sem_resposta: ["/fotos/x", "/fotos/y"],
        custo_real: null,
      },
    });
    await irParaRevisao(usuario);

    expect(
      screen.getAllByText(/pastas sem resposta confiável/),
    ).toHaveLength(1);
    // Nenhuma linha em branco para as pastas sem resposta — os nomes só
    // aparecem depois de "Ver quais »" expandir a lista (D-06).
    expect(screen.queryByText("/fotos/x")).not.toBeInTheDocument();
    expect(screen.queryByText("/fotos/y")).not.toBeInTheDocument();
  });

  it("sem pastas sem resposta, sem linha de resumo", async () => {
    const { usuario } = servirEMontar({
      "/api/genai-pasta/rodar": {
        propostas: [proposta("/fotos/a", "categoria", "Viagens")],
        pastas_sem_resposta: [],
        custo_real: null,
      },
    });
    await irParaRevisao(usuario);

    expect(
      screen.queryByText(/pastas sem resposta confiável/),
    ).not.toBeInTheDocument();
  });

  it("Ver quais expande os nomes", async () => {
    const { usuario } = servirEMontar({
      "/api/genai-pasta/rodar": {
        propostas: [proposta("/fotos/a", "categoria", "Viagens")],
        pastas_sem_resposta: ["/fotos/x"],
        custo_real: null,
      },
    });
    await irParaRevisao(usuario);

    expect(screen.queryByText("/fotos/x")).not.toBeInTheDocument();
    await usuario.click(screen.getByText("Ver quais »"));
    expect(await screen.findByText("/fotos/x")).toBeInTheDocument();
  });

  it("aprovar envia só as marcadas", async () => {
    const { usuario, chamadas } = servirEMontar({
      "/api/genai-pasta/rodar": {
        propostas: [
          proposta("/fotos/a", "categoria", "Viagens"),
          proposta("/fotos/b", "cidade", "Lisboa"),
        ],
        pastas_sem_resposta: [],
        custo_real: null,
      },
      "/api/genai-pasta/aprovar": { aprovadas: 1, descartadas: 1 },
    });
    await irParaRevisao(usuario);

    await usuario.click(
      screen.getByRole("checkbox", { name: "Aprovar proposta para /fotos/a" }),
    );
    await usuario.click(
      await screen.findByRole("button", { name: "Aprovar 1 selecionadas" }),
    );

    const chamadaAprovar = await vi.waitFor(() => {
      const achada = chamadas.find(
        (chamada) => chamada.caminho === "/api/genai-pasta/aprovar",
      );
      if (!achada) throw new Error("aprovar ainda não chamado");
      return achada;
    });
    expect(chamadaAprovar.corpo).toEqual({ pastas: ["/fotos/b"] });
  });

  it("fechar sem aprovar não chama aprovar", async () => {
    const onFechar = vi.fn();
    const { usuario, chamadas } = servirEMontar(
      {
        "/api/genai-pasta/rodar": {
          propostas: [proposta("/fotos/a", "categoria", "Viagens")],
          pastas_sem_resposta: [],
          custo_real: null,
        },
      },
      onFechar,
    );
    await irParaRevisao(usuario);

    await usuario.click(
      screen.getByRole("button", { name: "Fechar sem aprovar" }),
    );

    expect(onFechar).toHaveBeenCalled();
    expect(
      chamadas.some((c) => c.caminho === "/api/genai-pasta/aprovar"),
    ).toBe(false);
  });

  it("abre no passo 4 quando há proposta pendente", async () => {
    servirApi({
      "/api/genai-pasta/config": config(true, true),
      "/api/genai-pasta/propostas": [
        proposta("/fotos/a", "categoria", "Viagens"),
      ],
    });
    montar(<ClassificacaoPasta onFechar={vi.fn()} />);

    expect(await screen.findByText(/^Revisão — /)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Avançar" }),
    ).not.toBeInTheDocument();
  });

  it("passo concluído mostra a frase de expectativa", async () => {
    const { usuario } = servirEMontar({
      "/api/genai-pasta/rodar": {
        propostas: [proposta("/fotos/a", "categoria", "Viagens")],
        pastas_sem_resposta: [],
        custo_real: null,
      },
      "/api/genai-pasta/aprovar": { aprovadas: 1, descartadas: 0 },
    });
    await irParaRevisao(usuario);

    await usuario.click(
      await screen.findByRole("button", { name: "Aprovar 1 selecionadas" }),
    );

    expect(
      await screen.findByText(
        "As sugestões aparecem em Revisão na próxima geração de sugestões.",
      ),
    ).toBeInTheDocument();
  });
});
