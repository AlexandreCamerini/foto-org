import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import type { Job } from "../hooks/useJob";
import Botao from "../ui/Botao";

/** Varreduras que morreram com o processo (app fechado, Mac desligado).
 *
 * O servidor as carimba como interrompidas no boot; aqui elas viram uma
 * pendência visível com a ação que a resolve. Sem esta faixa, o trabalho
 * perdido não deixava rastro nenhum na interface — o dono varreu 225 mil
 * arquivos num dia e o app abriu no dia seguinte como se nada tivesse
 * acontecido.
 *
 * "Dispensar" é local e da sessão: a pendência real só morre quando um
 * scan mais novo da fonte conclui — aí o servidor para de listá-la. */
export default function RetomarScan({ job }: { job: Job }) {
  const { data } = useQuery({
    queryKey: ["scan-interrompidos"],
    queryFn: api.scansInterrompidos,
  });
  const [dispensados, setDispensados] = useState<ReadonlySet<number>>(
    new Set(),
  );

  const pendentes = (data ?? []).filter((s) => !dispensados.has(s.source_id));
  if (pendentes.length === 0) return null;

  return (
    <div data-testid="retomar-scan">
      {pendentes.map((scan) => (
        <div
          key={scan.source_id}
          className="flex items-center gap-2 border-b border-borda bg-painel px-3 py-1.5"
        >
          <span className="text-atencao">⚠</span>
          <span className="truncate">
            A varredura de <strong>{scan.apelido}</strong> foi interrompida
            {scan.vistos > 0 && (
              <span className="text-texto-2">
                {" "}
                ({scan.vistos.toLocaleString("pt-BR")} arquivos vistos)
              </span>
            )}
            {" — dá para retomar de onde parou."}
          </span>
          <Botao
            tamanho="sm"
            onClick={() => void job.escanear(scan.caminho)}
            disabled={job.rodando || !scan.disponivel}
            title={
              scan.disponivel
                ? "Varre de novo; o que já foi indexado é pulado"
                : "O volume desta fonte não está montado agora"
            }
            className="border-acento text-acento hover:bg-cartao"
          >
            Retomar
          </Botao>
          <Botao
            variante="fantasma"
            tamanho="sm"
            onClick={() =>
              setDispensados((atual) => new Set([...atual, scan.source_id]))
            }
            title="Esconder por enquanto (volta se o app reabrir)"
            className="px-1 text-texto-3"
          >
            ✕
          </Botao>
        </div>
      ))}
    </div>
  );
}
