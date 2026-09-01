"""Интеграция с Asterisk (ARI) для приёма и совершения звонков.

MVP-каркас: реальная реализация подключается к Asterisk REST Interface (ARI),
подписывается на события канала (StasisStart/StasisEnd) и передаёт аудио-поток
в voice_pipeline.
"""

from __future__ import annotations

from collections.abc import AsyncIterator


class AsteriskClient:
    """Обёртка над Asterisk ARI для управления звонками."""

    def __init__(self, ari_url: str, username: str, password: str) -> None:
        self.ari_url = ari_url
        self.username = username
        self.password = password

    async def originate_call(self, to_number: str, caller_id: str) -> str:
        """Инициировать исходящий звонок, вернуть channel_id."""
        raise NotImplementedError

    async def answer(self, channel_id: str) -> None:
        """Принять входящий звонок."""
        raise NotImplementedError

    async def hangup(self, channel_id: str) -> None:
        raise NotImplementedError

    async def stream_audio_in(self, channel_id: str) -> AsyncIterator[bytes]:
        """Стрим аудио от абонента (для передачи в STT)."""
        raise NotImplementedError
        yield b""  # pragma: no cover

    async def play_audio(self, channel_id: str, audio: bytes) -> None:
        """Проиграть синтезированный (TTS) аудио-ответ абоненту."""
        raise NotImplementedError
