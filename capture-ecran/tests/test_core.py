import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from capture_ecran import annotate, exporter, grabber
from capture_ecran.hotkeys import parse_hotkey, pretty
from capture_ecran.session import Session


def test_parse_hotkey():
    assert parse_hotkey("ctrl+shift+f9") == (0x2 | 0x4, 0x78)
    assert parse_hotkey("Ctrl+Maj+S") == (0x6, ord("S"))
    assert pretty("ctrl+shift+f9") == "Ctrl+Maj+F9"


@pytest.mark.parametrize("bad", ["f9", "ctrl+alt+1", "ctrl+shift+", "foo+f9", "ctrl+shift+blabla"])
def test_parse_hotkey_invalid(bad):
    with pytest.raises(ValueError):
        parse_hotkey(bad)


ITEMS = [
    {"type": "arrow", "p1": (10, 10), "p2": (200, 120), "color": "#E53935", "width": 6},
    {"type": "rect", "p1": (220, 20), "p2": (380, 100), "color": "#1E88E5", "width": 4},
    {"type": "ellipse", "p1": (20, 150), "p2": (120, 220), "color": "#43A047", "width": 4},
    {"type": "highlight", "p1": (140, 150), "p2": (300, 200), "color": "#FDD835"},
    {"type": "text", "pos": (20, 240), "text": "Bonjour\nà tous", "size": 28, "color": "#212121"},
    {"type": "step", "pos": (350, 250), "number": 2, "radius": 20, "color": "#E53935"},
    {"type": "pen", "points": [(300, 150), (320, 170), (340, 140)], "width": 4, "color": "#FB8C00"},
]


def test_render_changes_pixels_and_keeps_size():
    base = Image.new("RGB", (400, 300), "white")
    for it in ITEMS:
        out = annotate.render(base, [it])
        assert out.size == base.size
        assert out.tobytes() != base.tobytes(), it["type"]
    assert base.getpixel((10, 10)) == (255, 255, 255)  # l'original n'est pas modifié


def test_blur_pixelates_only_region():
    base = Image.effect_noise((200, 200), 80).convert("RGB")
    out = annotate.render(base, [{"type": "blur", "p1": (50, 50), "p2": (150, 150)}])
    assert out.getpixel((10, 10)) == base.getpixel((10, 10))
    assert out.crop((50, 50, 150, 150)).tobytes() != base.crop((50, 50, 150, 150)).tobytes()


def test_render_partially_offscreen_and_scaled():
    base = Image.new("RGB", (100, 100), "white")
    annotate.render(base, [{"type": "arrow", "p1": (-50, -50), "p2": (150, 150), "width": 6}])
    small = base.resize((50, 50))
    out = annotate.render(small, ITEMS[:2], scale=0.5)
    assert out.size == (50, 50)


def test_hit_translate_bbox():
    arrow = ITEMS[0]
    assert annotate.hit_test(arrow, (105, 65))
    assert not annotate.hit_test(arrow, (300, 10))
    moved = annotate.translate(arrow, 5, 7)
    assert moved["p1"] == (15, 17) and arrow["p1"] == (10, 10)
    for it in ITEMS:
        x0, y0, x1, y1 = annotate.item_bbox(it)
        assert x1 > x0 and y1 > y0


def test_session_roundtrip(tmp_path):
    s = Session.new(tmp_path, "Créer un compte ENT")
    c1 = s.add(Image.new("RGB", (50, 40), "red"))
    c2 = s.add(Image.new("RGB", (50, 40), "blue"))
    s.update(c1, s.load_original(c1), s.load_final(c1), [dict(ITEMS[0])], " Étape un ")
    s.move(c2, -1)
    s2 = Session.open(s.folder)
    assert [c.id for c in s2.captures] == [2, 1]
    assert s2.captures[1].caption == "Étape un"
    assert s2.captures[1].items[0]["p1"] == (10, 10)
    s2.remove(s2.captures[0])
    assert not (s.folder / "capture_002.png").exists()
    assert s2.add(Image.new("RGB", (5, 5))).id == 3  # pas de réutilisation d'identifiant


def test_srt_and_durations():
    assert exporter.srt_time(3723.5) == "01:02:03,500"
    assert exporter.estimate_duration("") == 3.0
    assert exporter.estimate_duration("x" * 1000) == 15.0
    srt = exporter.build_srt(["Un", "", "Trois"], [3, 3, 4])
    assert srt.startswith("1\n00:00:00,000 --> 00:00:02,950\nUn")
    assert "2\n00:00:06,000 --> 00:00:09,950\nTrois" in srt  # l'écran sans légende décale mais n'a pas d'entrée


def test_compose_frame_and_pack(tmp_path):
    img = Image.new("RGB", (1600, 900), "white")
    f = exporter.compose_frame(img, "Un sous-titre assez long " * 6)
    assert f.size == (1920, 1080)
    assert f.getpixel((960, 1040)) != (24, 24, 24)  # bande de sous-titre présente
    s = Session.new(tmp_path / "s", "Test")
    for t in ("Étape 1 : ouvrir le menu", "Étape 2 : cliquer sur Enregistrer"):
        c = s.add(img)
        s.update(c, img, img, [], t)
    res = exporter.export_video_pack(s, tmp_path / "out", fixed_seconds=1, make_mp4=exporter.find_ffmpeg() is not None)
    assert len(res.frames) == 2 and res.srt.exists()
    if exporter.find_ffmpeg():
        assert res.mp4 and res.mp4.stat().st_size > 1000, res.message
    html_path = exporter.export_html_guide(s, tmp_path / "f.html")
    text = html_path.read_text("utf-8")
    assert "Étape 2" in text and "data:image/png;base64" in text


def test_pack_requires_captures(tmp_path):
    with pytest.raises(ValueError):
        exporter.export_video_pack(Session.new(tmp_path, "vide"), tmp_path / "o")


def test_draw_pointer_edges():
    img = Image.new("RGB", (300, 200), "white")
    for x, y in [(0, 0), (299, 199), (150, 100)]:
        assert grabber.draw_pointer(img, x, y).size == img.size
    assert grabber.draw_pointer(img, 150, 100, halo=True).getpixel((150, 100)) != (255, 255, 255)
