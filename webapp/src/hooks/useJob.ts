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
  // Reconexão: tentativa atual (zera a cada mensagem saudável) e o timer
  // agendado, para o unmount não deixar um fetch órfão disparando depois.
  const tentativaRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const assinarRef = useRef<() => void>(() => {});

  const reconectar = useCallback(() => {
    // Backoff exponencial com teto: 1s, 2s, 4s… 15s. O /api/job decide o
    // que fazer: ainda rodando → reassina; terminou (ou o servidor
    // reiniciou) → mostra o estado final e manda as telas recontarem.
    const atraso = Math.min(15_000, 1_000 * 2 ** tentativaRef.current);
    tentativaRef.current += 1;
    timerRef.current = window.setTimeout(() => {
      void fetch("/api/job")
        .then((r) => r.json())
        .then((dados: JobEstado) => {
          setEstado(dados);
          if (dados.status === "rodando" || dados.status === "pausado") {
            assinarRef.current();
          } else {
            void queryClient.invalidateQueries();
          }
        })
        .catch(() => reconectar()); // servidor fora: insiste, mais devagar
    }, atraso);
  }, [queryClient]);

  const assinar = useCallback(() => {
    fonteRef.current?.close();
    const es = new EventSource("/api/progresso");
    fonteRef.current = es;
    es.onmessage = (ev) => {
      tentativaRef.current = 0; // conexão saudável zera o backoff
      const dados = JSON.parse(ev.data) as JobEstado;
      setEstado(dados);
      if (dados.status !== "rodando") {
        es.close();
        void queryClient.invalidateQueries();
      }
    };
    // Rede caiu, Mac dormiu, servidor engasgou. Fechar e nunca voltar era
    // o que congelava os contadores com o disco ainda girando — o usuário
    // olhava uma barra parada e concluía que o app tinha morrido.
    es.onerror = () => {
      es.close();
      reconectar();
    };
  }, [queryClient, reconectar]);
  useEffect(() => {
    assinarRef.current = assinar;
  }, [assinar]);

  // Reconecta a um trabalho que já estava rodando (ex.: recarregou a
  // página) — "pausado" conta como em andamento aqui: sem isto, recarregar
  // a página durante uma pausa perdia o indicador e o botão Continuar.
  // Estados terminais (concluído/erro/cancelado) ficam de fora de propósito:
  // não faz sentido ressuscitar o banner de um job antigo a cada reload.
  useEffect(() => {
    void fetch("/api/job")
      .then((r) => r.json())
      .then((dados: JobEstado) => {
        if (dados.status === "rodando" || dados.status === "pausado") {
          setEstado(dados);
          assinar();
        }
      });
    return () => {
      fonteRef.current?.close();
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
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

  // Pausar/continuar respondem 409 quando não há scan pausável/retomável
  // (ex.: o usuário clicou duas vezes, ou o scan terminou entre o clique e
  // a resposta). Não é um erro para a UI mostrar — o estado do job já é a
  // fonte da verdade, então só ignoramos.
  const pausar = useCallback(async () => {
    try {
      await disparar("/api/job/pausar", {});
    } catch {
      // 409: nada rodando para pausar.
    }
  }, [disparar]);

  const continuar = useCallback(async () => {
    try {
      await disparar("/api/job/continuar", {});
    } catch {
      // 409: nada pausado para continuar.
    }
  }, [disparar]);

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
    detectarDuplicatas: () => disparar("/api/duplicatas/detectar", {}),
    executarPlano: (planId: number) =>
      disparar(`/api/operacoes/${planId}/executar`, {}),
    cancelar: () => fetch("/api/job/cancelar", { method: "POST" }),
    pausar,
    continuar,
  };
}

export type Job = ReturnType<typeof useJob>;
