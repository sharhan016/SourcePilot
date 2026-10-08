import json

import httpx
import pytest
from pydantic import ValidationError
from sourcepilot.providers.llm import build_openai, build_openrouter
from sourcepilot.providers.search import ExaSearchProvider, FirecrawlSearchProvider
from sourcepilot.providers.types import LLMMessage, ProductCandidate


@pytest.mark.asyncio
async def test_exa_adapter_normalizes_provider_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "test-key"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "exa-1",
                        "title": "Apple business store",
                        "url": "https://example.com/macbook",
                        "text": "MacBook Pro 14-inch",
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        results = await ExaSearchProvider("test-key", client).search("macbook")
    assert results[0].provider == "exa"
    assert str(results[0].url) == "https://example.com/macbook"


@pytest.mark.asyncio
async def test_firecrawl_adapter_normalizes_provider_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "title": "Reseller",
                        "url": "https://supplier.example/product",
                        "markdown": "In stock",
                        "metadata": {"statusCode": 200},
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        results = await FirecrawlSearchProvider("test-key", client).search("macbook")
    assert results[0].provider == "firecrawl"
    assert results[0].content == "In stock"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "factory,name", [(build_openai, "openai"), (build_openrouter, "openrouter")]
)
async def test_llm_provider_switching_uses_same_contract(factory, name) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "procurement-model"
        assert "temperature" not in payload
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok":true}'}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = factory("procurement-model", "key", client)
        response = await provider.generate([LLMMessage(role="user", content="hello")])
    assert provider.name == name
    assert response == '{"ok":true}'


def test_extracted_candidates_cannot_target_private_networks() -> None:
    with pytest.raises(ValidationError):
        ProductCandidate(
            supplier_name="Untrusted source",
            supplier_website="http://127.0.0.1/admin",
            product_name="Laptop",
            source_url="http://169.254.169.254/latest/meta-data",
        )
