"""Text-to-speech: синтез голосового ответа агента (RU/UZ).

Основной провайдер MVP — Yandex SpeechKit REST API. Резервные/A-B провайдеры
для узбекского — Aisha AI, NeuronAI (см. docs/architecture.md).
"""

from __future__ import annotations

import httpx

YANDEX_TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

_LANGUAGE_CODES = {
    "ru": "ru-RU",
    "uz": "uz-UZ",
}

# Голоса по умолчанию на язык (обычные нейросетевые голоса Yandex SpeechKit).
_DEFAULT_VOICES = {
    "ru": "alena",
    "uz": "gulnoza",
}


class TextToSpeechError(RuntimeError):
    """Ошибка при обращении к TTS-провайдеру."""


class TextToSpeechProvider:
    """Базовый интерфейс TTS-провайдера."""

    async def synthesize(self, text: str, language: str, voice: str | None = None) -> bytes:
        """Синтезировать речь из текста, вернуть аудио (PCM/WAV)."""
        raise NotImplementedError


class YandexSpeechKitTTS(TextToSpeechProvider):
    def __init__(
        self,
        api_key: str,
        folder_id: str,
        audio_format: str = "lpcm",
        sample_rate_hz: int = 8000,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.api_key = api_key
        self.folder_id = folder_id
        self.audio_format = audio_format
        self.sample_rate_hz = sample_rate_hz
        self.timeout_seconds = timeout_seconds

    async def synthesize(self, text: str, language: str, voice: str | None = None) -> bytes:
        if not text:
            return b""
        lang_code = _LANGUAGE_CODES.get(language, language)
        data = {
            "text": text,
            "lang": lang_code,
            "voice": voice or _DEFAULT_VOICES.get(language, "alena"),
            "format": self.audio_format,
            "sampleRateHertz": str(self.sample_rate_hz),
            "folderId": self.folder_id,
        }
        headers = {"Authorization": f"Api-Key {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(YANDEX_TTS_URL, data=data, headers=headers)
        if response.status_code != 200:
            raise TextToSpeechError(
                f"Yandex SpeechKit TTS вернул {response.status_code}: {response.text}"
            )
        return response.content
