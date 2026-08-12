import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, type Media, type MediaDetalhe } from "../api";
import { formatarData } from "../data";
import { Confianca } from "./Confianca";
import Botao from "../ui/Botao";

/** Só o que NÃO é foto ganha rótulo: dizer "foto" em toda foto é ruído. */
const ROTULOS_TIPO: Record<string, string> = {
  captura: "captura de tela",
  recebida: "recebida em mensageiro",
  baixada: "baixada da web",
};

export default function Inspector({ media }: { media: Media | null }) {
  const { data: detalhe } = useQuery({
    queryKey: ["detalhe", media?.id],
    queryFn: () => api.detalhe(media!.id),
    enabled: media !== null,
  });

  return (
    <aside className="flex h-full w-72 shrink-0 superficie flex-col border-l border-borda">
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
            <Linha
              rotulo="Capturada"
              valor={formatarData(detalhe?.data_capturada)}
            />
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
            <Linha
              rotulo={rotuloDoLugar(detalhe?.local)}
              valor={
                detalhe?.local
                  ? [detalhe.local.cidade, detalhe.local.regiao, detalhe.local.pais]
                      .filter(Boolean)
                      .join(", ")
                  : null
              }
            />
            <Linha rotulo="Pasta" valor={detalhe?.pasta} />
          </dl>

          {/* Quando há sugestão, a evidência de vizinhança temporal já conta
              esta história em "Por quê?" — repetir num painel de 288px é
              ruído. O bloco cobre o caso sem sugestão (já aprovada, ou
              decidida pelo usuário), em que a estimativa ficaria muda. */}
          {detalhe?.estimativa && !detalhe?.sugestao && (
            <div className="mt-3 rounded-md border border-borda bg-cartao px-2 py-1.5 text-texto-2">
              Esta câmera não gravou coordenada. O lugar veio de{" "}
              <span className="text-texto">{detalhe.estimativa.doadora_nome}</span>
              {detalhe.estimativa.doadora_camera
                ? ` (${detalhe.estimativa.doadora_camera})`
                : ""}
              {detalhe.estimativa.delta_s != null
                ? `, tirada a ${formatarDelta(detalhe.estimativa.delta_s)} de distância.`
                : "."}
            </div>
          )}

          <TipoDaImagem media={media} detalhe={detalhe} />

          <MetadadosDoArquivo mediaId={media.id} />

          {detalhe?.sugestao && (
            <div className="mt-3 border-t border-borda pt-3">
              <div className="titulo-painel mb-2 flex items-center justify-between px-0">
                <span>Sugestão</span>
                <Confianca nivel={detalhe.sugestao.nivel} />
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
                      <Confianca nivel={ev.nivel} rotulo={false} />
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

/** A classificação do detector é PROVISÓRIA até você responder.
 *
 * Enquanto `tipo_provisorio` for true, o painel pergunta em vez de afirmar —
 * e a resposta vai para `tipo_confirmado`, que nenhuma geração de sugestões
 * sobrescreve. Sem essa separação, corrigir o tipo seria desfeito em
 * silêncio na próxima passagem do motor.
 */
function TipoDaImagem({
  media,
  detalhe,
}: {
  media: Media;
  detalhe?: MediaDetalhe;
}) {
  const queryClient = useQueryClient();
  const confirmar = useMutation({
    mutationFn: (tipo: string | null) => api.confirmarTipo(media.id, tipo),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["detalhe", media.id] });
      void queryClient.invalidateQueries({ queryKey: ["midia"] });
      void queryClient.invalidateQueries({ queryKey: ["panorama"] });
    },
  });

  const tipo = detalhe?.tipo_imagem;
  const provisorio = detalhe?.tipo_provisorio ?? false;
  // O detector conclui "foto" por padrão — na dúvida, é foto. Perguntar
  // "isto parece foto, não uma foto?" em toda foto do acervo é ruído: eram
  // 5.071 das 5.601. Só a conclusão de que NÃO é foto merece pergunta.
  // Quando o próprio usuário disse "é foto", aí sim aparece — com o desfazer.
  if (!tipo || (tipo === "foto" && provisorio)) return null;
  const rotulo = ROTULOS_TIPO[tipo] ?? tipo;

  if (provisorio) {
    return (
      <div className="mt-3 rounded-md border border-borda bg-cartao px-2 py-1.5">
        <div className="text-texto-2">
          Isto parece <span className="text-texto">{rotulo}</span>, não uma
          foto. Confere?
        </div>
        <div className="mt-1.5 flex gap-1.5">
          <Botao
            tamanho="sm"
            onClick={() => confirmar.mutate(tipo)}
            disabled={confirmar.isPending}
            className="bg-transparent hover:border-ok hover:text-ok"
          >
            Confere
          </Botao>
          <Botao
            tamanho="sm"
            onClick={() => confirmar.mutate("foto")}
            disabled={confirmar.isPending}
            className="bg-transparent hover:border-borda-forte"
          >
            Não, é foto
          </Botao>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-3 flex items-center gap-2 text-texto-2">
      <span>
        {rotulo} · <span className="text-texto-3">classificado por você</span>
      </span>
      <Botao
        variante="fantasma"
        tamanho="sm"
        onClick={() => confirmar.mutate(null)}
        className="px-1 text-texto-3"
        title="Devolver a decisão ao detector"
      >
        desfazer
      </Botao>
    </div>
  );
}

/** Tudo que estava gravado no arquivo — EXIF, GPS, IPTC, XMP, RAW.
 *
 * Fechado por padrão e buscado só ao abrir: um JPEG editado traz dezenas de
 * chaves XMP, e o inspetor é recarregado a cada seleção na grade. */
function MetadadosDoArquivo({ mediaId }: { mediaId: number }) {
  const [aberto, setAberto] = useState(false);
  const { data, isPending } = useQuery({
    queryKey: ["metadados", mediaId],
    queryFn: () => api.metadados(mediaId),
    enabled: aberto,
  });

  return (
    <div className="mt-3 border-t border-borda pt-3">
      <button
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        className="titulo-painel flex w-full items-center gap-1.5 px-0 hover:text-texto"
      >
        <span className="w-2">{aberto ? "▾" : "▸"}</span>
        Metadados do arquivo
        {data && <span className="text-texto-3">({data.total})</span>}
      </button>

      {aberto && isPending && (
        <div className="mt-1 text-texto-3">lendo…</div>
      )}
      {aberto && data && data.total === 0 && (
        <div className="mt-1 text-texto-3">
          Este arquivo não trouxe metadado nenhum.
        </div>
      )}
      {aberto &&
        data?.namespaces.map((ns) => (
          <div key={ns.nome} className="mt-2">
            <div className="mb-1 text-[11px] text-texto-3">{ns.rotulo}</div>
            <dl className="space-y-0.5">
              {ns.itens.map((item) => (
                <div key={item.chave} className="flex gap-2">
                  <dt className="w-24 shrink-0 break-all text-texto-3">
                    {item.chave}
                  </dt>
                  <dd className="min-w-0 break-all text-texto-2">{item.valor}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
    </div>
  );
}

/** O rótulo carrega a granularidade: um lugar herdado de horas atrás diz o
 *  país, e chamar isso de "Lugar · estimado" faria o usuário ler a linha
 *  como se a cidade estivesse ali (D-025). */
function rotuloDoLugar(local?: MediaDetalhe["local"]): string {
  if (!local?.estimado) return "Lugar";
  if (local.granularidade === "regiao") return "Lugar · região estimada";
  if (local.granularidade === "pais") return "Lugar · país estimado";
  return "Lugar · estimado";
}

function Linha({ rotulo, valor }: { rotulo: string; valor?: string | null }) {
  if (!valor) return null;
  return (
    <div className="flex gap-2">
      <dt className="w-20 shrink-0 text-texto-2">{rotulo}</dt>
      <dd className="break-all">{valor}</dd>
    </div>
  );
}

/** Δt legível, no mesmo vocabulário do motor (fotoorganizer/classification). */
function formatarDelta(segundos: number): string {
  return segundos < 60 ? `${segundos}s` : `${Math.round(segundos / 60)}min`;
}
