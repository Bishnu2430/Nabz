"""Narration with ElevenLabs text-to-speech (FR-26, ADR-0008).

The request carries only the explanation text, which is built from de-identified values. Audio is generated once
per explanation, on the first press of play, and stored for reuse. Voices come from ELEVENLABS_VOICE_<LANG>; when
unset, the first voice on the account is used (the key's "Voices: read" scope allows listing them).
"""

from __future__ import annotations

import re
from typing import Protocol

import httpx

API = "https://api.elevenlabs.io/v1"
HEADINGS = {
    "en": ("Your results.", "Questions for your doctor."),
    "hi": ("आपके परिणाम।", "डॉक्टर से पूछने के लिए सवाल।"),
    "or": ("ଆପଣଙ୍କ ଫଳାଫଳ।", "ଡାକ୍ତରଙ୍କୁ ପଚାରିବା ପାଇଁ ପ୍ରଶ୍ନ।"),
}


class TTSError(RuntimeError):
    pass


class TTSProvider(Protocol):
    def synthesize(self, text: str, language: str) -> bytes: ...


def narration_text(content: dict, language: str) -> str:
    intro, questions = HEADINGS.get(language, HEADINGS["en"])
    parts = [intro, content.get("summary", "")]
    for t in content.get("per_test", []):
        parts += [t.get("what_it_measures", ""), t.get("what_this_result_means", "")]
    if content.get("doctor_questions"):
        parts.append(questions)
        parts += content["doctor_questions"]
    lines = (line.strip().removeprefix("• ") for p in parts if p for line in p.splitlines())
    return "\n".join(line for line in lines if line)


class ElevenLabsProvider:
    """`models` maps a language to its model; eleven_multilingual_v2 has no Odia, so Odia defaults to eleven_v4."""

    def __init__(self, api_key: str, models: dict[str, str], voices: dict[str, str], timeout: float = 90.0,
                 client: httpx.Client | None = None):
        if not api_key:
            raise TTSError("ELEVENLABS_API_KEY is not set")
        self.models = models
        self.voices = {k: v for k, v in voices.items() if v}
        self._client = client or httpx.Client(timeout=timeout)
        self._headers = {"xi-api-key": api_key}

    def _voice(self, language: str) -> str:
        if voice := self.voices.get(language) or self.voices.get("en"):
            return voice
        r = self._client.get(f"{API}/voices", headers=self._headers)
        if r.status_code != 200 or not r.json().get("voices"):
            raise TTSError(f"no voice configured and the voice list failed (HTTP {r.status_code})")
        voices = r.json()["voices"]
        calm = [v for v in voices if re.search(r"warm|reassuring|calm|soothing", v.get("name", ""), re.I)]
        self.voices["en"] = (calm or voices)[0]["voice_id"]
        return self.voices["en"]

    def synthesize(self, text: str, language: str) -> bytes:
        model = self.models.get(language) or self.models["en"]
        try:
            r = self._client.post(f"{API}/text-to-speech/{self._voice(language)}",
                                  params={"output_format": "mp3_44100_128"}, headers=self._headers,
                                  json={"text": text, "model_id": model})
        except httpx.HTTPError as exc:
            raise TTSError(f"request failed: {type(exc).__name__}") from exc
        if r.status_code != 200 or not r.headers.get("content-type", "").startswith("audio/"):
            raise TTSError(f"HTTP {r.status_code}")
        return r.content
