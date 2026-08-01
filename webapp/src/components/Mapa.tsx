import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  api,
  type DadosMapa,
  type DoadoraMapa,
  type EscalaMapa,
  type LimitesMapa,
  type PontoMapa,
} from "../api";
import { Miniatura } from "./Miniatura";

/** O mapa do lugar de um grupo — sem cartografia real (D-031).
 *
 * Nenhum tile, nenhuma biblioteca de mapa, nenhuma requisição para fora:
 * mandar lat/lon de foto para um servidor de terceiros é exatamente o que o
 * invariante 4 proíbe. O que sobra é geometria pura sobre uma malha, e é
 * suficiente: a pergunta que esta tela responde é "de onde veio esta
 * coordenada e quanta dúvida ela carrega", não "qual é o nome da rua".
 *
 * O DESENHO É POR LUGAR, NÃO POR FOTO. Medido no acervo real: a viagem
 * "Dubai, Thai & Viet" tem 2.406 fotos sobre 31 coordenadas distintas, e o
 * evento "Pantanal" tem 80 sobre 4. Herdeira e doadora ficam na MESMA
 * coordenada (a herança não desloca nada), então desenhar um círculo por
 * foto empilharia 190 traçados idênticos no mesmo pixel: ilegível, e
 * mentindo sobre haver 190 lugares. Cada marcador é um lugar e diz quantas
 * fotos estão ali.
 */

// Espaço lógico do SVG. O viewBox escala com o contêiner; a projeção
// trabalha sempre nestas coordenadas.
const LARGURA = 1000;
const ALTURA = 620;
const MARGEM = 56;
// Abaixo disto o círculo da dúvida some sob o ponto: um raio de 30 m num
// mapa continental vale 0,006 px. Ele continua existindo, então continua
// visível — o piso é de legibilidade, e a frase diz o tamanho real.
const RAIO_MIN_PX = 7;
const LIMITE_LISTA = 40;

export interface Lugar {
  chave: string;
  lat: number;
  lon: number;
  /** Fotos cuja coordenada foi lida do próprio arquivo. */
  proprios: PontoMapa[];
  /** Fotos que herdaram a coordenada de outra foto. */
  herdados: PontoMapa[];
  /** Doadoras posicionadas aqui (podem estar fora do grupo). */
  doadoras: DoadoraMapa[];
  /** O maior raio entre os herdados — a dúvida do lugar é a maior dúvida
   *  que existe nele. Desenhar a média esconderia a pior. */
  raio_m: number;
  fora_de_alcance: number;
}

function chaveDe(lat: number, lon: number): string {
  return `${lat.toFixed(5)},${lon.toFixed(5)}`;
}

/** Agrupa por coordenada exata. A chave é a própria coordenada arredondada
 *  a ~1 m — não é um cluster heurístico por proximidade de tela, é o fato:
 *  estas fotos estão no mesmo ponto porque herdaram do mesmo doador. */
export function agruparPorLugar(dados: DadosMapa): Lugar[] {
  const lugares = new Map<string, Lugar>();
  const obter = (lat: number, lon: number): Lugar => {
    const chave = chaveDe(lat, lon);
    let lugar = lugares.get(chave);
    if (!lugar) {
      lugar = {
        chave,
        lat,
        lon,
        proprios: [],
        herdados: [],
        doadoras: [],
        raio_m: 0,
        fora_de_alcance: 0,
      };
      lugares.set(chave, lugar);
    }
    return lugar;
  };

  for (const ponto of dados.pontos) {
    const lugar = obter(ponto.lat, ponto.lon);
    if (ponto.estimado) {
      lugar.herdados.push(ponto);
      lugar.raio_m = Math.max(lugar.raio_m, ponto.raio_m ?? 0);
    } else {
      lugar.proprios.push(ponto);
    }
    if (ponto.motivo_indisponivel) lugar.fora_de_alcance += 1;
  }
  for (const doadora of dados.doadoras) {
    if (doadora.lat == null || doadora.lon == null) continue;
    obter(doadora.lat, doadora.lon).doadoras.push(doadora);
  }

  // Maior primeiro: quem tem mais foto é desenhado por baixo, e o lugar de
  // uma foto só não fica escondido atrás do lugar de duzentas.
  return [...lugares.values()].sort(
    (a, b) =>
      b.proprios.length + b.herdados.length - (a.proprios.length + a.herdados.length),
  );
}

export function totalDoLugar(lugar: Lugar): number {
  return lugar.proprios.length + lugar.herdados.length;
}

