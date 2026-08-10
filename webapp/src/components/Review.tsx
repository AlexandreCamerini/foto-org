import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Miniatura } from "./Miniatura";
import { api, type Media, type Sugestao } from "../api";
import { formatarData } from "../data";
import type { Job } from "../hooks/useJob";
import { Confianca } from "./Confianca";
import Botao from "../ui/Botao";

const STATUS_ABAS = [
  ["pendente", "Pendentes"],
  ["aprovada", "Aprovadas"],
  ["rejeitada", "Rejeitadas"],
] as const;

type Item = {
  id: number;
  media_id: number;
  nome: string;
  pasta: string;
  destino: string;
  nivel: string;
  status: string;
  data_capturada?: string | null;
  camera?: string | null;
  gps_estimado?: boolean;
  motivo_indisponivel?: string | null;
};

/** Revisão origem→destino: o usuário decide, o motor explica.
 *
 * A unidade de decisão é o GRUPO, não a foto solta (docs/DECISOES.md D-018):
 * "aprovar as 22 de Viagens/2024 - França" é uma decisão que dá para tomar
 * com a informação que se tem; "aprovar a linha 37 de 63" não é.
 */
export default function Review({
  job,
  fonte,
}: {
  job: Job;
  fonte?: number;
}) {
  const [status, setStatus] = useState<string>("pendente");
  // ABERTOS, não "fechados": a tela nasce com os grupos dobrados. Aberta,
  // ela mostrava ~200 linhas quase idênticas de 3 dos 10 grupos; dobrada,
  // mostra as 10 decisões que a fila realmente pede. Medido no acervo do
  // dono: 5.048 pendências, 10 destinos, e o nível de confiança é constante
  // dentro de cada um — a linha por foto não distingue nada.
  const [abertos, setAbertos] = useState<Set<string>>(new Set());
  const [porque, setPorque] = useState<number | null>(null);
  const [editando, setEditando] = useState<number | null>(null);
  const [valorEdicao, setValorEdicao] = useState("");
  const [erroEdicao, setErroEdicao] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Os grupos vêm inteiros e contados no banco — são dez linhas. A fila de
  // fotos NÃO vem junto: era ela que trazia 200 itens e fazia a tela
  // acreditar que o acervo tinha 3 grupos.
  const { data: grupos } = useQuery({
    queryKey: ["sugestoes", "grupos", status, fonte],
    queryFn: () => api.gruposDeSugestoes(status, fonte),
  });
  const { data: contagensData } = useQuery({
    queryKey: ["sugestoes", "contagens", status, fonte],
    queryFn: () => api.sugestoes(status, 0, 1, fonte),
  });

  const acao = useMutation({
    mutationFn: ({ ids, tipo }: { ids: number[]; tipo: string }) =>
      api.acaoSugestoes(ids, tipo),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["sugestoes"] }),
  });

  // Ação sobre o GRUPO: a tela manda o destino, o servidor resolve os ids.
  // Sem isto "Aprovar 597" aprovava as 85 que a página tinha trazido.
  const acaoNoGrupo = useMutation({
    mutationFn: ({ destino, tipo }: { destino: string; tipo: string }) =>
      api.acaoNoGrupo(destino, tipo, status, fonte),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["sugestoes"] }),
  });

  // Editar marca a sugestão como EDITADA no servidor (fotoorganizer/
  // repositories/suggestions.py) — ela some da aba atual ao recarregar
  // porque deixou de ser "pendente", o que é o comportamento certo: a
  // correção já valeu, não precisa de uma segunda aprovação.
  const editarDestino = useMutation({
    mutationFn: ({ id, destino }: { id: number; destino: string }) =>
      api.editarDestino(id, destino),
    onSuccess: () => {
      setEditando(null);
      setErroEdicao(null);
      void queryClient.invalidateQueries({ queryKey: ["sugestoes"] });
    },
    onError: (e: Error) => setErroEdicao(e.message),
  });

  const iniciarEdicao = (item: Item) => {
    setEditando(item.id);
    setValorEdicao(item.destino);
    setErroEdicao(null);
  };

  const cancelarEdicao = () => {
    setEditando(null);
    setErroEdicao(null);
  };

  const salvarEdicao = (id: number) => {
    const destino = valorEdicao.trim();
    if (!destino) return;
    editarDestino.mutate({ id, destino });
  };

  const contagens = contagensData?.contagens ?? {};
  const lista = grupos ?? [];
  const totalNaFila = lista.reduce((s, g) => s + g.total, 0);

  const alternarGrupo = (destino: string) =>
    setAbertos((s) => {
      const novo = new Set(s);
      novo.has(destino) ? novo.delete(destino) : novo.add(destino);
      return novo;
    });

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-borda px-3 py-2">
        {STATUS_ABAS.map(([valor, rotulo]) => (
          <button
            key={valor}
            onClick={() => setStatus(valor)}
            className={`rounded-md px-3 py-1 hover:bg-cartao ${
              status === valor ? "bg-realce text-texto" : "text-texto-2"
            }`}
          >
            {rotulo}
            <span className="ml-1.5 text-texto-3">{contagens[valor] ?? 0}</span>
          </button>
        ))}
        <div className="flex-1" />
        <span className="text-texto-3">
          {/* Números do banco, não da página: dizia "200 em 3 grupos" para
              uma fila de 5.048 em 10. */}
          {totalNaFila.toLocaleString("pt-BR")} em {lista.length}{" "}
          {lista.length === 1 ? "grupo" : "grupos"}
        </span>
        <Botao
          onClick={() => job.gerarSugestoes()}
          disabled={job.rodando}
            className="hover:border-borda-forte">
          {job.rodando && job.estado.tipo === "sugestoes"
            ? "Gerando…"
            : "Gerar/atualizar sugestões"}
        </Botao>
      </div>

      {lista.length === 0 ? (
        <div className="flex flex-1 items-center justify-center text-texto-2">
          Nada aqui — gere as sugestões ou mude o filtro de status.
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {lista.map((grupo) => {
            const destino = grupo.destino;
            const aberto = abertos.has(destino);
            const estimadas = grupo.estimadas;
            return (
              <section key={destino}>
                <header
                  role="button"
                  tabIndex={0}
                  aria-expanded={aberto}
                  onClick={() => alternarGrupo(destino)}
                  onKeyDown={(e) => {
                    // O botão "Aprovar" aqui dentro já responde ao próprio
                    // Enter — sem este filtro, o keydown dele borbulharia e
                    // abriria/fecharia o grupo junto com a aprovação.
                    if (e.target !== e.currentTarget) return;
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      alternarGrupo(destino);
                    }
                  }}
                  className="sticky top-0 z-10 flex cursor-pointer items-center gap-2 border-b border-borda bg-cartao px-3 py-2 hover:bg-realce focus:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-acento"
                >
                  <span className="w-3 text-texto-3">{aberto ? "▾" : "▸"}</span>
                  {/* Origem → destino na mesma linha: é a leitura "situação
                      atual → situação proposta" que não existia em tela
                      nenhuma. A pasta de origem só aparecia na linha da foto
                      quando faltavam câmera E data — ou seja, quase nunca. */}
                  <span className="min-w-0 shrink truncate text-texto-2">
                    {origemLegivel(grupo.origens)}
                  </span>
                  <span aria-hidden className="shrink-0 text-texto-3">
                    →
                  </span>
                  <span className="truncate font-medium">{destino}</span>
                  <span className="shrink-0 text-texto-2">
                    · {grupo.total.toLocaleString("pt-BR")}{" "}
                    {grupo.total === 1 ? "foto" : "fotos"}
                    {estimadas > 0 && (
                      <span className="text-herdado">
                        {" "}
                        · {estimadas.toLocaleString("pt-BR")} com lugar estimado
                      </span>
                    )}
                    {grupo.fora_de_alcance > 0 && (
                      // Sem isto o dono aprova 2.405 fotos de um disco
                      // desligado sem saber (mesma honestidade de D-033).
                      <span className="text-atencao">
                        {" "}
                        · {grupo.fora_de_alcance.toLocaleString("pt-BR")} fora
                        de alcance
                      </span>
                    )}
                  </span>
                  <Confianca nivel={grupo.nivel} />
                  <div className="flex-1" />
                  {status === "pendente" && (
                    <Botao tamanho="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        acaoNoGrupo.mutate({ destino, tipo: "aprovar" });
                      }}
            className="bg-transparent text-micro text-texto-2 hover:border-ok hover:text-ok">
                      Aprovar {grupo.total.toLocaleString("pt-BR")}
                    </Botao>
                  )}
                </header>

                {aberto && (
                  <FotosDoGrupo
                    destino={destino}
                    status={status}
                    fonte={fonte}
                    total={grupo.total}
                    renderizar={(s) => (

                    <div key={s.id} className="border-b border-borda/60">
                      {editando === s.id ? (
                        <div className="flex items-center gap-3 px-3 py-2">
                          <img
                            src={api.thumbUrl(s.media_id)}
                            alt={s.nome}
                            loading="lazy"
                            className="h-9 w-12 shrink-0 rounded object-cover bg-cartao"
                          />
                          <div className="min-w-0 flex-1">
                            <div className="mb-1 truncate text-[11px] text-texto-3">
                              {s.nome}
                            </div>
                            <input
                              autoFocus
                              value={valorEdicao}
                              onChange={(e) => setValorEdicao(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") salvarEdicao(s.id);
                                if (e.key === "Escape") cancelarEdicao();
                              }}
                              className="w-full rounded-md border border-borda bg-cartao px-2 py-1 outline-none focus:border-acento"
                            />
                            {erroEdicao && (
                              <div className="mt-1 text-[11px] text-erro">
                                {erroEdicao}
                              </div>
                            )}
                          </div>
                          <div className="flex shrink-0 gap-2">
                            <Botao tamanho="sm"
                              onClick={() => salvarEdicao(s.id)}
                              disabled={editarDestino.isPending}
            className="bg-transparent text-ok hover:bg-cartao">
                              Salvar
                            </Botao>
                            <Botao tamanho="sm"
                              onClick={cancelarEdicao}
            className="bg-transparent text-texto-2 hover:bg-cartao">
                              Cancelar
                            </Botao>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center gap-3 px-3 py-1.5 hover:bg-painel">
                          <Miniatura
                            media={{
                              id: s.media_id,
                              nome: s.nome,
                              data_capturada: s.data_capturada ?? null,
                              motivo_indisponivel: s.motivo_indisponivel ?? null,
                            } as Media}
                            /* 48px de largura não cabem os ~50px da data:
                               ela vazava para fora da caixa e encostava na
                               linha da câmera ao lado (6px medidos). A linha
                               ao lado já traz nome, câmera e data. */
                            denso
                            className="h-9 w-12 shrink-0 rounded bg-cartao"
                          />
                          <div className="min-w-0 flex-1">
                            {/* Nome primeiro. Antes a pasta vinha antes e o
                                truncate cortava a linha antes de o nome do
                                arquivo aparecer — 63 linhas idênticas. */}
                            <div className="truncate font-medium">{s.nome}</div>
                            <div className="truncate text-[11px] text-texto-2">
                              {[s.camera, formatarData(s.data_capturada)]
                                .filter(Boolean)
                                .join(" · ") || pastaCurta(s.pasta)}
                            </div>
                          </div>
                          <Botao variante="fantasma" tamanho="sm"
                            onClick={() => iniciarEdicao(s)}
                            title={`Editar destino de ${s.nome}`}
            className="px-1 text-texto-3">
                            ✎
                          </Botao>
                          <Botao variante="fantasma" tamanho="sm"
                            onClick={() =>
                              setPorque((p) => (p === s.media_id ? null : s.media_id))
                            }
                            aria-expanded={porque === s.media_id}
                            title={`Por que este destino para ${s.nome}?`}
            className="px-1">
                            <Confianca nivel={s.nivel} />
                          </Botao>
                          {status === "pendente" ? (
                            <div className="flex shrink-0 gap-2">
                              <Botao tamanho="sm"
                                onClick={() =>
                                  acao.mutate({ ids: [s.id], tipo: "aprovar" })
                                }
            className="bg-transparent text-texto-2 hover:border-ok hover:text-ok">
                                Aprovar
                              </Botao>
                              <Botao tamanho="sm"
                                onClick={() =>
                                  acao.mutate({ ids: [s.id], tipo: "rejeitar" })
                                }
            className="bg-transparent text-texto-2 hover:border-erro hover:text-erro">
                                Rejeitar
                              </Botao>
                            </div>
                          ) : (
                            <Botao tamanho="sm"
                              onClick={() =>
                                acao.mutate({ ids: [s.id], tipo: "desfazer" })
                              }
            className="bg-transparent text-texto-2 hover:bg-cartao">
                              Desfazer
                            </Botao>
                          )}
                        </div>
                      )}
                      {porque === s.media_id && <PorQue mediaId={s.media_id} />}
                    </div>
                    )}
                  />
                )}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

/** Quantas fotos de um grupo a tela carrega de uma vez.
 *
 *  O grupo maior do acervo real tem 2.406. Trazer tudo ao abrir seria
 *  repetir, dentro do grupo, o erro que a tela tinha na fila inteira. */
const POR_PAGINA = 200;

/** As fotos de UM grupo, buscadas só quando ele abre.
 *
 *  Antes a tela pedia 200 sugestões da fila inteira e deduzia os grupos do
 *  que chegava — o que, no acervo do dono, mostrava 3 dos 10 grupos e
 *  deixava 4.848 das 5.048 pendências sem nenhum gesto que as alcançasse.
 *  Agora o recorte é do servidor (`destino=`), e o que não coube tem um
 *  botão dizendo quanto falta em vez de sumir em silêncio. */
function FotosDoGrupo({
  destino,
  status,
  fonte,
  total,
  renderizar,
}: {
  destino: string;
  status: string;
  fonte?: number;
  total: number;
  renderizar: (item: Item) => React.ReactNode;
}) {
  const [limite, setLimite] = useState(POR_PAGINA);
  const { data, isPending } = useQuery({
    queryKey: ["sugestoes", "grupo", destino, status, fonte, limite],
    queryFn: () => api.sugestoes(status, 0, limite, fonte, destino),
  });

  if (isPending) {
    return <div className="px-3 py-2 text-texto-3">carregando…</div>;
  }
  const itens = (data?.itens ?? []) as Item[];
  const faltam = total - itens.length;
  return (
    <>
      {itens.map(renderizar)}
      {faltam > 0 && (
        <button
          onClick={() => setLimite((n) => n + POR_PAGINA)}
          className="w-full border-b border-borda/60 px-3 py-2 text-left text-texto-2 hover:bg-painel"
        >
          mostrar mais {Math.min(faltam, POR_PAGINA).toLocaleString("pt-BR")} ·
          faltam {faltam.toLocaleString("pt-BR")} de{" "}
          {total.toLocaleString("pt-BR")}
        </button>
      )}
    </>
  );
}

/** "de onde vêm", em uma linha. */
function origemLegivel(origens: { pasta: string; fotos: number }[]): string {
  if (origens.length === 0) return "—";
  const [maior, ...resto] = origens;
  const nome = maior.pasta.split("/").filter(Boolean).pop() || maior.pasta || "—";
  if (resto.length === 0) return nome;
  return `${nome} e mais ${resto.length}`;
}

/** Busca as evidências só quando o usuário pergunta — 63 linhas não podem
 *  disparar 63 requisições no carregamento. */
function PorQue({ mediaId }: { mediaId: number }) {
  const { data, isPending } = useQuery({
    queryKey: ["detalhe", mediaId],
    queryFn: () => api.detalhe(mediaId),
  });
  const sugestao = data?.sugestao as Sugestao | undefined;

  if (isPending) {
    return <div className="px-3 pb-2 pl-[68px] text-texto-3">carregando…</div>;
  }
  if (!sugestao?.evidencias?.length) {
    return (
      <div className="px-3 pb-2 pl-[68px] text-texto-3">
        Sem evidência registrada para esta sugestão.
      </div>
    );
  }
  return (
    <ul className="space-y-1 px-3 pb-2 pl-[68px]">
      {sugestao.evidencias.map((ev, i) => (
        <li key={i} className="flex gap-2 text-[11px]">
          <Confianca nivel={ev.nivel} rotulo={false} />
          <span className="text-texto-2">
            <span className="text-texto">{ev.campo}</span>: {ev.valor} —{" "}
            {ev.justificativa}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Caminho absoluto inteiro não cabe e não informa: o que localiza a foto é
 *  o fim do caminho, não o começo. */
function pastaCurta(pasta: string): string {
  const partes = pasta.split("/").filter(Boolean);
  return partes.length <= 2 ? pasta : "…/" + partes.slice(-2).join("/");
}
