import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import Operations from "./Operations";
import type { Job } from "../hooks/useJob";
import { montar, servirApi } from "../test/servidor";

function jobParado(sobrescrever: Partial<Job> = {}): Job {
  return {
    estado: { status: "nenhum" },
    rodando: false,
    limpar: vi.fn(),
    escanear: vi.fn(),
    importarApple: vi.fn(),
    importarTakeout: vi.fn(),
    gerarSugestoes: vi.fn(),
    detectarDuplicatas: vi.fn(),
    executarPlano: vi.fn(async () => {}),
    cancelar: vi.fn(),
    ...sobrescrever,
  } as Job;
}

function plano(dry_run_em: string | null, veredito: object = {}) {
  return {
    id: 1,
    nome: "Cópia para /destino",
    status: "planejada",
    dry_run_em,
    criado_em: "2026-07-26T10:00:00",
    total_itens: 2,
    concluidos: 0,
    com_conflito: 0,
    com_erro: 0,
    // Sem dry-run não há veredito; com dry-run, o padrão é tudo pronto.
    prontos: dry_run_em ? 2 : null,
    problemas: dry_run_em ? 0 : null,
    executavel: dry_run_em !== null,
    ...veredito,
  };
}

const ITENS = [
  {
    id: 1,
    origem: "/fotos/2019/DSC_0001.jpg",
    destino: "/destino/Viagens/2019/DSC_0001.jpg",
    status: "planejada",
    conflito: null,
    erro: null,
  },
  {
    id: 2,
    origem: "/fotos/whatsapp/IMG-1.jpg",
    destino: "/destino/Familia/2024/IMG-1.jpg",
    status: "planejada",
    conflito: null,
    erro: null,
  },
];

function rotas(dry_run_em: string | null, veredito: object = {}) {
  return {
    "/api/configuracoes/template": {
      template: "{categoria}/{ano} - {viagem}/{evento}/{pais}/{regiao}/{cidade}",
    },
    "/api/operacoes": [plano(dry_run_em, veredito)],
    "/api/operacoes/1": { ...plano(dry_run_em, veredito), itens: ITENS },
    "/api/operacoes/1/auditoria": [
      {
        id: 1,
        quando: "2026-07-26T10:00:00",
        acao: "plano_criado",
        resultado: "ok",
        detalhe: null,
      },
    ],
  };
}

describe("Operações", () => {
  it("sem dry-run, copiar fica bloqueado e a tela diz por quê", async () => {
    servirApi(rotas(null));
    const usuario = userEvent.setup();
    montar(<Operations job={jobParado()} />);

    await usuario.click(await screen.findByText("Cópia para /destino"));

    const copiar = await screen.findByRole("button", {
      name: /Copiar 2 arquivos/,
    });
    expect(copiar).toBeDisabled();
    expect(copiar).toHaveAttribute("title", "Rode o dry-run antes de copiar");
    expect(
      screen.getByText("sem dry-run — nada pode ser copiado ainda"),
    ).toBeInTheDocument();
  });

  it("com dry-run, copiar libera e dispara o plano certo", async () => {
    servirApi(rotas("2026-07-26T10:05:00"));
    const executarPlano = vi.fn(async () => {});
    const usuario = userEvent.setup();
    montar(<Operations job={jobParado({ executarPlano })} />);

    await usuario.click(await screen.findByText("Cópia para /destino"));
    const copiar = await screen.findByRole("button", {
      name: /Copiar 2 arquivos/,
    });
    expect(copiar).toBeEnabled();

    await usuario.click(copiar);
    expect(executarPlano).toHaveBeenCalledWith(1);
  });

  it("dry-run sem nada copiável bloqueia, mesmo tendo rodado", async () => {
    // O bug que este teste fixa: um plano cujas origens estavam todas num
    // volume desmontado mostrava "0 erros · dry-run ✓" e liberava o botão.
    // `com_erro` conta erro de EXECUÇÃO, e o plano nunca executou.
    servirApi(
      rotas("2026-07-26T10:05:00", {
        prontos: 0,
        problemas: 2,
        executavel: false,
      }),
    );
    const executarPlano = vi.fn(async () => {});
    const usuario = userEvent.setup();
    montar(<Operations job={jobParado({ executarPlano })} />);

    await usuario.click(await screen.findByText("Cópia para /destino"));
    const copiar = await screen.findByRole("button", {
      name: /Copiar 0 arquivos/,
    });
    expect(copiar).toBeDisabled();
    expect(copiar).toHaveAttribute(
      "title",
      "O dry-run não encontrou nenhum arquivo copiável",
    );
    expect(
      screen.getByText(/nenhum arquivo copiável \(2 problemas\)/),
    ).toBeInTheDocument();
    expect(executarPlano).not.toHaveBeenCalled();
  });

  it("o diff mostra o caminho relativo, sem o prefixo comum das árvores",
    async () => {
      servirApi(rotas(null));
      const usuario = userEvent.setup();
      montar(<Operations job={jobParado()} />);

      await usuario.click(await screen.findByText("Cópia para /destino"));

      expect(await screen.findByText("2019/DSC_0001.jpg")).toBeInTheDocument();
      expect(screen.getByText("→ Viagens/2019/DSC_0001.jpg"))
        .toBeInTheDocument();
      expect(screen.getByText("de /fotos")).toBeInTheDocument();
      expect(screen.getByText("para /destino")).toBeInTheDocument();
    });

  it("estado vazio orienta a próxima ação", async () => {
    servirApi({
      "/api/configuracoes/template": { template: "{categoria}/{ano}" },
      "/api/operacoes": [],
    });
    montar(<Operations job={jobParado()} />);
    expect(
      await screen.findByText("Aprove sugestões na aba Revisão", {
        exact: false,
      }),
    ).toBeInTheDocument();
  });

  it("Cancelar de cópia em andamento é neutro em repouso, vermelho só no hover (D-05, CONS-07)",
    async () => {
      servirApi(rotas("2026-07-26T10:00:00"));
      const cancelar = vi.fn();
      const usuario = userEvent.setup();
      montar(
        <Operations
          job={jobParado({
            rodando: true,
            estado: { status: "rodando", tipo: "operacao" },
            cancelar,
          })}
        />,
      );

      await usuario.click(await screen.findByText("Cópia para /destino"));
      const botao = await screen.findByRole("button", { name: "Cancelar" });

      // "hover:text-erro" contém a substring "text-erro" — não dá para
      // testar ausência de "text-erro" puro (falso positivo). O que só o
      // tom="erro" produz (cor em repouso) é "bg-erro/10"/"border-erro/40";
      // é isso que a asserção negativa tem que casar.
      expect(botao.className).toContain("hover:text-erro");
      expect(botao.className).not.toContain("bg-erro/10");
      expect(botao.className).not.toContain("border-erro/40");

      await usuario.click(botao);
      expect(cancelar).toHaveBeenCalledTimes(1);
    });
});
