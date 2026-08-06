import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { Plano, RelatorioDryRun } from "../api";
import type { Job } from "../hooks/useJob";
import TemplateEditor from "./TemplateEditor";

const CORES_STATUS: Record<string, string> = {
  concluida: "text-ok",
  erro: "text-erro",
  cancelada: "text-texto-2",
  executando: "text-acento",
};

function mb(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1e3))} KB`;
}

/** Pasta comum a todos os caminhos. Mostrada uma vez no cabeçalho, some de
 * cada linha: o que interessa no diff é o que muda, não o prefixo repetido
 * que empurra o nome do arquivo para fora da tela. */
function prefixoComum(caminhos: string[]): string {
  const pastas = caminhos.filter(Boolean).map((c) => c.split("/").slice(0, -1));
  if (pastas.length === 0) return "";
  const [primeira] = pastas;
  let i = 0;
  while (i < primeira.length && pastas.every((p) => p[i] === primeira[i])) i++;
  return primeira.slice(0, i).join("/");
}

function semPrefixo(caminho: string, prefixo: string): string {
  if (!caminho) return "—";
  return prefixo && caminho.startsWith(`${prefixo}/`)
    ? caminho.slice(prefixo.length + 1)
    : caminho;
}

/** O que o dry-run concluiu — a frase que decide se dá para copiar.
 *  Sem ela a tela mostrava só a data do dry-run, e um plano com todas as
 *  origens num volume desmontado se lia como pronto. */
function veredito(p: Plano): string {
  if (p.dry_run_em === null) return "sem dry-run — nada pode ser copiado ainda";
  const quando = new Date(p.dry_run_em).toLocaleString();
  if (p.prontos === null) return `dry-run em ${quando}`;
  if (p.prontos === 0)
    return `dry-run ${quando}: nenhum arquivo copiável (${p.problemas} problemas)`;
  if (p.problemas)
    return `dry-run ${quando}: ${p.prontos} prontos, ${p.problemas} com problema`;
  return `dry-run ${quando}: ${p.prontos} prontos, sem problemas`;
}

/** Operações físicas: plano → dry-run → aprovação → cópia verificada.
 * É a única tela do app que escreve fora do catálogo, e por isso a única
 * onde cada passo é explícito e reversível até o último clique. */
export default function Operations({ job }: { job: Job }) {
  const [destino, setDestino] = useState("");
  const [selecionado, setSelecionado] = useState<number | null>(null);
  const [relatorio, setRelatorio] = useState<RelatorioDryRun | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: planos } = useQuery({
    queryKey: ["planos"],
    queryFn: api.planos,
  });
  const { data: plano } = useQuery({
    queryKey: ["plano", selecionado],
    queryFn: () => api.plano(selecionado as number),
    enabled: selecionado !== null,
  });
  const { data: auditoria } = useQuery({
    queryKey: ["auditoria", selecionado],
    queryFn: () => api.auditoria(selecionado as number),
    enabled: selecionado !== null,
  });

  // Relatório é sempre do plano em tela — trocar de plano zera a evidência.
  useEffect(() => setRelatorio(null), [selecionado]);

  const criar = useMutation({
    mutationFn: () => api.criarPlano(destino.trim()),
    onSuccess: (novo) => {
      setErro(null);
      setSelecionado(novo.id);
      void queryClient.invalidateQueries({ queryKey: ["planos"] });
    },
    onError: (e: Error) => setErro(e.message),
  });

  const dryRun = useMutation({
    mutationFn: () => api.dryRun(selecionado as number),
    onSuccess: (r) => {
      setErro(null);
      setRelatorio(r);
      // O dry-run carimba o plano e escreve na auditoria — as duas precisam
      // recarregar, senão a trilha exibida fica mentindo.
      void queryClient.invalidateQueries({ queryKey: ["plano", selecionado] });
      void queryClient.invalidateQueries({
        queryKey: ["auditoria", selecionado],
      });
    },
    onError: (e: Error) => setErro(e.message),
  });

  const executando = job.rodando && job.estado.tipo === "operacao";
  // Ter rodado o dry-run não basta: ele precisa ter aprovado alguma coisa.
  const podeExecutar = plano != null && plano.executavel && !job.rodando;
  const raizOrigem = prefixoComum((plano?.itens ?? []).map((i) => i.origem));
  const raizDestino = prefixoComum((plano?.itens ?? []).map((i) => i.destino));

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
        <input
          value={destino}
          onChange={(e) => setDestino(e.target.value)}
          placeholder="Pasta de destino da biblioteca organizada…"
          className="w-96 rounded-md border border-borda bg-cartao px-2.5 py-1 outline-none placeholder:text-texto-3 focus:border-acento"
        />
        <button
          onClick={() => criar.mutate()}
          disabled={!destino.trim() || criar.isPending}
          className="rounded-md border border-borda bg-cartao px-3 py-1 hover:border-acento disabled:opacity-50"
        >
          Criar plano
        </button>
        {erro && <span className="text-erro">{erro}</span>}
      </div>

      <TemplateEditor job={job} />

      <div className="flex min-h-0 flex-1">
        <aside className="w-72 shrink-0 overflow-y-auto border-r border-borda">
          {(planos ?? []).length === 0 ? (
            <p className="p-3 text-texto-2">
              Nenhum plano ainda. Aprove sugestões na aba Revisão, escolha a
              pasta de destino acima e crie o primeiro plano.
            </p>
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
                <div className="text-texto-3">
                  <span className={CORES_STATUS[p.status] ?? "text-texto-2"}>
                    {p.status}
                  </span>{" "}
                  · {p.concluidos}/{p.total_itens} copiados
                  {p.com_erro > 0 && (
                    <span className="text-erro"> · {p.com_erro} erros</span>
                  )}
                  {/* "nada copiável" só é notícia enquanto ainda há o que
                      copiar. Num plano já concluído (143/143) o executável
                      é falso porque acabou, e a frase lia como falha ao
                      lado do próprio sucesso. */}
                  {p.dry_run_em !== null &&
                    !p.executavel &&
                    p.concluidos < p.total_itens && (
                      <span className="text-erro">
                        {" "}
                        · dry-run: nada copiável
                      </span>
                    )}
                </div>
              </button>
            ))
          )}
        </aside>

        <section className="flex min-w-0 flex-1 flex-col">
          {plano == null ? (
            <div className="flex flex-1 items-center justify-center text-texto-2">
              Escolha um plano para ver o que será copiado.
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
                <button
                  onClick={() => dryRun.mutate()}
                  disabled={dryRun.isPending || job.rodando}
                  className="shrink-0 whitespace-nowrap rounded-md border border-borda bg-cartao px-3 py-1 hover:border-acento disabled:opacity-50"
                >
                  {dryRun.isPending ? "Simulando…" : "Rodar dry-run"}
                </button>
                <button
                  onClick={() =>
                    job.executarPlano(plano.id).catch((e: Error) =>
                      setErro(e.message),
                    )
                  }
                  disabled={!podeExecutar}
                  title={
                    plano.dry_run_em === null
                      ? "Rode o dry-run antes de copiar"
                      : !plano.executavel
                        ? "O dry-run não encontrou nenhum arquivo copiável"
                        : "Copia os arquivos para o destino"
                  }
                  className="shrink-0 whitespace-nowrap rounded-md bg-acento px-3 py-1 text-texto-invertido hover:opacity-90 disabled:opacity-40"
                >
                  Copiar {plano.prontos ?? plano.total_itens - plano.concluidos}{" "}
                  arquivos
                </button>
                {executando && (
                  <button
                    onClick={() => job.cancelar()}
                    className="rounded-md border border-borda px-3 py-1 text-erro hover:bg-cartao"
                  >
                    Cancelar
                  </button>
                )}
                <div className="flex-1" />
                <span
                  className={
                    plano.dry_run_em && !plano.executavel
                      ? "text-erro"
                      : "text-texto-3"
                  }
                >
                  {veredito(plano)}
                </span>
              </div>

              {executando && (
                <div className="border-b border-borda px-3 py-1.5 text-texto-2">
                  Copiando {job.estado.processados ?? 0} de{" "}
                  {job.estado.vistos ?? plano.total_itens} — os originais
                  permanecem intactos.
                </div>
              )}

              {relatorio && (
                <div className="border-b border-borda bg-painel px-3 py-2">
                  <div>
                    {relatorio.prontos} prontos ·{" "}
                    {mb(relatorio.bytes_necessarios)} necessários
                    {relatorio.bytes_livres !== null && (
                      <>
                        {" "}
                        ·{" "}
                        <span
                          className={
                            relatorio.espaco_suficiente
                              ? "text-ok"
                              : "text-erro"
                          }
                        >
                          {mb(relatorio.bytes_livres)} livres
                        </span>
                      </>
                    )}
                  </div>
                  {relatorio.problemas.map((p) => (
                    <div key={p} className="text-texto-2">
                      ! {p}
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-6 border-b border-borda px-3 py-1 text-texto-2">
                <span className="min-w-0 flex-1 truncate">
                  de {raizOrigem || "/"}
                </span>
                <span className="min-w-0 flex-1 truncate">
                  para {raizDestino || "/"}
                </span>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto">
                {plano.itens.map((item) => (
                  <div
                    key={item.id}
                    className="border-b border-borda px-3 py-1.5"
                  >
                    <div className="flex gap-6">
                      <span className="min-w-0 flex-1 truncate text-texto-2">
                        {semPrefixo(item.origem, raizOrigem)}
                      </span>
                      <span className="min-w-0 flex-1 truncate text-acento">
                        → {semPrefixo(item.destino, raizDestino)}
                      </span>
                      <span
                        className={`shrink-0 ${
                          CORES_STATUS[item.status] ?? "text-texto-3"
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>
                    {(item.conflito || item.erro) && (
                      <div className="text-texto-2">
                        {item.erro ?? item.conflito}
                      </div>
                    )}
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
