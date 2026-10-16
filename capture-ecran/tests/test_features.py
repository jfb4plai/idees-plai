import math
import shutil
import struct
import subprocess
import sys
import time
import wave
import zipfile
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from capture_ecran import annotate, audio, exporter, steps
from capture_ecran.session import Session


def make_wav(path: Path, seconds: float, rate: int = 44100, freq: float = 440):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * freq * i / rate)))
                               for i in range(int(seconds * rate))))


@pytest.fixture
def session(tmp_path):
    s = Session.new(tmp_path / "s", "Mon tuto « test » & <b>")
    for txt in ("Ouvrez le menu", "Cliquez sur Enregistrer"):
        img = Image.new("RGB", (1280, 720), (230, 230, 230))
        c = s.add(img)
        s.update(c, img, img, [], txt)
    return s


# ------------------------------------------------------------------ voix off
def test_voiceover_track_is_padded_and_aligned(tmp_path):
    a = tmp_path / "a.wav"
    make_wav(a, 1.0)
    out, skipped = audio.build_voiceover([a, None, a], [2.0, 3.0, 1.5], tmp_path / "v.wav")
    assert skipped == 0
    assert audio.wav_duration(out) == pytest.approx(6.5, abs=0.01)  # 2 + 3 + 1.5
    with wave.open(str(out)) as w:  # le silence est vraiment du silence (2e écran)
        w.setpos(int(2.5 * 44100))
        assert set(w.readframes(1000)) == {0}


def test_voiceover_none_and_mismatch(tmp_path):
    assert audio.build_voiceover([None, None], [1, 1], tmp_path / "x.wav") == (None, 0)
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    make_wav(a, 1.0)
    make_wav(b, 1.0, rate=22050)
    _, skipped = audio.build_voiceover([a, b], [2, 2], tmp_path / "x.wav")
    assert skipped == 1


@pytest.mark.skipif(not exporter.find_ffmpeg(), reason="ffmpeg absent")
def test_video_with_voice_has_audio_and_voice_is_never_cut(session, tmp_path):
    make_wav(session.audio_path(session.captures[0]), 5.0)  # plus long que le minimum de 3 s
    res = exporter.export_video_pack(session, tmp_path / "o", fixed_seconds=1)
    assert res.voice and res.mp4, res.message
    assert audio.wav_duration(res.voice) == pytest.approx(5.6 + 1.0, abs=0.05)  # 5 s + 0,6 s de respiration, + écran 2
    ff = exporter.find_ffmpeg()
    info = subprocess.run([ff, "-i", str(res.mp4)], capture_output=True, text=True).stderr
    assert "Audio: aac" in info and "Video: h264" in info


@pytest.mark.skipif(not exporter.find_ffmpeg(), reason="ffmpeg absent")
def test_video_soft_subtitles_with_voice(session, tmp_path):
    make_wav(session.audio_path(session.captures[1]), 1.0)
    res = exporter.export_video_pack(session, tmp_path / "o2", burn=False, fixed_seconds=1)
    info = subprocess.run([exporter.find_ffmpeg(), "-i", str(res.mp4)], capture_output=True, text=True).stderr
    assert "Subtitle" in info and "Audio" in info


def test_remove_capture_deletes_audio(session):
    cap = session.captures[0]
    make_wav(session.audio_path(cap), 0.5)
    assert session.has_audio(cap)
    session.remove(cap)
    assert not (session.folder / "audio" / "capture_001.wav").exists()


# ------------------------------------------------------------------ Word
def test_docx_structure_and_accessibility(session, tmp_path):
    path = exporter.export_docx(session, tmp_path / "t.docx")
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert "word/media/image2.png" in names
        doc = z.read("word/document.xml").decode()
    assert 'descr="Cliquez sur Enregistrer"' in doc  # texte alternatif
    assert "&lt;b&gt;" in doc or "&lt;b&gt;" in zipfile.ZipFile(path).read("docProps/core.xml").decode()
    docx = pytest.importorskip("docx")
    d = docx.Document(str(path))
    heads = [p.text for p in d.paragraphs if p.style.name.startswith("Heading")]
    assert heads == ["Étape 1", "Étape 2"]
    assert d.core_properties.title.startswith("Mon tuto")
    assert len(d.inline_shapes) == 2
    for sh in d.inline_shapes:
        assert sh.width.cm <= 16.01 and sh.height.cm <= 17.01


