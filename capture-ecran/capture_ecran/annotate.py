"""Modèle d'annotations et rendu (Pillow uniquement, aucune dépendance d'interface).

Une annotation est un simple dict JSON-compatible, en coordonnées de l'image d'origine :
  arrow/rect/ellipse/highlight/blur : p1, p2 (+ color, width)
  text : pos, text, size, color        step : pos, number, radius, color
  pen  : points, width, color
`render(base, items, scale)` dessine le tout ; scale < 1 sert à l'aperçu à l'écran.
"""
from __future__ import annotations

import math
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

PALETTE = {"Rouge": "#E53935", "Orange": "#FB8C00", "Jaune": "#FDD835", "Vert": "#43A047",
           "Bleu": "#1E88E5", "Noir": "#212121", "Blanc": "#FFFFFF"}
SS = 3  # sur-échantillonnage : bords lisses

_FONTS = ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf"]
_FONTS_BOLD = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf"]


@lru_cache(maxsize=128)
def get_font(size: int, bold: bool = False):
    size = max(6, int(size))
    for name in (_FONTS_BOLD if bold else _FONTS):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _is_light(color: str) -> bool:
    r, g, b = hex_to_rgb(color)
    return (0.299 * r + 0.587 * g + 0.114 * b) > 160


def norm_box(p1, p2) -> tuple[float, float, float, float]:
    return min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])


def _text_size(text: str, size: int, stroke: int = 0) -> tuple[int, int]:
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = d.multiline_textbbox((0, 0), text or " ", font=get_font(size), stroke_width=stroke)
    return int(r + 2), int(b + 2)


