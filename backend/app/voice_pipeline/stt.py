"""Speech-to-text: распознавание речи абонента (RU/UZ).

Основной провайдер MVP — Yandex SpeechKit (поддерживает RU и UZ, включая
телефонные 8kHz модели). Резервные/A-B провайдеры для узбекского — Aisha AI,
NeuronAI (см. docs/architecture.md).

MVP-реализация использует синхронный REST-эндпоинт `stt:recognize`: чанки
аудио буферизуются и распознаются одним запросом после завершения потока.
Это проще и надёжнее для старта, чем потоковый gRPC API, но добавляет
задержку на всю длину реплики. Переход на потоковое распознавание (v3
StreamingRecognition, gRPC) с partial-результатами — оптимизация задержки на
следующем этапе (см. docs/architecture.md, "Ключевые технические риски").
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

YANDEX_STT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

# Yandex SpeechKit ожидает BCP-47 коды языков.
_LANGUAGE_CODES = {
    "ru": "ru-RU",
    "uz": "uz-UZ",
}


class SpeechToTextError(RuntimeError):
    """Ошибка при обращении к STT-провайдеру."""


class SpeechToTextProvider:
    """Базовый интерфейс STT-провайдера."""

    async def transcribe_stream(
        self, audio_chunks: AsyncIterator[bytes], language: str
    ) -> AsyncIterator[str]:
        """Принять поток аудио, вернуть поток распознанных фраз (partial/final)."""
        raise NotImplementedError
        yield ""  # pragma: no cover


class YandexSpeechKitSTT(SpeechToTextProvider):
    """STT через Yandex SpeechKit REST API.

    Ожидаемый формат аудио по умолчанию — LPCM 8kHz mono (типично для
    телефонии); при необходимости поменять через ``audio_format``/``sample_rate_hz``.
    """

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

    async def transcribe_stream(
        self, audio_chunks: AsyncIterator[bytes], language: str
    ) -> AsyncIterator[str]:
        buffer = bytearray()
        async for chunk in audio_chunks:
            buffer.extend(chunk)
        if not buffer:
            return
        text = await self._recognize(bytes(buffer), language)
        if text:
            yield text

    async def _recognize(self, audio: bytes, language: str) -> str:
        lang_code = _LANGUAGE_CODES.get(language, language)
        params = {
            "lang": lang_code,
            "format": self.audio_format,
            "sampleRateHertz": str(self.sample_rate_hz),
            "folderId": self.folder_id,
        }
        headers = {"Authorization": f"Api-Key {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                YANDEX_STT_URL, params=params, headers=headers, content=audio
            )
        if response.status_code != 200:
            raise SpeechToTextError(
                f"Yandex SpeechKit STT вернул {response.status_code}: {response.text}"
            )
        data = response.json()
        error_message = data.get("error_message")
        if error_message:
            raise SpeechToTextError(f"Yandex SpeechKit STT ошибка: {error_message}")
        return data.get("result", "")