export function tipoDoLugar(lugar: Lugar): "lido" | "estimado" | "misto" {
  if (lugar.herdados.length === 0) return "lido";
  if (lugar.proprios.length > 0 || lugar.doadoras.length > 0) return "misto";
  return "estimado";
}

export interface Projecao {
  x: (lon: number) => number;
  y: (lat: number) => number;
  /** Pixels do viewBox por metro no terreno. */
  pxPorMetro: number;
}

/** Equirretangular local: perto o bastante da verdade na escala de um grupo,
 *  e sem nenhuma dependência.
 *
 *  UM fator de escala para os dois eixos, deliberadamente. Esticar cada eixo
 *  até preencher a tela transformaria todo círculo de incerteza numa elipse
 *  — e a dúvida não tem direção preferida. Por isso os dois campos de
 *  `escala` são usados: eles convertem grau em metro, e o metro é que vira
 *  pixel. */
export function projetar(limites: LimitesMapa, escala: EscalaMapa): Projecao {
  const larguraM =
    (limites.lon_max - limites.lon_min) * escala.metros_por_grau_lon;
  const alturaM = (limites.lat_max - limites.lat_min) * escala.metros_por_grau_lat;
  const utilW = LARGURA - 2 * MARGEM;
  const utilH = ALTURA - 2 * MARGEM;
  // Um grupo inteiro numa coordenada só, todos com raio zero: não há extensão
  // para caber, e qualquer escala serve.
  const candidatos = [
    larguraM > 0 ? utilW / larguraM : Infinity,
    alturaM > 0 ? utilH / alturaM : Infinity,
  ];
  const pxPorMetro = Math.min(...candidatos);
  const escalaFinal = Number.isFinite(pxPorMetro) ? pxPorMetro : 1;
  const lonCentro = (limites.lon_min + limites.lon_max) / 2;
  const latCentro = (limites.lat_min + limites.lat_max) / 2;
  return {
    x: (lon) =>
      LARGURA / 2 + (lon - lonCentro) * escala.metros_por_grau_lon * escalaFinal,
    y: (lat) =>
      ALTURA / 2 - (lat - latCentro) * escala.metros_por_grau_lat * escalaFinal,
    pxPorMetro: escalaFinal,
  };
}

/** Estende os limites do servidor até caber as doadoras.
 *
 *  O servidor enquadra os PONTOS (e o raio deles). Uma doadora fora do grupo
 *  está, no acervo medido, exatamente sobre suas herdeiras — mas se um dia
 *  não estiver, ela sairia do quadro sem aviso, e a outra ponta do traço é
 *  justamente o que esta tela existe para mostrar. */
export function limitesComDoadoras(
  limites: LimitesMapa,
  doadoras: DoadoraMapa[],
): LimitesMapa {
  return doadoras.reduce(
    (acc, d) =>
      d.lat == null || d.lon == null
        ? acc
        : {
            lat_min: Math.min(acc.lat_min, d.lat),
            lat_max: Math.max(acc.lat_max, d.lat),
            lon_min: Math.min(acc.lon_min, d.lon),
            lon_max: Math.max(acc.lon_max, d.lon),
          },
    limites,
  );
}

