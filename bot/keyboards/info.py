"""Служебные клавиатуры `aida_max` на базе `maxo`."""

from maxo.utils.builders import KeyboardBuilder


def new_account(_) -> list[list[object]]:
    """Возвращает клавиатуру со ссылками для авторизации и онбординга."""
    return (
        KeyboardBuilder()
        .add_link(
            text=_("▶️ Authorization"),
            url="https://marketplace.dodois.io/11ecf3aaf97d059cb9706f21406ebd11",
        )
        .add_link(
            text=_("🗄 Knowledge base"),
            url="https://aida.kaiten.site",
        )
        .add_link(
            text=_("🤝 Aida Community"),
            url="https://t.me/aidacommunity",
        )
        .adjust(1, repeat=True)
        .build()
    )
