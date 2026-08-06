from dataclasses import dataclass


@dataclass(frozen=True)
class Icon:
    name: str
    path: str
    label: str


ICONS = {
    item.name: item
    for item in (
        Icon("check", "M5 12l4 4L19 6", "Confirmación"),
        Icon("close", "M6 6l12 12M18 6L6 18", "Cerrar"),
        Icon("search", "M21 21l-4.35-4.35M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z", "Buscar"),
        Icon("menu", "M4 6h16M4 12h16M4 18h16", "Menú"),
        Icon("warning", "M12 3 2 21h20L12 3Zm0 6v5m0 3h.01", "Advertencia"),
        Icon("info", "M12 8h.01M11 12h1v4h1M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z", "Información"),
    )
}


def icon(name):
    """Return a canonical icon or the information fallback."""
    return ICONS.get(name, ICONS["info"])