export default function Mapa({
  trip_id,
  event_id,
  nome,
  onEstadoVazio,
}: {
  trip_id?: number;
  event_id?: number;
  nome?: string;
  /** O rodapé convida a clicar num ponto — só faz sentido quando existe um.
   *  Sem isto o App não tem como saber que o grupo aberto não tem lugar
   *  nenhum, e a dica ficaria anunciando um atalho que a tela não tem. */
  onEstadoVazio?: (vazio: boolean) => void;
}) {
  const { data, isPending, error } = useQuery({
    queryKey: ["mapa", trip_id, event_id],
    queryFn: () => api.mapa({ trip_id, event_id }),
  });
  const [selecionado, setSelecionado] = useState<string | null>(null);

  const lugares = useMemo(() => (data ? agruparPorLugar(data) : []), [data]);
  useEffect(() => setSelecionado(null), [trip_id, event_id]);
  useEffect(() => {
    onEstadoVazio?.(data ? data.contagens.no_mapa === 0 : false);
    return () => onEstadoVazio?.(false);
  }, [data, onEstadoVazio]);

  if (isPending) {
    return (
      <div className="flex h-full items-center justify-center text-texto-2">
        Montando o mapa de {nome ?? "este grupo"}…
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-1 p-6 text-center">
        <div>Não consegui montar o mapa deste grupo.</div>
        <div className="text-texto-2">
          {error instanceof Error ? error.message : "erro desconhecido"}
        </div>
      </div>
    );
  }

  const { contagens } = data;

  // Mapa sem nenhum ponto não é um mapa em branco: é uma resposta, e ela
  // precisa ser dita. Um quadriculado vazio e mudo faz o dono concluir que a
  // tela quebrou — o mesmo defeito que os cards de viagem já tiveram.
  if (contagens.no_mapa === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
        <span aria-hidden className="text-2xl text-texto-3">
          ⊘
        </span>
        <div className="text-[15px]">Nenhuma foto deste grupo tem lugar.</div>
        <div className="max-w-[52ch] text-texto-2">
          {contagens.sem_coordenada} de {contagens.total} fotos estão sem
          coordenada: nenhuma gravou GPS e nenhuma ficou perto o bastante, no
          tempo, de uma foto que tivesse. Sem coordenada não há mapa — nem
          estimado.
        </div>
        <div className="max-w-[52ch] text-texto-3">
          Um lugar pode aparecer aqui depois de importar uma fonte que grave
          GPS (iPhone, Apple Fotos) e regerar as sugestões na aba Revisão.
        </div>
      </div>
    );
  }

  const limites = limitesComDoadoras(
    data.limites ?? { lat_min: 0, lat_max: 0, lon_min: 0, lon_max: 0 },
    data.doadoras,
  );
  const escala = data.escala ?? {
    metros_por_grau_lat: 111_320,
    metros_por_grau_lon: 111_320,
  };
  const projecao = projetar(limites, escala);
  const lugarSelecionado =
    lugares.find((l) => l.chave === selecionado) ?? null;

  // O traço do protótipo, e a razão de ele quase nunca aparecer: a herdeira
  // recebe a coordenada EXATA da doadora (17.819 de 17.819 pares medidos com
  // distância zero). Desenhar uma reta de comprimento zero não desenha nada;
  // desenhar uma reta com algum comprimento inventaria uma distância que não
  // existe. Então o traço só sai quando é verdade — e quando não é, quem liga
  // herdeira a doadora é o painel, que diz o nome de quem doou.
  const tracos: { de: Lugar; para: DoadoraMapa }[] = [];
  const porId = new Map(data.doadoras.map((d) => [d.id, d]));
  for (const lugar of lugares) {
    const vistos = new Set<number>();
    for (const h of lugar.herdados) {
      if (h.doadora_id == null || vistos.has(h.doadora_id)) continue;
      vistos.add(h.doadora_id);
      const doadora = porId.get(h.doadora_id);
      if (!doadora || doadora.lat == null) continue;
      if (chaveDe(doadora.lat, doadora.lon) !== lugar.chave)
        tracos.push({ de: lugar, para: doadora });
    }
  }

  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-auto p-4">
          <svg
            viewBox={`0 0 ${LARGURA} ${ALTURA}`}
            preserveAspectRatio="xMidYMid meet"
            role="img"
            aria-label={`Mapa esquemático de ${data.grupo.nome}: ${lugares.length} lugares, ${contagens.no_mapa} fotos`}
            className="block h-auto w-full rounded-lg border border-borda bg-painel"
          >
            <defs>
              <pattern
                id="malha-mapa"
                width="40"
                height="40"
                patternUnits="userSpaceOnUse"
              >
                <path
                  d="M40 0H0v40"
                  fill="none"
                  stroke="rgba(255,255,255,.04)"
                  strokeWidth="1"
                />
              </pattern>
            </defs>
            <rect width={LARGURA} height={ALTURA} fill="url(#malha-mapa)" />

            {tracos.map(({ de, para }) => (
              <line
                key={`${de.chave}->${para.id}`}
                x1={projecao.x(de.lon)}
                y1={projecao.y(de.lat)}
                x2={projecao.x(para.lon)}
                y2={projecao.y(para.lat)}
                stroke="var(--color-herdado)"
                strokeWidth={1.5}
                strokeDasharray="3 3"
                opacity={0.7}
              />
            ))}

            {lugares.map((lugar) => (
              <Marcador
                key={lugar.chave}
                lugar={lugar}
                projecao={projecao}
                selecionado={lugar.chave === selecionado}
                onSelecionar={() => setSelecionado(lugar.chave)}
              />
            ))}

            {rotulosSemColisao(lugares, projecao, selecionado).map((r) => (
              <text
                key={r.chave}
                x={r.x}
                y={r.y}
                fill={
                  r.selecionado ? "var(--color-texto)" : "var(--color-texto-2)"
                }
                fontSize={12}
                className="pointer-events-none"
              >
                {r.texto}
              </text>
            ))}
          </svg>
        </div>

        <Rodape dados={data} lugares={lugares.length} />
      </div>

      <PainelDoLugar
        lugar={lugarSelecionado}
        lugares={lugares.length}
        onFechar={() => setSelecionado(null)}
      />
    </div>
  );
}

