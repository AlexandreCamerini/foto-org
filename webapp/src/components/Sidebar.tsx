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
          className={`block w-full truncate px-3 py-2 text-left hover:bg-cartao ${
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
            className={`block w-full truncate px-3 py-2 text-left hover:bg-cartao ${
              fonteAtual === fonte.id ? "border-l-2 border-acento bg-cartao" : ""
            }`}
          >
            <span className="mr-1">{ICONE_TIPO[fonte.tipo] ?? "📁"}</span>
            {fonte.apelido ?? fonte.caminho.split("/").pop()}
            <span className="ml-1.5 text-texto-2">({fonte.fotos})</span>
            {!fonte.disponivel && (
              <span className="ml-1 text-atencao" title="indisponível">
                ⚠
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* ações */}
      <div className="space-y-2 border-t border-borda px-3 py-2">
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
                className="block w-full px-2 py-2 text-left hover:bg-painel"
              >
                🍎 Apple Fotos (somente leitura)
              </button>
              <button
                onClick={() => {
                  setMenuAberto(false);
                  setModal("takeout");
                }}
                className="block w-full px-2 py-2 text-left hover:bg-painel"
              >
                🌐 Google Takeout (pasta local)
              </button>
            </div>
          )}
        </div>
        {erro && <div className="text-erro">{erro}</div>}
      </div>

      {/* Progresso e totais vivem na barra de status da janela (StatusBar):
          o trabalho continua rodando quando o usuário troca de aba, e a
          sidebar não é o lugar de contar isso duas vezes. */}

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
          className="mb-3 w-full rounded-md border border-borda bg-cartao px-3 py-2 outline-none placeholder:text-texto-3 focus:border-acento"
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
            className="rounded-md bg-acento px-3 py-1 text-texto-invertido hover:opacity-90"
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}
