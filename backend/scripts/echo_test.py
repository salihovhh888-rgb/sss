#!/usr/bin/env python3
"""Эхо-тест голосового пайплайна: STT -> TTS без LLM (Неделя 1-2 в roadmap).

Проверяет базовую задержку и работоспособность STT/TTS-провайдеров: читает
локальный WAV-файл, распознаёт речь и сразу синтезирует ответ обратно в
WAV-файл — без диалогового движка. Требует настоящих ключей Yandex
SpeechKit в .env (см. README.md).

Использование:
    cd backend
    python scripts/echo_test.py input.wav output.wav --language ru
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.voice_pipeline.stt import YandexSpeechKitSTT  # noqa: E402
from app.voice_pipeline.tts import YandexSpeechKitTTS  # noqa: E402


def _read_pcm_from_wav(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        pcm = wav_file.readframes(wav_file.getnframes())
    return pcm, sample_rate


def _write_pcm_to_wav(path: Path, pcm: bytes, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)


async def _single_chunk_stream(data: bytes):
    yield data


async def run_echo_test(input_path: Path, output_path: Path, language: str) -> None:
    settings = get_settings()
    if not settings.yandex_speechkit_api_key:
        raise SystemExit(
            "YANDEX_SPEECHKIT_API_KEY не задан в .env — эхо-тест требует реальных ключей."
        )

    pcm, sample_rate = _read_pcm_from_wav(input_path)
    stt = YandexSpeechKitSTT(
        settings.yandex_speechkit_api_key, settings.yandex_speechkit_folder_id, sample_rate_hz=sample_rate
    )
    tts = YandexSpeechKitTTS(
        settings.yandex_speechkit_api_key, settings.yandex_speechkit_folder_id, sample_rate_hz=sample_rate
    )

    t0 = time.monotonic()
    transcript = ""
    async for text in stt.transcribe_stream(_single_chunk_stream(pcm), language):
        transcript += text
    t1 = time.monotonic()
    print(f"[STT] {t1 - t0:.2f}s: {transcript!r}")

    if not transcript:
        raise SystemExit("STT не распознал речь во входном файле — проверьте формат/язык.")

    audio = await tts.synthesize(transcript, language)
    t2 = time.monotonic()
    print(f"[TTS] {t2 - t1:.2f}s, {len(audio)} bytes")

    _write_pcm_to_wav(output_path, audio, sample_rate)
    print(f"Итоговая задержка round-trip: {t2 - t0:.2f}s. Результат сохранён в {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_wav", type=Path)
    parser.add_argument("output_wav", type=Path)
    parser.add_argument("--language", choices=["ru", "uz"], default="ru")
    args = parser.parse_args()
    asyncio.run(run_echo_test(args.input_wav, args.output_wav, args.language))


if __name__ == "__main__":
    main()
