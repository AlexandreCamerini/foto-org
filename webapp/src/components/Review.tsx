import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import type { Job } from "../hooks/useJob";
import { BadgeNivel } from "./Inspector";

const STATUS_ABAS = [
  ["pendente", "Pendentes"],
  ["aprovada", "Aprovadas"],
  ["rejeitada", "Rejeitadas"],
] as const;

/** Revisão origem→destino: o usuário decide, o motor explica. */
export default function Review({ job }: { job: Job }) {
  const [status, setStatus] = useState<string>("pendente");
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["sugestoes", status],
    queryFn: () => api.sugestoes(status),
  });

  const acao = useMutation({
    mutationFn: ({ ids, tipo }: { ids: number[]; tipo: string }) =>
      api.acaoSugestoes(ids, tipo),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["sugestoes"] }),
  });

  const itens = data?.itens ?? [];
  const contagens = data?.contagens ?? {};

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
        {STATUS_ABAS.map(([valor, rotulo]) => (
          <button
            key={valor}
            onClick={() => setStatus(valor)}
            className={`rounded-md px-3 py-1 hover:bg-cartao ${
              status === valor ? "bg-cartao text-acento" : "text-texto-2"
            }`}
          >
            {rotulo}
            <span className="ml-1.5 text-texto-3">
              {contagens[valor] ?? 0}
            </span>
          </button>
        ))}
        <div className="flex-1" />
        {status === "pendente" && itens.length > 0 && (
          <button
            onClick={() =>
              acao.mutate({ ids: itens.map((s) => s.id), tipo: "aprovar" })
            }
            className="rounded-md bg-acento px-3 py-1 text-white hover:opacity-90"
          >
            Aprovar todas ({itens.length})
          </button>
        )}
        <button
          onClick={() => job.gerarSugestoes()}
          disabled={job.rodando}
          className="rounded-md border border-borda bg-cartao px-3 py-1 hover:border-acento disabled:opacity-50"
        >
          {job.rodando && job.estado.tipo === "sugestoes"
            ? "Gerando…"
            : "Gerar/atualizar sugestões"}
        </button>
      </div>

      {itens.length === 0 ? (
        <div className="flex flex-1 items-center justify-center text-texto-2">
          Nada aqui — gere as sugestões ou mude o filtro de status.
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {itens.map((s) => (
            <div
              key={s.id}
              className="flex items-center gap-3 border-b border-borda px-3 py-2 hover:bg-painel"
            >
              <img
                src={api.thumbUrl(s.media_id)}
                alt={s.nome}
                loading="lazy"
                className="h-12 w-12 shrink-0 rounded object-cover"
              />
              <div className="min-w-0 flex-1">
                <div className="truncate">
                  <span className="text-texto-2">{s.pasta}/</span>
                  {s.nome}
                </div>
                <div className="truncate text-acento">→ {s.destino}</div>
              </div>
              <BadgeNivel nivel={s.nivel} />
              {status === "pendente" ? (
                <div className="flex shrink-0 gap-1.5">
                  <button
                    onClick={() => acao.mutate({ ids: [s.id], tipo: "aprovar" })}
                    className="rounded-md border border-borda px-2 py-0.5 text-conf-alta hover:bg-cartao"
                  >
                    Aprovar
                  </button>
                  <button
                    onClick={() => acao.mutate({ ids: [s.id], tipo: "rejeitar" })}
                    className="rounded-md border border-borda px-2 py-0.5 text-conf-baixa hover:bg-cartao"
                  >
                    Rejeitar
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => acao.mutate({ ids: [s.id], tipo: "desfazer" })}
                  className="shrink-0 rounded-md border border-borda px-2 py-0.5 text-texto-2 hover:bg-cartao"
                >
                  Desfazer
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
