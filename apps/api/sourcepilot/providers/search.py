from typing import Any

import httpx

from sourcepilot.providers.base import ProviderConfigurationError, ProviderResponseError
from sourcepilot.providers.types import SearchDocument


class ExaSearchProvider:
    name = "exa"

    def __init__(self, api_key: str | None, client: httpx.AsyncClient) -> None:
        self.api_key = api_key
        self.client = client

    async def search(self, query: str, limit: int = 8) -> list[SearchDocument]:
        if not self.api_key:
            raise ProviderConfigurationError("EXA_API_KEY is required for Exa research")
        response = await self.client.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": self.api_key},
            json={
                "query": query,
                "numResults": limit,
                "contents": {"text": {"maxCharacters": 8000}},
            },
        )
        response.raise_for_status()
        results = response.json().get("results")
        if not isinstance(results, list):
            raise ProviderResponseError("Exa response did not contain a results list")
        return [self._normalize(item) for item in results if item.get("url")]

    def _normalize(self, item: dict[str, Any]) -> SearchDocument:
        return SearchDocument(
            title=item.get("title") or "Untitled source",
            url=item["url"],
            content=item.get("text") or item.get("summary") or "",
            provider=self.name,
            metadata={"published_date": item.get("publishedDate"), "exa_id": item.get("id")},
        )


class FirecrawlSearchProvider:
    name = "firecrawl"

    def __init__(self, api_key: str | None, client: httpx.AsyncClient) -> None:
        self.api_key = api_key
        self.client = client

    async def search(self, query: str, limit: int = 8) -> list[SearchDocument]:
        if not self.api_key:
            raise ProviderConfigurationError("FIRECRAWL_API_KEY is required for Firecrawl research")
        response = await self.client.post(
            "https://api.firecrawl.dev/v1/search",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"query": query, "limit": limit, "scrapeOptions": {"formats": ["markdown"]}},
        )
        response.raise_for_status()
        data = response.json().get("data")
        if not isinstance(data, list):
            raise ProviderResponseError("Firecrawl response did not contain a data list")
        return [self._normalize(item) for item in data if item.get("url")]

    def _normalize(self, item: dict[str, Any]) -> SearchDocument:
        metadata = item.get("metadata") or {}
        return SearchDocument(
            title=item.get("title") or metadata.get("title") or "Untitled source",
            url=item["url"],
            content=item.get("markdown") or item.get("description") or "",
            provider=self.name,
            metadata={"status_code": metadata.get("statusCode")},
        )


class SearchProviderRouter:
    def __init__(self, primary, fallbacks: list | None = None) -> None:
        self.primary = primary
        self.fallbacks = fallbacks or []
        self.name = primary.name

    async def search(self, query: str, limit: int = 8) -> list[SearchDocument]:
        errors: list[str] = []
        for provider in (self.primary, *self.fallbacks):
            try:
                results = await provider.search(query, limit)
                self.name = provider.name
                return results
            except (httpx.HTTPError, ProviderConfigurationError, ProviderResponseError) as exc:
                errors.append(f"{provider.name}: {type(exc).__name__}")
        raise ProviderResponseError("all search providers failed: " + ", ".join(errors))