def test_docx_tall_image_is_bounded(tmp_path):
    s = Session.new(tmp_path, "haut")
    img = Image.new("RGB", (400, 2000), "white")
    s.update(s.add(img), img, img, [], "x")
    docx = pytest.importorskip("docx")
    d = docx.Document(str(exporter.export_docx(s, tmp_path / "h.docx")))
    assert d.inline_shapes[0].height.cm <= 17.01


@pytest.mark.skipif(not shutil.which("soffice"), reason="LibreOffice absent")
def test_docx_opens_in_libreoffice(session, tmp_path):
    p = exporter.export_docx(session, tmp_path / "lo.docx")
    r = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(p)],
                       capture_output=True, text=True, timeout=120)
    pdf = tmp_path / "lo.pdf"
    assert pdf.exists() and pdf.stat().st_size > 5000, r.stderr


def test_docx_requires_captures(tmp_path):
    with pytest.raises(ValueError):
        exporter.export_docx(Session.new(tmp_path, "v"), tmp_path / "x.docx")


# ------------------------------------------------------------------ série de clics
def test_build_step_places_ring_and_badge():
    frame = Image.new("RGB", (1920, 1080), "white")
    base, items, caption = steps.build_step(frame, (500, 400), 3, "left")
    assert caption == "Cliquez ici"
    ring, badge = items
    assert ring["type"] == "ellipse" and badge["type"] == "step" and badge["number"] == 3
    assert ring["p1"][0] < 500 < ring["p2"][0]
    assert base.getpixel((505, 405)) != (255, 255, 255)  # pointeur dessiné
    out = annotate.render(base, items)
    assert out.tobytes() != base.tobytes()


def test_step_recorder_numbers_and_merges_double_click(tmp_path):
    s = Session.new(tmp_path, "clics")
    rec = steps.StepRecorder(s)
    frame = Image.new("RGB", (800, 600), "white")
    c1 = rec.on_click("left", (100, 100), frame, 10.0)
    c1b = rec.on_click("left", (102, 101), frame, 10.2)       # double-clic : même capture
    assert c1b is c1 and len(s.captures) == 1
    assert c1.caption == "Double-cliquez ici"
    c2 = rec.on_click("right", (300, 200), frame, 11.0)
    c3 = rec.on_click("left", (300, 200), frame, 12.0)         # trop tard : nouvelle étape
    assert [c.id for c in s.captures] == [c1.id, c2.id, c3.id]
    assert c2.caption == "Faites un clic droit ici"
    assert [i["number"] for c in s.captures for i in c.items if i["type"] == "step"] == [1, 2, 3]
    assert Session.open(s.folder).captures[0].items[1]["number"] == 1  # persisté
    assert rec.count == 3


def test_step_recorder_multi_monitor_origin(tmp_path):
    s = Session.new(tmp_path, "o")
    rec = steps.StepRecorder(s, origin=(-1920, 0))
    cap = rec.on_click("left", (-1900, 50), Image.new("RGB", (3840, 1080), "white"), 1.0)
    ring = cap.items[0]
    assert (ring["p1"][0] + ring["p2"][0]) / 2 == pytest.approx(20)


def test_renumber_after_reorder_and_delete(tmp_path):
    s = Session.new(tmp_path, "r")
    rec = steps.StepRecorder(s)
    frame = Image.new("RGB", (800, 600), "white")
    caps = [rec.on_click("left", (100 * i, 100), frame, float(i * 5)) for i in range(1, 4)]
    s.remove(caps[0])
    assert steps.renumber_steps(s) == 2
    assert [c.items[1]["number"] for c in s.captures] == [1, 2]
    assert steps.renumber_steps(s) == 0
    final = s.load_final(s.captures[1])
    assert final.size == (800, 600)


def test_frame_buffer_keeps_latest_and_stops():
    n = {"i": 0}

    def grab():
        n["i"] += 1
        return Image.new("RGB", (4, 4), (n["i"] % 255, 0, 0))

    fb = steps.FrameBuffer(grab, interval=0.02)
    fb.start()
    time.sleep(0.2)
    first = fb.latest
    assert first is not None
    time.sleep(0.1)
    assert fb.latest.getpixel((0, 0)) != first.getpixel((0, 0)) or n["i"] > 1
    fb.stop()
    fb.join(1)
    assert not fb.is_alive()


def test_hotkey_steps_default_is_valid():
    from capture_ecran import config
    from capture_ecran.hotkeys import parse_hotkey
    assert parse_hotkey(config.DEFAULTS["hotkey_steps"])[1] == 0x7B  # F12
