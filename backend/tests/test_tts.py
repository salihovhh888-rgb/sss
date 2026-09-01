import httpx
import pytest
import respx

from app.voice_pipeline.tts import YandexSpeechKitTTS, TextToSpeechError, YANDEX_TTS_URL


async def test_synthesize_success():
    tts = YandexSpeechKitTTS(api_key="key", folder_id="folder")
    with respx.mock:
        respx.post(YANDEX_TTS_URL).mock(return_value=httpx.Response(200, content=b"\x00\x01audio-bytes"))
        audio = await tts.synthesize("Здравствуйте!", "ru")
    assert audio == b"\x00\x01audio-bytes"


async def test_synthesize_empty_text_returns_empty_bytes_without_request():
    tts = YandexSpeechKitTTS(api_key="key", folder_id="folder")
    with respx.mock:
        route = respx.post(YANDEX_TTS_URL)
        audio = await tts.synthesize("", "ru")
    assert audio == b""
    assert route.call_count == 0


async def test_synthesize_api_error_raises():
    tts = YandexSpeechKitTTS(api_key="key", folder_id="folder")
    with respx.mock:
        respx.post(YANDEX_TTS_URL).mock(return_value=httpx.Response(500, text="server error"))
        with pytest.raises(TextToSpeechError):
            await tts.synthesize("Здравствуйте!", "ru")


async def test_synthesize_uses_uz_defaults():
    tts = YandexSpeechKitTTS(api_key="key", folder_id="folder")
    with respx.mock:
        route = respx.post(YANDEX_TTS_URL).mock(return_value=httpx.Response(200, content=b"ok"))
        await tts.synthesize("Salom!", "uz")
    sent_data = httpx.QueryParams(route.calls.last.request.content.decode())
    assert sent_data["lang"] == "uz-UZ"
    assert sent_data["voice"] == "gulnoza"