/** Os rótulos "×N" que cabem sem se sobrepor.
 *
 *  Medido na viagem "Dubai, Thai & Viet": 30 lugares, e os do sudeste
 *  asiático caem a poucos pixels uns dos outros numa escala que vai de Dubai
 *  a Hanói. Desenhar os 30 rótulos empilha "×178" sobre "×172" sobre "×142"
 *  e nenhum dos três é legível — três números ilegíveis informam menos que
 *  um legível. Como `lugares` já vem do maior para o menor, quem perde o
 *  rótulo é sempre o lugar de menos fotos; ele continua dizendo o número no
 *  tooltip e no painel, ao clicar.
 *
 *  O lugar selecionado nunca perde o rótulo: ele é o que o usuário está
 *  olhando. */
export function rotulosSemColisao(
  lugares: Lugar[],
  projecao: Projecao,
  selecionado: string | null,
): { chave: string; x: number; y: number; texto: string; selecionado: boolean }[] {
  const ALTURA_ROTULO = 14;
  const caixas: [number, number, number, number][] = [];
  const saida = [];
  const ordenados = [
    ...lugares.filter((l) => l.chave === selecionado),
    ...lugares.filter((l) => l.chave !== selecionado),
  ];
  for (const lugar of ordenados) {
    const total = totalDoLugar(lugar);
    if (total <= 1) continue;
    const texto = `×${total}`;
    const raioPx = Math.max(RAIO_MIN_PX, lugar.raio_m * projecao.pxPorMetro);
    const x = projecao.x(lugar.lon) + Math.max(raioPx, 10) + 6;
    const y = projecao.y(lugar.lat) + 4;
    const caixa: [number, number, number, number] = [
      x,
      y - ALTURA_ROTULO,
      x + texto.length * 7,
      y,
    ];
    const colide = caixas.some(
      ([x1, y1, x2, y2]) =>
        !(caixa[2] < x1 || caixa[0] > x2 || caixa[3] < y1 || caixa[1] > y2),
    );
    if (colide) continue;
    caixas.push(caixa);
    saida.push({
      chave: lugar.chave,
      x,
      y,
      texto,
      selecionado: lugar.chave === selecionado,
    });
  }
  return saida;
}

function Marcador({
  lugar,
  projecao,
  selecionado,
  onSelecionar,
}: {
  lugar: Lugar;
  projecao: Projecao;
  selecionado: boolean;
  onSelecionar: () => void;
}) {
  const x = projecao.x(lugar.lon);
  const y = projecao.y(lugar.lat);
  const tipo = tipoDoLugar(lugar);
  const total = totalDoLugar(lugar);
  const raioPx = Math.max(RAIO_MIN_PX, lugar.raio_m * projecao.pxPorMetro);
  const temLido = lugar.proprios.length > 0 || lugar.doadoras.length > 0;
  const rotulo =
    total > 0
      ? `${total} foto${total > 1 ? "s" : ""} aqui`
      : `doadora: ${lugar.doadoras[0]?.nome ?? ""}`;

  return (
    <g
      data-lugar={lugar.chave}
      data-tipo={tipo}
      data-fotos={total}
      role="button"
      tabIndex={0}
      aria-label={rotulo}
      onClick={onSelecionar}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelecionar();
        }
      }}
      className="cursor-pointer outline-none"
    >
      <title>{rotulo}</title>
      {/* Alvo de clique generoso: o ponto tem 5 px, o dedo e o mouse não. */}
      <circle cx={x} cy={y} r={Math.max(raioPx, 14)} fill="transparent" />

      {lugar.herdados.length > 0 && (
        <circle
          cx={x}
          cy={y}
          r={raioPx}
          fill="var(--color-herdado)"
          fillOpacity={selecionado ? 0.16 : 0.07}
          stroke="var(--color-herdado)"
          strokeWidth={1.8}
          strokeDasharray="3 2.6"
        />
      )}

      {temLido ? (
        <circle cx={x} cy={y} r={5} fill="var(--color-texto)" />
      ) : (
        <circle
          cx={x}
          cy={y}
          r={2.5}
          fill="var(--color-herdado)"
          fillOpacity={0.9}
        />
      )}

      {selecionado && (
        <circle
          cx={x}
          cy={y}
          r={Math.max(raioPx, 12) + 4}
          fill="none"
          stroke="var(--color-acento)"
          strokeWidth={1.5}
        />
      )}

      {/* O rótulo "×N" é desenhado numa passada própria, depois de todos os
          marcadores — sem isso ele vira um número embaixo do círculo do
          vizinho, e ainda por cima ilegível sobre ele. */}
    </g>
  );
}

