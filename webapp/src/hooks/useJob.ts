import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

export interface JobEstado {
  status: "nenhum" | "rodando" | "concluido" | "pausado" | "erro" | string;
  tipo?: string;
  alvo?: string;
  vistos?: number;
  processados?: number;
  pulados?: number;
  erros?: number;
  arquivos_por_segundo?: number;
  mensagem?: string;
}

/** Estado do trabalho em background (scan/importação) via SSE; ao terminar,
 * invalida todas as queries — grade, fontes e contagens se atualizam. */
export function useJob() {
  const queryClient = useQueryClient();
  const [estado, setEstado] = useState<JobEstado>({ status: "nenhum" });
  const fonteRef = useRef<EventSource | null>(null);

  const assinar = useCallback(() => {
    fonteRef.current?.close();
    const es = new EventSource("/api/progresso");
    fonteRef.current = es;
    es.onmessage = (ev) => {
      const dados = JSON.parse(ev.data) as JobEstado;
      setEstado(dados);
      if (dados.status !== "rodando") {
        es.close();
        void queryClient.invalidateQueries();
      }
    };
    es.onerror = () => es.close();
  }, [queryClient]);

  // Reconecta a um trabalho que já estava rodando (ex.: recarregou a página).
  useEffect(() => {
    void fetch("/api/job")
      .then((r) => r.json())
      .then((dados: JobEstado) => {
        if (dados.status === "rodando") {
          setEstado(dados);
          assinar();
        }
      });
    return () => fonteRef.current?.close();
  }, [assinar]);

  const disparar = useCallback(
    async (url: string, body: unknown) => {
      const resposta = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const dados = await resposta.json();
      if (!resposta.ok) {
        throw new Error(dados.detail ?? `erro ${resposta.status}`);
      }
      setEstado(dados as JobEstado);
      assinar();
    },
    [assinar],
  );

  return {
    estado,
    rodando: estado.status === "rodando",
    limpar: () => setEstado({ status: "nenhum" }),
    escanear: (caminho: string) => disparar("/api/scan", { caminho }),
    importarApple: () =>
      disparar("/api/importar", { tipo: "apple_photos" }),
    importarTakeout: (caminho: string) =>
      disparar("/api/importar", { tipo: "google_takeout", caminho }),
    gerarSugestoes: () => disparar("/api/sugestoes/gerar", {}),
    cancelar: () => fetch("/api/job/cancelar", { method: "POST" }),
  };
}

export type Job = ReturnType<typeof useJob>;
