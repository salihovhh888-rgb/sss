from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.agent.dialogue import BusinessProfile, DialogueManager
from app.agent.functions import FunctionRegistry
from app.agent.knowledge import TenantKnowledgeBase


def _text_block(text: str):
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(name: str, input_: dict, tool_id: str = "tool-1"):
    return SimpleNamespace(type="tool_use", name=name, input=input_, id=tool_id)


def _response(content, stop_reason: str):
    return SimpleNamespace(content=content, stop_reason=stop_reason)


def _make_manager(profile_name: str = "salon", language: str = "ru") -> tuple[DialogueManager, AsyncMock]:
    profile = BusinessProfile.load(profile_name)
    kb = TenantKnowledgeBase.load(f"demo-{profile_name}")
    registry = FunctionRegistry(knowledge_base=kb)
    anthropic_client = AsyncMock()
    manager = DialogueManager(
        profile=profile,
        language=language,
        client_id="test-client",
        function_registry=registry,
        anthropic_client=anthropic_client,
        model="claude-test",
    )
    return manager, anthropic_client


def test_should_escalate_matches_trigger_phrase():
    manager, _ = _make_manager()
    assert manager.should_escalate("Позовите, пожалуйста, ПОЗОВИ ЧЕЛОВЕКА") is True
    assert manager.should_escalate("Хочу записаться на стрижку") is False


async def test_handle_user_utterance_fast_path_escalation_skips_llm():
    manager, anthropic_client = _make_manager()
    reply = await manager.handle_user_utterance("позови человека")
    assert manager.escalated is True
    assert anthropic_client.messages.create.await_count == 0
    assert reply


async def test_handle_user_utterance_plain_text_reply():
    manager, anthropic_client = _make_manager()
    anthropic_client.messages.create.return_value = _response(
        [_text_block("Здравствуйте! Чем могу помочь?")], stop_reason="end_turn"
    )

    reply = await manager.handle_user_utterance("Здравствуйте")

    assert reply == "Здравствуйте! Чем могу помочь?"
    assert manager.escalated is False
    assert anthropic_client.messages.create.await_count == 1


async def test_handle_user_utterance_runs_tool_use_loop():
    manager, anthropic_client = _make_manager()
    anthropic_client.messages.create.side_effect = [
        _response(
            [_tool_use_block("get_services", {}, tool_id="call-1")],
            stop_reason="tool_use",
        ),
        _response(
            [_text_block("У нас есть женская и мужская стрижка. Что вас интересует?")],
            stop_reason="end_turn",
        ),
    ]

    reply = await manager.handle_user_utterance("Какие у вас есть услуги?")

    assert "стрижка" in reply
    assert anthropic_client.messages.create.await_count == 2
    # История диалога должна содержать tool_result с данными об услугах,
    # присланными в ответ на вызов get_services моделью.
    tool_result_messages = [
        m
        for m in manager._messages
        if isinstance(m["content"], list)
        and m["content"]
        and isinstance(m["content"][0], dict)
        and m["content"][0].get("type") == "tool_result"
    ]
    assert len(tool_result_messages) == 1
    assert tool_result_messages[0]["role"] == "user"
    assert tool_result_messages[0]["content"][0]["tool_use_id"] == "call-1"


async def test_handle_user_utterance_escalate_tool_stops_loop():
    manager, anthropic_client = _make_manager()
    anthropic_client.messages.create.return_value = _response(
        [_tool_use_block("escalate_to_human", {"reason": "сложный вопрос"}, tool_id="call-esc")],
        stop_reason="tool_use",
    )

    reply = await manager.handle_user_utterance("У меня очень сложный вопрос")

    assert manager.escalated is True
    assert anthropic_client.messages.create.await_count == 1
    assert reply
