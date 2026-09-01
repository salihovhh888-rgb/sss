"""Speech-to-text: распознавание речи абонента (RU/UZ).

Основной провайдер MVP — Yandex SpeechKit (поддерживает RU и UZ, включая
телефонные 8kHz модели). Резервные/A-B провайдеры для узбекского — Aisha AI,
NeuronAI (см. docs/architecture.md).
"""

from __future__ import annotations

from collections.abc import AsyncIterator


class SpeechToTextProvider:
    """Базовый интерфейс STT-провайдера."""

    async def transcribe_stream(
        self, audio_chunks: AsyncIterator[bytes], language: str
    ) -> AsyncIterator[str]:
        """Принять поток аудио, вернуть поток распознанных фраз (partial/final)."""
        raise NotImplementedError
        yield ""  # pragma: no cover


class YandexSpeechKitSTT(SpeechToTextProvider):
    def __init__(self, api_key: str, folder_id: str) -> None:
        self.api_key = api_key
        self.folder_id = folder_id

    async def transcribe_stream(
        self, audio_chunks: AsyncIterator[bytes], language: str
    ) -> AsyncIterator[str]:
        raise NotImplementedError
        yield ""  # pragma: no cover
