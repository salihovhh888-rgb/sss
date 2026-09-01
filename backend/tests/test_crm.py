import httpx
import pytest
import respx

from app.integrations.crm import AmoCrmClient, Bitrix24Client, CrmError, Lead


async def test_amocrm_create_lead_success():
    client = AmoCrmClient(api_key="token", subdomain="demo")
    lead = Lead(name="Иван", phone="+998901234567", source="outbound_call", business_profile="sales")
    with respx.mock:
        respx.post("https://demo.amocrm.ru/api/v4/leads").mock(
            return_value=httpx.Response(200, json={"_embedded": {"leads": [{"id": 42}]}})
        )
        respx.post("https://demo.amocrm.ru/api/v4/leads/42/notes").mock(
            return_value=httpx.Response(200, json={"_embedded": {"notes": [{"id": 1}]}})
        )
        lead_id = await client.create_lead(lead)
    assert lead_id == "42"


async def test_amocrm_create_lead_error_raises():
    client = AmoCrmClient(api_key="token", subdomain="demo")
    lead = Lead(name="Иван", phone="+998901234567", source="outbound_call", business_profile="sales")
    with respx.mock:
        respx.post("https://demo.amocrm.ru/api/v4/leads").mock(
            return_value=httpx.Response(401, text="unauthorized")
        )
        with pytest.raises(CrmError):
            await client.create_lead(lead)


async def test_amocrm_update_lead_status_adds_note():
    client = AmoCrmClient(api_key="token", subdomain="demo")
    with respx.mock:
        route = respx.post("https://demo.amocrm.ru/api/v4/leads/42/notes").mock(
            return_value=httpx.Response(200, json={})
        )
        await client.update_lead_status("42", "заинтересован")
    assert route.called


async def test_bitrix24_create_lead_success():
    client = Bitrix24Client(webhook_url="https://b24.example.com/rest/1/xyz/")
    lead = Lead(name="Мария", phone="+998907654321", source="inbound_call", business_profile="courses")
    with respx.mock:
        respx.post("https://b24.example.com/rest/1/xyz/crm.lead.add.json").mock(
            return_value=httpx.Response(200, json={"result": 7})
        )
        lead_id = await client.create_lead(lead)
    assert lead_id == "7"


async def test_bitrix24_create_lead_error_raises():
    client = Bitrix24Client(webhook_url="https://b24.example.com/rest/1/xyz/")
    lead = Lead(name="Мария", phone="+998907654321", source="inbound_call", business_profile="courses")
    with respx.mock:
        respx.post("https://b24.example.com/rest/1/xyz/crm.lead.add.json").mock(
            return_value=httpx.Response(200, json={"error": "INVALID_REQUEST"})
        )
        with pytest.raises(CrmError):
            await client.create_lead(lead)


async def test_bitrix24_update_lead_status_success():
    client = Bitrix24Client(webhook_url="https://b24.example.com/rest/1/xyz")
    with respx.mock:
        respx.post("https://b24.example.com/rest/1/xyz/crm.lead.update.json").mock(
            return_value=httpx.Response(200, json={"result": True})
        )
        await client.update_lead_status("7", "IN_PROCESS")
