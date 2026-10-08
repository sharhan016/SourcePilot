import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any, TypeVar

import httpx

from sourcepilot.providers.types import SearchDocument

Result = TypeVar("Result")
EventSink = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class ExecutionPolicy:
    timeout_seconds: float = 20
    max_retries: int = 2
    base_backoff_seconds: float = 0.1


class CapabilityExecutor:
    """Applies bounded concurrency, timeouts, retries, and observability to tool calls."""

    def __init__(self, policy: ExecutionPolicy, concurrency: int, event_sink: EventSink) -> None:
        self.policy = policy
        self.semaphore = asyncio.Semaphore(concurrency)
        self.event_sink = event_sink
        self._cache: dict[str, Any] = {}

    async def call(
        self,
        *,
        capability: str,
        provider: str,
        cache_key: str,
        operation: Callable[[], Awaitable[Result]],
    ) -> Result:
        if cache_key in self._cache:
            await self.event_sink(
                {
                    "capability": capability,
                    "provider": provider,
                    "status": "cache_hit",
                    "duration_ms": 0,
                }
            )
            return self._cache[cache_key]
        async with self.semaphore:
            last_error: Exception | None = None
            for attempt in range(self.policy.max_retries + 1):
                started = monotonic()
                try:
                    result = await asyncio.wait_for(
                        operation(), timeout=self.policy.timeout_seconds
                    )
                    duration = int((monotonic() - started) * 1000)
                    self._cache[cache_key] = result
                    await self.event_sink(
                        {
                            "capability": capability,
                            "provider": provider,
                            "status": "completed",
                            "duration_ms": duration,
                            "attempt": attempt + 1,
                        }
                    )
                    return result
                except (TimeoutError, ConnectionError, OSError, httpx.TransportError) as exc:
                    last_error = exc
                    await self.event_sink(
                        {
                            "capability": capability,
                            "provider": provider,
                            "status": "retrying" if attempt < self.policy.max_retries else "failed",
                            "duration_ms": int((monotonic() - started) * 1000),
                            "attempt": attempt + 1,
                            "error_type": type(exc).__name__,
                        }
                    )
                    if attempt < self.policy.max_retries:
                        await asyncio.sleep(self.policy.base_backoff_seconds * (2**attempt))
            assert last_error is not None
            raise last_error


class WebSearchCapability:
    def __init__(self, provider, executor: CapabilityExecutor) -> None:
        self.provider = provider
        self.executor = executor

    async def search(self, query: str, limit: int = 8) -> list[SearchDocument]:
        return await self.executor.call(
            capability="web_search",
            provider=self.provider.name,
            cache_key=f"search:{self.provider.name}:{query}:{limit}",
            operation=lambda: self.provider.search(query, limit),
        )
