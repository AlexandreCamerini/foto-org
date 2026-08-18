import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../api";
import type {
  CampoAusenteGenaiPasta,
  CampoGenaiPasta,
  CandidataGenaiPasta,
  ConfigGenaiPasta,
  CustoGenaiPasta,
  PropostaGenaiPasta,
  RodadaGenaiPasta,
} from "../api";
import { Confianca } from "./Confianca";
import Botao from "../ui/Botao";

/** Os passos do assistente (UI-SPEC § Wizard state machine). */
type Passo =
  | "gate"
  | "candidatas"
  | "custo"
  | "rodando"
  | "revisao"
  | "concluido"
  | "erro";

/** Mesmo truncamento de `Review.tsx::pastaCurta` — reproduzido aqui em vez
 *  de importado porque `pastaCurta` não é exportada de lá, e Review.tsx
 *  passa a importar ESTE componente no plano 07-08: importar de volta
 *  criaria um ciclo de módulos. Qualquer mudança na lógica de truncamento
 *  precisa ser replicada nos dois lugares. */
function pastaCurta(pasta: string): string {
  const partes = pasta.split("/").filter(Boolean);
  return partes.length <= 2 ? pasta : "…/" + partes.slice(-2).join("/");
}

/** "categoria" / "cidade/país" / "categoria · cidade/país" — Copywriting
 *  Contract, Step 1 missing-field tag. `switch` implícito via `Record`
 *  exaustivo: um `CampoAusenteGenaiPasta` novo sem entrada aqui quebra a
 *  compilação, não silenciosamente vira "undefined" na tela. */
const RÓTULO_CAMPO_AUSENTE: Record<CampoAusenteGenaiPasta, string> = {
  categoria: "categoria",
  cidade_pais: "cidade/país",
};

function etiquetaCamposAusentes(campos: CampoAusenteGenaiPasta[]): string {
  return campos.map((c) => RÓTULO_CAMPO_AUSENTE[c]).join(" · ");
}

/** Rótulo de exibição de cada campo que uma proposta pode preencher
 *  (`_CAMPOS_DE_VALOR` em `genai_pasta.py`). Mesmo raciocínio de exaustividade
 *  do `Record` acima: um campo novo sem entrada aqui quebra a compilação. */
const RÓTULO_CAMPO_GENAI: Record<CampoGenaiPasta, string> = {
  categoria: "categoria",
  cidade: "cidade",
  pais: "país",
  evento: "evento",
};

/** Nível de confiança de toda proposta de GenAI de pasta: o score de
 *  `SCORES_REFERENCIA["llm_pasta"]` (0.55, `classification/confidence.py`)
 *  é PROVISÓRIO — ainda não medido contra o acervo real, medição fica para
 *  o plano 07-09 — mas hoje cai sempre em "média" (limiar 0.5-0.8). O
 *  endpoint de `rodar()` não devolve nível por proposta; este UI-SPEC (Open
 *  Item 1) deixa esse número fora de escopo, então fixar "média" aqui é
 *  mais honesto do que inventar um campo que o backend não expõe. */
const NIVEL_LLM_PASTA = "media";

/** Valores muito pequenos (frações de centavo) — 3 casas decimais, não o
 *  padrão de 2 do `Intl`, para o dono não ver "R$ 0,00" quando o custo real
 *  é "R$ 0,034". Formatação local, não decisão de negócio. */
function formatarMoeda(valor: number, prefixo: string): string {
  return `${prefixo} ${valor.toFixed(3).replace(".", ",")}`;
}

function formatarTokens(tokens: number): string {
  return tokens.toLocaleString("pt-BR");
}

// -- Passo 0 — Desligado (opt-in gate) -------------------------------------

