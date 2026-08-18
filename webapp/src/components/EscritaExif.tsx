import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { CampoExif, PlanoExif, RelatorioDryRunExif } from "../api";
import type { Job } from "../hooks/useJob";
import Botao from "../ui/Botao";

const ROTULO_CAMPO: Record<"gps" | "cidade" | "pais", string> = {
  gps: "GPS",
  cidade: "Cidade",
  pais: "País",
};

/** Texto do chip "pulado" — concordância de gênero por campo, mesmo texto
 *  do exemplo travado na UI-SPEC ("Cidade já preenchida"). */
const JA_PREENCHIDO: Record<"gps" | "cidade" | "pais", string> = {
  gps: "GPS já preenchido",
  cidade: "Cidade já preenchida",
  pais: "País já preenchido",
};

function formatarValorCampo(
  chave: "gps" | "cidade" | "pais",
  valor: CampoExif["valor"],
): string {
  if (chave === "gps" && Array.isArray(valor)) {
    return `GPS ${valor[0].toFixed(4)}, ${valor[1].toFixed(4)}`;
  }
  return `${ROTULO_CAMPO[chave]} ${valor ?? ""}`;
}

/** Um dos três chips de campo de uma linha tipo A. O `switch` sobre
 *  `StatusCampoExif` é exaustivo de propósito: `gravado`/`falha` só passam
 *  a existir de fato no plano 06-08 (execução real e detalhamento
 *  pós-gravação), mas cair aqui já hoje garante que o TypeScript acusa
 *  quando aquele plano esquecer de tratar um caso. */
function ChipCampo({
  chave,
  campo,
}: {
  chave: "gps" | "cidade" | "pais";
  campo: CampoExif;
}) {
  const rotulo = ROTULO_CAMPO[chave];
  switch (campo.status) {
    case "pronto":
      return (
        <span
          className="rounded-full border border-borda px-2 py-0.5 text-[11px] text-texto-2"
          title={campo.motivo ?? undefined}
        >
          {formatarValorCampo(chave, campo.valor)}
        </span>
      );
    case "pulado":
      // Comportamento esperado, não erro: mesmo token de "pulado" usado em
      // toda a tela — nunca text-erro.
      return (
        <span
          className="rounded-full border border-borda px-2 py-0.5 text-[11px] text-texto-2"
          title={campo.motivo ?? undefined}
        >
          {JA_PREENCHIDO[chave]}
        </span>
      );
    case "sem_valor":
      return (
        <span
          className="rounded-full border border-borda px-2 py-0.5 text-[11px] text-texto-3"
          title={campo.motivo ?? undefined}
        >
          {rotulo} —
        </span>
      );
    case "pendente":
    case "gravado":
    case "falha":
      return (
        <span
          className="rounded-full border border-borda px-2 py-0.5 text-[11px] text-texto-3"
          title={campo.motivo ?? undefined}
        >
          {rotulo}
        </span>
      );
  }
}

/** O que o dry-run concluiu — a frase que decide se dá para gravar.
 *  Mesma forma de `Operations.tsx::veredito`, verbo trocado para "gravar". */
function veredito(p: PlanoExif): string {
  if (p.dry_run_em === null) return "sem dry-run — nada pode ser gravado ainda";
  const quando = new Date(p.dry_run_em).toLocaleString();
  if (p.prontos === null) return `dry-run em ${quando}`;
  if (p.prontos === 0)
    return `dry-run ${quando}: nenhum arquivo a gravar (${p.problemas} problemas)`;
  if (p.problemas)
    return `dry-run ${quando}: ${p.prontos} prontos, ${p.problemas} com problema`;
  return `dry-run ${quando}: ${p.prontos} prontos, sem problemas`;
}

/** Escrita EXIF de localização: plano → dry-run → gravação, sempre
 *  in-place — não há para onde copiar, é o próprio arquivo original que
 *  ganha o campo vazio (D-075). Segunda tela do app que escreve fora do
 *  catálogo, no mesmo molde de `Operations.tsx`: cada passo explícito, e
 *  gravar fica bloqueado até o dry-run aprovar. */
