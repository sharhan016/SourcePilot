import json
from collections.abc import Sequence

import httpx
from pydantic import ValidationError

from sourcepilot.providers.base import (
    Output,
    ProviderConfigurationError,
    ProviderResponseError,
    compact_schema,
)
from sourcepilot.providers.types import LLMMessage


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        name: str,
        model: str,
        api_key: str | None,
        base_url: str,
        client: httpx.AsyncClient,
    ) -> None:
        self.name = name
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = client

    async def generate(self, messages: Sequence[LLMMessage]) -> str:
        payload = await self._request(messages)
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderResponseError(f"{self.name} returned an invalid completion") from exc

    async def structured_output(
        self, messages: Sequence[LLMMessage], output_type: type[Output]
    ) -> Output:
        schema_instruction = LLMMessage(
            role="system",
            content=(
                "Return only valid JSON matching this schema. Never infer unavailable facts: "
                + json.dumps(compact_schema(output_type), separators=(",", ":"))
            ),
        )
        raw = await self.generate([schema_instruction, *messages])
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.removeprefix("json").strip()
        try:
            return output_type.model_validate_json(raw)
        except ValidationError as exc:
            raise ProviderResponseError(f"{self.name} returned invalid structured output") from exc

    async def _request(self, messages: Sequence[LLMMessage]) -> dict:
        if not self.api_key:
            raise ProviderConfigurationError(f"API key is required for {self.name}")
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [message.model_dump() for message in messages],
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ProviderResponseError(f"{self.name} returned a non-object response")
        return payload


def build_openai(model: str, key: str | None, client: httpx.AsyncClient):
    return OpenAICompatibleProvider(
        name="openai", model=model, api_key=key, base_url="https://api.openai.com/v1", client=client
    )


def build_openrouter(model: str, key: str | None, client: httpx.AsyncClient):
    return OpenAICompatibleProvider(
        name="openrouter",
        model=model,
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
        client=client,
    )
