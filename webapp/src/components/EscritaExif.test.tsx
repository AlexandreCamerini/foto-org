// As asserções deste arquivo são presas às strings exatas do Copywriting
// Contract da UI-SPEC (06-UI-SPEC.md): é a cópia que o dono lê que precisa
// não regredir — não o estado interno do componente. Checkbox é sempre
// achado por role/label (getAllByRole/getByLabelText), nunca preso à
// estrutura do DOM — teste preso a estrutura quebra na próxima mudança de
// layout.
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import EscritaExif from "./EscritaExif";
import type { CampoExif, ItemPlanoExif, PlanoExif, StatusCampoExif } from "../api";
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
    executarEscritaExif: vi.fn(async () => {}),
    cancelar: vi.fn(),
    pausar: vi.fn(async () => {}),
    continuar: vi.fn(async () => {}),
    ...sobrescrever,
  } as Job;
}

function campo(
  status: StatusCampoExif,
  valor: CampoExif["valor"] = null,
  motivo: string | null = null,
): CampoExif {
  return { valor, status, motivo };
}

function itemExif(
  id: number,
  extra: Partial<Omit<ItemPlanoExif, "campos">> & {
    campos?: Partial<ItemPlanoExif["campos"]>;
  } = {},
): ItemPlanoExif {
  const { campos, ...resto } = extra;
  return {
    id,
    media_id: id,
    origem: "/fotos",
    nome: `foto-${id}.jpg`,
    incluido: true,
    formato_suportado: true,
    motivo_nao_suportado: null,
    sidecar_destino: null,
    pasta_sincronizada: null,
    erro: null,
    backup_original: null,
    campos: {
      gps: campo("pendente"),
      cidade: campo("pendente"),
      pais: campo("pendente"),
      ...campos,
    },
    ...resto,
  };
}

function planoExif(
  dry_run_em: string | null,
  extra: Partial<PlanoExif> = {},
): PlanoExif {
  return {
    id: 1,
    nome: "Plano de escrita 1",
    status: "planejado",
    dry_run_em,
    criado_em: "2026-08-18T10:00:00",
    total_itens: 2,
    prontos: dry_run_em ? 2 : null,
    problemas: dry_run_em ? 0 : null,
    campos_a_gravar: dry_run_em ? 6 : null,
    sidecars: dry_run_em ? 0 : null,
    nao_suportados: 0,
    sincronizados: 0,
    gravados: 0,
    com_erro: 0,
    executavel: dry_run_em !== null,
    ...extra,
  };
}

function rotas(plano: PlanoExif, itens: ItemPlanoExif[]) {
  return {
    "/api/exif": [plano],
    [`/api/exif/${plano.id}`]: { ...plano, itens },
    [`/api/exif/${plano.id}/auditoria`]: [],
  };
}