function Rodape({ dados, lugares }: { dados: DadosMapa; lugares: number }) {
  const { contagens } = dados;
  return (
    <div className="border-t border-borda px-4 py-2.5">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-texto-2">
        <span className="inline-flex items-center gap-1.5">
          <i className="h-[9px] w-[9px] rounded-full bg-texto" /> coordenada
          lida do arquivo
        </span>
        <span className="inline-flex items-center gap-1.5">
          <i className="h-[9px] w-[9px] rounded-full border-[1.5px] border-dashed border-herdado" />{" "}
          lugar estimado — o círculo é o tamanho da dúvida
        </span>
        <span className="text-texto-3">
          {lugares} {lugares === 1 ? "lugar" : "lugares"} ·{" "}
          {contagens.no_mapa} de {contagens.total} fotos no mapa
        </span>
      </div>
      {/* Aceite 6: estes dois números precisam estar NA TELA. Uma foto que
          some da grade sem explicação é a mesma falha por silêncio que já
          apareceu nos cards. */}
      <div className="mt-1 flex flex-wrap items-center gap-x-4 text-[11px]">
        <span className={contagens.sem_coordenada > 0 ? "text-texto-2" : "text-texto-3"}>
          {contagens.sem_coordenada} sem coordenada
          <span className="text-texto-3"> (não dá para desenhar)</span>
        </span>
        <span className={contagens.fora_de_alcance > 0 ? "text-atencao" : "text-texto-3"}>
          {contagens.fora_de_alcance} fora de alcance
          <span className="text-texto-3">
            {" "}
            (desenhadas; o arquivo é que não responde)
          </span>
        </span>
      </div>
      <div className="mt-1 text-[11px] text-texto-3">{dados.nota_do_raio}</div>
    </div>
  );
}

/** "Neste lugar": quem está aqui e por que o sistema acha que está.
 *
 *  O `porque` aparece verbatim, uma vez por doadora — é a frase que o
 *  servidor montou com o raio e a velocidade que a produziram, e reescrevê-la
 *  aqui duplicaria a calibração. */
