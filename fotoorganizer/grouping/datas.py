"""Datas escritas no nome da pasta.

"Visconde de Maua - Abril 2015" carrega duas informações num segmento só:
o lugar e o mês. "Pantanal Jul.2023" também. Separar as duas transforma um
nome de pasta em duas evidências independentes — o rótulo do evento, e uma
segunda testemunha para o ano que hoje vem apenas do EXIF.

O que sobra depois de tirar a data é o nome de verdade. Quando não sobra
nada ("2025_05_24"), o segmento era só uma data e não nomeia coisa alguma.

Convenção brasileira em datas numéricas ambíguas: 05-06-2015 é 5 de junho,
não 6 de maio. Onde a ordem não dá para decidir, o dia é descartado e fica
só mês e ano — melhor perder precisão do que afirmar o que não se sabe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Só "março" tem acento entre os nomes de mês, então as duas grafias
# cobrem o caso sem depender de normalização (que muda o comprimento do
# texto e estragaria os índices usados para recortar o resto).
_MESES: dict[str, int] = {
    "janeiro": 1, "jan": 1, "january": 1,
    "fevereiro": 2, "fev": 2, "february": 2, "feb": 2,
    "março": 3, "marco": 3, "mar": 3, "march": 3,
    "abril": 4, "abr": 4, "april": 4, "apr": 4,
    "maio": 5, "mai": 5, "may": 5,
    "junho": 6, "jun": 6, "june": 6,
    "julho": 7, "jul": 7, "july": 7,
    "agosto": 8, "ago": 8, "august": 8, "aug": 8,
    "setembro": 9, "set": 9, "sept": 9, "sep": 9, "september": 9,
    "outubro": 10, "out": 10, "october": 10, "oct": 10,
    "novembro": 11, "nov": 11, "november": 11,
    "dezembro": 12, "dez": 12, "december": 12, "dec": 12,
}
# Mais longos primeiro: senão "jan" casaria antes de "janeiro" e sobraria
# "eiro" no nome.
_MES_ALT = "|".join(sorted(_MESES, key=len, reverse=True))

# Anos plausíveis para fotografia pessoal. Sem esta âncora, "15 Anos"
# viraria data e "Serena 15 Anos" perderia o nome.
_ANO = r"(?:18|19|20)\d{2}"
_SEP = r"[-_./ ]"


@dataclass(frozen=True, slots=True)
class DataDaPasta:
    """Data lida do nome de uma pasta. `texto` é o trecho reconhecido,
    guardado para a justificativa poder citar o que foi lido."""

    ano: int
    mes: int | None = None
    dia: int | None = None
    texto: str = ""

    def rotulo(self) -> str:
        if self.mes is None:
            return f"{self.ano}"
        if self.dia is None:
            return f"{self.ano}-{self.mes:02d}"
        return f"{self.ano}-{self.mes:02d}-{self.dia:02d}"


# Ordem importa: do mais específico para o mais genérico. O primeiro que
# casar e for uma data válida vence.
_PADROES: tuple[re.Pattern[str], ...] = (
    # 2025-05-24, 2025_05_24, 2025.05.24
    re.compile(
        rf"\b(?P<ano>{_ANO}){_SEP}(?P<mes>\d{{1,2}}){_SEP}(?P<dia>\d{{1,2}})\b"
    ),
    # 24-05-2025, 24.05.2025 (dia primeiro, convenção brasileira)
    re.compile(
        rf"\b(?P<dia>\d{{1,2}}){_SEP}(?P<mes>\d{{1,2}}){_SEP}(?P<ano>{_ANO})\b"
    ),
    # Abril 2015, Jul.2023, Julho de 2023, Abril/2015
    re.compile(
        rf"\b(?P<mes_nome>{_MES_ALT})\.?{_SEP}?(?:de{_SEP})?(?P<ano>{_ANO})\b",
        re.IGNORECASE,
    ),
    # 2015-04, 2015_04 (não aceita espaço: "Rio 2016 04" é ano + número)
    re.compile(rf"\b(?P<ano>{_ANO})[-_.](?P<mes>\d{{1,2}})\b"),
    # 2015
    re.compile(rf"\b(?P<ano>{_ANO})\b"),
)

# Sobras de separador nas bordas depois de remover a data.
_BORDAS = " -–—_.,;:/\t"


def _limpar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip(_BORDAS).strip()


def _montar(m: re.Match[str]) -> DataDaPasta | None:
    grupos = m.groupdict()
    ano = int(grupos["ano"])

    mes: int | None = None
    if grupos.get("mes_nome"):
        mes = _MESES[grupos["mes_nome"].lower()]
    elif grupos.get("mes"):
        mes = int(grupos["mes"])
        if not 1 <= mes <= 12:
            return None

    dia: int | None = None
    if grupos.get("dia"):
        dia = int(grupos["dia"])
        if not 1 <= dia <= 31:
            return None

    return DataDaPasta(ano=ano, mes=mes, dia=dia, texto=m.group(0))


def separar_data(segmento: str) -> tuple[str, DataDaPasta | None]:
    """Divide um segmento de pasta em (nome, data).

    "Visconde de Maua - Abril 2015" → ("Visconde de Maua", 2015-04)
    "2025_05_24"                    → ("", 2025-05-24)
    "Serena 15 Anos"                → ("Serena 15 Anos", None)
    """
    for padrao in _PADROES:
        for m in padrao.finditer(segmento):
            data = _montar(m)
            if data is None:
                continue  # 2015-13 não é ano-mês; tenta o próximo padrão
            resto = f"{segmento[:m.start()]} {segmento[m.end():]}"
            return _limpar(resto), data
    return _limpar(segmento), None


def data_no_caminho(caminho: str) -> DataDaPasta | None:
    """Data mais específica escrita no caminho, procurando da folha para a
    raiz. A pasta mais funda é a que fala da foto; as de cima falam do
    arquivamento ("2015" acima de "Abril 2015" é o mesmo ano, mais vago)."""
    melhor: DataDaPasta | None = None
    for segmento in reversed([s for s in caminho.split("/") if s]):
        _nome, data = separar_data(segmento)
        if data is None:
            continue
        if melhor is None:
            melhor = data
        elif data.ano == melhor.ano and _precisao(data) > _precisao(melhor):
            melhor = data
    return melhor


def _precisao(data: DataDaPasta) -> int:
    return (data.mes is not None) + (data.dia is not None)


_ABREV_MES = ("jan", "fev", "mar", "abr", "mai", "jun",
              "jul", "ago", "set", "out", "nov", "dez")


def rotulo_mes(ano: int, mes: int) -> str:
    """"jun.2026" — o formato que o dono já usa no próprio acervo
    ("Pantanal Jul.2023"), em minúsculas para não competir com o nome."""
    return f"{_ABREV_MES[mes - 1]}.{ano}"