describe("EscritaExif", () => {
  it("sem dry-run, gravar fica desabilitado", async () => {
    const plano = planoExif(null);
    servirApi(rotas(plano, [itemExif(1), itemExif(2)]));
    const usuario = userEvent.setup();
    montar(<EscritaExif job={jobParado()} />);

    await usuario.click(await screen.findByText(plano.nome));

    const gravar = await screen.findByRole("button", {
      name: /Gravar \d+ arquivos/,
    });
    expect(gravar).toBeDisabled();
    expect(
      screen.getByText("sem dry-run — nada pode ser gravado ainda"),
    ).toBeInTheDocument();
  });

  it("estado vazio", async () => {
    servirApi({ "/api/exif": [] });
    montar(<EscritaExif job={jobParado()} />);
    expect(await screen.findByText("Nada para gravar")).toBeInTheDocument();
  });

  it("linha tipo A mostra o valor que entraria", async () => {
    const plano = planoExif("2026-08-18T11:00:00");
    const itens = [
      itemExif(1, {
        campos: {
          gps: campo("pronto", [-23.5505, -46.6333]),
          cidade: campo("pronto", "São Paulo"),
          pais: campo("pronto", "Brasil"),
        },
      }),
    ];
    servirApi(rotas(plano, itens));
    const usuario = userEvent.setup();
    montar(<EscritaExif job={jobParado()} />);
    await usuario.click(await screen.findByText(plano.nome));

    expect(await screen.findByText(/São Paulo/)).toBeInTheDocument();
    expect(screen.getByText(/Brasil/)).toBeInTheDocument();
    expect(screen.getByText(/-23.5505/)).toBeInTheDocument();
  });

  it("campo já preenchido aparece como pulado, não como erro", async () => {
    const plano = planoExif("2026-08-18T11:00:00");
    const itens = [
      itemExif(1, {
        campos: {
          cidade: campo(
            "pulado",
            null,
            "já preenchido: Rio de Janeiro — não sobrescrito",
          ),
        },
      }),
    ];
    servirApi(rotas(plano, itens));
    const usuario = userEvent.setup();
    montar(<EscritaExif job={jobParado()} />);
    await usuario.click(await screen.findByText(plano.nome));

    const chip = await screen.findByText(/já preenchida/);
    expect(chip.className).not.toContain("text-erro");
    expect(chip.title).toContain("não sobrescrito");
  });

  it("desmarcar uma linha muda a contagem da CTA", async () => {
    const plano = planoExif("2026-08-18T11:00:00");
    const itens = [itemExif(1), itemExif(2)];
    servirApi(rotas(plano, itens));
    const usuario = userEvent.setup();
    montar(<EscritaExif job={jobParado()} />);
    await usuario.click(await screen.findByText(plano.nome));

    expect(
      await screen.findByRole("button", { name: "Gravar 2 arquivos" }),
    ).toBeInTheDocument();

    const checkboxes = screen.getAllByRole("checkbox");
    await usuario.click(checkboxes[0]);

    expect(
      await screen.findByRole("button", { name: "Gravar 1 arquivos" }),
    ).toBeInTheDocument();
  });

  it("desmarcar tudo desabilita a CTA", async () => {
    const plano = planoExif("2026-08-18T11:00:00", {
      total_itens: 1,
      prontos: 1,
    });
    servirApi(rotas(plano, [itemExif(1)]));
    const usuario = userEvent.setup();
    montar(<EscritaExif job={jobParado()} />);
    await usuario.click(await screen.findByText(plano.nome));

    await usuario.click(await screen.findByRole("checkbox"));

    const gravar = await screen.findByRole("button", {
      name: "Gravar 0 arquivos",
    });
    expect(gravar).toBeDisabled();
  });

  it("a execução envia só os ids marcados", async () => {
    const plano = planoExif("2026-08-18T11:00:00");
    const itens = [itemExif(1), itemExif(2)];
    servirApi(rotas(plano, itens));
    const executarEscritaExif = vi.fn(async () => {});
    const usuario = userEvent.setup();
    montar(<EscritaExif job={jobParado({ executarEscritaExif })} />);
    await usuario.click(await screen.findByText(plano.nome));

    const checkboxes = await screen.findAllByRole("checkbox");
    await usuario.click(checkboxes[1]); // desmarca o segundo item (id 2)

    const gravar = await screen.findByRole("button", {
      name: "Gravar 1 arquivos",
    });
    await usuario.click(gravar);

    expect(executarEscritaExif).toHaveBeenCalledWith(plano.id, [1]);
  });

  it("linha de formato não suportado nasce desmarcada e mostra o motivo", async () => {
    const plano = planoExif("2026-08-18T11:00:00");
    const itens = [
      itemExif(1, {
        incluido: false,
        formato_suportado: false,
        motivo_nao_suportado: "CR3 — sem teste de escrita neste acervo",
        sidecar_destino: "/fotos/foto-1.cr3.xmp",
      }),
    ];
    servirApi(rotas(plano, itens));
    const usuario = userEvent.setup();
    montar(<EscritaExif job={jobParado()} />);
    await usuario.click(await screen.findByText(plano.nome));

    expect(
      await screen.findByText(/CR3 — sem teste de escrita neste acervo/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Gravar sidecar .xmp para este arquivo"),
    ).toBeInTheDocument();
    const checkbox = screen.getByLabelText(
      "Gravar sidecar .xmp para este arquivo",
    );
    expect(checkbox).not.toBeChecked();
  });

  it("linha em pasta sincronizada avisa e continua marcada", async () => {
    const plano = planoExif("2026-08-18T11:00:00");
    const itens = [itemExif(1, { pasta_sincronizada: "iCloud Drive" })];
    servirApi(rotas(plano, itens));
    const usuario = userEvent.setup();
    montar(<EscritaExif job={jobParado()} />);
    await usuario.click(await screen.findByText(plano.nome));

    expect(
      await screen.findByText("☁ Pasta sincronizada — iCloud Drive"),
    ).toBeInTheDocument();
    const checkbox = screen.getByLabelText("Gravar localização em foto-1.jpg");
    expect(checkbox).toBeChecked();
  });

  it("linha que é B e C ao mesmo tempo mostra os dois badges", async () => {
    const plano = planoExif("2026-08-18T11:00:00");
    const itens = [
      itemExif(1, {
        formato_suportado: false,
        motivo_nao_suportado: "HEIC — reprovado no teste empírico",
        pasta_sincronizada: "Dropbox",
      }),
    ];
    servirApi(rotas(plano, itens));
    const usuario = userEvent.setup();
    montar(<EscritaExif job={jobParado()} />);
    await usuario.click(await screen.findByText(plano.nome));

    expect(
      await screen.findByText(/HEIC — reprovado no teste empírico/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("☁ Pasta sincronizada — Dropbox"),
    ).toBeInTheDocument();
  });

  it("detalhamento por campo depois da execução", async () => {
    const plano = planoExif("2026-08-18T11:00:00", { gravados: 1 });
    const itens = [
      itemExif(1, {
        campos: {
          gps: campo(
            "falha",
            null,
            "valor rejeitado pelo exiftool (ver auditoria)",
          ),
          cidade: campo("gravado", "São Paulo"),
          pais: campo("gravado", "Brasil"),
        },
      }),
    ];
    servirApi(rotas(plano, itens));
    const usuario = userEvent.setup();
    montar(<EscritaExif job={jobParado()} />);
    await usuario.click(await screen.findByText(plano.nome));

    expect(
      await screen.findByText(
        "falha — GPS: valor rejeitado pelo exiftool (ver auditoria)",
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("✓")).toHaveLength(2);
    expect(screen.getByText("✗")).toBeInTheDocument();
  });

  it("backup preservado aparece quando há falha", async () => {
    const plano = planoExif("2026-08-18T11:00:00");
    const itens = [
      itemExif(1, {
        erro: "Verificação falhou: hash mudou de forma inesperada",
        backup_original: "/fotos/foto-1.jpg_original",
      }),
    ];
    servirApi(rotas(plano, itens));
    const usuario = userEvent.setup();
    montar(<EscritaExif job={jobParado()} />);
    await usuario.click(await screen.findByText(plano.nome));

    expect(
      await screen.findByText(
        "Verificação falhou: hash mudou de forma inesperada",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Cópia de recuperação preservada/),
    ).toBeInTheDocument();
  });
});
