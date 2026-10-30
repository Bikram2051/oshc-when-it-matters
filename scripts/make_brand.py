"""Build the OSHC When It Matters logo files from the bundled Atkinson font.

    python scripts/make_brand.py

Writes two SVGs to app/static/brand/:
  logo.svg  the full lockup: a red OSHC badge with "When It / Matters" beside it
  mark.svg  the badge alone, shown when the sidebar is closed

Letters are drawn as outlines, so the logo looks the same on any computer without
the font installed. Needs fonttools and brotli (pip install fonttools brotli).
Colours match .streamlit/config.toml.
"""
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "app/static/fonts/atkinson-hyperlegible-next-latin-700-normal.woff2"
OUT = ROOT / "app/static/brand"

RED = "#D50032"    # Swinburne-inspired red, 5.4:1 against white
INK = "#111111"
WHITE = "#FFFFFF"

BADGE_H = 1000      # every size below is relative to the badge height
RADIUS = 70
BADGE_SIZE = 470    # font size of OSHC inside the badge
BADGE_PAD_X = 150
GAP = 130           # between the badge and the words
WORD_SIZE = 405     # font size of "When It" / "Matters"


class Font:
    def __init__(self, path: Path):
        self.font = TTFont(path)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm
        self.cap = self.font["OS/2"].sCapHeight

    def width(self, text: str, size: float) -> float:
        return sum(self.glyphs[self.cmap[ord(c)]].width for c in text) * size / self.upm

    def path(self, text: str, size: float, x: float, baseline: float) -> str:
        """SVG path data for text at (x, baseline), y pointing down."""
        scale = size / self.upm
        pen = SVGPathPen(self.glyphs)
        for char in text:
            name = self.cmap[ord(char)]
            self.glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, baseline)))
            x += self.glyphs[name].width * scale
        return pen.getCommands()

    def cap_height(self, size: float) -> float:
        return self.cap * size / self.upm

    def extent(self, text: str, size: float) -> tuple[float, float]:
        """Highest point above and lowest point below the baseline, at this size."""
        top, bottom = 0.0, 0.0
        for char in text:
            pen = BoundsPen(self.glyphs)
            self.glyphs[self.cmap[ord(char)]].draw(pen)
            if pen.bounds:
                bottom, top = min(bottom, pen.bounds[1]), max(top, pen.bounds[3])
        return top * size / self.upm, -bottom * size / self.upm


def _badge(font: Font) -> tuple[float, str]:
    width = font.width("OSHC", BADGE_SIZE) + 2 * BADGE_PAD_X
    baseline = (BADGE_H + font.cap_height(BADGE_SIZE)) / 2
    shapes = (f'<rect width="{width:.0f}" height="{BADGE_H}" rx="{RADIUS}" fill="{RED}"/>'
              f'<path fill="{WHITE}" d="{font.path("OSHC", BADGE_SIZE, BADGE_PAD_X, baseline)}"/>')
    return width, shapes


def _svg(width: float, label: str, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {BADGE_H}" '
            f'role="img" aria-label="{label}"><title>{label}</title>{body}</svg>\n')


def main() -> None:
    font = Font(FONT)
    badge_w, badge = _badge(font)

    # Two lines that fill the badge height exactly: tallest letter of the first line
    # touches the top edge, the lowest point of the second touches the bottom edge.
    first = font.extent("When It", WORD_SIZE)[0]
    second = BADGE_H - font.extent("Matters", WORD_SIZE)[1]
    x = badge_w + GAP
    words = (f'<path fill="{INK}" d="{font.path("When It", WORD_SIZE, x, first)}"/>'
             f'<path fill="{INK}" d="{font.path("Matters", WORD_SIZE, x, second)}"/>')
    total = x + max(font.width("When It", WORD_SIZE), font.width("Matters", WORD_SIZE)) + 20

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "logo.svg").write_text(_svg(total, "OSHC When It Matters", badge + words), encoding="utf-8")
    (OUT / "mark.svg").write_text(_svg(badge_w, "OSHC When It Matters", badge), encoding="utf-8")
    print(f"logo.svg {total:.0f}x{BADGE_H}, mark.svg {badge_w:.0f}x{BADGE_H}")


if __name__ == "__main__":
    main()
