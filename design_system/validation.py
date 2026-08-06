import re
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = PACKAGE_ROOT / "static" / "sedl"
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
Z_INDEX = re.compile(r"z-index\s*:\s*(-?\d+)")
INLINE_STYLE = re.compile(r"\sstyle\s*=", re.IGNORECASE)
SPACING_VALUE = re.compile(r"(?:margin|padding|gap)\s*:\s*([^;}]+)")


def validate_static_contract():
    """Return violations confined to the new SEDL package."""
    violations = []
    for path in STATIC_ROOT.rglob("*.css"):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(STATIC_ROOT).as_posix()
        if relative != "tokens/colors.css" and HEX.search(text):
            violations.append(f"{relative}: color hexadecimal fuera de tokens")
        if relative != "tokens/zindex.css" and Z_INDEX.search(text):
            violations.append(f"{relative}: z-index arbitrario")
        if not relative.startswith("tokens/"):
            for value in SPACING_VALUE.findall(text):
                normalized = value.replace("!important", "").strip()
                if normalized != "0" and not normalized.startswith("var("):
                    violations.append(f"{relative}: espaciado fuera de tokens")
                    break
    for path in (PACKAGE_ROOT / "templates").rglob("*.html"):
        if INLINE_STYLE.search(path.read_text(encoding="utf-8")):
            violations.append(f"{path.name}: CSS inline")
    return violations
