import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import type { Job } from "../hooks/useJob";
import Botao from "../ui/Botao";

const NIVEIS = [
  ["todos", "Todos"],
  ["exato", "Idênticos"],
  ["conteudo", "Mesmo conteúdo"],
  ["visual", "Parecidos"],
  ["sequencia", "Sequências"],
] as const;

/** Duplicatas e rajadas: grupos à esquerda, survey lado a lado à direita.
 * Nada é excluído — o usuário marca papéis para a fase de operações. */
export default function Duplicates({ job }: { job: Job }) {
  const [nivel, setNivel] = useState<string>("todos");
  const [grupoId, setGrupoId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data: grupos } = useQuery({
    queryKey: ["duplicatas"],
    queryFn: () => api.duplicatas(),
  });

  const acao = useMutation({
    mutationFn: ({ url, body }: { url: string; body?: unknown }) =>
      fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["duplicatas"] }),
  });

  const visiveis = (grupos ?? []).filter(
    (g) => nivel === "todos" || g.nivel === nivel,
  );
  const grupo = visiveis.find((g) => g.id === grupoId) ?? visiveis[0] ?? null;
  const recuperavel = (grupos ?? [])
    .filter((g) => g.nivel !== "sequencia")
    .reduce((soma, g) => soma + g.bytes_recuperaveis, 0);

  return (
    <div className="flex h-full min-h-0">
      {/* lista de grupos */}
      <div className="flex w-96 shrink-0 flex-col border-r border-borda">
        <div className="flex flex-wrap items-center gap-1 border-b border-borda px-3 py-2">
          {NIVEIS.map(([valor, rotulo]) => (
            <button
              key={valor}
              onClick={() => {
                setNivel(valor);
                setGrupoId(null);
              }}
              className={`rounded-full px-3 py-0.5 hover:bg-cartao ${
                nivel === valor ? "bg-cartao text-acento" : "text-texto-2"
              }`}
            >
              {rotulo}
            </button>
          ))}
        </div>
        <div className="border-b border-borda px-3 py-1.5 text-texto-2">
          {(grupos ?? []).length} grupos ·{" "}
          {tamanhoLegivel(recuperavel)} recuperáveis
          <Botao tamanho="sm"
            onClick={() => job.detectarDuplicatas()}
            disabled={job.rodando}
            className="ml-2">
            {job.rodando && job.estado.tipo === "duplicatas"
              ? "Detectando…"
              : "Detectar"}
          </Botao>
        </div>
        <div className="flex-1 overflow-y-auto">
          {visiveis.map((g) => (
            <button
              key={g.id}
              onClick={() => setGrupoId(g.id)}
              className={`block w-full border-b border-borda px-3 py-2 text-left hover:bg-painel ${
                grupo?.id === g.id ? "border-l-2 border-l-acento bg-painel" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <span
                  className={
                    g.nivel === "sequencia" ? "text-atencao" : undefined
                  }
                >
                  {g.rotulo}
                </span>
                <span className="text-texto-3">{g.membros.length} fotos</span>
              </div>
              <div className="text-texto-2">
                {g.nivel === "sequencia"
                  ? "escolha o melhor frame"
                  : `${tamanhoLegivel(g.bytes_recuperaveis)} recuperáveis`}
                {g.n_fontes > 1 ? ` · em ${g.n_fontes} fontes` : ""}
                {g.resolvido_automaticamente
                  ? " · resolvido automaticamente"
                  : g.decidido
                    ? " · decidido ✓"
                    : ""}
              </div>
            </button>
          ))}
          {visiveis.length === 0 && (
            <div className="px-3 py-6 text-center text-texto-2">
              Nenhum grupo — rode a detecção.
            </div>
          )}
        </div>
      </div>

      {/* survey do grupo selecionado */}
      {grupo === null ? (
        <div className="flex flex-1 items-center justify-center text-texto-2">
          Selecione um grupo para comparar lado a lado.
        </div>
      ) : (
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
            <span className="shrink-0 font-semibold">{grupo.rotulo}</span>
            {grupo.resolvido_automaticamente && (
              <span
                title="Bytes idênticos (SHA-256): o algoritmo escolheu a cópia mais organizada como principal. Revise ou desfaça se preferir outra."
                className="shrink-0 rounded-md border border-acento/40 px-1.5 py-0.5 text-[11px] text-acento"
              >
                resolvido automaticamente
              </span>
            )}
            <span className="min-w-0 flex-1 truncate text-texto-2">
              {grupo.resolvido_automaticamente
                ? "Cópia idêntica (SHA-256) — o algoritmo já marcou a principal. Escolha outra se discordar."
                : grupo.nivel === "sequencia"
                  ? "Rajada da mesma câmera — marque o melhor frame como principal."
                  : "Marque a cópia a manter como principal."}
            </span>
            <Botao tamanho="sm"
              onClick={() =>
                acao.mutate({ url: `/api/duplicatas/${grupo.id}/ignorar` })
              }
            className="bg-transparent text-texto-2 hover:bg-cartao">
              Ignorar grupo
            </Botao>
            <Botao tamanho="sm"
              onClick={() =>
                acao.mutate({ url: `/api/duplicatas/${grupo.id}/desfazer` })
              }
            className="bg-transparent text-texto-2 hover:bg-cartao">
              Desfazer
            </Botao>
          </div>
          <div className="grid flex-1 auto-rows-min grid-cols-2 gap-4 overflow-y-auto p-4 xl:grid-cols-3">
            {grupo.membros.map((m) => (
              <figure
                key={m.member_id}
                className={`overflow-hidden rounded-md border bg-cartao ${
                  m.papel === "principal"
                    ? "border-ok"
                    : m.papel === "ignorado"
                      ? "border-borda opacity-50"
                      : "border-borda"
                }`}
              >
                <img
                  src={api.previewUrl(m.media_id)}
                  alt={m.nome}
                  loading="lazy"
                  className="aspect-[4/3] w-full bg-black object-contain"
                />
                <figcaption className="space-y-1 p-2">
                  <div className="truncate font-medium" title={m.caminho}>
                    {m.nome}
                  </div>
                  <div className="flex items-center justify-between text-texto-2">
                    <span>{tamanhoLegivel(m.tamanho)}</span>
                    {m.papel === "principal" ? (
                      <span className="text-ok">✓ principal</span>
                    ) : (
                      <Botao tamanho="sm"
                        onClick={() =>
                          acao.mutate({
                            url: `/api/duplicatas/${grupo.id}/principal`,
                            body: { media_id: m.media_id },
                          })
                        }
            className="bg-transparent hover:border-ok hover:text-ok">
                        {grupo.nivel === "sequencia"
                          ? "Melhor frame"
                          : "Manter esta"}
                      </Botao>
                    )}
                  </div>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function tamanhoLegivel(bytes: number): string {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
}
