"""Text-to-speech: синтез голосового ответа агента (RU/UZ).

Основной провайдер MVP — Yandex SpeechKit. Резервные/A-B провайдеры для
узбекского — Aisha AI, NeuronAI (см. docs/architecture.md).
"""

from __future__ import annotations


class TextToSpeechProvider:
    """Базовый интерфейс TTS-провайдера."""

    async def synthesize(self, text: str, language: str, voice: str | None = None) -> bytes:
        """Синтезировать речь из текста, вернуть аудио (PCM/WAV)."""
        raise NotImplementedError


class YandexSpeechKitTTS(TextToSpeechProvider):
    def __init__(self, api_key: str, folder_id: str) -> None:
        self.api_key = api_key
        self.folder_id = folder_id

    async def synthesize(self, text: str, language: str, voice: str | None = None) -> bytes:
        raise NotImplementedError
