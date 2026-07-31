import { useQuery } from "@tanstack/react-query";

import { api } from "../api";
import type { Job } from "../hooks/useJob";

const ROTULO_JOB: Record<string, string> = {
  scan: "Varrendo",
  import: "Importando",
  sugestoes: "Gerando sugestões",
  duplicatas: "Procurando duplicatas",
  operacao: "Copiando",
};

/** Barra de status da janela inteira (docs/DIRECAO_DE_ARTE.md): o progresso
 * é persistente e honesto, nunca um spinner modal — e fica visível em
 * qualquer aba, porque o trabalho continua mesmo quando o usuário sai da
 * tela que o disparou. */
export default function StatusBar({ job, dica }: { job: Job; dica?: string }) {
  const { data: status } = useQuery({
    queryKey: ["status"],
    queryFn: api.status,
  });

  const estado = job.estado;
  const pausado = estado.status === "pausado";
  // Pausa só existe para scan (jobs.py); mostrar o botão para outros tipos
  // seria uma ação que sempre volta 409.
  const podePausar = estado.tipo === "scan";
  const ativo = job.rodando || pausado;
  const concluido = !ativo && estado.status !== "nenhum";

  // Largura real quando o total já é conhecido; senão a barra indeterminada
  // (pulso) — nunca fingir um progresso que não temos como medir.
  const vistos = estado.vistos ?? 0;
  const progresso =
    vistos > 0
      ? Math.min(100, Math.round(((estado.processados ?? 0) / vistos) * 100))
      : null;

  return (
    <footer className="flex h-7 shrink-0 items-center gap-3 border-t border-borda bg-painel px-3">
      {ativo && (
        <>
          <span className="h-1 w-24 overflow-hidden rounded bg-cartao">
            {progresso === null ? (
              <span className="block h-full w-1/3 animate-pulse rounded bg-acento" />
            ) : (
              <span
                data-testid="barra-progresso"
                className="block h-full rounded bg-acento transition-[width]"
                style={{ width: `${progresso}%` }}
              />
            )}
          </span>
          <span className="truncate">
            {pausado ? "Pausado" : ROTULO_JOB[estado.tipo ?? ""] ?? "Trabalhando"}
            {!pausado && estado.alvo ? ` ${estado.alvo}` : ""}
            {pausado ? "" : "…"}
          </span>
          <span className="shrink-0 text-texto-2">
            {estado.processados ?? 0}
            {estado.vistos ? ` / ${estado.vistos}` : ""}
            {estado.erros ? ` · ${estado.erros} erros` : ""}
            {estado.arquivos_por_segundo
              ? ` · ${estado.arquivos_por_segundo} arq/s`
              : ""}
          </span>
          {podePausar &&
            (pausado ? (
              <button
                onClick={() => void job.continuar()}
                className="shrink-0 rounded px-1 text-texto-2 hover:text-acento"
              >
                Continuar
              </button>
            ) : (
              <button
                onClick={() => void job.pausar()}
                className="shrink-0 rounded px-1 text-texto-2 hover:text-acento"
              >
                Pausar
              </button>
            ))}
          <button
            onClick={() => void job.cancelar()}
            className="shrink-0 rounded px-1 text-texto-2 hover:text-erro"
          >
            cancelar
          </button>
        </>
      )}

      {concluido && (
        <>
          <span
            className={`truncate ${
              estado.status === "erro" ? "text-erro" : "text-texto-2"
            }`}
          >
            {estado.status === "erro"
              ? estado.mensagem
              : `Concluído: ${estado.processados ?? 0} processados` +
                (estado.pulados ? `, ${estado.pulados} pulados` : "") +
                (estado.erros ? `, ${estado.erros} erros` : "")}
          </span>
          <button
            onClick={job.limpar}
            title="Dispensar"
            className="shrink-0 rounded px-1 text-texto-3 hover:text-texto"
          >
            ✕
          </button>
        </>
      )}

      {!ativo && !concluido && dica && (
        <span className="truncate text-texto-3">{dica}</span>
      )}

      <div className="flex-1" />
      <span className="shrink-0 text-texto-2">
        {status?.total ?? 0} fotos · {status?.fontes ?? 0} fontes
        {status?.erros ? ` · ${status.erros} erros` : ""}
      </span>
    </footer>
  );
}
