"""Speech-to-text via faster-whisper. CPU-friendly (model 'tiny', ~75MB).

Modelul se incarca lazy (la prima cerere) si se pastreaza in memorie.
TTS-ul (text-to-speech) se face in browser via Web Speech API (vezi dashboard).
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model():
    """Incarca lazy modelul Whisper. Tiny e suficient pt comenzi scurte (RO)."""
    try:
        from faster_whisper import WhisperModel

        size = os.environ.get("WHISPER_MODEL_SIZE", "tiny")
        logger.info("Incarc Whisper model: %s", size)
        # int8 = quantizat, ~50% memorie, viteza similara
        return WhisperModel(size, device="cpu", compute_type="int8")
    except Exception as exc:  # pragma: no cover
        logger.exception("Whisper indisponibil: %s", exc)
        return None


def voice_available() -> bool:
    return _load_model() is not None


def transcribe(audio_path: str, language: str = "ro") -> Optional[str]:
    """Transcrie un fisier audio (mp3/wav/m4a/ogg). Returneaza None la eroare."""
    model = _load_model()
    if model is None:
        return None
    try:
        segments, info = model.transcribe(
            audio_path,
            language=language,
            task="transcribe",
            beam_size=1,  # rapid pe CPU
            vad_filter=True,  # ignora liniste/zgomot
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        logger.info("Transcript (%.1fs audio): %s", info.duration, text[:80])
        return text
    except Exception as exc:
        logger.exception("Eroare transcribe: %s", exc)
        return None


def reset_cache() -> None:
    _load_model.cache_clear()
