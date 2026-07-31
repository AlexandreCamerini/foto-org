import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { api, type Sugestao } from "../api";
import type { Job } from "../hooks/useJob";
import { Confianca } from "./Confianca";

const STATUS_ABAS = [
  ["pendente", "Pendentes"],
  ["aprovada", "Aprovadas"],
  ["rejeitada", "Rejeitadas"],
] as const;

type Item = {
  id: number;
  media_id: number;
  nome: string;
  pasta: string;
  destino: string;
  nivel: string;
  status: string;
  data_capturada?: string | null;
  camera?: string | null;
  gps_estimado?: boolean;
};

/** Revisão origem→destino: o usuário decide, o motor explica.
 *
 * A unidade de decisão é o GRUPO, não a foto solta (docs/DECISOES.md D-018):
 * "aprovar as 22 de Viagens/2024 - França" é uma decisão que dá para tomar
 * com a informação que se tem; "aprovar a linha 37 de 63" não é.
 */
export default function Review({ job }: { job: Job }) {
  const [status, setStatus] = useState<string>("pendente");
  const [fechados, setFechados] = useState<Set<string>>(new Set());
  const [porque, setPorque] = useState<number | null>(null);
  const [editando, setEditando] = useState<number | null>(null);
  const [valorEdicao, setValorEdicao] = useState("");
  const [erroEdicao, setErroEdicao] = useState<string | null>(null);
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

  // Editar marca a sugestão como EDITADA no servidor (fotoorganizer/
  // repositories/suggestions.py) — ela some da aba atual ao recarregar
  // porque deixou de ser "pendente", o que é o comportamento certo: a
  // correção já valeu, não precisa de uma segunda aprovação.
  const editarDestino = useMutation({
    mutationFn: ({ id, destino }: { id: number; destino: string }) =>
      api.editarDestino(id, destino),
    onSuccess: () => {
      setEditando(null);
      setErroEdicao(null);
      void queryClient.invalidateQueries({ queryKey: ["sugestoes"] });
    },
    onError: (e: Error) => setErroEdicao(e.message),
  });

  const iniciarEdicao = (item: Item) => {
    setEditando(item.id);
    setValorEdicao(item.destino);
    setErroEdicao(null);
  };

  const cancelarEdicao = () => {
    setEditando(null);
    setErroEdicao(null);
  };

  const salvarEdicao = (id: number) => {
    const destino = valorEdicao.trim();
    if (!destino) return;
    editarDestino.mutate({ id, destino });
  };

  const itens = (data?.itens ?? []) as Item[];
  const contagens = data?.contagens ?? {};

  // O repositório já devolve ordenado por destino, então agrupar é varrer.
  const grupos = useMemo(() => {
    const mapa = new Map<string, Item[]>();
    for (const item of itens) {
      const lista = mapa.get(item.destino);
      if (lista) lista.push(item);
      else mapa.set(item.destino, [item]);
    }
    return [...mapa.entries()];
  }, [itens]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
        {STATUS_ABAS.map(([valor, rotulo]) => (
          <button
            key={valor}
            onClick={() => setStatus(valor)}
            className={`rounded-md px-3 py-1 hover:bg-cartao ${
              status === valor ? "bg-realce text-texto" : "text-texto-2"
            }`}
          >
            {rotulo}
            <span className="ml-1.5 text-texto-3">{contagens[valor] ?? 0}</span>
          </button>
        ))}
        <div className="flex-1" />
        <span className="text-texto-3">
          {itens.length} em {grupos.length}{" "}
          {grupos.length === 1 ? "grupo" : "grupos"}
        </span>
        <button
          onClick={() => job.gerarSugestoes()}
          disabled={job.rodando}
          className="rounded-md border border-borda bg-cartao px-3 py-1 hover:border-borda-forte disabled:opacity-50"
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
          {grupos.map(([destino, doGrupo]) => {
            const aberto = !fechados.has(destino);
            const estimadas = doGrupo.filter((i) => i.gps_estimado).length;
            return (
              <section key={destino}>
                <header
                  onClick={() =>
                    setFechados((s) => {
                      const novo = new Set(s);
                      novo.has(destino) ? novo.delete(destino) : novo.add(destino);
                      return novo;
                    })
                  }
                  className="sticky top-0 z-10 flex cursor-pointer items-center gap-2 border-b border-borda bg-cartao px-3 py-2 hover:bg-realce"
                >
                  <span className="w-3 text-texto-3">{aberto ? "▾" : "▸"}</span>
                  <span className="truncate font-medium">{destino}</span>
                  <span className="shrink-0 text-texto-2">
                    · {doGrupo.length}{" "}
                    {doGrupo.length === 1 ? "foto" : "fotos"}
                    {estimadas > 0 && (
                      <span className="text-herdado">
                        {" "}
                        · {estimadas} com lugar estimado
                      </span>
                    )}
                  </span>
                  <div className="flex-1" />
                  {status === "pendente" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        acao.mutate({
                          ids: doGrupo.map((i) => i.id),
                          tipo: "aprovar",
                        });
                      }}
                      className="shrink-0 rounded-md border border-borda px-2 py-0.5 text-[11px] text-texto-2 hover:border-ok hover:text-ok"
                    >
                      Aprovar {doGrupo.length}
                    </button>
                  )}
                </header>

                {aberto &&
                  doGrupo.map((s) => (
                    <div key={s.id} className="border-b border-borda/60">
                      {editando === s.id ? (
                        <div className="flex items-center gap-3 px-3 py-2">
                          <img
                            src={api.thumbUrl(s.media_id)}
                            alt={s.nome}
                            loading="lazy"
                            className="h-9 w-12 shrink-0 rounded object-cover bg-cartao"
                          />
                          <div className="min-w-0 flex-1">
                            <div className="mb-1 truncate text-[11px] text-texto-3">
                              {s.nome}
                            </div>
                            <input
                              autoFocus
                              value={valorEdicao}
                              onChange={(e) => setValorEdicao(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") salvarEdicao(s.id);
                                if (e.key === "Escape") cancelarEdicao();
                              }}
                              className="w-full rounded-md border border-borda bg-cartao px-2 py-1 outline-none focus:border-acento"
                            />
                            {erroEdicao && (
                              <div className="mt-1 text-[11px] text-erro">
                                {erroEdicao}
                              </div>
                            )}
                          </div>
                          <div className="flex shrink-0 gap-2">
                            <button
                              onClick={() => salvarEdicao(s.id)}
                              disabled={editarDestino.isPending}
                              className="rounded-md border border-borda px-2 py-0.5 text-ok hover:bg-cartao disabled:opacity-50"
                            >
                              Salvar
                            </button>
                            <button
                              onClick={cancelarEdicao}
                              className="rounded-md border border-borda px-2 py-0.5 text-texto-2 hover:bg-cartao"
                            >
                              Cancelar
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center gap-3 px-3 py-2 hover:bg-painel">
                          <img
                            src={api.thumbUrl(s.media_id)}
                            alt={s.nome}
                            loading="lazy"
                            className="h-9 w-12 shrink-0 rounded object-cover bg-cartao"
                          />
                          <div className="min-w-0 flex-1">
                            {/* Nome primeiro. Antes a pasta vinha antes e o
                                truncate cortava a linha antes de o nome do
                                arquivo aparecer — 63 linhas idênticas. */}
                            <div className="truncate font-medium">{s.nome}</div>
                            <div className="truncate text-[11px] text-texto-3">
                              {[s.camera, formatarData(s.data_capturada)]
                                .filter(Boolean)
                                .join(" · ") || pastaCurta(s.pasta)}
                            </div>
                          </div>
                          <button
                            onClick={() => iniciarEdicao(s)}
                            className="shrink-0 rounded px-1 py-0.5 text-texto-3 hover:bg-cartao hover:text-texto"
                            title={`Editar destino de ${s.nome}`}
                          >
                            ✎
                          </button>
                          <button
                            onClick={() =>
                              setPorque((p) => (p === s.media_id ? null : s.media_id))
                            }
                            className="shrink-0 rounded px-1 py-0.5 hover:bg-cartao"
                            aria-expanded={porque === s.media_id}
                            title={`Por que este destino para ${s.nome}?`}
                          >
                            <Confianca nivel={s.nivel} />
                          </button>
                          {status === "pendente" ? (
                            <div className="flex shrink-0 gap-2">
                              <button
                                onClick={() =>
                                  acao.mutate({ ids: [s.id], tipo: "aprovar" })
                                }
                                className="rounded-md border border-borda px-2 py-0.5 text-ok hover:bg-cartao"
                              >
                                Aprovar
                              </button>
                              <button
                                onClick={() =>
                                  acao.mutate({ ids: [s.id], tipo: "rejeitar" })
                                }
                                className="rounded-md border border-borda px-2 py-0.5 text-erro hover:bg-cartao"
                              >
                                Rejeitar
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() =>
                                acao.mutate({ ids: [s.id], tipo: "desfazer" })
                              }
                              className="shrink-0 rounded-md border border-borda px-2 py-0.5 text-texto-2 hover:bg-cartao"
                            >
                              Desfazer
                            </button>
                          )}
                        </div>
                      )}
                      {porque === s.media_id && <PorQue mediaId={s.media_id} />}
                    </div>
                  ))}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

/** Busca as evidências só quando o usuário pergunta — 63 linhas não podem
 *  disparar 63 requisições no carregamento. */
function PorQue({ mediaId }: { mediaId: number }) {
  const { data, isPending } = useQuery({
    queryKey: ["detalhe", mediaId],
    queryFn: () => api.detalhe(mediaId),
  });
  const sugestao = data?.sugestao as Sugestao | undefined;

  if (isPending) {
    return <div className="px-3 pb-2 pl-[68px] text-texto-3">carregando…</div>;
  }
  if (!sugestao?.evidencias?.length) {
    return (
      <div className="px-3 pb-2 pl-[68px] text-texto-3">
        Sem evidência registrada para esta sugestão.
      </div>
    );
  }
  return (
    <ul className="space-y-1 px-3 pb-2 pl-[68px]">
      {sugestao.evidencias.map((ev, i) => (
        <li key={i} className="flex gap-2 text-[11px]">
          <Confianca nivel={ev.nivel} rotulo={false} />
          <span className="text-texto-2">
            <span className="text-texto">{ev.campo}</span>: {ev.valor} —{" "}
            {ev.justificativa}
          </span>
        </li>
      ))}
    </ul>
  );
}

function formatarData(iso?: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Caminho absoluto inteiro não cabe e não informa: o que localiza a foto é
 *  o fim do caminho, não o começo. */
function pastaCurta(pasta: string): string {
  const partes = pasta.split("/").filter(Boolean);
  return partes.length <= 2 ? pasta : "…/" + partes.slice(-2).join("/");
}
