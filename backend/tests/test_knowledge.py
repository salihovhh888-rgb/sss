import pytest

from app.agent.knowledge import TenantKnowledgeBase


def test_load_demo_salon_services():
    kb = TenantKnowledgeBase.load("demo-salon")
    services = kb.get_services()
    assert any(s["name"] == "Женская стрижка" for s in services)


def test_load_unknown_tenant_raises():
    with pytest.raises(FileNotFoundError):
        TenantKnowledgeBase.load("does-not-exist")


def test_search_knowledge_base_matches_question():
    kb = TenantKnowledgeBase.load("demo-salon")
    results = kb.search_knowledge_base("часы работы")
    assert results
    assert "9:00" in results[0]["answer"]


def test_search_knowledge_base_falls_back_to_top_entries():
    kb = TenantKnowledgeBase.load("demo-salon")
    results = kb.search_knowledge_base("совершенно случайный запрос без совпадений")
    assert len(results) <= 3


def test_get_objection_response_matches_keyword():
    kb = TenantKnowledgeBase.load("demo-sales")
    response = kb.get_objection_response("это слишком дорого для нас")
    assert "окупается" in response


def test_get_objection_response_default_fallback():
    kb = TenantKnowledgeBase.load("demo-sales")
    response = kb.get_objection_response("у нас уже есть похожая система")
    assert response  # дефолтный ответ, не пустая строка
