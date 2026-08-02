"""Preferências da UI persistidas em `application_settings`.

Diferente do `config.toml` (editado à mão pelo usuário): esta tabela é
escrita pelo próprio app quando o usuário decide algo pela interface — hoje
só o template de destino, mas a chave é genérica para o que vier depois.
"""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import ApplicationSetting

CHAVE_TEMPLATE_DESTINO = "template_destino"

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
