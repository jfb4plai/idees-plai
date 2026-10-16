"""Exports : pack vidéo (images + sous-titres .srt + MP4 si ffmpeg), fiche pas-à-pas HTML."""
from __future__ import annotations

import base64
import html
import io
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

from . import audio
from .annotate import get_font
from .session import Session

VIDEO_SIZE = (1920, 1080)


# ---------------------------------------------------------------- sous-titres
def estimate_duration(caption: str, minimum: float = 3.0, chars_per_second: float = 14.0) -> float:
    """Durée d'affichage : le temps de lire la légende, avec un minimum et un plafond."""
    if not caption.strip():
        return minimum
    return min(15.0, max(minimum, 1.5 + len(caption) / chars_per_second))


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(captions: list[str], durations: list[float]) -> str:
    out, t, n = [], 0.0, 0
    for cap, dur in zip(captions, durations):
        if cap.strip():
            n += 1
            out.append(f"{n}\n{srt_time(t)} --> {srt_time(t + dur - 0.05)}\n{cap.strip()}\n")
        t += dur
    return "\n".join(out)


# ---------------------------------------------------------------- images
def wrap_text(text: str, font, max_width: int) -> list[str]:
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines: list[str] = []
    for para in text.splitlines() or [""]:
        cur = ""
        for word in para.split():
            trial = f"{cur} {word}".strip()
            if cur and draw.textlength(trial, font=font) > max_width:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        lines.append(cur)
    return lines


