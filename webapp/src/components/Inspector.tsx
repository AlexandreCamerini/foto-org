import { useQuery } from "@tanstack/react-query";

import { api, type Media } from "../api";

const COR_NIVEL: Record<string, string> = {
  alta: "text-conf-alta",
  media: "text-conf-media",
  baixa: "text-conf-baixa",
};
const ROTULO_NIVEL: Record<string, string> = {
  alta: "Alta",
  media: "Média",
  baixa: "Baixa",
};

export function BadgeNivel({ nivel }: { nivel: string }) {
  return (
    <span
      className={`rounded border border-borda px-1.5 py-0.5 text-[11px] ${COR_NIVEL[nivel] ?? ""}`}
    >
      {ROTULO_NIVEL[nivel] ?? nivel}
    </span>
  );
}

export default function Inspector({ media }: { media: Media | null }) {
  const { data: detalhe } = useQuery({
    queryKey: ["detalhe", media?.id],
    queryFn: () => api.detalhe(media!.id),
    enabled: media !== null,
  });

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-l border-borda bg-painel">
      <div className="titulo-painel px-3 pb-2 pt-3">Inspetor</div>
      {media === null ? (
        <div className="px-3 text-texto-2">
          Selecione uma foto para ver metadados, sugestão e evidências.
        </div>
      ) : (
        <div className="overflow-y-auto px-3 pb-3">
          <img
            src={api.thumbUrl(media.id)}
            alt={media.nome}
            className="mb-2 w-full rounded-md bg-cartao object-contain"
          />
          <div className="mb-2 break-all font-semibold">{media.nome}</div>
          <dl className="space-y-1 text-texto-2">
            <Linha rotulo="Capturada" valor={detalhe?.data_capturada} />
            <Linha
              rotulo="Câmera"
              valor={[detalhe?.make, detalhe?.model].filter(Boolean).join(" ")}
            />
            <Linha rotulo="Lente" valor={detalhe?.lente} />
            <Linha
              rotulo="Dimensões"
              valor={
                detalhe?.largura ? `${detalhe.largura}×${detalhe.altura}` : null
              }
            />
            <Linha
              rotulo="GPS"
              valor={
                detalhe?.gps_lat != null
                  ? `${detalhe.gps_lat.toFixed(4)}, ${detalhe.gps_lon!.toFixed(4)}`
                  : null
              }
            />
            <Linha rotulo="Pasta" valor={detalhe?.pasta} />
          </dl>

          {detalhe?.sugestao && (
            <div className="mt-3 border-t border-borda pt-3">
              <div className="titulo-painel mb-2 flex items-center justify-between px-0">
                <span>Sugestão</span>
                <BadgeNivel nivel={detalhe.sugestao.nivel} />
              </div>
              <div className="mb-2 break-all rounded-md bg-cartao px-2 py-1.5">
                {detalhe.sugestao.destino}
              </div>
              <div className="titulo-painel mb-1">Por quê?</div>
              <ul className="space-y-2">
                {detalhe.sugestao.evidencias.map((ev, i) => (
                  <li key={i} className="rounded-md bg-cartao px-2 py-1.5">
                    <div className="mb-0.5 flex items-center justify-between">
                      <span className="font-medium">
                        {ev.campo}: {ev.valor}
                      </span>
                      <BadgeNivel nivel={ev.nivel} />
                    </div>
                    <div className="text-texto-2">{ev.justificativa}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor?: string | null }) {
  if (!valor) return null;
  return (
    <div className="flex gap-2">
      <dt className="w-20 shrink-0 text-texto-3">{rotulo}</dt>
      <dd className="break-all">{valor}</dd>
    </div>
  );
}