function PassoGate({
  config,
  habilitarPendente,
  onHabilitar,
  onFechar,
}: {
  config: ConfigGenaiPasta;
  habilitarPendente: boolean;
  onHabilitar: () => void;
  onFechar: () => void;
}) {
  const [marcado, setMarcado] = useState(false);

  return (
    <div className="flex flex-col gap-4 py-6">
      <div className="flex items-start gap-2">
        <span className="text-atencao">⚠</span>
        <span className="font-titulo">
          Classificação de pasta por IA está desligada
        </span>
      </div>

      {config.servicos_externos ? (
        <>
          <p className="text-texto-2">
            Ao habilitar, o nome de cada pasta candidata e os metadados já
            catalogados (nunca imagens) são enviados ao Claude Sonnet 5 numa
            única chamada por sessão, com custo estimado mostrado antes de
            cada envio. Nada sai da máquina sem sua confirmação explícita a
            cada sessão.
          </p>
          <label className="flex items-center gap-2 text-texto">
            <input
              type="checkbox"
              className="h-3.5 w-3.5 shrink-0 rounded-sm border-borda-forte accent-acento"
              checked={marcado}
              onChange={(e) => setMarcado(e.target.checked)}
            />
            Habilitar classificação de pasta por IA
          </label>
          <div className="flex justify-end gap-2">
            <Botao variante="fantasma" onClick={onFechar}>
              Cancelar
            </Botao>
            <Botao
              variante="solido"
              disabled={!marcado || habilitarPendente}
              onClick={onHabilitar}
            >
              Habilitar e continuar
            </Botao>
          </div>
        </>
      ) : (
        <>
          <p className="text-texto-2">
            Serviços externos estão desligados nas configurações do app —
            habilite [privacidade] servicos_externos antes de usar este
            recurso.
          </p>
          <div className="flex justify-end">
            <Botao variante="fantasma" onClick={onFechar}>
              Cancelar
            </Botao>
          </div>
        </>
      )}
    </div>
  );
}

// -- Passo 1 — Candidatos (D-01) -------------------------------------------

