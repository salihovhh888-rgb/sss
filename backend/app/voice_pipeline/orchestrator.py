"""Оркестрация одного звонка: телефония <-> STT <-> диалоговый движок <-> TTS.

Связывает воедино AsteriskClient, STT/TTS-провайдеров и DialogueManager
(app.agent.dialogue) для одного активного разговора (call session).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.dialogue import DialogueManager
from app.telephony.asterisk_client import AsteriskClient
from app.voice_pipeline.stt import SpeechToTextProvider
from app.voice_pipeline.tts import TextToSpeechProvider


@dataclass
class CallSession:
    channel_id: str
    business_profile: str  # "courses" | "salon" | "sales"
    language: str  # "ru" | "uz"


class CallOrchestrator:
    def __init__(
        self,
        telephony: AsteriskClient,
        stt: SpeechToTextProvider,
        tts: TextToSpeechProvider,
        dialogue: DialogueManager,
    ) -> None:
        self.telephony = telephony
        self.stt = stt
        self.tts = tts
        self.dialogue = dialogue

    async def handle_call(self, session: CallSession) -> None:
        """Основной цикл звонка: слушать -> распознавать -> отвечать -> синтезировать.

        MVP-каркас: реальная реализация запускает STT-стрим параллельно с
        воспроизведением TTS-ответов, поддерживает barge-in (прерывание) и
        эскалацию на человека при затруднении (см. docs/architecture.md).
        """
        raise NotImplementedError