function PainelDoLugar({
  lugar,
  lugares,
  onFechar,
}: {
  lugar: Lugar | null;
  lugares: number;
  onFechar: () => void;
}) {
  if (!lugar) {
    return (
      <aside className="w-[300px] shrink-0 overflow-y-auto border-l border-borda bg-painel p-3">
        <div className="titulo-painel mb-2">Neste lugar</div>
        <p className="text-texto-2">
          Clique num ponto para ver quais fotos estão ali e de onde veio a
          coordenada de cada uma.
        </p>
        <p className="mt-2 text-texto-3">
          {lugares} {lugares === 1 ? "lugar" : "lugares"} neste grupo. Fotos que
          herdaram o lugar ficam exatamente sobre a foto que doou — por isso um
          ponto costuma valer por muitas.
        </p>
      </aside>
    );
  }

  const total = totalDoLugar(lugar);
  // Uma entrada por doadora, com a frase do herdeiro de MAIOR raio: se as
  // fotos deste ponto herdaram com dúvidas diferentes, a que manda é a pior.
  const porDoadora = new Map<string, PontoMapa>();
  for (const h of lugar.herdados) {
    const chave = h.doadora_nome ?? "?";
    const atual = porDoadora.get(chave);
    if (!atual || (h.raio_m ?? 0) > (atual.raio_m ?? 0)) porDoadora.set(chave, h);
  }
  const contagemPorDoadora = new Map<string, number>();
  for (const h of lugar.herdados) {
    const chave = h.doadora_nome ?? "?";
    contagemPorDoadora.set(chave, (contagemPorDoadora.get(chave) ?? 0) + 1);
  }

  const foraDoGrupo = lugar.doadoras.filter((d) => !d.no_grupo);
  const fotos = [...lugar.proprios, ...lugar.herdados].sort((a, b) =>
    (a.data_capturada ?? "").localeCompare(b.data_capturada ?? ""),
  );

  return (
    <aside className="w-[300px] shrink-0 overflow-y-auto border-l border-borda bg-painel p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="titulo-painel">Neste lugar</div>
        <button
          onClick={onFechar}
          className="rounded px-1 text-texto-3 hover:text-texto"
          title="Fechar"
        >
          ✕
        </button>
      </div>

      <div className="mb-1 font-medium">
        {total} {total === 1 ? "foto" : "fotos"}
      </div>
      <div className="mb-3 text-texto-3">
        {lugar.lat.toFixed(5)}, {lugar.lon.toFixed(5)}
      </div>

      {porDoadora.size > 0 && (
        <div className="mb-3">
          <div className="titulo-painel mb-1.5">Por que este lugar</div>
          {[...porDoadora.entries()].map(([doadora, ponto]) => (
            <div
              key={doadora}
              className="mb-2 rounded border border-borda border-l-2 border-l-herdado p-2 text-texto-2"
            >
              <div className="mb-1 text-texto">
                {contagemPorDoadora.get(doadora)}{" "}
                {contagemPorDoadora.get(doadora) === 1
                  ? "foto herdou"
                  : "fotos herdaram"}{" "}
                de {doadora}
              </div>
              {/* A frase pronta do servidor. Aceite 3. */}
              <div>{ponto.porque}</div>
            </div>
          ))}
        </div>
      )}

      {lugar.proprios.length > 0 && (
        <div className="mb-3 text-texto-2">
          {lugar.proprios.length}{" "}
          {lugar.proprios.length === 1 ? "foto gravou" : "fotos gravaram"} esta
          coordenada no próprio arquivo — sem dúvida a desenhar.
        </div>
      )}

      {/* O ponto cheio precisa ter dono. A doadora costuma estar FORA do
          grupo — é uma referência do Apple Fotos, sem viagem nem evento — e
          sem esta linha o mapa desenha um ponto branco que não corresponde a
          nenhuma foto da lista abaixo. */}
      {foraDoGrupo.length > 0 && (
        <div className="mb-3 text-texto-2">
          O ponto cheio aqui{" "}
          {foraDoGrupo.length === 1 ? "é a foto que doou" : "são as fotos que doaram"}{" "}
          a coordenada, de fora deste grupo:{" "}
          <span className="text-texto">
            {foraDoGrupo.map((d) => d.nome).join(", ")}
          </span>
          .
        </div>
      )}

      {lugar.fora_de_alcance > 0 && (
        <div className="mb-3 rounded border border-borda border-l-2 border-l-atencao p-2 text-texto-2">
          {lugar.fora_de_alcance}{" "}
          {lugar.fora_de_alcance === 1 ? "foto está" : "fotos estão"} fora de
          alcance: a coordenada está no catálogo, o arquivo é que não responde
          agora.
        </div>
      )}

      <div className="titulo-painel mb-1.5">Fotos aqui</div>
      {fotos.slice(0, LIMITE_LISTA).map((p) => (
        <div
          key={p.media_id}
          className="flex gap-2 border-b border-borda/60 py-1.5 last:border-b-0"
          title={p.porque ?? "Coordenada lida do próprio arquivo."}
        >
          <Miniatura
            media={{
              id: p.media_id,
              nome: p.nome,
              data_capturada: p.data_capturada,
              motivo_indisponivel: p.motivo_indisponivel,
            }}
            className="h-[30px] w-[40px] shrink-0 rounded text-[9px]"
          />
          <div className="min-w-0">
            <div className="truncate">{p.nome}</div>
            <div className="text-texto-3">
              {[p.camera, hora(p.data_capturada)].filter(Boolean).join(" · ")}
            </div>
            <div className={p.estimado ? "text-herdado" : "text-texto-2"}>
              {p.estimado ? "estimado" : "lido do arquivo"}
            </div>
          </div>
        </div>
      ))}
      {fotos.length > LIMITE_LISTA && (
        <div className="pt-2 text-texto-3">
          e mais {fotos.length - LIMITE_LISTA} neste mesmo ponto — todas com a
          mesma origem de coordenada.
        </div>
      )}
    </aside>
  );
}

function hora(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? null
    : d.toLocaleString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
}
