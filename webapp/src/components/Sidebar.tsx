import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import type { Job } from "../hooks/useJob";

const ICONE_TIPO: Record<string, string> = {
  pasta: "📁",
  apple_photos: "🍎",
  google_takeout: "🌐",
};

interface Props {
  fonteAtual: number | null;
  onSelecionar: (sourceId: number | null) => void;
  job: Job;
}

export default function Sidebar({ fonteAtual, onSelecionar, job }: Props) {
  const { data: fontes } = useQuery({ queryKey: ["fontes"], queryFn: api.fontes });
  const { data: status } = useQuery({ queryKey: ["status"], queryFn: api.status });
  const [modal, setModal] = useState<"pasta" | "takeout" | null>(null);
  const [menuAberto, setMenuAberto] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const total = status?.total ?? 0;

  const executar = (acao: Promise<void>) => {
    setErro(null);
    acao.catch((e: Error) => setErro(e.message));
    setModal(null);
    setMenuAberto(false);
  };

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-borda bg-painel">
      <div className="titulo-painel px-3 pb-2 pt-3">Fontes</div>
      <nav className="flex-1 overflow-y-auto">
        <button
          onClick={() => onSelecionar(null)}
          className={`block w-full truncate px-3 py-1.5 text-left hover:bg-cartao ${
            fonteAtual === null ? "border-l-2 border-acento bg-cartao" : ""
          }`}
        >
          Todas as fotos
          <span className="ml-1.5 text-texto-2">({total})</span>
        </button>
        {(fontes ?? []).map((fonte) => (
          <button
            key={fonte.id}
            onClick={() => onSelecionar(fonte.id)}
            title={fonte.caminho}
            className={`block w-full truncate px-3 py-1.5 text-left hover:bg-cartao ${
              fonteAtual === fonte.id ? "border-l-2 border-acento bg-cartao" : ""
            }`}
          >
            <span className="mr-1">{ICONE_TIPO[fonte.tipo] ?? "📁"}</span>
            {fonte.apelido ?? fonte.caminho.split("/").pop()}
            <span className="ml-1.5 text-texto-2">({fonte.fotos})</span>
            {!fonte.disponivel && (
              <span className="ml-1 text-conf-media" title="indisponível">
                ⚠
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* ações */}
      <div className="space-y-1.5 border-t border-borda px-3 py-2">
        <button
          onClick={() => setModal("pasta")}
          disabled={job.rodando}
          className="w-full rounded-md border border-borda bg-cartao px-2 py-1 hover:border-acento disabled:opacity-50"
        >
          Adicionar pasta…
        </button>
        <div className="relative">
          <button
            onClick={() => setMenuAberto((v) => !v)}
            disabled={job.rodando}
            className="w-full rounded-md border border-borda bg-cartao px-2 py-1 hover:border-acento disabled:opacity-50"
          >
            Importar catálogo…
          </button>
          {menuAberto && (
            <div className="absolute bottom-full left-0 z-10 mb-1 w-full rounded-md border border-borda bg-cartao shadow-lg">
              <button
                onClick={() => executar(job.importarApple())}
                className="block w-full px-2 py-1.5 text-left hover:bg-painel"
              >
                🍎 Apple Fotos (somente leitura)
              </button>
              <button
                onClick={() => {
                  setMenuAberto(false);
                  setModal("takeout");
                }}
                className="block w-full px-2 py-1.5 text-left hover:bg-painel"
              >
                🌐 Google Takeout (pasta local)
              </button>
            </div>
          )}
        </div>
        {erro && <div className="text-conf-baixa">{erro}</div>}
      </div>

      {/* progresso do trabalho atual */}
      {job.estado.status !== "nenhum" && (
        <div className="border-t border-borda px-3 py-2">
          {job.rodando ? (
            <>
              <div className="mb-1 flex items-center justify-between">
                <span className="truncate text-texto-2">
                  {job.estado.tipo === "scan" ? "Varrendo" : "Importando"}…
                </span>
                <button
                  onClick={() => void job.cancelar()}
                  className="text-texto-2 hover:text-conf-baixa"
                >
                  cancelar
                </button>
              </div>
              <div className="mb-1 h-1 overflow-hidden rounded bg-cartao">
                <div className="h-full w-1/3 animate-pulse rounded bg-acento" />
              </div>
              <div className="text-texto-2">
                {job.estado.vistos ?? 0} vistos ·{" "}
                {job.estado.processados ?? 0} processados
                {job.estado.erros ? ` · ${job.estado.erros} erros` : ""}
                {job.estado.arquivos_por_segundo
                  ? ` · ${job.estado.arquivos_por_segundo} arq/s`
                  : ""}
              </div>
            </>
          ) : (
            <div className="flex items-start justify-between gap-2">
              <span
                className={
                  job.estado.status === "erro" ? "text-conf-baixa" : "text-texto-2"
                }
              >
                {job.estado.status === "erro"
                  ? job.estado.mensagem
                  : `Concluído: ${job.estado.processados ?? 0} processados, ` +
                    `${job.estado.pulados ?? 0} pulados` +
                    (job.estado.erros ? `, ${job.estado.erros} erros` : "")}
              </span>
              <button onClick={job.limpar} className="text-texto-3 hover:text-texto">
                ✕
              </button>
            </div>
          )}
        </div>
      )}

      <div className="border-t border-borda px-3 py-2 text-texto-2">
        {total} fotos · {status?.fontes ?? 0} fontes
        {status?.erros ? ` · ${status.erros} erros` : ""}
      </div>

      {/* modal simples de caminho */}
      {modal && (
        <ModalCaminho
          titulo={
            modal === "pasta"
              ? "Caminho da pasta de fotos"
              : "Pasta do Google Takeout (extraída)"
          }
          onConfirmar={(caminho) =>
            executar(
              modal === "pasta"
                ? job.escanear(caminho)
                : job.importarTakeout(caminho),
            )
          }
          onCancelar={() => setModal(null)}
        />
      )}
    </aside>
  );
}

function ModalCaminho({
  titulo,
  onConfirmar,
  onCancelar,
}: {
  titulo: string;
  onConfirmar: (caminho: string) => void;
  onCancelar: () => void;
}) {
  const [valor, setValor] = useState("");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-96 rounded-lg border border-borda bg-painel p-4">
        <div className="mb-2 font-semibold">{titulo}</div>
        <input
          autoFocus
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && valor.trim()) onConfirmar(valor.trim());
            if (e.key === "Escape") onCancelar();
          }}
          placeholder="/Users/voce/Pictures/Viagens"
          className="mb-3 w-full rounded-md border border-borda bg-cartao px-2.5 py-1.5 outline-none placeholder:text-texto-3 focus:border-acento"
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancelar}
            className="rounded-md px-3 py-1 text-texto-2 hover:bg-cartao"
          >
            Cancelar
          </button>
          <button
            onClick={() => valor.trim() && onConfirmar(valor.trim())}
            className="rounded-md bg-acento px-3 py-1 text-white hover:opacity-90"
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}