export default function EscritaExif({ job }: { job: Job }) {
  const [selecionado, setSelecionado] = useState<number | null>(null);
  const [relatorio, setRelatorio] = useState<RelatorioDryRunExif | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: planos } = useQuery({
    queryKey: ["planosExif"],
    queryFn: api.planosExif,
  });
  const { data: plano } = useQuery({
    queryKey: ["planoExif", selecionado],
    queryFn: () => api.planoExif(selecionado as number),
    enabled: selecionado !== null,
  });
  const { data: auditoria } = useQuery({
    queryKey: ["auditoriaExif", selecionado],
    queryFn: () => api.auditoriaExif(selecionado as number),
    enabled: selecionado !== null,
  });

  // Relatório é sempre do plano em tela — trocar de plano zera a evidência.
  useEffect(() => setRelatorio(null), [selecionado]);

  const criar = useMutation({
    mutationFn: () => api.criarPlanoExif(),
    onSuccess: (novo) => {
      setErro(null);
      setSelecionado(novo.id);
      void queryClient.invalidateQueries({ queryKey: ["planosExif"] });
    },
    onError: (e: Error) => setErro(e.message),
  });

  const dryRun = useMutation({
    mutationFn: () => api.dryRunExif(selecionado as number),
    onSuccess: (r) => {
      setErro(null);
      setRelatorio(r);
      // O dry-run carimba o plano e escreve na auditoria — as duas
      // precisam recarregar, senão a trilha exibida fica mentindo.
      void queryClient.invalidateQueries({ queryKey: ["planoExif", selecionado] });
      void queryClient.invalidateQueries({
        queryKey: ["auditoriaExif", selecionado],
      });
    },
    onError: (e: Error) => setErro(e.message),
  });

  const executando = job.rodando && job.estado.tipo === "escrita_exif";
  // Ter rodado o dry-run não basta: ele precisa ter aprovado algo gravável.
  const podeGravar = plano != null && plano.executavel && !job.rodando;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
        <Botao onClick={() => criar.mutate()} disabled={criar.isPending}>
          Criar plano de escrita
        </Botao>
        {erro && <span className="text-erro">{erro}</span>}
      </div>

      <div className="flex min-h-0 flex-1">
        <aside className="w-72 shrink-0 overflow-y-auto border-r border-borda">
          {(planos ?? []).length === 0 ? (
            <div className="flex flex-col gap-2 p-3">
              <div className="font-titulo">Nada para gravar</div>
              <p className="text-texto-2">
                Todo arquivo catalogado já tem GPS, cidade e país
                preenchidos, ou nenhuma sugestão de localização foi gerada
                ainda. Gere sugestões em Revisão e aprove-as antes de criar
                um plano aqui.
              </p>
            </div>
          ) : (
            (planos ?? []).map((p) => (
              <button
                key={p.id}
                onClick={() => setSelecionado(p.id)}
                className={`block w-full border-b border-borda px-3 py-2 text-left hover:bg-painel ${
                  selecionado === p.id ? "bg-cartao" : ""
                }`}
              >
                <div className="truncate">{p.nome}</div>
                <div className="text-texto-2">
                  {p.status} · {p.gravados}/{p.total_itens} gravados
                  {p.com_erro > 0 && (
                    <span className="text-erro"> · {p.com_erro} erros</span>
                  )}
                </div>
              </button>
            ))
          )}
        </aside>

        <section className="flex min-w-0 flex-1 flex-col">
          {plano == null ? (
            <div className="flex flex-1 items-center justify-center text-texto-2">
              Escolha um plano para ver o que será gravado.
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
                <Botao
                  onClick={() => dryRun.mutate()}
                  disabled={dryRun.isPending || job.rodando}
                  className="whitespace-nowrap"
                >
                  {dryRun.isPending ? "Simulando…" : "Rodar dry-run"}
                </Botao>
                <Botao
                  variante="solido"
                  onClick={() =>
                    // Ainda sem checkbox por linha — `itens: null` grava o
                    // plano inteiro. A seleção pontual entra no 06-08.
                    job
                      .executarEscritaExif(plano.id, null)
                      .catch((e: Error) => setErro(e.message))
                  }
                  disabled={!podeGravar}
                  title={
                    plano.dry_run_em === null
                      ? "Rode o dry-run antes de gravar"
                      : !plano.executavel
                        ? "O dry-run não encontrou nenhum campo gravável"
                        : "Grava os campos vazios no arquivo original"
                  }
                  className="whitespace-nowrap"
                >
                  Gravar {plano.prontos ?? plano.total_itens - plano.gravados}{" "}
                  arquivos
                </Botao>
                {executando && (
                  <Botao
                    variante="fantasma"
                    onClick={() => job.cancelar()}
                    className="hover:text-erro"
                  >
                    Cancelar
                  </Botao>
                )}
                <div className="flex-1" />
                <span
                  className={
                    plano.dry_run_em && !plano.executavel
                      ? "text-erro"
                      : "text-texto-2"
                  }
                >
                  {veredito(plano)}
                </span>
              </div>

              {executando && (
                <div className="border-b border-borda px-3 py-1.5 text-texto-2">
                  Gravando {job.estado.processados ?? 0} de{" "}
                  {job.estado.vistos ?? plano.total_itens} — o original só
                  muda campo por campo, com verificação antes de seguir.
                </div>
              )}

              {relatorio && (
                <div className="border-b border-borda bg-painel px-3 py-2">
                  <div>
                    {relatorio.prontos} prontos · {relatorio.campos_a_gravar}{" "}
                    campos a gravar
                    {relatorio.sidecars > 0 && (
                      <> · {relatorio.sidecars} sidecars</>
                    )}
                  </div>
                  {relatorio.problemas.map((p) => (
                    <div key={p} className="text-texto-2">
                      ! {p}
                    </div>
                  ))}
                </div>
              )}

              <div className="min-h-0 flex-1 overflow-y-auto">
                {plano.itens.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-3 border-b border-borda px-3 py-1.5"
                  >
                    <span className="min-w-0 flex-1 truncate font-titulo">
                      {item.nome}
                    </span>
                    <div className="flex shrink-0 gap-3">
                      <ChipCampo chave="gps" campo={item.campos.gps} />
                      <ChipCampo chave="cidade" campo={item.campos.cidade} />
                      <ChipCampo chave="pais" campo={item.campos.pais} />
                    </div>
                  </div>
                ))}
              </div>

              {auditoria && auditoria.length > 0 && (
                <details className="border-t border-borda">
                  <summary className="cursor-pointer px-3 py-1.5 text-texto-2">
                    Auditoria ({auditoria.length} registros)
                  </summary>
                  <div className="max-h-48 overflow-y-auto px-3 pb-2">
                    {auditoria.map((linha) => (
                      <div key={linha.id} className="text-texto-2">
                        {new Date(linha.quando).toLocaleTimeString()} ·{" "}
                        {linha.acao} · {linha.resultado}
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