def compose_frame(img: Image.Image, caption: str = "", size=VIDEO_SIZE, burn: bool = True) -> Image.Image:
    """Image de la vidéo : capture centrée sur fond sombre, sous-titre incrusté en bas."""
    W, H = size
    canvas = Image.new("RGBA", size, (24, 24, 24, 255))
    has_band = burn and bool(caption.strip())
    band_h = int(H * 0.2) if has_band else 0
    margin = int(H * 0.03)
    aw, ah = W - 2 * margin, H - band_h - 2 * margin
    k = min(aw / img.width, ah / img.height, 1.5)
    shown = img.convert("RGB").resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.LANCZOS)
    canvas.paste(shown, (margin + (aw - shown.width) // 2, margin + (ah - shown.height) // 2))
    if has_band:
        band = Image.new("RGBA", (W, band_h), (0, 0, 0, 215))
        canvas.alpha_composite(band, (0, H - band_h))
        d = ImageDraw.Draw(canvas)
        size_px = H // 18
        while True:
            font = get_font(size_px)
            lines = wrap_text(caption.strip(), font, int(W * 0.86))
            line_h = int(size_px * 1.25)
            if len(lines) * line_h <= band_h - 24 or size_px <= 22:
                break
            size_px -= 2
        y = H - band_h + (band_h - len(lines) * line_h) // 2
        for line in lines:
            w = d.textlength(line, font=font)
            d.text(((W - w) / 2, y), line, font=font, fill="#FFFFFF", stroke_width=2, stroke_fill="#000000")
            y += line_h
    return canvas.convert("RGB")


# ---------------------------------------------------------------- ffmpeg
def find_ffmpeg() -> str | None:
    """ffmpeg dans le PATH, ou à côté du programme (ffmpeg.exe / ffmpeg/ffmpeg.exe)."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    here = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    for cand in (here / "ffmpeg.exe", here / "ffmpeg" / "ffmpeg.exe", here / "ffmpeg" / "bin" / "ffmpeg.exe"):
        if cand.is_file():
            return str(cand)
    return None


@dataclass
class VideoResult:
    folder: Path
    frames: list[Path] = field(default_factory=list)
    srt: Path | None = None
    mp4: Path | None = None
    voice: Path | None = None
    message: str = ""


def export_video_pack(session: Session, out_dir: Path, burn: bool = True, fixed_seconds: float | None = None,
                      make_mp4: bool = True, size=VIDEO_SIZE) -> VideoResult:
    """Écrit frames 1920×1080, soustitres.srt et, si ffmpeg est présent, video.mp4."""
    caps = session.captures
    if not caps:
        raise ValueError("Aucune capture dans cette série.")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    res = VideoResult(out_dir)
    texts = [c.caption for c in caps]
    durs = [fixed_seconds if fixed_seconds else estimate_duration(t) for t in texts]
    wavs = [session.audio_path(c) if session.has_audio(c) else None for c in caps]
    # une image reste affichée au moins le temps de la voix (+ une respiration) : on ne coupe jamais la parole
    durs = [max(d, audio.wav_duration(w) + 0.6) if w else d for d, w in zip(durs, wavs)]
    for i, cap in enumerate(caps, start=1):
        frame = compose_frame(session.load_final(cap), cap.caption, size, burn)
        p = out_dir / f"image_{i:03d}.png"
        frame.save(p)
        res.frames.append(p)
    res.srt = out_dir / "soustitres.srt"
    res.srt.write_text(build_srt(texts, durs), "utf-8-sig")  # BOM : accents corrects dans les lecteurs Windows
    (out_dir / "durees.txt").write_text(
        "\n".join(f"{p.name}\t{d:.1f} s\t{t}" for p, d, t in zip(res.frames, durs, texts)), "utf-8")
    voice, skipped = audio.build_voiceover(wavs, durs, out_dir / "voixoff.wav")
    res.voice = voice
    ffmpeg = find_ffmpeg() if make_mp4 else None
    if not make_mp4:
        res.message = "Images et sous-titres prêts (vidéo non demandée)."
    elif not ffmpeg:
        res.message = ("Images et sous-titres prêts. Pour obtenir directement un fichier MP4, installez ffmpeg "
                       "(voir le mode d'emploi vidéo) ou assemblez les images dans Clipchamp.")
    else:
        res.mp4 = _run_ffmpeg(ffmpeg, out_dir, res.frames, durs, res.srt, burn, res, voice)
    if skipped:
        res.message += f" ({skipped} enregistrement(s) vocal(aux) au format différent ignoré(s).)"
    return res


def _run_ffmpeg(ffmpeg: str, out_dir: Path, frames: list[Path], durs: list[float], srt: Path, burn: bool,
                res: VideoResult, voice: Path | None = None) -> Path | None:
    listing = []
    for p, d in zip(frames, durs):
        listing += [f"file '{p.name}'", f"duration {d:.2f}"]
    listing.append(f"file '{frames[-1].name}'")  # exigence du démultiplexeur concat
    (out_dir / "liste.txt").write_text("\n".join(listing), "utf-8")
    out = out_dir / "video.mp4"
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", "liste.txt"]
    maps = ["-map", "0:v"]
    n_in = 1
    if voice:
        cmd += ["-i", voice.name]
        maps += ["-map", f"{n_in}:a"]
        n_in += 1
    if not burn:  # sous-titres « souples » : piste activable dans le lecteur
        cmd += ["-i", srt.name]
        maps += ["-map", f"{n_in}:s", "-c:s", "mov_text", "-metadata:s:s:0", "language=fra"]
    cmd += maps + ["-vf", "fps=25,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20"]
    if voice:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    cmd += ["-movflags", "+faststart", out.name]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        r = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True, creationflags=flags, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as e:
        res.message = f"ffmpeg n'a pas pu s'exécuter ({e}). Images et sous-titres sont prêts."
        return None
    (out_dir / "liste.txt").unlink(missing_ok=True)
    if r.returncode != 0 or not out.exists():
        tail = (r.stderr or "").strip().splitlines()[-1:]
        res.message = "ffmpeg a échoué" + (f" : {tail[0]}" if tail else ".")
        return None
    res.message = "Vidéo créée."
    return out


# ---------------------------------------------------------------- fiche HTML
_CSS = """body{font-family:Verdana,Arial,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1b1b1b;line-height:1.6}
h1{font-size:1.7rem}.step{break-inside:avoid;margin:2rem 0;border-top:3px solid #1E88E5;padding-top:1rem}
.num{display:inline-block;background:#1E88E5;color:#fff;border-radius:50%;width:2.2em;height:2.2em;line-height:2.2em;
text-align:center;font-weight:bold;margin-right:.6em}.cap{font-size:1.2rem;font-weight:bold}
img{max-width:100%;border:1px solid #bbb;margin-top:.8rem}@media print{body{margin:0}.step{page-break-inside:avoid}}"""


def export_html_guide(session: Session, path: Path, max_width: int = 1400) -> Path:
    """Fiche « pas à pas » autonome (images intégrées) : s'imprime ou s'enregistre en PDF."""
    parts = [f"<!doctype html><html lang='fr'><meta charset='utf-8'><title>{html.escape(session.title)}</title>"
             f"<style>{_CSS}</style><h1>{html.escape(session.title)}</h1>"]
    for i, cap in enumerate(session.captures, start=1):
        img = session.load_final(cap)
        if img.width > max_width:
            img = img.resize((max_width, int(img.height * max_width / img.width)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        text = html.escape(cap.caption) if cap.caption else ""
        parts.append(f"<section class='step'><span class='num'>{i}</span><span class='cap'>{text}</span><br>"
                     f"<img alt='Étape {i}' src='data:image/png;base64,{b64}'></section>")
    path = Path(path)
    path.write_text("".join(parts), "utf-8")
    return path


# ---------------------------------------------------------------- document Word (.docx)
# Écrit à la main (zip + XML) : aucune dépendance, et un résultat accessible (titres Word réels,
# texte alternatif sur chaque image, police Verdana 12 pt lisible).
_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
       'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
       'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
       'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')

_STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {_NS}>
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Verdana" w:hAnsi="Verdana" w:cs="Verdana"/><w:sz w:val="24"/><w:lang w:val="fr-BE"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="312" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:spacing w:after="360"/></w:pPr><w:rPr><w:b/><w:color w:val="1565C0"/><w:sz w:val="44"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="360" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="1565C0"/><w:sz w:val="32"/></w:rPr></w:style>
</w:styles>"""

_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

_EMU_PER_CM = 360000
_MAX_W_CM, _MAX_H_CM = 16.0, 17.0


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _para(text: str, style: str | None = None, bold: bool = False, keep_next: bool = False) -> str:
    ppr = (f'<w:pStyle w:val="{style}"/>' if style else "") + ("<w:keepNext/>" if keep_next else "")
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    runs = "".join(f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(line)}</w:t></w:r>'
                   + ("<w:r><w:br/></w:r>" if i < len(text.split("\n")) - 1 else "")
                   for i, line in enumerate(text.split("\n")))
    return f"<w:p><w:pPr>{ppr}</w:pPr>{runs}</w:p>"


def _image_para(rid: str, n: int, cx: int, cy: int, alt: str) -> str:
    alt = _esc(alt)
    return (f'<w:p><w:pPr><w:spacing w:after="360"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{n}" name="Capture {n}" descr="{alt}"/>'
            f'<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
            f'<pic:nvPicPr><pic:cNvPr id="{n}" name="capture_{n}.png" descr="{alt}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
            f'</wp:inline></w:drawing></w:r></w:p>')


def export_docx(session: Session, path: Path, max_px: int = 1600) -> Path:
    """Document Word : titre, puis pour chaque capture « Étape n » + légende + image (A4, marges 2 cm)."""
    import zipfile
    from datetime import datetime, timezone
    if not session.captures:
        raise ValueError("Aucune capture dans cette série.")
    body = [_para(session.title or "Ma série de captures", style="Title")]
    rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>']
    media: list[tuple[str, bytes]] = []
    for n, cap in enumerate(session.captures, start=1):
        img = session.load_final(cap)
        if img.width > max_px:
            img = img.resize((max_px, int(img.height * max_px / img.width)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        media.append((f"word/media/image{n}.png", buf.getvalue()))
        rid = f"rId{n + 1}"
        rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image{n}.png"/>')
        # on remplit la largeur utile (16 cm) sauf si l'image est très haute : alors on limite la hauteur
        w_cm = min(_MAX_W_CM, _MAX_H_CM * img.width / img.height)
        h_cm = w_cm * img.height / img.width
        body.append(_para(f"Étape {n}", style="Heading1"))
        if cap.caption:
            body.append(_para(cap.caption, bold=True, keep_next=True))
        body.append(_image_para(rid, n, int(w_cm * _EMU_PER_CM), int(h_cm * _EMU_PER_CM),
                                cap.caption or f"Capture d'écran de l'étape {n}"))
    sect = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr>')
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {_NS}><w:body>'
                + "".join(body) + sect + "</w:body></w:document>")
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                + "".join(rels) + "</Relationships>")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{_esc(session.title)}</dc:title><dc:language>fr-BE</dc:language>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created></cp:coreProperties>')
    path = Path(path)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", _STYLES)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("docProps/core.xml", core)
        for name, data in media:
            z.writestr(name, data)
    return path
