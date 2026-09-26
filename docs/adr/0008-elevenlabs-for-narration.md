# ADR-0008 · ElevenLabs for narration

**Status:** Accepted · 2026-09-26

## Context

FR-26 asks for the explanation to be narrated in English, Hindi or Odia when voice consent is on. The docs left the provider open between a commercial API and an open-source Indic TTS model, to be decided in Sprint 5.

## Decision

- Use the **ElevenLabs** text-to-speech API (`TTS_PROVIDER=elevenlabs`, model `eleven_multilingual_v2`), with one voice ID per language in `.env` (`ELEVENLABS_VOICE_EN`, `_HI`, `_OR`).
- The API key is scoped to the minimum: Text to Speech (access), Voices (read), Models (access) and User (access). Everything else is off.
- Audio is generated once per explanation and language, stored on the `uploads` volume (`explanation.audio_key`) and reused. This also serves offline demo mode.
- Narration is generated **on demand** (first press of play), not for every explanation, to save characters.
- The TTS request contains only the explanation text. That text has no names or identifiers, because explanations are built from de-identified values.

## Consequences

- **Odia is unverified.** Check the `languages` list returned by `GET /v1/models` in Sprint 5. If Odia is missing, ship Odia as text-only (as risk R-03 already allows), or add AI4Bharat Indic Parler-TTS for Odia only behind the same `TTSProvider` interface.
- **Cost** is per character. An explanation is about 1,500–2,500 characters per language; watch the quota through `GET /v1/user/subscription`.
- **Pronunciation.** Medical abbreviations may be misread. A pronunciation dictionary (read permission) can be added later without code changes to the call site.
