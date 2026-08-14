// Mesma string de fotoorganizer/classification/templates.py
// (DESTINO_NAO_CLASSIFICADO) — é a raiz do único destino que o motor produz
// sem nenhuma evidência de categoria/viagem/evento (engine.py,
// `_destino_nao_classificado`). O nível de confiança desses grupos reflete
// só a confiança da DATA (score 0.95 do EXIF) — mostrar "Alta" ali mentiria
// sobre existir uma classificação, que não existe (D-071).
export const DESTINO_NAO_CLASSIFICADO = "Não classificadas";

export function naoClassificado(destino: string): boolean {
  return (
    destino === DESTINO_NAO_CLASSIFICADO ||
    destino.startsWith(`${DESTINO_NAO_CLASSIFICADO}/`)
  );
}
