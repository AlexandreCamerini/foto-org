"""Preferências da UI persistidas em `application_settings`.

Diferente do `config.toml` (editado à mão pelo usuário): esta tabela é
escrita pelo próprio app quando o usuário decide algo pela interface — o
template de destino e o opt-in de classificação de pasta por GenAI (D-080:
`servicos_externos`, a chave MESTRA, continua só no TOML, fora do alcance
da UI; este opt-in é o do RECURSO, gravável pela interface).
"""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import ApplicationSetting

CHAVE_TEMPLATE_DESTINO = "template_destino"
CHAVE_GENAI_PASTA = "classificacao_pasta_genai"

# Tipo dos valores aceitos pela coluna JSON de ApplicationSetting.valor.
SettingValue = str | int | float | bool | dict | list | None


class SettingsRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def obter(self, chave: str) -> SettingValue:
        """Valor bruto salvo para `chave`, ou `None` se nunca foi definido —
        ausência de preferência não é erro, é o estado inicial de qualquer
        catálogo novo."""
        with self._factory() as session:
            registro = session.get(ApplicationSetting, chave)
            return registro.valor if registro is not None else None

    def definir(self, chave: str, valor: SettingValue) -> None:
        with self._factory() as session:
            registro = session.get(ApplicationSetting, chave)
            if registro is None:
                session.add(ApplicationSetting(chave=chave, valor=valor))
            else:
                registro.valor = valor
            session.commit()

    # -- conveniência: template de destino ---------------------------------
    def obter_template(self, default: str) -> str:
        """`default` é sempre `TEMPLATE_PADRAO` na prática, mas fica a
        cargo de quem chama para não acoplar este repositório ao módulo de
        classificação."""
        valor = self.obter(CHAVE_TEMPLATE_DESTINO)
        return valor if isinstance(valor, str) and valor else default

    def salvar_template(self, template: str) -> None:
        self.definir(CHAVE_TEMPLATE_DESTINO, template)

    # -- conveniência: opt-in de classificação de pasta por GenAI (D-080) --
    def genai_pasta_habilitado(self) -> bool:
        """`False` quando a chave nunca foi definida — ausência de
        preferência é o estado inicial, não erro, e o padrão do recurso é
        desligado (GENAI-01)."""
        valor = self.obter(CHAVE_GENAI_PASTA)
        return bool(valor) if isinstance(valor, bool) else False

    def definir_genai_pasta(self, habilitado: bool) -> None:
        self.definir(CHAVE_GENAI_PASTA, habilitado)