function PassoCandidatas({
  candidatas,
  selecionadas,
  onAlternar,
  onDesligar,
  onAvancar,
  avancarPendente,
  onFechar,
}: {
  candidatas: CandidataGenaiPasta[];
  selecionadas: Set<string>;
  onAlternar: (pasta: string) => void;
  onDesligar: () => void;
  onAvancar: () => void;
  avancarPendente: boolean;
  onFechar: () => void;
}) {
  const total = candidatas.length;
  const marcadas = selecionadas.size;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="font-titulo">Pastas candidatas</span>
          {total > 0 && (
            <p className="text-texto-2">
              Sistema pré-filtrou pastas com categoria OU cidade/país
              vazios. Desmarque o que não quer incluir nesta sessão.
            </p>
          )}
        </div>
        <span
          role="button"
          tabIndex={0}
          className="shrink-0 cursor-pointer text-texto-3 hover:text-texto-2"
          onClick={onDesligar}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") onDesligar();
          }}
        >
          Desligar
        </span>
      </div>

      {total === 0 ? (
        <>
          <p className="text-texto-2">
            Nenhuma pasta com categoria ou cidade/país vazios no catálogo
            atual.
          </p>
          <div className="flex justify-end">
            <Botao variante="fantasma" onClick={onFechar}>
              Fechar
            </Botao>
          </div>
        </>
      ) : (
        <>
          <div>
            {candidatas.map((c) => (
              <div
                key={c.pasta}
                className="flex items-center gap-3 border-b border-borda px-3 py-1.5"
              >
                <input
                  type="checkbox"
                  className="h-3.5 w-3.5 shrink-0 rounded-sm border-borda-forte accent-acento"
                  checked={selecionadas.has(c.pasta)}
                  onChange={() => onAlternar(c.pasta)}
                  aria-label={`Incluir ${pastaCurta(c.pasta)}`}
                />
                <span className="min-w-0 flex-1 truncate font-titulo">
                  {pastaCurta(c.pasta)}
                </span>
                <span className="shrink-0 text-[11px] text-texto-2">
                  {etiquetaCamposAusentes(c.campos_ausentes)} ·{" "}
                  {c.n_fotos} fotos
                </span>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between">
            <span className="text-texto-2">
              {marcadas} de {total} pastas selecionadas
            </span>
            <div className="flex gap-2">
              <Botao variante="fantasma" onClick={onFechar}>
                Cancelar
              </Botao>
              <Botao
                variante="solido"
                disabled={marcadas === 0 || avancarPendente}
                title={
                  marcadas === 0 ? "Selecione ao menos uma pasta" : undefined
                }
                onClick={onAvancar}
              >
                Avançar
              </Botao>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// -- Passo 2 — Custo (D-04/D-05, D-079) -------------------------------------

function PassoCusto({
  custo,
  totalPastas,
  onVoltar,
  onConfirmar,
  confirmarPendente,
}: {
  custo: CustoGenaiPasta;
  totalPastas: number;
  onVoltar: () => void;
  onConfirmar: () => void;
  confirmarPendente: boolean;
}) {
  const entradaBrl = custo.custo_entrada_usd * custo.cambio_usd_brl;
  const saidaBrl = custo.teto_custo_saida_usd * custo.cambio_usd_brl;

  return (
    <div className="flex flex-col gap-3">
      <span className="font-titulo">Custo estimado desta sessão</span>
      <p className="text-texto-2">
        {totalPastas} pastas · 1 chamada ao Claude Sonnet 5
      </p>

      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between text-texto-3">
          <span>Entrada (estimada):</span>
          <span>
            até {formatarTokens(custo.tokens_entrada)} tokens · até{" "}
            {formatarMoeda(entradaBrl, "R$")}
          </span>
        </div>
        <div className="flex items-center justify-between text-texto-3">
          <span>Saída (estimativa):</span>
          <span>
            até {formatarTokens(custo.teto_tokens_saida)} tokens · até{" "}
            {formatarMoeda(saidaBrl, "R$")}
          </span>
        </div>
        <div className="flex items-center justify-between border-t border-borda pt-1 font-titulo">
          <span>Total estimado:</span>
          <span>
            até {formatarMoeda(custo.teto_custo_total_brl, "R$")} (
            {formatarMoeda(custo.teto_custo_total_usd, "US$")})
          </span>
        </div>
      </div>

      <p className="text-texto-2">
        Nada foi enviado ainda — os dois números acima são estimativas
        locais. Depois de confirmar, a contagem exata da entrada aparece no
        resumo final. O valor acima é o teto, o custo real tende a ser
        menor.
      </p>

      <div className="flex justify-end gap-2">
        <Botao variante="fantasma" onClick={onVoltar}>
          Voltar
        </Botao>
        <Botao
          variante="solido"
          disabled={confirmarPendente}
          onClick={onConfirmar}
        >
          Confirmar e classificar
        </Botao>
      </div>
    </div>
  );
}

// -- Passo 3 — Rodando -------------------------------------------------------

function PassoRodando({ segundos }: { segundos: number }) {
  const minutos = Math.floor(segundos / 60);
  const segs = segundos % 60;
  const relogio = `${minutos}:${String(segs).padStart(2, "0")}`;

  return (
    <div className="flex flex-col items-center gap-3 py-6 text-center">
      <span className="font-titulo">
        Consultando Claude Sonnet 5… ({relogio})
      </span>
      <p className="text-texto-2">
        A chamada já foi enviada e não pode ser cancelada — aguarde a
        resposta.
      </p>
    </div>
  );
}

// -- Estado de erro -----------------------------------------------------------

function PassoErro({
  motivo,
  onVoltar,
  onFechar,
}: {
  motivo: string;
  onVoltar: () => void;
  onFechar: () => void;
}) {
  return (
    <div className="flex flex-col gap-4 py-6">
      <p className="text-erro">
        Não foi possível classificar: {motivo}. Nenhum dado foi perdido —
        tente novamente quando quiser.
      </p>
      <div className="flex justify-end gap-2">
        <Botao variante="fantasma" onClick={onFechar}>
          Fechar
        </Botao>
        <Botao variante="solido" onClick={onVoltar}>
          Voltar
        </Botao>
      </div>
    </div>
  );
}

// -- Passo 4 — Revisão (D-03 antes/depois por pasta) -------------------------

function PassoRevisao({
  rodada,
  aprovadas,
  onAlternar,
  expandido,
  onExpandir,
  semRespostaExpandido,
  onAlternarSemResposta,
  onAprovar,
  aprovarPendente,
  onFechar,
}: {
  rodada: RodadaGenaiPasta;
  aprovadas: Set<string>;
  onAlternar: (pasta: string) => void;
  expandido: string | null;
  onExpandir: (pasta: string) => void;
  semRespostaExpandido: boolean;
  onAlternarSemResposta: () => void;
  onAprovar: () => void;
  aprovarPendente: boolean;
  onFechar: () => void;
}) {
  // Agrupado por PASTA, não por campo: o dono decide por pasta (D-01/D-03) —
  // uma pasta com proposta de categoria E de cidade vira UMA linha com duas
  // linhas "depois", nunca duas linhas de pasta repetida.
  const porPasta = new Map<string, PropostaGenaiPasta[]>();
  for (const p of rodada.propostas) {
    const lista = porPasta.get(p.pasta) ?? [];
    lista.push(p);
    porPasta.set(p.pasta, lista);
  }
  const pastas = Array.from(porPasta.keys());
  const total = pastas.length;
  const marcadas = aprovadas.size;

  return (
    <div className="flex flex-col gap-3">
      <span className="font-titulo">Revisão — {total} propostas</span>

      <div>
        {pastas.map((pasta) => {
          const propostas = porPasta.get(pasta)!;
          return (
            <div key={pasta} className="border-b border-borda px-3 py-1.5">
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="h-3.5 w-3.5 shrink-0 rounded-sm border-borda-forte accent-acento"
                  checked={aprovadas.has(pasta)}
                  onChange={() => onAlternar(pasta)}
                  aria-label={`Aprovar proposta para ${pastaCurta(pasta)}`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-titulo">{pastaCurta(pasta)}</span>
                    <Botao
                      variante="fantasma"
                      tamanho="sm"
                      onClick={() => onExpandir(pasta)}
                      title={`Por que esta proposta para ${pastaCurta(pasta)}?`}
                      aria-expanded={expandido === pasta}
                      className="shrink-0 px-1"
                    >
                      ⓘ
                    </Botao>
                  </div>
                  {propostas.map((p) => (
                    <div key={p.campo} className="flex flex-col">
                      <span className="text-texto-2">
                        antes: {RÓTULO_CAMPO_GENAI[p.campo]} — {p.valor_antes ?? "(vazio)"}
                      </span>
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-titulo">
                          depois: {RÓTULO_CAMPO_GENAI[p.campo]} — {p.valor_proposto}
                        </span>
                        <span className="rounded-full border border-herdado/40 bg-herdado/10 text-herdado px-1.5 py-0.5 text-[11px]">
                          IA · pasta
                        </span>
                        <Confianca nivel={NIVEL_LLM_PASTA} />
                      </span>
                    </div>
                  ))}
                  {expandido === pasta && (
                    <div className="mt-1 flex flex-col gap-1 text-texto-2">
                      {propostas.map((p) => (
                        <span key={p.campo}>
                          {RÓTULO_CAMPO_GENAI[p.campo]}: {p.justificativa}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {rodada.pastas_sem_resposta.length > 0 && (
        <div className="flex flex-col gap-1 border-b border-borda px-3 py-1.5">
          <div className="flex items-start gap-2">
            <span className="text-atencao">⚠</span>
            <span className="text-texto-2">
              {rodada.pastas_sem_resposta.length} pastas sem resposta confiável — Claude não teve segurança pra classificar. Nenhuma sugestão foi criada.{" "}
              <span
                role="button"
                tabIndex={0}
                className="cursor-pointer text-texto-3 hover:text-texto-2"
                aria-expanded={semRespostaExpandido}
                onClick={onAlternarSemResposta}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") onAlternarSemResposta();
                }}
              >
                Ver quais »
              </span>
            </span>
          </div>
          {semRespostaExpandido && (
            <ul className="pl-6 text-texto-3">
              {rodada.pastas_sem_resposta.map((pasta) => (
                <li key={pasta}>{pastaCurta(pasta)}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="text-texto-2">
          {marcadas} de {total} propostas selecionadas
        </span>
        <div className="flex gap-2">
          <Botao variante="fantasma" onClick={onFechar}>
            Fechar sem aprovar
          </Botao>
          <Botao
            variante="solido"
            disabled={marcadas === 0 || aprovarPendente}
            onClick={onAprovar}
          >
            Aprovar {marcadas} selecionadas
          </Botao>
        </div>
      </div>
    </div>
  );
}

// -- Passo 5 — Concluído -------------------------------------------------------

function PassoConcluido({
  aprovadas,
  custoReal,
  custoEstimado,
  onFechar,
}: {
  aprovadas: number;
  custoReal: CustoGenaiPasta | null;
  custoEstimado: CustoGenaiPasta | null;
  onFechar: () => void;
}) {
  // D-079 (decisão híbrida): o custo real da entrada só existe depois da
  // chamada, calculado por `contar_exato()`. Quando falha (never-crash,
  // 07-03) ou a rodada veio de uma sessão recuperada sem custo próprio,
  // cai no valor estimado do passo 2 com a ressalva — nunca mostra R$ 0,00
  // como se a chamada não tivesse custado nada.
  const linhaCusto = custoReal
    ? {
        valor: formatarMoeda(
          custoReal.custo_entrada_usd * custoReal.cambio_usd_brl,
          "R$",
        ),
        tokens: formatarTokens(custoReal.tokens_entrada),
        sufixo: "contagem exata",
      }
    : custoEstimado
      ? {
          valor: formatarMoeda(
            custoEstimado.custo_entrada_usd * custoEstimado.cambio_usd_brl,
            "R$",
          ),
          tokens: formatarTokens(custoEstimado.tokens_entrada),
          sufixo: "estimativa — contagem exata indisponível",
        }
      : null;

  return (
    <div className="flex flex-col gap-3 py-6">
      <div className="flex items-center gap-2">
        <span className="text-ok">✓</span>
        <span className="font-titulo">{aprovadas} pastas classificadas</span>
      </div>
      {linhaCusto && (
        <p className="text-texto-2">
          Custo real desta sessão: {linhaCusto.valor} ({linhaCusto.tokens} tokens de entrada, {linhaCusto.sufixo})
        </p>
      )}
      <p className="text-texto-2">
        As sugestões aparecem em Revisão na próxima geração de sugestões.
      </p>
      <div className="flex justify-end">
        <Botao variante="solido" onClick={onFechar}>
          Fechar
        </Botao>
      </div>
    </div>
  );
}

// -- Componente principal ----------------------------------------------------

/** Assistente de classificação de pasta por GenAI (GENAI-01): portão de
 *  consentimento, lista de candidatas, custo, chamada em voo, revisão
 *  antes/depois e conclusão — os cinco passos do UI-SPEC. Casca de modal
 *  copiada de `ModalCaminho.tsx`, painel mais largo (multi-linha, não um
 *  campo só). */
export function ClassificacaoPasta({ onFechar }: { onFechar: () => void }) {
  const [passo, setPasso] = useState<Passo | null>(null);
  const [selecionadas, setSelecionadas] = useState<Set<string>>(new Set());
  const [custo, setCusto] = useState<CustoGenaiPasta | null>(null);
  const [rodada, setRodada] = useState<RodadaGenaiPasta | null>(null);
  const [aprovadas, setAprovadas] = useState<Set<string>>(new Set());
  const [expandidoJustificativa, setExpandidoJustificativa] = useState<
    string | null
  >(null);
  const [semRespostaExpandido, setSemRespostaExpandido] = useState(false);
  const [aprovadasCount, setAprovadasCount] = useState(0);
  const [erro, setErro] = useState<string | null>(null);
  const [segundos, setSegundos] = useState(0);
  const queryClient = useQueryClient();

  const { data: config } = useQuery({
    queryKey: ["configGenaiPasta"],
    queryFn: api.configGenaiPasta,
  });

  // Recuperação de sessão paga não aprovada (D-07): uma chamada ao modelo
  // já foi COBRADA se `propostas` existir no servidor — perder essas linhas
  // por causa de um refresh do navegador cobraria duas vezes pelo mesmo
  // resultado. Só roda depois de saber que o gate está aberto; o UI-SPEC não
  // previu este caminho porque a persistência de proposta foi decidida
  // depois (07-01).
  const { data: pendentes, isError: pendentesFalhou } = useQuery({
    queryKey: ["propostasGenaiPasta"],
    queryFn: api.propostasGenaiPasta,
    enabled: !!config?.classificacao_pasta_genai && passo === null,
  });

  // Semeia o passo inicial UMA vez, a partir do gate real do servidor e da
  // recuperação acima — não reage a refetches depois (o dono já está
  // navegando no assistente nesse ponto, e cada mutação move o passo por
  // conta própria). Uma falha na consulta de recuperação (never-crash) não
  // trava o assistente: cai no caminho normal do passo 1.
  useEffect(() => {
    if (!config || passo !== null) return;
    if (!config.classificacao_pasta_genai) {
      setPasso("gate");
      return;
    }
    if (pendentes === undefined && !pendentesFalhou) return; // aguardando
    if (pendentes && pendentes.length > 0) {
      setRodada({ propostas: pendentes, pastas_sem_resposta: [], custo_real: null });
      setPasso("revisao");
    } else {
      setPasso("candidatas");
    }
  }, [config, passo, pendentes, pendentesFalhou]);

  const { data: candidatas } = useQuery({
    queryKey: ["candidatasGenaiPasta"],
    queryFn: api.candidatasGenaiPasta,
    // Não busca mais quando o passo já é revisão/concluído — a sessão
    // recuperada pula direto para lá e não precisa da lista de candidatas.
    enabled:
      passo !== null &&
      passo !== "gate" &&
      passo !== "revisao" &&
      passo !== "concluido",
  });

  // Nasce com TODAS marcadas (D-01: fraseologia é opt-out, "desmarque o que
  // não quer") — semeado só quando a referência da consulta muda, nunca a
  // partir de um toggle local (mesmo padrão de `EscritaExif.tsx`).
  useEffect(() => {
    if (candidatas) {
      setSelecionadas(new Set(candidatas.map((c) => c.pasta)));
    }
  }, [candidatas]);

  // Passo 4 nasce com TODAS as propostas marcadas para aprovação (mesma
  // fraseologia opt-out de D-01) — semeado quando a referência de `rodada`
  // muda, tanto no fim da chamada síncrona quanto na recuperação de sessão.
  useEffect(() => {
    if (rodada) {
      setAprovadas(new Set(rodada.propostas.map((p) => p.pasta)));
    }
  }, [rodada]);

  const habilitarMutation = useMutation({
    mutationFn: (habilitado: boolean) => api.habilitarGenaiPasta(habilitado),
    onSuccess: (novoConfig, habilitado) => {
      setErro(null);
      queryClient.setQueryData(["configGenaiPasta"], novoConfig);
      setPasso(habilitado ? "candidatas" : "gate");
    },
    onError: (e: Error) => setErro(e.message),
  });

  const custoMutation = useMutation({
    mutationFn: (pastas: string[]) => api.estimarCustoGenaiPasta(pastas),
    onSuccess: (c) => {
      setErro(null);
      setCusto(c);
      setPasso("custo");
    },
    onError: (e: Error) => setErro(e.message),
  });

  const rodarMutation = useMutation({
    mutationFn: (pastas: string[]) => api.rodarGenaiPasta(pastas),
    onSuccess: (r) => {
      setErro(null);
      setRodada(r);
      setPasso("revisao");
    },
    onError: (e: Error) => {
      setErro(e.message);
      setPasso("erro");
    },
  });

  const aprovarMutation = useMutation({
    mutationFn: (pastas: string[]) => api.aprovarGenaiPasta(pastas),
    onSuccess: (resultado) => {
      setErro(null);
      setAprovadasCount(resultado.aprovadas);
      setPasso("concluido");
    },
    onError: (e: Error) => setErro(e.message),
  });

  // Contador de segundos do passo 3 — feedback honesto de "não travou",
  // nunca uma barra de progresso falsa que fingiria uma certeza que uma
  // chamada única não tem (UI-SPEC § Step 3).
  useEffect(() => {
    if (passo !== "rodando") return;
    setSegundos(0);
    const id = setInterval(() => setSegundos((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [passo]);

  // Nenhum caminho de fechar fica ativo durante o passo 3 — a chamada já
  // foi enviada e não é cancelável (Entry point, UI-SPEC).
  const podeFechar = passo !== "rodando";

  useEffect(() => {
    function aoTeclar(e: KeyboardEvent) {
      if (e.key === "Escape" && podeFechar) onFechar();
    }
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [podeFechar, onFechar]);

  function alternarSelecao(pasta: string) {
    setSelecionadas((atual) => {
      const novo = new Set(atual);
      if (novo.has(pasta)) novo.delete(pasta);
      else novo.add(pasta);
      return novo;
    });
  }

  function alternarAprovacao(pasta: string) {
    setAprovadas((atual) => {
      const novo = new Set(atual);
      if (novo.has(pasta)) novo.delete(pasta);
      else novo.add(pasta);
      return novo;
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/95"
      onClick={() => podeFechar && onFechar()}
    >
      <div
        className="w-[720px] max-w-[92vw] max-h-[85vh] overflow-y-auto rounded-md border border-borda bg-painel p-4"
        onClick={(e) => e.stopPropagation()}
      >
        {erro && passo !== "erro" && (
          <div className="mb-3 text-erro">{erro}</div>
        )}

        {passo === null && (
          <div className="py-6 text-center text-texto-2">Carregando…</div>
        )}

        {passo === "gate" && config && (
          <PassoGate
            config={config}
            habilitarPendente={habilitarMutation.isPending}
            onHabilitar={() => habilitarMutation.mutate(true)}
            onFechar={onFechar}
          />
        )}

        {passo === "candidatas" && (
          <PassoCandidatas
            candidatas={candidatas ?? []}
            selecionadas={selecionadas}
            onAlternar={alternarSelecao}
            onDesligar={() => habilitarMutation.mutate(false)}
            avancarPendente={custoMutation.isPending}
            onAvancar={() => custoMutation.mutate(Array.from(selecionadas))}
            onFechar={onFechar}
          />
        )}

        {passo === "custo" && custo && (
          <PassoCusto
            custo={custo}
            totalPastas={selecionadas.size}
            onVoltar={() => setPasso("candidatas")}
            confirmarPendente={rodarMutation.isPending}
            onConfirmar={() => {
              setPasso("rodando");
              rodarMutation.mutate(Array.from(selecionadas));
            }}
          />
        )}

        {passo === "rodando" && <PassoRodando segundos={segundos} />}

        {passo === "erro" && (
          <PassoErro
            motivo={erro ?? ""}
            onVoltar={() => setPasso("custo")}
            onFechar={onFechar}
          />
        )}

        {passo === "revisao" && rodada && (
          <PassoRevisao
            rodada={rodada}
            aprovadas={aprovadas}
            onAlternar={alternarAprovacao}
            expandido={expandidoJustificativa}
            onExpandir={(pasta) =>
              setExpandidoJustificativa((atual) =>
                atual === pasta ? null : pasta,
              )
            }
            semRespostaExpandido={semRespostaExpandido}
            onAlternarSemResposta={() => setSemRespostaExpandido((v) => !v)}
            onAprovar={() => aprovarMutation.mutate(Array.from(aprovadas))}
            aprovarPendente={aprovarMutation.isPending}
            onFechar={onFechar}
          />
        )}

        {passo === "concluido" && (
          <PassoConcluido
            aprovadas={aprovadasCount}
            custoReal={rodada?.custo_real ?? null}
            custoEstimado={custo}
            onFechar={onFechar}
          />
        )}
      </div>
    </div>
  );
}
