from typing import Any

import pytest
from typing_extensions import override

from langchain_core.caches import RETURN_VAL_TYPE, BaseCache
from langchain_core.caches import InMemoryCache as ModelCache
from langchain_core.globals import set_llm_cache
from langchain_core.language_models import FakeListLLM


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("global_cache", [False, True])
@pytest.mark.parametrize("batched", [False, True])
@pytest.mark.parametrize(
    ("first_kwargs", "second_kwargs"),
    [
        ({"max_tokens": 16}, {"max_tokens": 1024}),
        ({"temperature": 0}, {"temperature": 0.7}),
    ],
)
async def test_cache_respects_invocation_kwargs(
    first_kwargs: dict[str, Any],
    second_kwargs: dict[str, Any],
    *,
    async_mode: bool,
    global_cache: bool,
    batched: bool,
) -> None:
    """Different generation options must not share a cached completion."""
    cache = ModelCache()
    if global_cache:
        set_llm_cache(cache)
    llm = FakeListLLM(
        cache=None if global_cache else cache,
        responses=["first response", "second response", "unexpected cache miss"],
    )

    async def invoke(kwargs: dict[str, Any]) -> str:
        bound = llm.bind(**kwargs)
        prompt = "Explain the returns policy."
        if batched:
            if async_mode:
                return (await bound.abatch([prompt]))[0]
            return bound.batch([prompt])[0]
        if async_mode:
            return await bound.ainvoke(prompt)
        return bound.invoke(prompt)

    try:
        assert await invoke(first_kwargs) == "first response"
        assert await invoke(second_kwargs) == "second response"
        assert await invoke(first_kwargs) == "first response"
        assert await invoke(second_kwargs) == "second response"
        assert llm.i == 2
    finally:
        if global_cache:
            set_llm_cache(None)


class InMemoryCache(BaseCache):
    """In-memory cache used for testing purposes."""

    def __init__(self) -> None:
        """Initialize with empty cache."""
        self._cache: dict[tuple[str, str], RETURN_VAL_TYPE] = {}

    def lookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        """Look up based on `prompt` and `llm_string`."""
        return self._cache.get((prompt, llm_string), None)

    def update(self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE) -> None:
        """Update cache based on `prompt` and `llm_string`."""
        self._cache[prompt, llm_string] = return_val

    @override
    def clear(self, **kwargs: Any) -> None:
        """Clear cache."""
        self._cache = {}

    def __len__(self) -> int:
        """Return the number of cached entries."""
        return len(self._cache)


async def test_local_cache_generate_async() -> None:
    global_cache = InMemoryCache()
    local_cache = InMemoryCache()
    try:
        set_llm_cache(global_cache)
        llm = FakeListLLM(cache=local_cache, responses=["foo", "bar"])
        output = await llm.agenerate(["foo"])
        assert output.generations[0][0].text == "foo"
        output = await llm.agenerate(["foo"])
        assert output.generations[0][0].text == "foo"
        assert global_cache._cache == {}
        assert len(local_cache._cache) == 1
    finally:
        set_llm_cache(None)


def test_local_cache_generate_sync() -> None:
    global_cache = InMemoryCache()
    local_cache = InMemoryCache()
    try:
        set_llm_cache(global_cache)
        llm = FakeListLLM(cache=local_cache, responses=["foo", "bar"])
        output = llm.generate(["foo"])
        assert output.generations[0][0].text == "foo"
        output = llm.generate(["foo"])
        assert output.generations[0][0].text == "foo"
        assert global_cache._cache == {}
        assert len(local_cache._cache) == 1
    finally:
        set_llm_cache(None)


class InMemoryCacheBad(BaseCache):
    """In-memory cache used for testing purposes."""

    def __init__(self) -> None:
        """Initialize with empty cache."""
        self._cache: dict[tuple[str, str], RETURN_VAL_TYPE] = {}

    def lookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        """Look up based on `prompt` and `llm_string`."""
        msg = "This code should not be triggered"
        raise NotImplementedError(msg)

    def update(self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE) -> None:
        """Update cache based on `prompt` and `llm_string`."""
        msg = "This code should not be triggered"
        raise NotImplementedError(msg)

    @override
    def clear(self, **kwargs: Any) -> None:
        """Clear cache."""
        self._cache = {}


def test_no_cache_generate_sync() -> None:
    global_cache = InMemoryCacheBad()
    try:
        set_llm_cache(global_cache)
        llm = FakeListLLM(cache=False, responses=["foo", "bar"])
        output = llm.generate(["foo"])
        assert output.generations[0][0].text == "foo"
        output = llm.generate(["foo"])
        assert output.generations[0][0].text == "bar"
        assert global_cache._cache == {}
    finally:
        set_llm_cache(None)


async def test_no_cache_generate_async() -> None:
    global_cache = InMemoryCacheBad()
    try:
        set_llm_cache(global_cache)
        llm = FakeListLLM(cache=False, responses=["foo", "bar"])
        output = await llm.agenerate(["foo"])
        assert output.generations[0][0].text == "foo"
        output = await llm.agenerate(["foo"])
        assert output.generations[0][0].text == "bar"
        assert global_cache._cache == {}
    finally:
        set_llm_cache(None)
