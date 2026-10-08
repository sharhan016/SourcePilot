from collections.abc import Sequence
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from sourcepilot.providers.types import LLMMessage, SearchDocument

Output = TypeVar("Output", bound=BaseModel)


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, limit: int = 8) -> list[SearchDocument]: ...


class LLMProvider(Protocol):
    name: str
    model: str

    async def generate(self, messages: Sequence[LLMMessage]) -> str: ...

    async def structured_output(
        self, messages: Sequence[LLMMessage], output_type: type[Output]
    ) -> Output: ...


class ProviderConfigurationError(RuntimeError):
    pass


class ProviderResponseError(RuntimeError):
    pass


def compact_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    schema.pop("title", None)
    return schema
