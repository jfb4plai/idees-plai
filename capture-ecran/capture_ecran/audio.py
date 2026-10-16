"""Voix off : enregistrement du micro (Windows, via MCI : aucune dépendance) et lecture."""
from __future__ import annotations

import sys
import wave
from pathlib import Path


class AudioError(Exception):
    """Message destiné à l'utilisateur (micro absent, accès refusé…)."""


class Recorder:
    """Interface commune : start() puis stop(chemin) qui écrit un WAV PCM 16 bits mono 44,1 kHz."""

    def start(self) -> None:
        raise NotImplementedError

    def stop(self, path: Path) -> None:
        raise NotImplementedError

    def cancel(self) -> None:
        pass


class MciRecorder(Recorder):
    ALIAS = "plai_voix"

    def __init__(self):
        import ctypes
        self._mci = ctypes.WinDLL("winmm")
        self._ct = ctypes

    def _send(self, cmd: str) -> None:
        code = self._mci.mciSendStringW(cmd, None, 0, None)
        if code:
            buf = self._ct.create_unicode_buffer(256)
            self._mci.mciGetErrorStringW(code, buf, 256)
            raise AudioError(f"{buf.value or 'erreur audio'} (code {code})")

    def start(self) -> None:
        self._mci.mciSendStringW(f"close {self.ALIAS}", None, 0, None)
        try:
            self._send(f"open new type waveaudio alias {self.ALIAS}")
            self._send(f"set {self.ALIAS} time format ms bitspersample 16 channels 1 "
                       "samplespersec 44100 alignment 2 bytespersec 88200")
            self._send(f"record {self.ALIAS}")
        except AudioError as e:
            self.cancel()
            raise AudioError("Impossible d'utiliser le micro. Vérifiez qu'il est branché et autorisé "
                             "(Paramètres Windows > Confidentialité > Microphone). Détail : " + str(e)) from e

    def stop(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._send(f"stop {self.ALIAS}")
            self._send(f'save {self.ALIAS} "{path}"')
        finally:
            self.cancel()

    def cancel(self) -> None:
        self._mci.mciSendStringW(f"close {self.ALIAS}", None, 0, None)


def make_recorder() -> Recorder | None:
    """Un enregistreur utilisable sur cette machine, ou None."""
    if sys.platform == "win32":
        try:
            return MciRecorder()
        except OSError:
            return None
    return None


def play(path: Path) -> None:
    if sys.platform == "win32":
        import winsound
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)


def stop_play() -> None:
    if sys.platform == "win32":
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)


def wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except (wave.Error, EOFError, OSError):
        return 0.0


def build_voiceover(wavs: list[Path | None], durations: list[float], out: Path) -> tuple[Path | None, int]:
    """Assemble une piste unique : la voix de chaque écran, complétée de silence jusqu'à la
    durée de l'écran. Retourne (fichier ou None si aucune voix, nombre de fichiers ignorés)."""
    params, skipped = None, 0
    for p in wavs:
        if p and p.exists():
            with wave.open(str(p), "rb") as w:
                params = params or (w.getnchannels(), w.getsampwidth(), w.getframerate())
    if params is None:
        return None, 0
    nch, width, rate = params
    with wave.open(str(out), "wb") as o:
        o.setnchannels(nch)
        o.setsampwidth(width)
        o.setframerate(rate)
        for p, dur in zip(wavs, durations):
            target = int(round(dur * rate))
            data = b""
            if p and p.exists():
                with wave.open(str(p), "rb") as w:
                    if (w.getnchannels(), w.getsampwidth(), w.getframerate()) == params:
                        data = w.readframes(w.getnframes())
                    else:
                        skipped += 1
            frame_bytes = nch * width
            data = data[: target * frame_bytes]
            o.writeframes(data + b"\x00" * (target * frame_bytes - len(data)))
    return out, skipped