def item_bbox(it: dict) -> tuple[float, float, float, float]:
    """Boîte englobante (coordonnées de l'image d'origine), marge de trait incluse."""
    t = it["type"]
    if t in ("arrow", "rect", "ellipse", "highlight", "blur"):
        x0, y0, x1, y1 = norm_box(it["p1"], it["p2"])
        pad = it.get("width", 4) / 2 + 2
        if t == "arrow":
            pad += max(18, it.get("width", 4) * 4)
        return x0 - pad, y0 - pad, x1 + pad, y1 + pad
    if t == "text":
        x, y = it["pos"]
        w, h = _text_size(it["text"], it.get("size", 32), max(1, it.get("size", 32) // 12))
        return x - 4, y - 4, x + w + 4, y + h + 4
    if t == "step":
        x, y = it["pos"]
        r = it.get("radius", 20) + 4
        return x - r, y - r, x + r, y + r
    if t == "pen":
        xs = [p[0] for p in it["points"]]
        ys = [p[1] for p in it["points"]]
        pad = it.get("width", 4) / 2 + 2
        return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    raise ValueError(f"type d'annotation inconnu : {t}")


def _seg_dist(p, a, b) -> float:
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - (ax + u * dx), p[1] - (ay + u * dy))


def hit_test(it: dict, pt, tol: float = 8) -> bool:
    t = it["type"]
    if t == "arrow":
        return _seg_dist(pt, it["p1"], it["p2"]) <= tol + it.get("width", 4)
    if t == "pen":
        pts = it["points"]
        return any(_seg_dist(pt, pts[i], pts[i + 1]) <= tol + it.get("width", 4) for i in range(len(pts) - 1)) \
            or (len(pts) == 1 and math.hypot(pt[0] - pts[0][0], pt[1] - pts[0][1]) <= tol)
    x0, y0, x1, y1 = item_bbox(it)
    return x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1


def translate(it: dict, dx: float, dy: float) -> dict:
    new = dict(it)
    for k in ("p1", "p2", "pos"):
        if k in it:
            new[k] = (it[k][0] + dx, it[k][1] + dy)
    if "points" in it:
        new["points"] = [(x + dx, y + dy) for x, y in it["points"]]
    return new


def _pixelate(img: Image.Image, it: dict, scale: float) -> None:
    x0, y0, x1, y1 = (v * scale for v in norm_box(it["p1"], it["p2"]))
    box = (max(0, int(x0)), max(0, int(y0)), min(img.width, int(math.ceil(x1))), min(img.height, int(math.ceil(y1))))
    w, h = box[2] - box[0], box[3] - box[1]
    if w < 2 or h < 2:
        return
    block = max(6, int(14 * scale))
    region = img.crop(box)
    small = region.resize((max(1, w // block), max(1, h // block)), Image.BILINEAR)
    img.paste(small.resize((w, h), Image.NEAREST), box)


def _draw_arrow(d, tr, it, scale):
    a, b = tr(it["p1"]), tr(it["p2"])
    wpx = max(1, it.get("width", 6) * scale * SS)
    color = it.get("color", PALETTE["Rouge"])
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    head = min(max(18, it.get("width", 6) * 4) * scale * SS, max(length * 0.6, 4))
    base = (b[0] - head * 0.8 * math.cos(ang), b[1] - head * 0.8 * math.sin(ang))
    d.line([a, base], fill=color, width=int(wpx))
    spread = math.radians(26)
    left = (b[0] - head * math.cos(ang - spread), b[1] - head * math.sin(ang - spread))
    right = (b[0] - head * math.cos(ang + spread), b[1] - head * math.sin(ang + spread))
    d.polygon([b, left, right], fill=color)


def _apply(img: Image.Image, it: dict, scale: float) -> None:
    t = it["type"]
    if t == "blur":
        _pixelate(img, it, scale)
        return
    x0, y0, x1, y1 = (v * scale for v in item_bbox(it))
    ox, oy = max(0, int(math.floor(x0)) - 2), max(0, int(math.floor(y0)) - 2)
    ex, ey = min(img.width, int(math.ceil(x1)) + 2), min(img.height, int(math.ceil(y1)) + 2)
    if ex <= ox or ey <= oy:
        return
    w, h = ex - ox, ey - oy
    layer = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    def tr(p):
        return (p[0] * scale - ox) * SS, (p[1] * scale - oy) * SS

    color = it.get("color", PALETTE["Rouge"])
    wpx = max(1, int(it.get("width", 6) * scale * SS))
    if t == "arrow":
        _draw_arrow(d, tr, it, scale)
    elif t in ("rect", "highlight"):
        a, b = tr(it["p1"]), tr(it["p2"])
        box = [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
        if t == "highlight":
            d.rectangle(box, fill=hex_to_rgb(color) + (110,))
        else:
            d.rounded_rectangle(box, radius=4 * SS, outline=color, width=wpx)
    elif t == "ellipse":
        a, b = tr(it["p1"]), tr(it["p2"])
        d.ellipse([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], outline=color, width=wpx)
    elif t == "pen":
        pts = [tr(p) for p in it["points"]]
        if len(pts) == 1:
            pts = pts * 2
        d.line(pts, fill=color, width=wpx, joint="curve")
        r = wpx / 2
        for p in (pts[0], pts[-1]):
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)
    elif t == "text":
        size = it.get("size", 32) * scale * SS
        stroke = max(1, int(size / 12))
        outline = "#000000" if _is_light(color) else "#FFFFFF"
        d.multiline_text(tr(it["pos"]), it["text"], font=get_font(size), fill=color,
                         stroke_width=stroke, stroke_fill=outline)
    elif t == "step":
        cx, cy = tr(it["pos"])
        r = it.get("radius", 20) * scale * SS
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color, outline="#FFFFFF", width=max(1, int(r / 7)))
        txtcol = "#000000" if _is_light(color) else "#FFFFFF"
        d.text((cx, cy), str(it.get("number", 1)), font=get_font(r * 1.25, bold=True), fill=txtcol, anchor="mm")
    layer = layer.resize((w, h), Image.LANCZOS)
    img.paste(layer, (ox, oy), layer)


def render_over(img: Image.Image, items: list[dict], scale: float = 1.0) -> Image.Image:
    """Dessine les annotations SUR img (modifiée sur place) et la renvoie."""
    for it in items:
        _apply(img, it, scale)
    return img


def render(base: Image.Image, items: list[dict], scale: float = 1.0) -> Image.Image:
    """Copie de base (déjà à l'échelle `scale`) avec les annotations dessinées dessus."""
    return render_over(base.convert("RGB").copy(), items, scale)
