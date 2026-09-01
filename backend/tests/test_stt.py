import httpx
import pytest
import respx

from app.voice_pipeline.stt import YandexSpeechKitSTT, SpeechToTextError, YANDEX_STT_URL


async def _chunks(*parts: bytes):
    for part in parts:
        yield part


async def test_transcribe_stream_success():
    stt = YandexSpeechKitSTT(api_key="key", folder_id="folder")
    with respx.mock:
        respx.post(YANDEX_STT_URL).mock(
            return_value=httpx.Response(200, json={"result": "Здравствуйте, хочу записаться"})
        )
        results = [text async for text in stt.transcribe_stream(_chunks(b"abc", b"def"), "ru")]
    assert results == ["Здравствуйте, хочу записаться"]


async def test_transcribe_stream_empty_audio_yields_nothing():
    stt = YandexSpeechKitSTT(api_key="key", folder_id="folder")
    results = [text async for text in stt.transcribe_stream(_chunks(), "ru")]
    assert results == []


async def test_transcribe_stream_api_error_raises():
    stt = YandexSpeechKitSTT(api_key="key", folder_id="folder")
    with respx.mock:
        respx.post(YANDEX_STT_URL).mock(return_value=httpx.Response(400, text="bad request"))
        with pytest.raises(SpeechToTextError):
            async for _ in stt.transcribe_stream(_chunks(b"abc"), "ru"):
                pass


async def test_transcribe_stream_result_error_message_raises():
    stt = YandexSpeechKitSTT(api_key="key", folder_id="folder")
    with respx.mock:
        respx.post(YANDEX_STT_URL).mock(
            return_value=httpx.Response(200, json={"error_message": "invalid language"})
        )
        with pytest.raises(SpeechToTextError):
            async for _ in stt.transcribe_stream(_chunks(b"abc"), "uz"):
                pass
