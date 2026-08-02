import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import TemplateEditor from "./TemplateEditor";
import type { Job } from "../hooks/useJob";
import { erro, montar, servirApi } from "../test/servidor";

const TEMPLATE_ATUAL =
  "{categoria}/{ano} - {viagem}/{evento}/{pais}/{regiao}/{cidade}";

function jobParado(sobrescrever: Partial<Job> = {}): Job {
  return {
    estado: { status: "nenhum" },
    rodando: false,
    limpar: vi.fn(),
    escanear: vi.fn(),
    importarApple: vi.fn(),
    importarTakeout: vi.fn(),
    gerarSugestoes: vi.fn(async () => {}),
    detectarDuplicatas: vi.fn(),
    executarPlano: vi.fn(async () => {}),
    cancelar: vi.fn(),
    pausar: vi.fn(async () => {}),
    continuar: vi.fn(async () => {}),
    ...sobrescrever,
  } as Job;
}

const EXEMPLOS_PREVIEW = [
  {
    rotulo: "com viagem",
    campos: { categoria: "Viagens", ano: "2024", viagem: "Tailândia" },
    destino: "Viagens/2024 - Tailândia",
  },
  {
    rotulo: "sem viagem nem evento — cai para país, região, cidade",
    campos: { categoria: "Viagens", ano: "2024", pais: "Tailândia" },
    destino: "Viagens/2024 - Tailândia/Chiang Mai",
  },
];

/** Abre o painel (fechado por padrão) num componente já montado. */
async function abrir() {
  const usuario = userEvent.setup();
  await usuario.click(await screen.findByText("Template do destino"));
  return usuario;
}

describe("TemplateEditor", () => {
  it("mostra o template atual, carregado do servidor", async () => {
    servirApi({
      "/api/configuracoes/template": { template: TEMPLATE_ATUAL },
      "/api/configuracoes/template/preview": { exemplos: EXEMPLOS_PREVIEW },
    });
    montar(<TemplateEditor job={jobParado()} />);

    await abrir();

    expect(await screen.findByLabelText("Template do destino")).toHaveValue(
      TEMPLATE_ATUAL,
    );
  });

  it("preview atualiza com debounce ao digitar, sem uma requisição por tecla", async () => {
    const chamadas = servirApi({
      "/api/configuracoes/template": { template: "" },
      "/api/configuracoes/template/preview": { exemplos: EXEMPLOS_PREVIEW },
    });
    montar(<TemplateEditor job={jobParado()} />);
    const usuario = await abrir();

    const campo = await screen.findByLabelText("Template do destino");
    await usuario.type(campo, "{{ano}");

    expect(
      await screen.findByText("Viagens/2024 - Tailândia"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "sem viagem nem evento — cai para país, região, cidade",
      ),
    ).toBeInTheDocument();

    // Debounce: bem menos requisições de preview do que teclas digitadas
    // ("{ano}" tem 5 caracteres, cada um dispararia uma sem o debounce).
    const chamadasPreview = chamadas.filter(
      (c) => c.caminho === "/api/configuracoes/template/preview",
    );
    expect(chamadasPreview.length).toBeLessThan(5);
  });

  it("salvar chama PUT com o texto do campo", async () => {
    const chamadas = servirApi({
      "/api/configuracoes/template": { template: TEMPLATE_ATUAL },
      "/api/configuracoes/template/preview": { exemplos: EXEMPLOS_PREVIEW },
    });
    montar(<TemplateEditor job={jobParado()} />);
    const usuario = await abrir();

    const campo = await screen.findByLabelText("Template do destino");
    await usuario.clear(campo);
    await usuario.type(campo, "{{categoria}/{{ano}");

    await usuario.click(screen.getByRole("button", { name: "Salvar" }));

    const chamadaSalvar = await vi.waitFor(() => {
      const c = chamadas.find(
        (c) =>
          c.caminho === "/api/configuracoes/template" && c.metodo === "PUT",
      );
      if (!c) throw new Error("PUT ainda não chegou");
      return c;
    });
    expect(chamadaSalvar.corpo).toEqual({ template: "{categoria}/{ano}" });
  });

  it("placeholder inválido mostra o erro do servidor inline, sem travar o campo", async () => {
    servirApi({
      "/api/configuracoes/template": { template: TEMPLATE_ATUAL },
      "/api/configuracoes/template/preview": { exemplos: EXEMPLOS_PREVIEW },
    });
    montar(<TemplateEditor job={jobParado()} />);
    const usuario = await abrir();

    const campo = await screen.findByLabelText("Template do destino");
    // Garante que o GET já resolveu e ficou em cache antes de trocar o
    // dublê de fetch — só o PUT de "Salvar" abaixo deve ver o erro.
    expect(campo).toHaveValue(TEMPLATE_ATUAL);

    servirApi({
      "/api/configuracoes/template": erro(
        422,
        "placeholder inválido: {fantasia}",
      ),
    });

    await usuario.clear(campo);
    await usuario.type(campo, "{{fantasia}");
    await usuario.click(screen.getByRole("button", { name: "Salvar" }));

    expect(
      await screen.findByText("placeholder inválido: {fantasia}"),
    ).toBeInTheDocument();

    // O erro não trava o campo — continua editável.
    expect(campo).toBeEnabled();
    await usuario.type(campo, "x");
    expect(campo).toHaveValue("{fantasia}x");
  });

  it("regenerar sugestões pendentes chama o job de gerar sugestões", async () => {
    servirApi({
      "/api/configuracoes/template": { template: TEMPLATE_ATUAL },
      "/api/configuracoes/template/preview": { exemplos: EXEMPLOS_PREVIEW },
    });
    const gerarSugestoes = vi.fn(async () => {});
    montar(<TemplateEditor job={jobParado({ gerarSugestoes })} />);
    const usuario = await abrir();

    const botao = await screen.findByRole("button", {
      name: "Regenerar sugestões pendentes",
    });
    // Nada foi editado desde que o template carregou — a tela mostra
    // exatamente o que está salvo, então pode regenerar.
    expect(botao).toBeEnabled();

    await usuario.click(botao);
    expect(gerarSugestoes).toHaveBeenCalledTimes(1);
  });

  it("editar o campo sem salvar desabilita regenerar — evita recriar sugestões a partir de um rascunho", async () => {
    servirApi({
      "/api/configuracoes/template": { template: TEMPLATE_ATUAL },
      "/api/configuracoes/template/preview": { exemplos: EXEMPLOS_PREVIEW },
    });
    const gerarSugestoes = vi.fn(async () => {});
    montar(<TemplateEditor job={jobParado({ gerarSugestoes })} />);
    const usuario = await abrir();

    const campo = await screen.findByLabelText("Template do destino");
    expect(campo).toHaveValue(TEMPLATE_ATUAL);
    await usuario.type(campo, "x");

    const botao = screen.getByRole("button", {
      name: "Regenerar sugestões pendentes",
    });
    expect(botao).toBeDisabled();
    expect(botao).toHaveAttribute(
      "title",
      "Salve o template antes de regenerar",
    );
  });
});
