"""Prise de la capture : écran(s) entier(s), fenêtre active, avec pointeur dessiné."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageGrab

from . import winapi

# Flèche de souris standard, pointe en (0, 0), pour un pointeur de ~20 px.
_ARROW = [(0, 0), (0, 17), (4, 13), (7, 20), (10, 19), (7, 12), (12, 12)]


def draw_pointer(img: Image.Image, x: int, y: int, halo: bool = True) -> Image.Image:
    """Dessine un pointeur (et un halo jaune facultatif) à la position (x, y) de l'image."""
    img = img.convert("RGBA")
    k = max(1.0, img.height / 1080) * 1.5
    if halo:
        r = 24 * k
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse([x - r, y - r, x + r, y + r], fill=(255, 214, 0, 95),
                                      outline=(255, 160, 0, 200), width=max(2, int(2 * k)))
        img = Image.alpha_composite(img, layer)
    ss = 4  # sur-échantillonnage pour des bords lisses
    size = int(26 * k)
    cur = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    pts = [(px * k * ss, py * k * ss) for px, py in _ARROW]
    d = ImageDraw.Draw(cur)
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=int(1.6 * ss))
    cur = cur.resize((size, size), Image.LANCZOS)
    img.alpha_composite(cur, (max(0, int(x)), max(0, int(y))) if x >= 0 and y >= 0 else (0, 0))
    return img.convert("RGB")


def grab_screen(draw_cursor: bool = True, halo: bool = True) -> tuple[Image.Image, tuple[int, int]]:
    """Capture tous les écrans. Retourne (image, origine) ; origine = coin haut-gauche
    de l'écran virtuel (peut être négatif avec plusieurs écrans)."""
    img = ImageGrab.grab(all_screens=True).convert("RGB")
    vs = winapi.virtual_screen()
    origin = (vs[0], vs[1]) if vs else (0, 0)
    if draw_cursor:
        pos = winapi.cursor_pos()
        if pos:
            cx, cy = pos[0] - origin[0], pos[1] - origin[1]
            if 0 <= cx < img.width and 0 <= cy < img.height:
                img = draw_pointer(img, cx, cy, halo)
    return img, origin


def crop_active_window(img: Image.Image, origin: tuple[int, int]) -> Image.Image:
    """Recadre sur la fenêtre active ; renvoie l'image entière si elle est introuvable."""
    rect = winapi.foreground_window_rect()
    if not rect:
        return img
    x0, y0, x1, y1 = rect[0] - origin[0], rect[1] - origin[1], rect[2] - origin[0], rect[3] - origin[1]
    box = (max(0, x0), max(0, y0), min(img.width, x1), min(img.height, y1))
    if box[2] - box[0] < 20 or box[3] - box[1] < 20:
        return img
    return img.crop(box)
