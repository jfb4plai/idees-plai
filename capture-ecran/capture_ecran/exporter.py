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
    for i, cap in enumerate(caps, start=1):
        frame = compose_frame(session.load_final(cap), cap.caption, size, burn)
        p = out_dir / f"image_{i:03d}.png"
        frame.save(p)
        res.frames.append(p)
    res.srt = out_dir / "soustitres.srt"
    res.srt.write_text(build_srt(texts, durs), "utf-8-sig")  # BOM : accents corrects dans les lecteurs Windows
    (out_dir / "durees.txt").write_text(
        "\n".join(f"{p.name}\t{d:.1f} s\t{t}" for p, d, t in zip(res.frames, durs, texts)), "utf-8")
    ffmpeg = find_ffmpeg() if make_mp4 else None
    if not make_mp4:
        res.message = "Images et sous-titres prêts (vidéo non demandée)."
    elif not ffmpeg:
        res.message = ("Images et sous-titres prêts. Pour obtenir directement un fichier MP4, installez ffmpeg "
                       "(voir le mode d'emploi vidéo) ou assemblez les images dans Clipchamp.")
    else:
        res.mp4 = _run_ffmpeg(ffmpeg, out_dir, res.frames, durs, res.srt, burn, res)
    return res


def _run_ffmpeg(ffmpeg: str, out_dir: Path, frames: list[Path], durs: list[float], srt: Path, burn: bool,
                res: VideoResult) -> Path | None:
    listing = []
    for p, d in zip(frames, durs):
        listing += [f"file '{p.name}'", f"duration {d:.2f}"]
    listing.append(f"file '{frames[-1].name}'")  # exigence du démultiplexeur concat
    (out_dir / "liste.txt").write_text("\n".join(listing), "utf-8")
    out = out_dir / "video.mp4"
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", "liste.txt"]
    if not burn:  # sous-titres « souples » : piste activable dans le lecteur
        cmd += ["-i", srt.name, "-c:s", "mov_text", "-metadata:s:s:0", "language=fra"]
    cmd += ["-vf", "fps=25,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-movflags", "+faststart", out.name]
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
