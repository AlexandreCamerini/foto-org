import type { ButtonHTMLAttributes, ReactNode } from "react";

/** O botão da interface.
 *
 * Existe porque o app tinha 59 `<button>` crus repetindo a mesma classe com
 * pequenas divergências: `rounded-md border border-borda bg-cartao px-3 py-1
 * hover:border-acento disabled:opacity-50` aparecia seis vezes, ora com
 * `px-2`, ora com `px-2.5`, ora com `w-full`. Nenhuma dessas diferenças era
 * uma decisão — eram cópias que envelheceram separadas.
 *
 * O modelo de variação vem da referência (`design-system-origem.md` §8.2):
 * eixos ORTOGONAIS, resolvidos por uma tabela só, em vez de uma classe por
 * combinação. A diferença aqui é a paleta: a direção de arte deste app não
 * tem acento cromático (D-017), então `tom` só entra onde a cor significa
 * ESTADO — nunca para decorar um botão.
 */

type Variante = "solido" | "contorno" | "fantasma";
type Tom = "erro" | "ok" | "atencao";
type Tamanho = "sm" | "md" | "lg";

// A fórmula, escrita uma vez. Cada variante é fundo + texto + borda + hover;
// trocar o vocabulário visual do app é editar estas três linhas.
const VARIANTES: Record<Variante, string> = {
  solido:
    "bg-acento text-texto-invertido hover:opacity-90",
  contorno:
    "border border-borda bg-cartao text-texto hover:border-acento",
  fantasma: "text-texto-2 hover:bg-cartao hover:text-texto",
};

// Estado tem cor própria e a mesma fórmula em todas as variantes: fundo a
// 10%, texto e borda na cor cheia. É o que faz um erro parecer erro sem
// virar caixa vermelha.
const TONS: Record<Tom, string> = {
  erro: "border-erro/40 bg-erro/10 text-erro hover:bg-erro/20",
  ok: "border-ok/40 bg-ok/10 text-ok hover:bg-ok/20",
  atencao: "border-atencao/40 bg-atencao/10 text-atencao hover:bg-atencao/20",
};

const TAMANHOS: Record<Tamanho, string> = {
  sm: "px-2 py-0.5",
  md: "px-3 py-1",
  lg: "px-3 py-2",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: Variante;
  /** Só quando a cor significa estado. Vence a variante. */
  tom?: Tom;
  tamanho?: Tamanho;
  /** Largura total do contêiner. */
  cheio?: boolean;
  children?: ReactNode;
};

export default function Botao({
  variante = "contorno",
  tom,
  tamanho = "md",
  cheio = false,
  className = "",
  disabled = false,
  type = "button",
  children,
  ...resto
}: Props) {
  const classes = [
    // `rounded-controle` e `duration-[var(--dur-micro)]` são os tokens do
    // bloco 1 ganhando o primeiro consumidor.
    "shrink-0 rounded-controle transition-colors duration-[var(--dur-micro)]",
    tom ? `border ${TONS[tom]}` : VARIANTES[variante],
    TAMANHOS[tamanho],
    cheio ? "w-full" : "",
    // O app tinha `disabled:opacity-50` em 13 lugares e `cursor-not-allowed`
    // em nenhum, `aria-disabled` em nenhum. Botão apagado que não avisa ao
    // leitor de tela nem muda o cursor está desabilitado só para quem enxerga.
    disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled}
      aria-disabled={disabled || undefined}
      {...resto}
    >
      {children}
    </button>
  );
}
