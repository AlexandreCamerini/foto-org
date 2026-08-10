import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import { rotulosDeFontes } from "../fontes";
import type { Job } from "../hooks/useJob";
import Botao from "../ui/Botao";

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
  // Custa um `diskutil` por fonte fora de alcance — não é `disponivel`
  // simples, então fica numa consulta própria em vez de inchar `/api/fontes`
  // (que a grade inteira lê a cada render).
  const { data: reapontamentos } = useQuery({
    queryKey: ["reapontamentos"],
    queryFn: api.reapontamentos,
  });
  const [modal, setModal] = useState<"pasta" | "takeout" | "apple" | null>(null);
  const [reapontarId, setReapontarId] = useState<number | null>(null);
  const [menuAberto, setMenuAberto] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const total = status?.total ?? 0;
  const rotulos = rotulosDeFontes(fontes ?? []);
  const mudouDeLugar = new Set((reapontamentos ?? []).map((r) => r.source_id));

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
          <div
            key={fonte.id}
            className={`flex items-center px-3 py-2 hover:bg-cartao ${
              fonteAtual === fonte.id ? "border-l-2 border-acento bg-cartao" : ""
            }`}
          >
            <button
              onClick={() => onSelecionar(fonte.id)}
              title={fonte.caminho}
              className="min-w-0 flex-1 truncate text-left"
            >
              <span className="mr-1">{ICONE_TIPO[fonte.tipo] ?? "📁"}</span>
              {rotulos.get(fonte.id) ?? fonte.caminho}
              <span className="ml-1.5 text-texto-2">({fonte.fotos})</span>
              {!fonte.disponivel && !mudouDeLugar.has(fonte.id) && (
                <span className="ml-1 text-atencao" title="indisponível">
                  ⚠
                </span>
              )}
            </button>
            {mudouDeLugar.has(fonte.id) && (
              <Botao tom="atencao" tamanho="sm"
                onClick={() => setReapontarId(fonte.id)}
                title="O volume voltou noutro ponto de montagem — reapontar o catálogo sem recatalogar"
            className="ml-1">
                ↦ mudou de lugar
              </Botao>
            )}
          </div>
        ))}
      </nav>

      {/* ações */}
      <div className="space-y-2 border-t border-borda px-3 py-2">
        <Botao tamanho="sm" cheio
          onClick={() => setModal("pasta")}
          disabled={job.rodando}>
          Adicionar pasta…
        </Botao>
        <div className="relative">
          <Botao tamanho="sm" cheio
            onClick={() => setMenuAberto((v) => !v)}
            disabled={job.rodando}>
            Importar catálogo…
          </Botao>
          {menuAberto && (
            <div className="absolute bottom-full left-0 z-10 mb-1 w-full rounded-md border border-borda bg-cartao shadow-lg">
              <button
                onClick={() => {
                  setMenuAberto(false);
                  setModal("apple");
                }}
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
      {(modal === "pasta" || modal === "takeout") && (
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

      {modal === "apple" && (
        <ModalAvisoApple
          onConfirmar={() => executar(job.importarApple())}
          onCancelar={() => setModal(null)}
        />
      )}

      {reapontarId !== null && (
        <ModalReapontar
          sourceId={reapontarId}
          onFechar={() => setReapontarId(null)}
        />
      )}
    </aside>
  );
}

/** O volume desta fonte remontou noutro ponto — reescreve `Source.caminho`
 * e todos os `MediaFile.caminho` dela no catálogo, sem tocar em arquivo
 * nenhum. Prévia sempre visível antes de confirmar (invariante 2). */
function ModalReapontar({
  sourceId,
  onFechar,
}: {
  sourceId: number;
  onFechar: () => void;
}) {
  const queryClient = useQueryClient();
  const { data: previa, isLoading, error } = useQuery({
    queryKey: ["reapontar-preview", sourceId],
    queryFn: () => api.previaReapontamento(sourceId),
  });
  const confirmar = useMutation({
    mutationFn: () => api.reapontarFonte(sourceId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["fontes"] });
      void queryClient.invalidateQueries({ queryKey: ["reapontamentos"] });
      onFechar();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-[32rem] rounded-md border border-borda bg-painel p-4">
        <div className="mb-2 font-semibold">Fonte mudou de lugar</div>
        {isLoading && <p className="text-texto-2">Verificando…</p>}
        {error && (
          <p className="text-erro">{(error as Error).message}</p>
        )}
        {previa && (
          <>
            <p className="mb-3 text-texto-2">
              O volume de <strong>{previa.apelido}</strong> voltou montado
              noutro ponto. Isto reescreve só o catálogo — nenhum arquivo é
              tocado no disco.
            </p>
            <div className="mb-3 flex items-center gap-2 truncate">
              <span
                className="min-w-0 flex-1 truncate text-texto-2"
                title={previa.prefixo_antigo}
              >
                {previa.prefixo_antigo}
              </span>
              <span aria-hidden className="shrink-0 text-texto-3">
                →
              </span>
              <span
                className="min-w-0 flex-1 truncate font-medium"
                title={previa.prefixo_novo}
              >
                {previa.prefixo_novo}
              </span>
            </div>
            <p className="mb-3 text-texto-2">
              {previa.total_media_files.toLocaleString("pt-BR")} arquivo(s)
              de mídia serão reapontados.
            </p>
            {previa.total_ignoradas_sem_prefixo > 0 && (
              <p className="mb-3 text-texto-3">
                {previa.total_ignoradas_sem_prefixo.toLocaleString("pt-BR")}{" "}
                referência(s) desta fonte (ex.: catálogo externo) não têm
                esse prefixo e ficam intocadas.
              </p>
            )}
            {confirmar.isError && (
              <p className="mb-3 text-erro">
                {(confirmar.error as Error).message}
              </p>
            )}
          </>
        )}
        <div className="flex justify-end gap-2">
          <Botao variante="fantasma"
            onClick={onFechar}>
            Cancelar
          </Botao>
          <Botao variante="solido"
            onClick={() => confirmar.mutate()}
            disabled={!previa || confirmar.isPending}>
            {confirmar.isPending ? "Reapontando…" : "Reapontar"}
          </Botao>
        </div>
      </div>
    </div>
  );
}

/** Aviso prévio antes de tocar no Apple Fotos: a leitura da biblioteca pode
 * exigir Acesso Total ao Disco, e é melhor o usuário saber disso antes de
 * ver um erro do macOS do que descobrir na hora. */
function ModalAvisoApple({
  onConfirmar,
  onCancelar,
}: {
  onConfirmar: () => void;
  onCancelar: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-96 rounded-md border border-borda bg-painel p-4">
        <div className="mb-2 font-semibold">Importar do Apple Fotos</div>
        <p className="mb-3 text-texto-2">
          A importação é somente leitura — nenhuma foto é movida, renomeada
          ou alterada na sua biblioteca. O macOS pode pedir Acesso Total ao
          Disco para o app conseguir abrir o catálogo do Apple Fotos: em
          Ajustes → Privacidade e Segurança → Acesso Total ao Disco.
        </p>
        <div className="flex justify-end gap-2">
          <Botao variante="fantasma"
            onClick={onCancelar}>
            Cancelar
          </Botao>
          <Botao variante="solido"
            onClick={onConfirmar}>
            Continuar
          </Botao>
        </div>
      </div>
    </div>
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
      <div className="w-96 rounded-md border border-borda bg-painel p-4">
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
          <Botao variante="fantasma"
            onClick={onCancelar}>
            Cancelar
          </Botao>
          <Botao variante="solido"
            onClick={() => valor.trim() && onConfirmar(valor.trim())}>
            Confirmar
          </Botao>
        </div>
      </div>
    </div>
  );
}
